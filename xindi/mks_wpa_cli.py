"""Port of src/mks_wpa_cli.cpp - wifi control through the wpa_supplicant control socket.

The C buffers are byte strings here; values copied into the fixed size char
arrays of the result structures are truncated the same way.
"""

import os

from . import state as g
from . import ui
from .cpp import b2s, s2b, cstr, strtol, access, system, sleep, usleep
from .mks_log import MKSLOG, MKSLOG_RED, MKSLOG_YELLOW, MKSLOG_BLUE
from .wpa_ctrl import (wpa_ctrl_open, wpa_ctrl_request, wpa_ctrl_close, wpa_ctrl_attach,
                       wpa_ctrl_pending, wpa_ctrl_recv, WPS_EVENT_AP_AVAILABLE)

WPA_PATH = "/var/run/wpa_supplicant/wlan0"


def wpa_cli_msg_cb(msg, length):
    print(b2s(cstr(msg)))


def result_get(s, key, val_len):
    """Looks for ``key`` in ``s`` and returns the text after the following '='
    up to the end of the line (at most val_len - 1 bytes), or None."""
    pos = s.find(key)
    if pos == -1:
        return None
    pos = s.find(b"=", pos)
    if pos == -1:
        return None
    pos += 1
    out = bytearray()
    while pos < len(s) and s[pos:pos + 1] not in (b"\n", b"\0") and val_len > 1:
        out += s[pos:pos + 1]
        pos += 1
        val_len -= 1
    return bytes(out)


def mks_wifi_run_cmd_signal_poll(result):
    """Query the signal state of the connected AP (0 on success, -1 on failure)"""
    cmd = "SIGNAL_POLL"
    result.__dict__.update(g.mks_wifi_signal_poll_result_t().__dict__)
    ret, ack = mks_wifi_run_cmd(cmd, 1024)
    if ret < 0 or len(ack) == 0:
        print("Err: %s" % cmd)
        return -1
    if ack[:4] == b"FAIL":
        print("Err: %s (FAIL)" % cmd)
    result.ack = b2s(ack)
    for item, attr in ((b"RSSI", "rssi"), (b"LINKSPEED", "linkspeed"), (b"FREQUENCY", "frequency"), (b"NOISE", "noise")):
        val = result_get(ack, item, 512)
        if val is not None:
            setattr(result, attr, strtol(b2s(val), 10))
    return ret


def mks_wifi_run_cmd(cmd, size):
    """Returns (ret, reply) - reply is cut at the first NUL like result[*len] = 0 does."""
    ctrl = wpa_ctrl_open(WPA_PATH)
    if not ctrl:
        print("Err: wpa_ctrl_open()")
        return -1, b""
    ret, reply = wpa_ctrl_request(ctrl, cmd, size, None)
    wpa_ctrl_close(ctrl)
    return ret, cstr(reply)


def mks_wifi_run_cmd_status(result):
    cmd = "STATUS"
    result.__dict__.update(g.mks_wifi_status_result_t().__dict__)

    ret, ack = mks_wifi_run_cmd(cmd, 1024)

    if ret < 0 or len(ack) == 0:
        print("Err: %s" % cmd)
        return ret

    if ack[:4] == b"FAIL":
        print("Err: %s (FAIL)" % cmd)

    result.ack = b2s(ack)

    def get(source, key, size):
        val = result_get(source, key, size)
        return b2s(val) if val is not None else ""

    result.bssid = get(ack, b"bssid", 18)

    val = result_get(ack, b"freq", 512)
    if val is not None:
        result.freq = strtol(b2s(val), 10)

    nack = ack[5:]
    result.ssid = get(nack, b"ssid", 128)

    val = result_get(ack, b"id", 512)
    if val is not None:
        result.id = strtol(b2s(val), 10)

    result.mode = get(ack, b"mode", 16)
    result.pairwise_cipher = get(ack, b"pairwise_cipher", 16)
    result.group_cipher = get(ack, b"group_cipher", 16)
    result.key_mgmt = get(ack, b"key_mgmt", 16)
    result.wpa_state = get(ack, b"wpa_state", 32)
    result.ip_address = get(ack, b"ip_address", 18)
    g.wifi_ip_address = result.ip_address
    result.address = get(ack, b"address", 18)
    result.uuid = get(ack, b"uuid", 64)

    return ret


def test_wifi_run_cmd_signal():
    result = g.mks_wifi_signal_poll_result_t()
    mks_wifi_run_cmd_signal_poll(result)
    print("test_wifi_run_cmd_signal: ack: \n%s" % result.ack, end="")
    print("test_wifi_run_cmd_signal: rssi: %d" % result.rssi)
    print("test_wifi_run_cmd_signal: linkspeed: %d" % result.linkspeed)
    print("test_wifi_run_cmd_signal frequency: %d" % result.frequency)
    print("test_wifi_run_cmd_signal noise: %d" % result.noise)


def test_wifi_run_cmd_status():
    result = g.mks_wifi_status_result_t()
    mks_wifi_run_cmd_status(result)
    print("test_wifi_run_cmd_status: ack:\n%s" % result.ack, end="")
    for name in ("bssid", "freq", "ssid", "id", "mode", "pairwise_cipher", "group_cipher", "key_mgmt",
                 "wpa_state", "ip_address", "address", "uuid"):
        print("test_wifi_run_cmd_status: %s:%s" % (name, getattr(result, name)))


def mks_wifi_hdlevent_thread(arg=None):
    # 4.4.3 wifi fixes
    flag = 0
    t = 0
    path = WPA_PATH

    while True:
        if access(path) == 0:
            break
        usleep(100000)

    g.mon_conn = wpa_ctrl_open(path)

    if not g.mon_conn:
        MKSLOG_YELLOW("Failed to start the wpa monitor thread")
        return
    else:
        MKSLOG_YELLOW("mon_conn opened")
        wpa_ctrl_attach(g.mon_conn)

    while True:
        if wpa_ctrl_pending(g.mon_conn) > 0:
            ret, data = wpa_ctrl_recv(g.mon_conn, 4096 - 1)
            if ret == 0:
                buf = cstr(data)
                MKSLOG_YELLOW("Got wpa event: \n%s", b2s(buf))
                if b"CTRL-EVENT-SCAN-RESULTS" in buf:
                    MKSLOG_BLUE("Scan results are available")
                elif b"CTRL-EVENT-DISCONNECTED" in buf:
                    MKSLOG_BLUE("Wifi disconnected")
                    MKSLOG_BLUE("Trying to connect to the new wifi")
                    g.wlan_state_str = "disconnected"
                    mks_enable_network()
                    flag = 0
                    t = 0
                elif b"CTRL-EVENT-CONNECTED" in buf:
                    MKSLOG_BLUE("Wifi connected")
                    # 4.4.1 CLL wifi refresh fix
                    mks_enable_network()
                    usleep(10000)
                    g.wlan_state_str = "connected"
                    if g.current_page_id == ui.TJC_PAGE_WIFI_CONNECT:
                        ui.page_to(ui.TJC_PAGE_WIFI_SUCCESS)
                elif s2b(WPS_EVENT_AP_AVAILABLE) in buf:
                    MKSLOG("Available WPS AP found in scan results.")
                    # 4.4.3 CLL wifi fix
                    if g.current_page_id == ui.TJC_PAGE_WIFI_CONNECT and flag == 0:
                        # on the connect page with flag 0: select the network and set the special flag value 2
                        system("wpa_cli select_network 0")
                        flag = 2
                elif b"pre-shared key may be incorrect" in buf:
                    if g.current_page_id == ui.TJC_PAGE_WIFI_CONNECT:
                        ui.page_to(ui.TJC_PAGE_WIFI_FAILED)
                # 4.4.3 CLL wifi refresh fix
                elif b"CONN_FAILED" in buf or b"timed out" in buf or b"WRONG_KEY" in buf:
                    if g.current_page_id == ui.TJC_PAGE_WIFI_CONNECT:
                        ui.page_to(ui.TJC_PAGE_WIFI_FAILED)
                        flag = 0
                        t = 0
                elif b"Associated with" in buf:
                    MKSLOG_RED("Associated")
                elif b"NETWORK-NOT-FOUND" in buf and g.current_page_id == ui.TJC_PAGE_WIFI_CONNECT and flag == 2:
                    # 4.4.3 CLL wifi fix
                    if t < 3:
                        t += 1
                    elif t == 3:
                        ui.page_to(ui.TJC_PAGE_WIFI_FAILED)
                        system("wpa_cli disable_network 0")
                        flag = 0
                        t = 0
        else:
            usleep(10000)


def mks_wpa_scan_scanresults():
    from .MakerbaseWiFi import parse_scan_results
    # 4.4.1 CLL wifi refresh fix
    g.ctrl_conn = wpa_ctrl_open(WPA_PATH)

    if not g.ctrl_conn:
        print("Open wpa control interfaces failed!")
        return -3
    else:
        print("Successful!")

    ret, reply = wpa_ctrl_request(g.ctrl_conn, "SCAN", 4096 - 1, None)
    if ret == -2:
        print("Command timed out.")
        return ret
    elif ret < 0:
        print("Command failed.")
        return ret
    elif ret == 0:
        replyBuff = cstr(reply)
        print("Received message: \n%s" % b2s(replyBuff))
        if replyBuff[:2] == b"OK":
            MKSLOG_YELLOW("Scan result: %s", b2s(replyBuff))
            sleep(2)

    ret, reply = wpa_ctrl_request(g.ctrl_conn, "SCAN_RESULTS", 4096 - 1, None)

    if ret == -2:
        MKSLOG_RED("Command timed out.")
        return ret
    elif ret < 0:
        MKSLOG_RED("Command failed.")
        return ret
    elif ret == 0:
        replyBuff = cstr(reply)
        g.str_scan_results = b2s(replyBuff)
        MKSLOG("%s", g.str_scan_results)
        parse_scan_results(replyBuff)

    return ret


def mks_set_ssid(ssid):
    """ssid: bytes"""
    # 4.4.1 CLL wifi refresh fix
    g.ctrl_conn = wpa_ctrl_open(WPA_PATH)

    if not g.ctrl_conn:
        print("Open wpa control interfaces failed!")
        return -3
    else:
        print("Successful!")

    # wpa_ctrl_request SET_NETWORK ssid  (snprintf(cmd, sizeof(cmd) - 1, ...) -> at most 62 bytes)
    cmd = (b"SET_NETWORK 0 ssid \"" + ssid + b"\"")[:62]
    MKSLOG_RED("Sending command: %s", b2s(cmd))
    ret, reply = wpa_ctrl_request(g.ctrl_conn, cmd, 2048 - 1, None)
    if ret == -2:
        MKSLOG_RED("Command timed out.")
        return ret
    elif ret < 0:
        MKSLOG_RED("Command failed.")
        return ret
    elif ret == 0:
        replyBuff = cstr(reply)
        MKSLOG_YELLOW("Reply: %s", b2s(replyBuff))
        if b"OK" in replyBuff:
            return ret
    return ret


def mks_set_psk(psk):
    """psk: bytes"""
    # 4.4.1 CLL wifi refresh fix
    g.ctrl_conn = wpa_ctrl_open(WPA_PATH)

    if not g.ctrl_conn:
        print("Open wpa control interfaces failed!")
        return -3
    else:
        print("Successful!")

    # wpa_ctrl_request SET_NETWORK psk
    cmd = b"SET_NETWORK 0 psk \"" + psk + b"\""
    MKSLOG_RED("Sending command: %s", b2s(cmd))
    replyBuff = b""
    ret, reply = wpa_ctrl_request(g.ctrl_conn, cmd, 2048 - 1, None)
    if ret == 0:
        replyBuff = cstr(reply)
        MKSLOG_YELLOW("Reply: %s", b2s(replyBuff))
        if b"OK" in replyBuff:
            system("ifconfig wlan0 down")
            system("ifconfig wlan0 up")
            # 4.4.3 CLL wifi fix
            system("wpa_cli reassociate")
            if mks_enable_network() == -2 and g.current_page_id == ui.TJC_PAGE_WIFI_CONNECT:
                ui.page_to(ui.TJC_PAGE_WIFI_FAILED)
            else:
                MKSLOG_RED("Check passed")
            return ret
    else:
        # NOTE: the original has "else if (ret = -2)" (assignment), so this branch
        # is always taken for any error and the function returns -2.
        ret = -2
        MKSLOG_RED("Command timed out. %s", b2s(replyBuff))

    return ret


def mks_disable_network():
    if not g.ctrl_conn:
        MKSLOG_RED("Open wpa control interfaces failed!")
        return -3
    else:
        MKSLOG_RED("Successful!")

    ret, reply = wpa_ctrl_request(g.ctrl_conn, "DISABLE_NETWORK 0", 4096 - 1, wpa_cli_msg_cb)
    if ret == -2:
        MKSLOG_RED("Command timed out.")
        return ret
    elif ret < 0:
        MKSLOG_RED("Command failed.")
    elif ret == 0:
        replyBuff = cstr(reply)
        MKSLOG_YELLOW("Reply: %s", b2s(replyBuff))
        if b"OK" in replyBuff:
            MKSLOG_RED("Enabling the network")
    return ret


def mks_enable_network():
    # 4.4.1 CLL wifi refresh fix
    g.ctrl_conn = wpa_ctrl_open(WPA_PATH)

    if not g.ctrl_conn:
        MKSLOG_RED("Open wpa control interfaces failed!")
        return -3
    else:
        MKSLOG_RED("Successful!")

    ret, reply = wpa_ctrl_request(g.ctrl_conn, "ENABLE_NETWORK 0", 4096 - 1, None)
    if ret == -2:
        MKSLOG_RED("Command timed out.")
        return ret
    elif ret < 0:
        MKSLOG_RED("Command failed.")
        return ret
    elif ret == 0:
        MKSLOG_YELLOW("Reply: %s", b2s(cstr(reply)))
    return ret


def mks_save_config():
    if not g.ctrl_conn:
        MKSLOG_RED("Open wpa control interfaces failed!")
        return -3
    else:
        MKSLOG_RED("Successful!")

    ret, reply = wpa_ctrl_request(g.ctrl_conn, "SAVE_CONFIG", 2048 - 1, None)
    if ret == -2:
        MKSLOG_RED("Command timed out.")
        return ret
    elif ret < 0:
        MKSLOG_RED("Command failed.")
    elif ret == 0:
        replyBuff = cstr(reply)
        MKSLOG_YELLOW("Reply: %s", b2s(replyBuff))
        if b"OK" in replyBuff:
            MKSLOG_YELLOW("Wifi configuration saved")
            mks_wpa_get_status()       # get the status here
            system("sync")
            if ui.TJC_PAGE_WIFI_SAVING == g.current_page_id:
                sleep(3)
                g.page_wifi_list_ssid_button_enabled[0] = False
                g.page_wifi_list_ssid_button_enabled[1] = False
                g.page_wifi_list_ssid_button_enabled[2] = False
                g.page_wifi_list_ssid_button_enabled[3] = False
                g.page_wifi_ssid_list_pages = 0
                g.page_wifi_current_pages = 0
                from . import event
                event.go_to_network()       # 4.4.22 (was page_to(TJC_PAGE_WIFI_LIST))
    return ret


def mks_wpa_cli_open_connection():
    g.ctrl_conn = wpa_ctrl_open(WPA_PATH)
    # 4.4.1 CLL wifi refresh fix
    if g.ctrl_conn:
        g.mks_wpa_cli_connected = True
        MKSLOG_RED("wpa connection opened")
        return 0
    else:
        g.mks_wpa_cli_connected = False
        return -1


def mks_wpa_cli_close_connection():
    wpa_ctrl_close(g.ctrl_conn)
    g.ctrl_conn = None
    g.mks_wpa_cli_connected = False
    MKSLOG_RED("wpa connection closed")
    return 0


def mks_wpa_scan():
    if not g.ctrl_conn:
        MKSLOG_RED("Failed to open the wpa control interface!\n")
        return -3
    else:
        MKSLOG_BLUE("Successful")

    ret, reply = wpa_ctrl_request(g.ctrl_conn, "SCAN", 4096 - 1, wpa_cli_msg_cb)
    if ret == -2:
        MKSLOG_RED("Command timed out.")
    elif ret < 0:
        MKSLOG_RED("Command failed.")
    elif ret == 0:
        replyBuff = cstr(reply)
        MKSLOG_RED("Received message: \n%s\n", b2s(replyBuff))
        if replyBuff[:2] == b"OK":
            MKSLOG_YELLOW("Result: %s", b2s(replyBuff))
    return ret


def mks_wpa_scan_results():
    if not g.ctrl_conn:
        MKSLOG_RED("Failed to open the wpa control interface!\n")
        return -3
    else:
        MKSLOG_BLUE("Successful")

    ret, reply = wpa_ctrl_request(g.ctrl_conn, "SCAN_RESULTS", 4096 - 1, wpa_cli_msg_cb)
    if ret == -2:
        MKSLOG_RED("Command timed out.")
    elif ret < 0:
        MKSLOG_RED("Command failed.")
    elif ret == 0:
        MKSLOG_RED("Received:\n%s", b2s(cstr(reply)))
    return ret


def mks_wpa_get_status():
    if not g.ctrl_conn:
        print("Open wpa control interfaces failed!")
        return -3
    else:
        print("Successful!")

    ret, reply = wpa_ctrl_request(g.ctrl_conn, "STATUS", 512 - 1, None)
    if ret == -2:
        print("Command timed out.")
        return ret
    elif ret < 0:
        print("Command failed.")
        return ret
    elif ret == 0:
        MKSLOG_YELLOW("Reply:\n%s", b2s(cstr(reply)))
    return ret


def mks_parse_status(status):
    status.__dict__.update(g.mks_wifi_status_t().__dict__)
    src = s2b(g.mks_wifi_status)

    def get(key, size):
        val = result_get(src, key, size)
        return b2s(val) if val is not None else ""

    status.bssid = get(b"bssid", 18)
    status.wpa_state = get(b"wpa_state", 32)
    status.ip_address = get(b"ip_address", 18)
    status.address = get(b"address", 18)
    return 0
