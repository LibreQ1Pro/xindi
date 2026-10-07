"""The screen pages that manage the NetworkManager connections (added to the screen firmware, see
display_firmware/tools/add_network_pages.py): saved networks, one network, "forget" confirmation, the state of the
interfaces, and the keyboard modes (password of a scanned / saved network, hidden network)."""

from . import state as g
from . import pageids as ids
from . import pics
from . import ui
from . import network
from . import netstrings
from .cpp import b2s, sleep, pthread_create
from .mks_log import MKSLOG, MKSLOG_BLUE
from .send_msg import send_cmd_txt, send_cmd_picc, send_cmd_picc2, send_cmd_raw

ROWS = 5

# modes of the keyboard page: what the text typed on it is
KB_PSK_SCANNED = 1      # password of the network chosen in the scan list (g.net.get_wifi_name)
KB_PSK_SAVED = 2        # new password of the saved connection S.sel
KB_HIDDEN_SSID = 3      # name of a hidden network
KB_HIDDEN_PSK = 4       # its password (empty = open network)


class S:
    saved = []          # saved wifi connections, see network.saved_wifi()
    page = 0
    enabled = [False] * ROWS
    sel = None          # the connection of the detail page
    hidden_ssid = ""
    kbmode = KB_PSK_SCANNED


def tr(key):
    """The text ``key`` of netstrings in the language of the screen."""
    from . import settings, wifi_ui
    settings.get_language_status()
    return netstrings.text(key, g.config.language_status)


def _clip(text, length):
    """Text for a screen string: no quotes / control characters, at most ``length`` characters."""
    text = "".join(c if c >= " " and c != '"' else "'" for c in text if c >= " ")
    return text if len(text) <= length else text[:length - 2] + ".."


def _txt(obj, text):
    send_cmd_txt(g.tty_fd, obj, text)


def _lines(*lines):
    return "\\r".join(line for line in lines if line)       # "\r" is the line break of the screen


# ---------------------------------------------------------------------------------------------- saved networks
def open_saved():
    S.saved = network.saved_wifi()
    S.page = 0
    ui.page_to(ids.NET_SAVED)
    show_saved()


def _pages():
    return (len(S.saved) + ROWS - 1) // ROWS


def show_saved():
    pages = _pages()
    for i in range(ROWS):
        index = S.page * ROWS + i
        item = S.saved[index] if index < len(S.saved) else None
        row = "row" + str(i + 1)
        _txt(row + "_txt", _clip(item["ssid"], 24) if item else "")
        if item and item["active"]:
            send_cmd_picc(g.tty_fd, row, pics.rows_check)
            send_cmd_picc2(g.tty_fd, row, pics.rows_check_press)
        elif item:
            send_cmd_picc(g.tty_fd, row, pics.rows_lock)
            send_cmd_picc2(g.tty_fd, row, pics.bg_settings_press)
        else:
            send_cmd_picc(g.tty_fd, row, pics.bg_settings_panel)
            send_cmd_picc2(g.tty_fd, row, pics.bg_settings_panel)
        S.enabled[i] = item is not None
    first = pages <= 1 or S.page == 0
    last = pages <= 1 or S.page == pages - 1
    for button, off in (("prev_btn", first), ("next_btn", last)):
        send_cmd_picc(g.tty_fd, button, "126" if off else "125")
        send_cmd_picc2(g.tty_fd, button, "123" if off else "124")


def saved_clicked(widget_id):
    if widget_id < ROWS:
        index = S.page * ROWS + widget_id
        if S.enabled[widget_id] and index < len(S.saved):
            open_detail(S.saved[index])
    elif widget_id == 5 and S.page > 0:         # previous
        S.page -= 1
        show_saved()
    elif widget_id == 6 and S.page < _pages() - 1:      # next
        S.page += 1
        show_saved()
    elif widget_id == 23:                       # back
        from . import settings, wifi_ui
        wifi_ui.go_to_network()


# ---------------------------------------------------------------------------------------------- one network
def open_detail(item):
    S.sel = item
    ui.page_to(ids.NET_DETAIL)
    show_detail()


def _reload_selected():
    for item in network.saved_wifi():
        if item["uuid"] == S.sel["uuid"]:
            S.sel = item
            return True
    return False


def show_detail():
    item = S.sel
    state = tr("saved")
    if item["active"]:
        ip = network.device_report("wifi")["ip"]
        state = tr("connected") + (", " + ip if ip else "")
    _txt("ssid_txt", _clip(item["ssid"], 24))
    _txt("status_txt", _clip(state, 30))
    _txt("connect_btn", tr("disconnect") if item["active"] else tr("connect"))
    _txt("auto_btn", tr("autoconnect") + (tr("on") if item["autoconnect"] else tr("off")))


def detail_clicked(widget_id):
    item = S.sel
    if widget_id == 1:
        if item["active"]:
            network.disconnect_wifi()
            _reload_selected()
            show_detail()
        else:
            ui.page_to(ids.WIFI_CONNECT)
            network.start_connect_saved(item["uuid"], item["ssid"])
    elif widget_id == 2:
        open_keyboard(KB_PSK_SAVED, 8, item["ssid"])
    elif widget_id == 3:
        network.set_autoconnect(item["uuid"], not item["autoconnect"])
        _reload_selected()
        show_detail()
    elif widget_id == 4:
        ui.page_to(ids.NET_CONFIRM)
        _txt("msg", _lines(tr("forget"), '"' + _clip(item["ssid"], 22) + '"?',
                            tr("saved_password"), tr("will_be_deleted")))
    elif widget_id == 23:
        open_saved()


def confirm_clicked(widget_id):
    if widget_id == 1:
        network.forget(S.sel["uuid"])
        open_saved()
    elif widget_id in (0, 23):
        if _reload_selected():
            open_detail(S.sel)
        else:
            open_saved()


# ---------------------------------------------------------------------------------------------- interfaces
def open_info():
    ui.page_to(ids.NET_INFO)
    show_info()


def _state_word(report, radio=True):
    if report["name"] is None:
        return tr("no_adapter")
    if not radio:
        return tr("off_state")
    return {"connected": tr("connected"),
            "unavailable": tr("unavailable")}.get(report["state"], tr("disconnected"))


def show_info():
    wifi = network.device_report("wifi")
    radio = network.wifi_radio()
    lan = network.device_report("ethernet")
    gw = tr("gateway")
    wifi_lines = ["Wi-Fi  " + (wifi["name"] or "-"), _state_word(wifi, radio)]
    if wifi["state"] == "connected":
        wifi_lines += ["SSID  " + _clip(wifi["ssid"], 18), "IP  " + wifi["ip"], gw + "  " + wifi["gateway"]]
    lan_lines = ["LAN  " + (lan["name"] or "-"), _state_word(lan)]
    if lan["state"] == "connected":
        lan_lines += ["IP  " + lan["ip"], gw + "  " + lan["gateway"], "MAC  " + lan["mac"]]
    _txt("wifi_txt", _lines(*[_clip(line, 28) for line in wifi_lines]))
    _txt("lan_txt", _lines(*[_clip(line, 28) for line in lan_lines]))
    _txt("radio_btn", "Wi-Fi: " + (tr("on") if radio else tr("off")))


def _toggle_thread(arg):
    network.set_wifi_radio(not network.wifi_radio())
    sleep(2)        # NetworkManager needs a moment to bring the radio up / down
    if g.screen.page == ids.NET_INFO:
        show_info()


def info_clicked(widget_id):
    if widget_id == 1:          # the wired link is never switched: LAN and Wi-Fi are used together
        pthread_create(_toggle_thread, None)
    elif widget_id == 23:
        from . import settings, wifi_ui
        wifi_ui.refresh_ip_address()


# ---------------------------------------------------------------------------------------------- keyboard
def open_keyboard(mode, minimum, title):
    """Opens the keyboard page; the screen sends back ``0x70 mode row text`` when the text is accepted.
    The title of the page is the name of the network (``g.net.get_wifi_name``)."""
    S.kbmode = mode
    g.net.get_wifi_name = title
    g.screen.printing_wifi_keyboard_enabled = True
    send_cmd_raw(g.tty_fd, "kbmode=%d" % mode)
    send_cmd_raw(g.tty_fd, "kbmin=%d" % minimum)
    ui.page_to(ids.WIFI_KB)


def open_hidden():
    S.hidden_ssid = ""
    open_keyboard(KB_HIDDEN_SSID, 1, tr("network_name"))


def keyboard_back():
    g.screen.printing_wifi_keyboard_enabled = False
    if S.kbmode == KB_PSK_SAVED and S.sel is not None:
        open_detail(S.sel)
    else:
        from . import settings, wifi_ui
        wifi_ui.go_to_network()


def keyboard_text(mode, text):
    """The text accepted on the keyboard page (str)."""
    from . import settings, wifi_ui
    MKSLOG_BLUE("Keyboard mode %d", mode)
    g.screen.printing_wifi_keyboard_enabled = False
    if mode == KB_PSK_SCANNED:
        ui.page_to(ids.WIFI_CONNECT)
        wifi_ui.print_ssid_psk(text.encode("utf-8"))
    elif mode == KB_PSK_SAVED and S.sel is not None:
        ui.page_to(ids.WIFI_CONNECT)
        network.start_connect_saved(S.sel["uuid"], S.sel["ssid"], text)
    elif mode == KB_HIDDEN_SSID:
        S.hidden_ssid = text
        open_keyboard(KB_HIDDEN_PSK, 0, text)
    elif mode == KB_HIDDEN_PSK:
        ui.page_to(ids.WIFI_CONNECT)
        network.mks_start_connect(S.hidden_ssid, text, hidden=True)
    else:
        MKSLOG("Unknown keyboard mode %d", mode)
