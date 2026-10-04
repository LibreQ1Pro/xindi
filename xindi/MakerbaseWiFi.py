"""Port of src/MakerbaseWiFi.cpp - wifi scan result handling."""

import re

from . import state as g
from .cpp import b2s, s2b, cstr, access, atoi
from .mks_log import MKSLOG, MKSLOG_RED, MKSLOG_YELLOW, cout
from .MakerbaseShell import execute_cmd


def set_page_wifi_ssid_list(pages):
    g.page_wifi_ssid_list[0] = ""
    g.page_wifi_ssid_list[1] = ""
    g.page_wifi_ssid_list[2] = ""
    g.page_wifi_ssid_list[3] = ""
    g.page_wifi_ssid_list[4] = ""

    it = 0
    for i in range(pages * 5):
        it += 1

    for k in range(5):
        if it < len(g.ssid_list):
            g.page_wifi_ssid_list[k] = g.ssid_list[it]
            it += 1

    for j in range(5):
        cout(g.page_wifi_ssid_list[j])


def get_ssid_list_pages():
    """4.4.1 CLL wifi refresh fix"""
    if len(g.ssid_list) % 5 == 0:
        g.page_wifi_ssid_list_pages = len(g.ssid_list) // 5
    else:
        g.page_wifi_ssid_list_pages = len(g.ssid_list) // 5 + 1

    if g.page_wifi_ssid_list_pages > 5:
        g.page_wifi_ssid_list_pages = 5


def get_wlan0_status():
    from .mks_wpa_cli import mks_wifi_run_cmd_status
    mks_wifi_run_cmd_status(g.status_result)


def detected_wlan0():
    if access("/var/run/wpa_supplicant/wlan0") == 0:
        return True
    else:
        return False


def split_scan_result(result):
    """Unused in the program (replaced by parse_scan_results)."""
    g.result_list = []
    g.level_list = []
    g.ssid_list = []

    delimiter = "\n"
    while True:
        pos = result.find(delimiter)
        if pos == -1:
            break
        token = result[:pos]
        g.result_list.append(token)
        result = result[pos + len(delimiter):]

    for i in range(1, len(g.result_list)):
        fields = s2b(g.result_list[i]).split()
        # sscanf(sub_result, "%s \t %s \t %s \t %s \t %s", ...) == 5
        if len(fields) >= 5:
            re_ = printf_decode(64, fields[4])
            g.level_list.append(atoi(b2s(fields[2])))
            if re_[:1] in (b"", b"\x00"):
                MKSLOG_YELLOW("The scanned ssid is \\0")
            else:
                g.ssid_list.append(b2s(cstr(re_)))

    for j in range(len(g.ssid_list)):
        if g.current_connected_ssid_name == g.ssid_list[j]:
            temp = g.ssid_list[j]
            g.ssid_list[j] = g.ssid_list[0]
            g.ssid_list[0] = temp
    for k in range(len(g.ssid_list)):
        MKSLOG_RED("%s", g.ssid_list[k])


def rescan():
    MKSLOG("wpa_cli SCAN")
    return wpa_cli("SCAN")


def save_wpa_conf():
    MKSLOG("Saving WPA config")
    return wpa_cli("SAVE_CONFIG")


def wpa_cli(command):
    cmd = "wpa_cli " + command
    return execute_cmd(cmd)


_CHANNELS = {
    2412: "2.4GHz 1", 2417: "2.4GHz 2", 2422: "2.4GHz 3", 2427: "2.4GHz 4", 2432: "2.4GHz 5",
    2437: "2.4GHz 6", 2442: "2.4GHz 7", 2447: "2.4GHz 8", 2452: "2.4GHz 9", 2457: "2.4GHz 10",
    2462: "2.4GHz 11", 2467: "2.4GHz 12", 2472: "2.4GHz 13", 2484: "2.4GHz 14",
    5035: "5GHz 7", 5040: "5GHz 8", 5045: "5GHz 9", 5055: "5GHz 11", 5060: "5GHz 12", 5080: "5GHz 16",
    5170: "5GHz 34", 5180: "5GHz 36", 5190: "5GHz 38", 5200: "5GHz 40", 5210: "5GHz 42", 5220: "5GHz 44",
    5230: "5GHz 46", 5240: "5GHz 48", 5260: "5GHz 52", 5280: "5GHz 56", 5300: "5GHz 60", 5320: "5GHz 64",
    5500: "5GHz 100", 5560: "5GHz 112", 5580: "5GHz 116", 5600: "5GHz 120", 5620: "5GHz 124",
    5640: "5GHz 128", 5660: "5GHz 132", 5680: "5GHz 136", 5700: "5GHz 140", 5720: "5GHz 144",
    5745: "5GHz 149", 5765: "5GHz 153", 5785: "5GHz 157", 5805: "5GHz 161", 5825: "5GHz 165",
    4915: "5GHz 183", 4920: "5GHz 184", 4925: "5GHz 185", 4935: "5GHz 187", 4940: "5GHz 188",
    4945: "5GHz 189", 4960: "5GHz 192", 4980: "5GHz 196",
}


def lookup(freq):
    """WifiChannels"""
    return _CHANNELS.get(freq, "")


def hex2num(c):
    if 0x30 <= c <= 0x39:
        return c - 0x30
    if 0x61 <= c <= 0x66:
        return c - 0x61 + 10
    if 0x41 <= c <= 0x46:
        return c - 0x41 + 10
    return -1


def hex2byte(s, pos):
    a = hex2num(s[pos]) if pos < len(s) else -1
    if a < 0:
        return -1
    b = hex2num(s[pos + 1]) if pos + 1 < len(s) else -1
    if b < 0:
        return -1
    return (a << 4) | b


def printf_decode(maxlen, s):
    """Decodes wpa_supplicant's printf escaped string ``s`` (bytes) into at most
    maxlen - 1 bytes (the C version also NUL terminates the buffer)."""
    buf = bytearray()
    pos = 0
    n = len(s)
    while pos < n and s[pos] != 0:
        if len(buf) + 1 >= maxlen:
            break
        c = s[pos]
        if c == 0x5C:   # '\\'
            pos += 1
            c = s[pos] if pos < n else 0
            if c == 0x5C:
                buf.append(0x5C)
                pos += 1
            elif c == 0x22:     # '"'
                buf.append(0x22)
                pos += 1
            elif c == 0x6E:     # 'n'
                buf.append(0x0A)
                pos += 1
            elif c == 0x72:     # 'r'
                buf.append(0x0D)
                pos += 1
            elif c == 0x74:     # 't'
                buf.append(0x09)
                pos += 1
            elif c == 0x65:     # 'e'
                buf.append(0x1B)
                pos += 1
            elif c == 0x78:     # 'x'
                pos += 1
                val = hex2byte(s, pos)
                if val < 0:
                    val = hex2num(s[pos]) if pos < n else -1
                    if val < 0:
                        continue
                    buf.append(val)
                    pos += 1
                else:
                    buf.append(val)
                    pos += 2
            elif 0x30 <= c <= 0x37:     # '0' .. '7'
                val = c - 0x30
                pos += 1
                if pos < n and 0x30 <= s[pos] <= 0x37:
                    val = val * 8 + (s[pos] - 0x30)
                    pos += 1
                if pos < n and 0x30 <= s[pos] <= 0x37:
                    val = val * 8 + (s[pos] - 0x30)
                    pos += 1
                buf.append(val & 0xFF)
            else:
                pass
        else:
            buf.append(c)
            pos += 1
    return bytes(buf)


def parse_scan_results(scan_results):
    """scan_results: bytes (SCAN_RESULTS reply)"""
    g.result_list = []
    g.level_list = []
    g.ssid_list = []

    buffer = cstr(scan_results)[:4095]
    # strtok(buffer, "\n") skips empty lines
    lines = [l for l in buffer.split(b"\n") if l][:128]

    for i in range(1, len(lines)):
        ssid_line = lines[i][:255]
        # strtok(lines[i], " \t")
        fields = []
        ssid_line_index = 0
        for m in re.finditer(rb"[^ \t]+", lines[i]):
            if 4 == len(fields):
                ssid_line_index = m.start()
            fields.append(m.group(0))

        if len(fields) < 5:
            print("Invalid scan result: %s" % b2s(lines[i]))
            continue
        else:
            ssid_name = printf_decode(192, ssid_line[ssid_line_index:])
            if ssid_name[:1] in (b"", b"\x00"):
                pass
            else:
                g.ssid_list.append(b2s(cstr(ssid_name)))

    for j in range(len(g.ssid_list)):
        if g.current_connected_ssid_name == g.ssid_list[j]:
            temp = g.ssid_list[j]
            g.ssid_list[j] = g.ssid_list[0]
            g.ssid_list[0] = temp

    for k in range(len(g.ssid_list)):
        MKSLOG_RED("%s", g.ssid_list[k])

    return 0
