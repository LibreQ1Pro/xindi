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
from .send_msg import send_cmd_page, send_cmd_val


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


def tjc_event_setted_handler(page_id, widget_id, first, second):
    from . import actions, settings
    cout("!!!", page_id)
    cout("!!!", widget_id)
    cout("!!!", chr(first))
    cout("!!!", chr(second))
    number = (second << 8) + first
    if page_id == ids.PRINTING:
        if widget_id == ids.PRINTING_EXTRUDER:
            if number > 350:
                number = 350
            g.screen.printing_keyboard_enabled = False
            actions.set_extruder_target(number)
            send_cmd_val(g.tty_fd, "nozzle_set", to_string(number))
            settings.set_extruder_target(number)
        elif widget_id == ids.PRINTING_HEATER_BED:
            if number > 120:
                number = 120
            g.screen.printing_keyboard_enabled = False
            actions.set_heater_bed_target(number)
            send_cmd_val(g.tty_fd, "bed_set", to_string(number))
            settings.set_heater_bed_target(number)
        elif widget_id == ids.PRINTING_FAN_1:
            if number > 100:
                number = 100
            g.screen.printing_keyboard_enabled = False
            actions.set_fan0(number)
        # 4.4.2 CLL fan2 added
        elif widget_id == ids.PRINTING_FAN_2:
            if number > 100:
                number = 100
            g.screen.printing_keyboard_enabled = False
            actions.set_fan2(number)
        elif widget_id == ids.PRINTING_FAN_3:
            if number > 100:
                number = 100
            g.screen.printing_keyboard_enabled = False
            actions.set_fan3(number)
        # NOTE: the keyboard (keybdB) always reports page 20 for these two, the
        # values live on the second printing page (printing_2.n2 / n3)
        elif widget_id == ids.PRINTING_2_SPEED:
            if number > 150:
                number = 150
            g.screen.printing_keyboard_enabled = False
            actions.set_printer_speed(number)
            send_cmd_val(g.tty_fd, "speed_val", to_string(number))
        elif widget_id == ids.PRINTING_2_FLOW:
            if number > 150:
                number = 150
            g.screen.printing_keyboard_enabled = False
            actions.set_printer_flow(number)
            send_cmd_val(g.tty_fd, "flow_val", to_string(number))
        elif widget_id == ids.PRINTING_HOT:
            if number > 60:
                number = 60
            g.screen.printing_keyboard_enabled = False
            actions.set_hot_target(number)
            settings.set_hot_target(number)

    elif page_id == ids.FILAMENT:
        if widget_id == ids.FILAMENT_SET_EXTRUDER:
            if number > 350:
                number = 350
            actions.set_extruder_target(number)
            settings.set_extruder_target(number)
            page_to(ids.FILAMENT)
        elif widget_id == ids.FILAMENT_SET_HEATERBED:
            if number > 120:
                number = 120
            actions.set_heater_bed_target(number)
            settings.set_heater_bed_target(number)
            page_to(ids.FILAMENT)
        elif widget_id == ids.FILAMENT_SET_FAN_1:
            if number > 100:
                number = 100
            actions.set_fan0(number)
            g.screen.move_fan_setting = False     # the slider was released
        elif widget_id == ids.FILAMENT_SET_FAN_2:
            if number > 100:
                number = 100
            actions.set_fan2(number)
            g.screen.move_fan_setting = False
        elif widget_id == ids.FILAMENT_SET_FAN_3:
            if number > 100:
                number = 100
            actions.set_fan3(number)
            g.screen.move_fan_setting = False
        elif widget_id == ids.FILAMENT_SET_HOT:
            if number > 60:
                number = 60
            actions.set_hot_target(number)
            settings.set_hot_target(number)
            page_to(ids.FILAMENT)


def tjc_event_keyboard(cmd):
    pass
    MKSLOG("Keyboard value received, mode %d, row %d\n", cmd[1], cmd[2])        # the text may be a password
    psk = cstr(cmd[3:])         # char *psk = &cmd[3];
    # display_firmware: the keyboard page sends its mode (cmd[1]), see netui.py
    mode = netui.KB_PSK_SCANNED if cmd[1] == ids.WIFI_LIST else cmd[1]      # the stock keyboard sends the page id
    if mode in (netui.KB_PSK_SCANNED, netui.KB_PSK_SAVED, netui.KB_HIDDEN_SSID, netui.KB_HIDDEN_PSK):
        netui.keyboard_text(mode, b2s(psk))


from . import netui    # noqa: E402  (netui imports this module)
