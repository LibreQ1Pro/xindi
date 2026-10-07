"""Port of src/ui.cpp / include/ui.h - handling of the events sent by the TJC screen.

Page ids and widget ids correspond to the pages / components of the screen
project UI/MATE_272_480.HMI.

NOTE: the port follows QIDI's xindi V4.4.22 binary (there are no sources of it)
for the screen firmware V4.4.24: page 81 became the network page, pages 94 and
95 were added, pages 96..109 belong to QIDI Link (QIDI's cloud), which the port
does not implement: their events are ignored and the network page keeps them
disabled ("LAN only").
"""

from . import state as g
from . import pageids as ids
from .cpp import b2s, cstr, to_string
from .mks_log import MKSLOG, MKSLOG_BLUE, MKSLOG_RED, cout
from .screen_tx import send_cmd_page, send_cmd_val


def parse_cmd_msg_from_tjc_screen(cmd):
    """``cmd`` is the 4096 byte read buffer (zero padded) of the main loop."""
    g.screen.event_id = cmd[0]
    MKSLOG_BLUE("#########################%s", b2s(cstr(cmd)))
    MKSLOG_RED("0x%x", cmd[0])
    MKSLOG_RED("0x%x", cmd[1])
    MKSLOG_RED("0x%x", cmd[2])
    MKSLOG_RED("0x%x", cmd[3])
    event_id = g.screen.event_id
    if event_id == 0x03:
        pass        # error while reading the screen firmware data, screen recovery mode
    elif event_id == 0x05:
        g.update.get_0x05 = True
        cout("Ready to send data")
        MKSLOG_RED("0x%x", cmd[0])
        # receiving 0x05 means the screen data can be sent
    elif event_id == 0x1a:
        cout("Invalid variable name")
    elif event_id == 0x24:
        g.update.get_0x24 = True
    elif event_id == 0x65:
        g.screen.page_id = cmd[1]
        g.screen.widget_id = cmd[2]
        g.screen.type_id = cmd[3]
        from . import clicks
        clicks.handle(g.screen.page_id, g.screen.widget_id, g.screen.type_id)
    elif event_id in (0x66, 0x67, 0x68):
        pass
    elif event_id == 0x70:
        MKSLOG_RED("0x%x", event_id)
        tjc_event_keyboard(cmd)
    elif event_id == 0x71:
        g.screen.page_id = cmd[1]
        tjc_event_setted_handler(cmd[1], cmd[2], cmd[3], cmd[4])
    elif event_id in (0x86, 0x87, 0x88, 0x89):
        MKSLOG_RED("0x%x", event_id)
        if event_id == 0x88:        # the screen has just powered up: it knows nothing of what the host sent before
            send_ui_version()
            if g.screen.page != ids.LOGO:
                page_to(g.screen.page)
    elif event_id == 0x91:
        g.screen.page = ids.LOGO
        page_to(ids.UPDATE_SUCCESS)
    elif event_id == 0xfd:
        g.update.get_0xfd = True
        MKSLOG_RED("0x%x 0x%x 0x%x 0x%x ", cmd[0], cmd[1], cmd[2], cmd[3])
    elif event_id == 0xfe:
        g.update.get_0xfe = True
        MKSLOG_RED("0x%x 0x%x 0x%x 0x%x ", cmd[0], cmd[1], cmd[2], cmd[3])
    elif event_id == 0xff:
        MKSLOG_RED("0x%x", event_id)
    elif event_id == 0x04:
        g.update.get_0x04 = True
        MKSLOG_RED("0x%x", cmd[0])
    elif event_id == 0x06:
        g.update.get_0x06 = True


# The version of the port as semver. The screen cannot compare semver, so it gets major * 10000 + minor * 100 + patch
# (1.7.10 -> 10710, 0.1.0 -> 100); the main page of the screen firmware shows a warning when it differs from the number
# it was built for (display_firmware/pages/main.json). The screen forgets it on every power-up, so it is sent again
# whenever the main page is opened and when the screen reports a start.
VERSION = (0, 1, 0)


def version_number(version):
    """The number the screen compares: major (0-99), minor (0-99), patch (0-99)."""
    major, minor, patch = version
    if not (0 <= major <= 99 and 0 <= minor <= 99 and 0 <= patch <= 99):
        raise ValueError("version %r does not fit the screen: every part must be 0..99" % (version,))
    return major * 10000 + minor * 100 + patch


UI_VERSION = str(version_number(VERSION))


def send_ui_version():
    send_cmd_val(g.tty_fd, "logo.version", UI_VERSION)


def page_to(page_id):
    if page_id == ids.MAIN:
        send_ui_version()
    g.screen.previous_page = g.screen.page
    g.screen.page = page_id
    send_cmd_page(g.tty_fd, to_string(page_id))


def _printing_target(setter, widget, limit, settings_setter=None):
    """Value of a printing page widget: clamp, apply, echo it back to the widget and store it."""
    def handle(number):
        from . import actions, settings
        g.screen.printing_keyboard_enabled = False
        number = min(number, limit)
        getattr(actions, setter)(number)
        if widget:
            send_cmd_val(g.tty_fd, widget, to_string(number))
        if settings_setter:
            getattr(settings, settings_setter)(number)
    return handle


def _filament_target(setter, limit, settings_setter=None, reopen=True, slider=False):
    """Value of a filament page widget: clamp and apply, then redraw the page (or end the slider drag)."""
    def handle(number):
        from . import actions, settings
        number = min(number, limit)
        getattr(actions, setter)(number)
        if settings_setter:
            getattr(settings, settings_setter)(number)
        if slider:
            g.screen.move_fan_setting = False     # the slider was released
        if reopen:
            page_to(ids.FILAMENT)
    return handle


# (page, widget) -> handler(number).  NOTE: the keyboard (keybdB) always reports page 20 for the speed and flow
# values, they live on the second printing page (printing_2.n2 / n3)
SETTED = {
    (ids.PRINTING, ids.PRINTING_EXTRUDER): _printing_target("set_extruder_target", "nozzle_set", 350, "set_extruder_target"),
    (ids.PRINTING, ids.PRINTING_HEATER_BED): _printing_target("set_heater_bed_target", "bed_set", 120, "set_heater_bed_target"),
    (ids.PRINTING, ids.PRINTING_FAN_1): _printing_target("set_fan0", None, 100),
    (ids.PRINTING, ids.PRINTING_FAN_2): _printing_target("set_fan2", None, 100),      # 4.4.2 CLL fan2 added
    (ids.PRINTING, ids.PRINTING_FAN_3): _printing_target("set_fan3", None, 100),
    (ids.PRINTING, ids.PRINTING_2_SPEED): _printing_target("set_printer_speed", "speed_val", 150),
    (ids.PRINTING, ids.PRINTING_2_FLOW): _printing_target("set_printer_flow", "flow_val", 150),
    (ids.PRINTING, ids.PRINTING_HOT): _printing_target("set_hot_target", None, 60, "set_hot_target"),
    (ids.FILAMENT, ids.FILAMENT_SET_EXTRUDER): _filament_target("set_extruder_target", 350, "set_extruder_target"),
    (ids.FILAMENT, ids.FILAMENT_SET_HEATERBED): _filament_target("set_heater_bed_target", 120, "set_heater_bed_target"),
    (ids.FILAMENT, ids.FILAMENT_SET_FAN_1): _filament_target("set_fan0", 100, reopen=False, slider=True),
    (ids.FILAMENT, ids.FILAMENT_SET_FAN_2): _filament_target("set_fan2", 100, reopen=False, slider=True),
    (ids.FILAMENT, ids.FILAMENT_SET_FAN_3): _filament_target("set_fan3", 100, reopen=False, slider=True),
    (ids.FILAMENT, ids.FILAMENT_SET_HOT): _filament_target("set_hot_target", 60, "set_hot_target"),
}


def tjc_event_setted_handler(page_id, widget_id, first, second):
    cout("!!!", page_id)
    cout("!!!", widget_id)
    cout("!!!", chr(first))
    cout("!!!", chr(second))
    handler = SETTED.get((page_id, widget_id))
    if handler:
        handler((second << 8) + first)


def tjc_event_keyboard(cmd):
    pass
    MKSLOG("Keyboard value received, mode %d, row %d\n", cmd[1], cmd[2])        # the text may be a password
    psk = cstr(cmd[3:])         # char *psk = &cmd[3];
    # display_firmware: the keyboard page sends its mode (cmd[1]), see netui.py
    mode = netui.KB_PSK_SCANNED if cmd[1] == ids.WIFI_LIST else cmd[1]      # the stock keyboard sends the page id
    if mode in (netui.KB_PSK_SCANNED, netui.KB_PSK_SAVED, netui.KB_HIDDEN_SSID, netui.KB_HIDDEN_PSK):
        netui.keyboard_text(mode, b2s(psk))


from . import netui    # noqa: E402  (netui imports this module)
