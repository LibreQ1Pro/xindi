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
from .cpp import b2s, cstr, to_string, system, sleep
from .mks_log import MKSLOG, MKSLOG_BLUE, MKSLOG_RED, cout
from .send_msg import send_cmd_page, send_cmd_val, send_cmd_tsw

# ---------------------------------------------------------------------------
# include/ui.h
# ---------------------------------------------------------------------------

# The navigation buttons at the bottom of every page send the same widget ids
TJC_PAGE_ALL_TO_MAIN = 0x1e
TJC_PAGE_ALL_TO_ADJUST = 0x1f
TJC_PAGE_ALL_TO_FILE_LIST = 0x20
TJC_PAGE_ALL_TO_SETTING = 0x21

TJC_PAGE_LOGO = 0

TJC_PAGE_RESTART = 1

TJC_PAGE_SHUTDOWN = 2

TJC_PAGE_OPEN_LANGUAGE = 3
TJC_PAGE_OPEN_LANGUAGE_NEXT = 0x00
TJC_PAGE_OPEN_LANGUAGE_SKIP = 0x01

TJC_PAGE_OPEN_POP = 4
TJC_PAGE_OPEN_POP_YES = 0x00
TJC_PAGE_OPEN_POP_NO = 0x01

TJC_PAGE_OPEN_VIDEO_1 = 5
TJC_PAGE_OPEN_VIDEO_1_NEXT = 0x00

TJC_PAGE_OPEN_VIDEO_2 = 6
TJC_PAGE_OPEN_VIDEO_2_NEXT = 0x00

TJC_PAGE_OPEN_WARNING = 7
TJC_PAGE_OPEN_WARNING_NEXT = 0x00

TJC_PAGE_OPEN_VIDEO_3 = 8
TJC_PAGE_OPEN_VIDEO_3_NEXT = 0x00
TJC_PAGE_OPEN_VIDEO_3_UP = 0x01
TJC_PAGE_OPEN_VIDEO_3_DOWN = 0x02

TJC_PAGE_OPEN_HEATERBED = 9
TJC_PAGE_OPEN_HEATERBED_ON_OFF = 0x00
TJC_PAGE_OPEN_HEATERBED_UP = 0x01
TJC_PAGE_OPEN_HEATERBED_DOWN = 0x02
TJC_PAGE_OPEN_HEATERBED_NEXT = 0x03

TJC_PAGE_OPEN_CALIBRATE = 10

TJC_PAGE_OPEN_FILAMENTVIDEO_0 = 72
TJC_PAGE_OPEN_FILAMENTVIDEO_0_NEXT = 0x00

TJC_PAGE_OPEN_FILAMENTVIDEO_1 = 11
TJC_PAGE_OPEN_FILAMENTVIDEO_1_NEXT = 0x00

TJC_PAGE_OPEN_FILAMENTVIDEO_2 = 12
TJC_PAGE_OPEN_FILAMENTVIDEO_2_DOWN = 0x00
TJC_PAGE_OPEN_FILAMENTVIDEO_2_UP = 0x01
TJC_PAGE_OPEN_FILAMENTVIDEO_2_NEXT = 0x02
TJC_PAGE_OPEN_FILAMENTVIDEO_2_ON_OFF = 0x03

TJC_PAGE_OPEN_FILAMENTVIDEO_3 = 13
TJC_PAGE_OPEN_FILAMENTVIDEO_3_NEXT = 0x00
TJC_PAGE_OPEN_FILAMENTVIDEO_3_EXTRUDE = 0x01

TJC_PAGE_OPEN_FINISH = 14
TJC_PAGE_OPEN_FINISH_YES = 0x00

TJC_PAGE_MAIN = 15
TJC_PAGE_MAIN_CASELIGHT = 0x00
TJC_PAGE_MAIN_BEEP = 0x01
TJC_PAGE_MAIN_STOP = 0x02
TJC_PAGE_MAIN_SET_TEMP = 0x03
TJC_PAGE_MAIN_SET_TEMP_2 = 0x04          # 4.4.24: three buttons open the filament page
TJC_PAGE_MAIN_SET_TEMP_3 = 0x05
TJC_PAGE_MAIN_CACHE = 0x06

TJC_PAGE_FILE_LIST = 16
TJC_PAGE_FILE_LIST_BACK = 0x00
TJC_PAGE_FILE_LIST_BTN_1 = 0x01
TJC_PAGE_FILE_LIST_BTN_2 = 0x02
TJC_PAGE_FILE_LIST_BTN_3 = 0x03
TJC_PAGE_FILE_LIST_BTN_4 = 0x04
TJC_PAGE_FILE_LIST_BTN_5 = 0x05
TJC_PAGE_FILE_LIST_PREVIOUS = 0x0a
TJC_PAGE_FILE_LIST_NEXT = 0x0b
TJC_PAGE_FILE_LIST_LOCAL = 0x0c
TJC_PAGE_FILE_LIST_USB = 0x0d

TJC_PAGE_PREVIEW = 17
TJC_PAGE_PREVIEW_BACK = 0x00
TJC_PAGE_PREVIEW_START = 0x01
TJC_PAGE_PREVIEW_BED_LEVELING = 0x02
TJC_PAGE_PREVIEW_TIMELAPSE = 0x03        # 4.4.22

TJC_PAGE_PREVIEW_POP_1 = 18
TJC_PAGE_PREVIEW_POP_2 = 19
TJC_PAGE_PREVIEW_POP_YES = 0x00
# 4.4.1 CLL "do not show again" button on the filament confirmation pop-ups
TJC_PAGE_PREVIEW_POP_NO_POP = 0x01

TJC_PAGE_PRINTING = 20
TJC_PAGE_PRINTING_EXTRUDER = 0x00
TJC_PAGE_PRINTING_HEATER_BED = 0x01
TJC_PAGE_PRINTING_NEXT = 0x02
TJC_PAGE_PRINTING_EMERGENCY_STOP = 0x03  # 4.4.22: was the case light button
TJC_PAGE_PRINTING_FAN_1 = 0x04
TJC_PAGE_PRINTING_FAN_2 = 0x05
TJC_PAGE_PRINTING_FAN_3 = 0x06
TJC_PAGE_PRINTING_HOT = 0x07
TJC_PAGE_PRINTING_PAUSE_RESUME = 0x0a
TJC_PAGE_PRINTING_STOP = 0x0b

TJC_PAGE_PRINTING_KB = 21
TJC_PAGE_PRINTING_KB_BACK = 0x00
TJC_PAGE_PRINTING_KB_MUTE = 0x01          # 4.4.22 silent mode (50% speed)
TJC_PAGE_PRINTING_KB_PAUSE_RESUME = 0x0a
TJC_PAGE_PRINTING_KB_STOP = 0x0b

TJC_PAGE_PRINT_ZOFFSET = 22
TJC_PAGE_PRINT_ZOFFSET_BACK = 0x00
TJC_PAGE_PRINT_ZOFFSET_SET_001 = 0x01
TJC_PAGE_PRINT_ZOFFSET_SET_005 = 0x02
TJC_PAGE_PRINT_ZOFFSET_SET_01 = 0x03
TJC_PAGE_PRINT_ZOFFSET_SET_05 = 0x04
TJC_PAGE_PRINT_ZOFFSET_UP = 0x05
TJC_PAGE_PRINT_ZOFFSET_DOWN = 0x06
TJC_PAGE_PRINT_ZOFFSET_PAUSE_RESUME = 0x0a
TJC_PAGE_PRINT_ZOFFSET_STOP = 0x0b

TJC_PAGE_PRINT_FILAMENT = 23
TJC_PAGE_PRINT_FILAMENT_ON_OFF = 0x00
TJC_PAGE_PRINT_FILAMENT_T_UP = 0x01
TJC_PAGE_PRINT_FILAMENT_T_DOWN = 0x02
TJC_PAGE_PRINT_FILAMENT_LOAD = 0x03
TJC_PAGE_PRINT_FILAMENT_UNLOAD = 0x04
TJC_PAGE_PRINT_FILAMENT_RETRACT = 0x05
TJC_PAGE_PRINT_FILAMENT_EXTRUDE = 0x06
TJC_PAGE_PRINT_FILAMENT_PAUSE_RESUME = 0x0a
TJC_PAGE_PRINT_FILAMENT_STOP = 0x0b

TJC_PAGE_PRINTING_2 = 24
TJC_PAGE_PRINTING_2_BACK = 0x00
TJC_PAGE_PRINTING_2_ZOFFSET = 0x01
TJC_PAGE_PRINTING_2_SPEED = 0x02
TJC_PAGE_PRINTING_2_FLOW = 0x03
TJC_PAGE_PRINTING_2_CASE_LIGHT = 0x04    # 4.4.22
TJC_PAGE_PRINTING_2_PAUSE_RESUME = 0x0a
TJC_PAGE_PRINTING_2_STOP = 0x0b

TJC_PAGE_PRINT_FINISH = 25
TJC_PAGE_PRINT_FINISH_YES = 0x00

TJC_PAGE_PRINT_STOP = 26
TJC_PAGE_PRINT_STOP_YES = 0x00
TJC_PAGE_PRINT_STOP_NO = 0x01

TJC_PAGE_PRINT_STOPPING = 27

TJC_PAGE_PRINT_NO_FILAMENT = 28
TJC_PAGE_PRINT_NO_FILAMENT_YES = 0x00

TJC_PAGE_PRINT_LOW_TEMP = 29
TJC_PAGE_PRINT_LOW_TEMP_YES = 0x00

TJC_PAGE_MOVE = 30
TJC_PAGE_MOVE_SET_01 = 0x00
TJC_PAGE_MOVE_SET_1 = 0x01
TJC_PAGE_MOVE_SET_10 = 0x02
TJC_PAGE_MOVE_Z_UP = 0x03
TJC_PAGE_MOVE_MOTOR = 0x04
TJC_PAGE_MOVE_Z_DOWN = 0x05
TJC_PAGE_MOVE_Y_UP = 0x06
TJC_PAGE_MOVE_Y_DOWN = 0x07
TJC_PAGE_MOVE_X_DOWN = 0x08
TJC_PAGE_MOVE_X_UP = 0x09
TJC_PAGE_MOVE_HOME = 0x0a
TJC_PAGE_MOVE_TO_FILAMENT = 0x16

TJC_PAGE_MOVE_POP_1 = 31
TJC_PAGE_MOVE_POP_1_YES = 0x00

TJC_PAGE_MOVE_POP_2 = 32
TJC_PAGE_MOVE_POP_2_YES = 0x00
TJC_PAGE_MOVE_POP_2_NO = 0x01

TJC_PAGE_FILAMENT_SET_FAN = 33
TJC_PAGE_FILAMENT_SET_FAN_BACK = 0x00
TJC_PAGE_FILAMENT_SET_FAN_SETTING = 0x01

TJC_PAGE_FILAMENT_KB = 34
TJC_PAGE_FILAMENT_KB_BACK = 0x00

TJC_PAGE_FILAMENT_POP_1 = 35
TJC_PAGE_FILAMENT_POP_1_YES = 0x00

TJC_PAGE_FILAMENT_POP_2 = 36
TJC_PAGE_FILAMENT_POP_2_YES = 0x00
TJC_PAGE_FILAMENT_POP_2_TO_LOAD = 0x01
TJC_PAGE_FILAMENT_POP_2_NEXT = 0x02
TJC_PAGE_FILAMENT_POP_2_BACK = 0x03

TJC_PAGE_FILAMENT_POP_3 = 37
TJC_PAGE_FILAMENT_POP_3_YES = 0x00
TJC_PAGE_FILAMENT_POP_3_RETRY = 0x01
TJC_PAGE_FILAMENT_POP_3_NEXT = 0x02
TJC_PAGE_FILAMENT_POP_3_BACK = 0x03

TJC_PAGE_FILAMENT_UNLOAD_FINISH = 38
TJC_PAGE_FILAMENT_UNLOAD_FINISH_YES = 0x00

TJC_PAGE_LEVEL_MODE = 39
TJC_PAGE_LEVEL_MODE_AUTO_LEVEL = 0x00
TJC_PAGE_LEVEL_MODE_SYNTONY = 0x01
TJC_PAGE_LEVEL_MODE_BED_CALIBRATION = 0x02
TJC_PAGE_LEVEL_MODE_TO_COMMON_SETTING = 0x17
TJC_PAGE_LEVEL_MODE_ZOFFSET = 0x18

TJC_PAGE_ZOFFSET = 40
TJC_PAGE_ZOFFSET_BACK = 0x00

TJC_PAGE_AUTO_HEATERBED = 41
TJC_PAGE_AUTO_HEATERBED_DOWN = 0x00
TJC_PAGE_AUTO_HEATERBED_UP = 0x01
TJC_PAGE_AUTO_HEATERBED_ON_OFF = 0x02
TJC_PAGE_AUTO_HEATERBED_BACK = 0x03
TJC_PAGE_AUTO_HEATERBED_NEXT = 0x04

TJC_PAGE_AUTO_MOVING = 42

TJC_PAGE_AUTO_FINISH = 43
TJC_PAGE_AUTO_FINISH_YES = 0x00

TJC_PAGE_PRE_BED_CALIBRATION = 44
TJC_PAGE_PRE_BED_CALIBRATION_SET_001 = 0x00
TJC_PAGE_PRE_BED_CALIBRATION_SET_005 = 0x01
TJC_PAGE_PRE_BED_CALIBRATION_SET_01 = 0x02
TJC_PAGE_PRE_BED_CALIBRATION_SET_05 = 0x03
TJC_PAGE_PRE_BED_CALIBRATION_UP = 0x04
TJC_PAGE_PRE_BED_CALIBRATION_DOWN = 0x05
TJC_PAGE_PRE_BED_CALIBRATION_ENTER = 0x06

TJC_PAGE_BED_MOVING = 45

TJC_PAGE_BED_CALIBRATION = 46
TJC_PAGE_BED_CALIBRATION_NEXT = 0x00

TJC_PAGE_BED_FINISH = 47
TJC_PAGE_BED_FINISH_OK = 0x00
TJC_PAGE_BED_FINISH_SCREW1 = 0x01
TJC_PAGE_BED_FINISH_SCREW2 = 0x02
TJC_PAGE_BED_FINISH_SCREW3 = 0x03
TJC_PAGE_BED_FINISH_Z_TILT = 0x04

TJC_PAGE_SYNTONY_MOVE = 48
TJC_PAGE_SYNTONY_MOVE_JUMP_OUT = 0x00

TJC_PAGE_SYNTONY_FINISH = 49
TJC_PAGE_SYNTONY_FINISH_YES = 0x00

TJC_PAGE_INTERNET = 50
TJC_PAGE_INTERNET_REFRESH = 0x00
TJC_PAGE_INTERNET_TO_WIFI = 0x16
TJC_PAGE_INTERNET_TO_SETTING = 0x17

TJC_PAGE_WIFI_LIST = 51
TJC_PAGE_WIFI_LIST_SSID_1 = 0x00
TJC_PAGE_WIFI_LIST_SSID_2 = 0x01
TJC_PAGE_WIFI_LIST_SSID_3 = 0x02
TJC_PAGE_WIFI_LIST_SSID_4 = 0x03
TJC_PAGE_WIFI_LIST_SSID_5 = 0x04
TJC_PAGE_WIFI_LIST_REFRESH = 0x07
TJC_PAGE_WIFI_LIST_PREVIOUS = 0x05
TJC_PAGE_WIFI_LIST_NEXT = 0x06
TJC_PAGE_WIFI_LIST_TO_WIFI = 0x16
TJC_PAGE_WIFI_LIST_TO_SETTING = 0x17
TJC_PAGE_WIFI_LIST_SAVED = 0x08       # display_firmware: saved networks / hidden network buttons
TJC_PAGE_WIFI_LIST_HIDDEN = 0x09

TJC_PAGE_WIFI_CONNECT = 52
TJC_PAGE_WIFI_CONNECT_TIMEOUT = 0x00      # 4.4.24: timer of the page

TJC_PAGE_WIFI_SAVING = 53

TJC_PAGE_WIFI_SUCCESS = 54
TJC_PAGE_WIFI_SUCCESS_YES = 0x00

TJC_PAGE_WIFI_FAILED = 55
TJC_PAGE_WIFI_FAILED_YES = 0x00

TJC_PAGE_WIFI_KB = 56
TJC_PAGE_WIFI_KB_BACK = 0x00

TJC_PAGE_COMMON_SETTING = 57
TJC_PAGE_COMMON_SETTING_LANGUAGE = 0x00
TJC_PAGE_COMMON_SETTING_WIFI = 0x01
TJC_PAGE_COMMON_SETTING_SYSTEM = 0x02
TJC_PAGE_COMMON_SETTING_SERVICE = 0x03
TJC_PAGE_COMMON_SETTING_SCREEN_SLEEP = 0x04
TJC_PAGE_COMMON_SETTING_UPDATE = 0x05
TJC_PAGE_COMMON_SETTING_RESTORE = 0x06
TJC_PAGE_COMMON_SETTING_OOBE_OFF = 0x07
TJC_PAGE_COMMON_SETTING_TO_LEVEL_MODE = 0x16
TJC_PAGE_COMMON_SETTING_OOBE_ON = 0x17

# CLL the following pages need similar handling in xindi, so they share one handler; everything else is done by the UI program itself
TJC_PAGE_LANGUAGE = 58
TJC_PAGE_SYS_OK = 59
TJC_PAGE_RESET = 60
TJC_PAGE_SERVICE = 61
TJC_PAGE_SLEEP_MODE = 62
TJC_PAGE_BACK_TO_COMMON_SETTING = 0x00
TJC_PAGE_RESET_PRINT_LOG = 0x01
TJC_PAGE_RESET_RESTART_KLIPPER = 0x02
TJC_PAGE_RESET_RESTART_FIRMWARE = 0x03

TJC_PAGE_UPDATE_FOUND = 63
TJC_PAGE_UPDATE_FOUND_YES = 0x00
TJC_PAGE_UPDATE_FOUND_NO = 0x01

TJC_PAGE_UPDATE_NOT_FOUND = 64
TJC_PAGE_UPDATE_NOT_FOUND_YES = 0x00

TJC_PAGE_UPDATE_FINISH = 65

TJC_PAGE_UPDATE_SUCCESS = 66
TJC_PAGE_UPDATE_SUCCESS_YES = 0x00

TJC_PAGE_RESTORE_CONFIG = 67
TJC_PAGE_RESTORE_CONFIG_YES = 0x00
TJC_PAGE_RESTORE_CONFIG_NO = 0x01

TJC_PAGE_PRINT_LOG_S = 68
TJC_PAGE_PRINT_LOG_F = 69
TJC_PAGE_PRINT_LOG_YES = 0x00

TJC_PAGE_DETECT_ERROR = 70
TJC_PAGE_DETECT_ERROR_YES = 0x00

TJC_PAGE_GCODE_ERROR = 71
TJC_PAGE_GCODE_ERROR_YES = 0x00

# 4.4.2 CLL screen sleep feature
TJC_PAGE_SCREEN_SLEEP = 73
TJC_PAGE_SCREEN_SLEEP_ENTER = 0x01
TJC_PAGE_SCREEN_SLEEP_EXIT = 0x00

TJC_PAGE_LEVEL_ERROR = 74
TJC_PAGE_LEVEL_ERROR_YES = 0x00

TJC_PAGE_FILAMENT = 75
TJC_PAGE_FILAMENT_SET_EXTRUDER = 0x00
TJC_PAGE_FILAMENT_SET_HEATERBED = 0x01
TJC_PAGE_FILAMENT_EXTRUDER_ON_OFF = 0x02
TJC_PAGE_FILAMENT_HEATERBED_ON_OFF = 0x03
TJC_PAGE_FILAMENT_TO_FAN = 0x04
TJC_PAGE_FILAMENT_LOAD = 0x05
TJC_PAGE_FILAMENT_UNLOAD = 0x06
TJC_PAGE_FILAMENT_EXTRUDER_UP = 0x07
TJC_PAGE_FILAMENT_EXTRUDER_DOWN = 0x08
TJC_PAGE_FILAMENT_SET_10 = 0x09
TJC_PAGE_FILAMENT_SET_50 = 0x0a
TJC_PAGE_FILAMENT_SET_100 = 0x0b
TJC_PAGE_FILAMENT_SET_FAN_1 = 0x0c
TJC_PAGE_FILAMENT_SET_FAN_2 = 0x0d
TJC_PAGE_FILAMENT_SET_FAN_3 = 0x0e
TJC_PAGE_FILAMENT_HOT_ON_OFF = 0x0f
TJC_PAGE_FILAMENT_SET_HOT = 0x10
TJC_PAGE_FILAMENT_TO_FILAMENT = 0x16
TJC_PAGE_FILAMENT_TO_MOVE = 0x17

TJC_PAGE_PRINT_NO_FILAMENT_2 = 76
TJC_PAGE_PRINT_NO_FILAMENT_2_YES = 0x00

TJC_PAGE_MEMORY_WARNING = 77
TJC_PAGE_MEMORY_WARNING_YES = 0x00

TJC_PAGE_UPDATING = 78

TJC_PAGE_PRE_HEAT = 79
TJC_PAGE_PRE_HEAT_SET_220 = 0x00
TJC_PAGE_PRE_HEAT_SET_250 = 0x01
TJC_PAGE_PRE_HEAT_SET_300 = 0x02
TJC_PAGE_PRE_HEAT_BACK = 0x04

TJC_PAGE_RESUME_PRINT = 80
TJC_PAGE_RESUME_PRINT_YES = 0x00
TJC_PAGE_RESUME_PRINT_NO = 0x01
TJC_PAGE_RESUME_PRINT_LOADED = 0x02       # 4.4.24: sent by the page when it is shown

# 4.4.24: the QR code page became the network page (internet_page)
TJC_PAGE_INTERNET_PAGE = 81
TJC_PAGE_INTERNET_PAGE_BACK = 0x01
TJC_PAGE_INTERNET_PAGE_ETHERNET = 0x02
TJC_PAGE_INTERNET_PAGE_WIFI = 0x03
TJC_PAGE_INTERNET_PAGE_INFO = 0x05        # display_firmware: the QIDI Link rows became network rows
TJC_PAGE_INTERNET_PAGE_SAVED = 0x06
TJC_PAGE_INTERNET_PAGE_HIDDEN = 0x07

# pages added by display_firmware (network management), see netui.py
TJC_PAGE_NET_SAVED = 110
TJC_PAGE_NET_DETAIL = 111
TJC_PAGE_NET_CONFIRM = 112
TJC_PAGE_NET_INFO = 113

TJC_PAGE_SERVER_SET = 82
TJC_PAGE_SERVER_SET_REFRESH = 0x00
TJC_PAGE_SERVER_SET_BACK = 0x01
TJC_PAGE_SERVER_SET_LOCAL = 0x02
TJC_PAGE_SERVER_SET_PREVIOUS = 0x03
TJC_PAGE_SERVER_SET_NEXT = 0x04
TJC_PAGE_SERVER_SET_1 = 0x05
TJC_PAGE_SERVER_SET_2 = 0x06
TJC_PAGE_SERVER_SET_3 = 0x07
TJC_PAGE_SERVER_SET_4 = 0x08

TJC_PAGE_UPDATE_MODE = 83
TJC_PAGE_UPDATE_MODE_BACK = 0x00
TJC_PAGE_UPDATE_MODE_LOCAL = 0x01
TJC_PAGE_UPDATE_MODE_ONLINE = 0x02

TJC_PAGE_ONLINE_UPDATE = 84
TJC_PAGE_ONLINE_UPDATE_BACK = 0x00
TJC_PAGE_ONLINE_UPDATE_YES = 0x01
TJC_PAGE_ONLINE_UPDATE_NO = 0x02

TJC_PAGE_SEARCH_SERVER = 85

TJC_PAGE_UNLOAD_MODE = 86
TJC_PAGE_UNLOAD_MODE_MANUAL = 0x00
TJC_PAGE_UNLOAD_MODE_AUTO = 0x01
TJC_PAGE_UNLOAD_MODE_BACK = 0x02

TJC_PAGE_AUTO_UNLOAD = 87
TJC_PAGE_AUTO_UNLOAD_TO_LOAD = 0x00
TJC_PAGE_AUTO_UNLOAD_YES = 0x01

TJC_PAGE_OPEN_LANGUAGE2 = 88

TJC_PAGE_LANGUAGE2 = 89

TJC_PAGE_INSTALLING = 90

TJC_PAGE_AUTO_WARNING = 91
TJC_PAGE_AUTO_WARNING_YES = 0x00

TJC_PAGE_CALIBRATE_WARNING = 92
TJC_PAGE_CALIBRATE_WARNING_NEXT = 0x00
TJC_PAGE_CALIBRATE_WARNING_BACK = 0x01

TJC_PAGE_RE_PRINTING = 93

# 4.4.24
TJC_PAGE_OPEN_MOVING = 94
TJC_PAGE_OPEN_MOVING_TIMER = 0x00

TJC_PAGE_STOP_CONFIRM = 95
TJC_PAGE_STOP_CONFIRM_YES = 0x00
TJC_PAGE_STOP_CONFIRM_NO = 0x01

# QIDI Link (QIDI's cloud): link_login .. server_error2, not implemented
TJC_PAGE_LINK_FIRST = 96
TJC_PAGE_LINK_LAST = 109



DEFAULT_DIR = "gcodes/"


def parse_cmd_msg_from_tjc_screen(cmd):
    """``cmd`` is the 4096 byte read buffer (zero padded) of the main loop."""
    import sys
    from . import mks_file
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
        tjc_event_clicked_handler(g.screen.page_id, g.screen.widget_id, g.screen.type_id)
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
            if g.screen.page != TJC_PAGE_LOGO:
                page_to(g.screen.page)
    elif event_id == 0x91:
        g.screen.page = TJC_PAGE_LOGO
        page_to(TJC_PAGE_UPDATE_SUCCESS)
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
    if page_id == TJC_PAGE_MAIN:
        send_ui_version()
    g.screen.previous_page = g.screen.page
    g.screen.page = page_id
    send_cmd_page(g.tty_fd, to_string(page_id))


def _printer_not_failed():
    return g.klippy.webhooks_state != "shutdown" and g.klippy.webhooks_state != "error"


def _nav_guarded(widget_id):
    """ALL_TO_* buttons of the pages that are reachable while Klipper is in an error state."""
    from . import actions, filelist
    if widget_id == TJC_PAGE_ALL_TO_MAIN:
        if _printer_not_failed():
            page_to(TJC_PAGE_MAIN)
        return True
    if widget_id == TJC_PAGE_ALL_TO_FILE_LIST:
        if _printer_not_failed():
            filelist.go_to_file_list()
        return True
    if widget_id == TJC_PAGE_ALL_TO_ADJUST:
        if _printer_not_failed():
            actions.go_to_adjust()
        return True
    return False


def tjc_event_clicked_handler(page_id, widget_id, type_id):
    from . import mks_file
    from .mks_update import start_update
    from .MakerbaseWiFi import set_page_wifi_ssid_list
    from . import actions, filelist, pages, settings, updates, wifi_ui
    cout("+++++++++++++++++++", page_id)
    cout("+++++++++++++++++++", widget_id)
    cout("+++++++++++++++++++", type_id)

    # first page of the out-of-box guide
    if page_id == TJC_PAGE_OPEN_LANGUAGE:
        if widget_id == TJC_PAGE_OPEN_LANGUAGE_NEXT:
            page_to(TJC_PAGE_OPEN_VIDEO_1)
            actions.get_object_status()
        elif widget_id == TJC_PAGE_OPEN_LANGUAGE_SKIP:
            page_to(TJC_PAGE_OPEN_POP)

    elif page_id == TJC_PAGE_OPEN_POP:
        if widget_id == TJC_PAGE_OPEN_POP_YES:
            page_to(TJC_PAGE_MAIN)
            settings.set_oobe_enabled(False)
        elif widget_id == TJC_PAGE_OPEN_POP_NO:
            page_to(TJC_PAGE_OPEN_LANGUAGE)

    # second page of the guide
    elif page_id == TJC_PAGE_OPEN_VIDEO_1:
        if widget_id == TJC_PAGE_OPEN_VIDEO_1_NEXT:
            page_to(TJC_PAGE_OPEN_VIDEO_2)

    # third page of the guide
    elif page_id == TJC_PAGE_OPEN_VIDEO_2:
        if widget_id == TJC_PAGE_OPEN_VIDEO_2_NEXT:
            page_to(TJC_PAGE_OPEN_WARNING)

    # fourth page of the guide
    elif page_id == TJC_PAGE_OPEN_WARNING:
        if widget_id == TJC_PAGE_OPEN_WARNING_NEXT:
            actions.open_heater_bed_up()
            page_to(TJC_PAGE_OPEN_MOVING)       # 4.4.22: wait until the bed has moved

    # 4.4.22 "the bed is moving" page of the guide; its timer sends 0
    elif page_id == TJC_PAGE_OPEN_MOVING:
        if widget_id == TJC_PAGE_OPEN_MOVING_TIMER:
            page_to(TJC_PAGE_OPEN_FILAMENTVIDEO_0)

    # fifth page of the guide
    elif page_id == TJC_PAGE_OPEN_VIDEO_3:
        if widget_id == TJC_PAGE_OPEN_VIDEO_3_NEXT:
            page_to(TJC_PAGE_OPEN_FILAMENTVIDEO_1)     # CLL levelling and input shaping removed from the guide
        elif widget_id == TJC_PAGE_OPEN_VIDEO_3_UP:
            actions.set_move_dist(10.0)
            actions.move_z_decrease()
        elif widget_id == TJC_PAGE_OPEN_VIDEO_3_DOWN:
            actions.set_move_dist(10.0)
            actions.move_z_increase()

    elif page_id == TJC_PAGE_OPEN_HEATERBED:
        if widget_id == TJC_PAGE_OPEN_HEATERBED_DOWN:
            actions.set_auto_level_heater_bed_target(False)
        elif widget_id == TJC_PAGE_OPEN_HEATERBED_UP:
            actions.set_auto_level_heater_bed_target(True)
        elif widget_id == TJC_PAGE_OPEN_HEATERBED_ON_OFF:
            actions.filament_heater_bed_target()
        elif widget_id == TJC_PAGE_OPEN_HEATERBED_NEXT:
            actions.open_calibrate_start()

    elif page_id == TJC_PAGE_OPEN_FILAMENTVIDEO_0 or page_id == TJC_PAGE_OPEN_FILAMENTVIDEO_1:
        if page_id == TJC_PAGE_OPEN_FILAMENTVIDEO_0:
            if widget_id == TJC_PAGE_OPEN_FILAMENTVIDEO_0_NEXT:
                page_to(TJC_PAGE_OPEN_FILAMENTVIDEO_1)
            # NOTE: no "break" in the original - falls through into the next case
        if widget_id == TJC_PAGE_OPEN_FILAMENTVIDEO_1_NEXT:
            page_to(TJC_PAGE_OPEN_FILAMENTVIDEO_2)

    elif page_id == TJC_PAGE_OPEN_FILAMENTVIDEO_2:
        if widget_id == TJC_PAGE_OPEN_FILAMENTVIDEO_2_UP:
            actions.set_filament_extruder_target(True)
        elif widget_id == TJC_PAGE_OPEN_FILAMENTVIDEO_2_DOWN:
            actions.set_filament_extruder_target(False)
        elif widget_id == TJC_PAGE_OPEN_FILAMENTVIDEO_2_NEXT:
            page_to(TJC_PAGE_OPEN_FILAMENTVIDEO_3)
        elif widget_id == TJC_PAGE_OPEN_FILAMENTVIDEO_2_ON_OFF:
            actions.open_set_print_filament_target()

    elif page_id == TJC_PAGE_OPEN_FILAMENTVIDEO_3:
        if widget_id == TJC_PAGE_OPEN_FILAMENTVIDEO_3_NEXT:
            actions.set_extruder_target(0)
            page_to(TJC_PAGE_OPEN_FINISH)
        elif widget_id == TJC_PAGE_OPEN_FILAMENTVIDEO_3_EXTRUDE:
            actions.open_start_extrude()

    elif page_id == TJC_PAGE_OPEN_FINISH:
        if widget_id == TJC_PAGE_OPEN_FINISH_YES:
            actions.open_more_level_finish()

    elif page_id == TJC_PAGE_MAIN:
        if widget_id == TJC_PAGE_ALL_TO_MAIN:
            pass
        elif widget_id == TJC_PAGE_ALL_TO_FILE_LIST:
            filelist.go_to_file_list()
        elif widget_id == TJC_PAGE_ALL_TO_ADJUST:
            actions.go_to_adjust()
        elif widget_id == TJC_PAGE_ALL_TO_SETTING:
            actions.go_to_setting()
        elif widget_id == TJC_PAGE_MAIN_CASELIGHT:
            actions.led_on_off()
        elif widget_id == TJC_PAGE_MAIN_BEEP:
            actions.beep_on_off()
        elif widget_id == TJC_PAGE_MAIN_STOP:
            actions.motors_off()
        elif widget_id in (TJC_PAGE_MAIN_SET_TEMP, TJC_PAGE_MAIN_SET_TEMP_2, TJC_PAGE_MAIN_SET_TEMP_3):
            g.screen.adjust_mode = "Filament"
            page_to(TJC_PAGE_FILAMENT)
        elif widget_id == TJC_PAGE_MAIN_CACHE:
            g.files.list_pages = 0
            g.files.list_current_pages = 0
            g.files.list_folder_layers = 0
            g.files.list_previous_path = ""
            g.files.list_root_path = DEFAULT_DIR
            g.files.list_path = ""
            filelist.refresh_page_files(g.files.list_current_pages)
            if g.files.list_list_show_type[0] == "[c]":
                filelist.clear_cp0_image()
                mks_file.get_sub_dir_files_list(0)
                g.screen.file_mode = "Local"

    elif page_id == TJC_PAGE_FILE_LIST:
        if widget_id == TJC_PAGE_ALL_TO_MAIN:
            page_to(TJC_PAGE_MAIN)
        elif widget_id == TJC_PAGE_ALL_TO_FILE_LIST:
            pass
        elif widget_id == TJC_PAGE_ALL_TO_ADJUST:
            actions.go_to_adjust()
        elif widget_id == TJC_PAGE_ALL_TO_SETTING:
            actions.go_to_setting()
        elif widget_id == TJC_PAGE_FILE_LIST_BACK:
            if g.files.list_folder_layers == 0 or (g.files.list_folder_layers == 1 and g.screen.file_mode != "Local"):
                pass
            else:
                mks_file.get_parenet_dir_files_list()
        elif widget_id in (TJC_PAGE_FILE_LIST_BTN_1, TJC_PAGE_FILE_LIST_BTN_2, TJC_PAGE_FILE_LIST_BTN_3,
                           TJC_PAGE_FILE_LIST_BTN_4):
            filelist.clear_cp0_image()
            mks_file.get_sub_dir_files_list(widget_id - TJC_PAGE_FILE_LIST_BTN_1)
            g.screen.bed_leveling = True
        # 4.4.22: the list is marked as changed and the touch is disabled
        # until the pictures of the new page are sent
        elif widget_id == TJC_PAGE_FILE_LIST_PREVIOUS:
            if filelist.detect_disk() == -1 and g.screen.file_mode == "USB":
                g.screen.file_list_refreshed = False
                filelist.go_to_file_list()
            elif g.files.list_current_pages > 0:
                g.screen.file_list_refreshed = False
                g.files.list_current_pages -= 1
                page_to(TJC_PAGE_FILE_LIST)
                send_cmd_tsw(g.tty_fd, "255", "0")
                filelist.refresh_page_files(g.files.list_current_pages)
                filelist.refresh_files_list()
            MKSLOG_BLUE("%d", g.files.list_folder_layers)
        elif widget_id == TJC_PAGE_FILE_LIST_NEXT:
            if filelist.detect_disk() == -1 and g.screen.file_mode == "USB":
                g.screen.file_list_refreshed = False
                filelist.go_to_file_list()
            elif g.files.list_current_pages < g.files.list_pages:
                g.screen.file_list_refreshed = False
                g.files.list_current_pages += 1
                page_to(TJC_PAGE_FILE_LIST)
                send_cmd_tsw(g.tty_fd, "255", "0")
                filelist.refresh_page_files(g.files.list_current_pages)
                filelist.refresh_files_list()
            MKSLOG_BLUE("%d", g.files.list_folder_layers)
        # 4.4.2 CLL local / USB buttons on the file list page
        elif widget_id == TJC_PAGE_FILE_LIST_LOCAL:
            if g.screen.file_mode != "Local":
                g.screen.file_mode = "Local"
                g.screen.file_list_refreshed = False
                filelist.go_to_file_list()
        elif widget_id == TJC_PAGE_FILE_LIST_USB:
            if g.screen.file_mode != "USB":
                g.screen.file_mode = "USB"
                g.screen.file_list_refreshed = False
                filelist.go_to_file_list()

    elif page_id == TJC_PAGE_PREVIEW:
        if g.screen.page == TJC_PAGE_PREVIEW:
            printing_or_paused = (g.klippy.print_stats_state == "printing" or g.klippy.print_stats_state == "paused")
            if widget_id == TJC_PAGE_ALL_TO_MAIN:
                if printing_or_paused:
                    page_to(TJC_PAGE_PRINTING)
                    g.screen.jump_print = False
                else:
                    page_to(TJC_PAGE_MAIN)
            elif widget_id == TJC_PAGE_ALL_TO_FILE_LIST:
                pass
            elif widget_id == TJC_PAGE_ALL_TO_ADJUST:
                if printing_or_paused:
                    page_to(TJC_PAGE_PRINTING)
                    g.screen.jump_print = False
                else:
                    actions.go_to_adjust()
            elif widget_id == TJC_PAGE_ALL_TO_SETTING:
                if printing_or_paused:
                    page_to(TJC_PAGE_PRINTING)
                    g.screen.jump_print = False
                else:
                    actions.go_to_setting()
            elif widget_id == TJC_PAGE_PREVIEW_BACK:
                # 4.4.3 CLL keep the preview page from getting stuck
                if printing_or_paused:
                    page_to(TJC_PAGE_PRINTING)
                    g.screen.jump_print = False
                elif g.files.meta_parse_finished == False:
                    mks_file.get_parenet_dir_files_list()
                    pages.clear_preview()
                    g.screen.show_preview_complete = False
                    filelist.clear_cp0_image()
                else:
                    if g.screen.show_preview_complete == True:     # the button only works once the preview is loaded
                        mks_file.get_parenet_dir_files_list()
                        pages.clear_preview()             # clear the data when going back
                        g.screen.show_preview_complete = False
                        filelist.clear_cp0_image()
            elif widget_id == TJC_PAGE_PREVIEW_START:
                if printing_or_paused:
                    page_to(TJC_PAGE_PRINTING)
                    g.screen.jump_print = False
                elif g.screen.show_preview_complete == True:
                    g.screen.muted = False             # 4.4.22 silent mode is per print
                    actions.print_start()
                    sleep(1)
                    if g.klippy.filament_detected == True:
                        MKSLOG("No filament runout detected")
                        g.klippy.print_stats_state = "printing"
                        actions.check_filament_type()
                        actions.start_printing(g.files.list_print_files_path)
                        g.screen.show_preview_complete = False
                    else:
                        MKSLOG("Filament runout detected")
                        page_to(TJC_PAGE_PRINT_NO_FILAMENT)
                g.screen.main_picture_detected = False
                g.screen.main_picture_refreshed = False
            elif widget_id == TJC_PAGE_PREVIEW_BED_LEVELING:
                if printing_or_paused:
                    page_to(TJC_PAGE_PRINTING)
                    g.screen.jump_print = False
                else:
                    if g.screen.bed_leveling == True:
                        g.screen.bed_leveling = False
                    else:
                        g.screen.bed_leveling = True
            elif widget_id == TJC_PAGE_PREVIEW_TIMELAPSE:
                actions.switch_timelapse_state()

    elif page_id == TJC_PAGE_PREVIEW_POP_1 or page_id == TJC_PAGE_PREVIEW_POP_2:
        if widget_id == TJC_PAGE_PREVIEW_POP_YES:
            page_to(TJC_PAGE_PRINTING)
        elif widget_id == TJC_PAGE_PREVIEW_POP_NO_POP:
            if g.screen.page == TJC_PAGE_PREVIEW_POP_1:
                g.screen.preview_pop_1_on = False
            elif g.screen.page == TJC_PAGE_PREVIEW_POP_2:
                g.screen.preview_pop_2_on = False
            page_to(TJC_PAGE_PRINTING)

    elif page_id == TJC_PAGE_PRINTING:
        if widget_id in (TJC_PAGE_PRINTING_EXTRUDER, TJC_PAGE_PRINTING_HEATER_BED, TJC_PAGE_PRINTING_FAN_1,
                         TJC_PAGE_PRINTING_FAN_2, TJC_PAGE_PRINTING_FAN_3, TJC_PAGE_PRINTING_HOT):
            g.screen.printing_keyboard_enabled = True
            pages.clear_printing_arg()
        elif widget_id == TJC_PAGE_PRINTING_NEXT:
            page_to(TJC_PAGE_PRINTING_2)
        elif widget_id == TJC_PAGE_PRINTING_EMERGENCY_STOP:
            page_to(TJC_PAGE_STOP_CONFIRM)
        elif widget_id == TJC_PAGE_PRINTING_PAUSE_RESUME:
            g.klippy.ready = False
            actions.set_print_pause()
            page_to(TJC_PAGE_PRINT_FILAMENT)
            pages.clear_printing_arg()
        elif widget_id == TJC_PAGE_PRINTING_STOP:
            page_to(TJC_PAGE_PRINT_STOP)
            pages.clear_printing_arg()

    elif page_id == TJC_PAGE_PRINTING_KB:
        if widget_id == TJC_PAGE_PRINTING_KB_BACK:
            g.screen.printing_keyboard_enabled = False
            MKSLOG_BLUE("Restored")
        elif widget_id == TJC_PAGE_PRINTING_KB_MUTE:
            MKSLOG_BLUE("Silent mode switched")
            if g.screen.muted == False:
                g.screen.muted = True
                actions.set_printer_speed(50)
            else:
                g.screen.muted = False
                actions.set_printer_speed(100)
        elif widget_id == TJC_PAGE_PRINTING_KB_PAUSE_RESUME:
            g.screen.printing_keyboard_enabled = False
            actions.set_print_pause()
            page_to(TJC_PAGE_PRINT_FILAMENT)
            pages.clear_printing_arg()
        elif widget_id == TJC_PAGE_PRINTING_KB_STOP:
            g.screen.printing_keyboard_enabled = False
            page_to(TJC_PAGE_PRINT_STOP)
            pages.clear_printing_arg()

    elif page_id == TJC_PAGE_PRINT_ZOFFSET:
        if widget_id == TJC_PAGE_PRINT_ZOFFSET_BACK:
            g.screen.printing_keyboard_enabled = False
            page_to(TJC_PAGE_PRINTING_2)
        elif widget_id == TJC_PAGE_PRINT_ZOFFSET_SET_001:
            actions.set_intern_zoffset(0.01)
        elif widget_id == TJC_PAGE_PRINT_ZOFFSET_SET_005:
            actions.set_intern_zoffset(0.05)
        elif widget_id == TJC_PAGE_PRINT_ZOFFSET_SET_01:
            actions.set_intern_zoffset(0.1)
        elif widget_id == TJC_PAGE_PRINT_ZOFFSET_SET_05:
            actions.set_intern_zoffset(0.5)
        elif widget_id == TJC_PAGE_PRINT_ZOFFSET_UP:
            actions.set_zoffset(False)
        elif widget_id == TJC_PAGE_PRINT_ZOFFSET_DOWN:
            actions.set_zoffset(True)
        elif widget_id == TJC_PAGE_PRINT_ZOFFSET_PAUSE_RESUME:
            g.klippy.ready = False
            actions.set_print_pause()
            page_to(TJC_PAGE_PRINT_FILAMENT)
            pages.clear_printing_arg()
        elif widget_id == TJC_PAGE_PRINT_ZOFFSET_STOP:
            page_to(TJC_PAGE_PRINT_STOP)

    elif page_id == TJC_PAGE_PRINT_FILAMENT:
        if widget_id == TJC_PAGE_PRINT_FILAMENT_ON_OFF:
            actions.set_print_filament_target()
        elif widget_id == TJC_PAGE_PRINT_FILAMENT_T_UP:
            actions.set_filament_extruder_target(True)
        elif widget_id == TJC_PAGE_PRINT_FILAMENT_T_DOWN:
            actions.set_filament_extruder_target(False)
        elif widget_id == TJC_PAGE_PRINT_FILAMENT_LOAD:
            g.screen.load_mode = True
            page_to(TJC_PAGE_PRE_HEAT)
        elif widget_id == TJC_PAGE_PRINT_FILAMENT_UNLOAD:
            g.screen.load_mode = False
            page_to(TJC_PAGE_PRE_HEAT)
        elif widget_id == TJC_PAGE_PRINT_FILAMENT_PAUSE_RESUME:
            MKSLOG_BLUE("get_filament_detected_enable: %d", int(actions.get_filament_detected_enable()))
            MKSLOG_BLUE("get_filament_detected: %d", int(actions.get_filament_detected()))
            g.klippy.ready = False
            page_to(TJC_PAGE_PRINTING)
            actions.set_print_resume()
        elif widget_id == TJC_PAGE_PRINT_FILAMENT_STOP:
            page_to(TJC_PAGE_PRINT_STOP)
            pages.clear_printing_arg()
        elif widget_id == TJC_PAGE_PRINT_FILAMENT_RETRACT:
            actions.send_gcode("M603\n")
        elif widget_id == TJC_PAGE_PRINT_FILAMENT_EXTRUDE:
            actions.set_print_filament_dist(50)
            actions.start_extrude()

    elif page_id == TJC_PAGE_PRINTING_2:
        if widget_id == TJC_PAGE_PRINTING_2_BACK:
            page_to(TJC_PAGE_PRINTING)
        elif widget_id in (TJC_PAGE_PRINTING_2_SPEED, TJC_PAGE_PRINTING_2_FLOW):
            g.screen.printing_keyboard_enabled = True
            pages.clear_printing_arg()
        elif widget_id == TJC_PAGE_PRINTING_2_ZOFFSET:
            page_to(TJC_PAGE_PRINT_ZOFFSET)
        elif widget_id == TJC_PAGE_PRINTING_2_PAUSE_RESUME:
            g.klippy.ready = False
            actions.set_print_pause()
            page_to(TJC_PAGE_PRINT_FILAMENT)
            pages.clear_printing_arg()
        elif widget_id == TJC_PAGE_PRINTING_2_STOP:
            page_to(TJC_PAGE_PRINT_STOP)
        elif widget_id == TJC_PAGE_PRINTING_2_CASE_LIGHT:
            actions.led_on_off()

    elif page_id == TJC_PAGE_PRINT_FINISH:
        if widget_id == TJC_PAGE_PRINT_FINISH_YES:
            actions.finish_print()

    elif page_id == TJC_PAGE_PRINT_STOP:
        if widget_id == TJC_PAGE_PRINT_STOP_YES:
            g.klippy.idle_timeout_state = "Printing"
            page_to(TJC_PAGE_PRINT_STOPPING)
            actions.cancel_print()
        elif widget_id == TJC_PAGE_PRINT_STOP_NO:
            page_to(g.screen.previous_page)

    # 4.4.22 emergency stop from the printing page
    elif page_id == TJC_PAGE_STOP_CONFIRM:
        if widget_id == TJC_PAGE_STOP_CONFIRM_YES:
            page_to(TJC_PAGE_PRINT_STOPPING)
            g.klippy.print_stats_state = "paused"
            actions.motors_off()
        elif widget_id == TJC_PAGE_STOP_CONFIRM_NO:
            page_to(TJC_PAGE_PRINTING)

    elif page_id == TJC_PAGE_PRINT_NO_FILAMENT:
        if widget_id == TJC_PAGE_PRINT_NO_FILAMENT_YES:
            g.klippy.filament_detected = True
            if g.screen.previous_page == TJC_PAGE_PREVIEW:
                actions.get_object_status()
                page_to(TJC_PAGE_MOVE)
            else:
                actions.get_object_status()
                page_to(TJC_PAGE_PRINT_FILAMENT)

    elif page_id == TJC_PAGE_PRINT_NO_FILAMENT_2 or page_id == TJC_PAGE_PRINT_LOW_TEMP:
        if page_id == TJC_PAGE_PRINT_NO_FILAMENT_2:
            if widget_id == TJC_PAGE_PRINT_NO_FILAMENT_2_YES:
                actions.get_object_status()
                page_to(TJC_PAGE_PRINT_FILAMENT)
            # NOTE: no "break" in the original - falls through into the next case
        if widget_id == TJC_PAGE_PRINT_LOW_TEMP_YES:
            g.klippy.idle_timeout_state = "Ready"
            page_to(TJC_PAGE_PRINT_FILAMENT)

    elif page_id == TJC_PAGE_MOVE:
        if widget_id == TJC_PAGE_MOVE_SET_01:
            actions.set_move_dist(0.1)
        elif widget_id == TJC_PAGE_MOVE_SET_1:
            actions.set_move_dist(1.0)
        elif widget_id == TJC_PAGE_MOVE_SET_10:
            actions.set_move_dist(10.0)
        elif widget_id == TJC_PAGE_MOVE_Z_UP:
            actions.move_z_decrease()
        elif widget_id == TJC_PAGE_MOVE_Z_DOWN:
            actions.move_z_increase()
        elif widget_id == TJC_PAGE_MOVE_MOTOR:
            actions.move_motors_off()
        elif widget_id == TJC_PAGE_MOVE_X_UP:
            actions.move_x_increase()
        elif widget_id == TJC_PAGE_MOVE_X_DOWN:
            actions.move_x_decrease()
        elif widget_id == TJC_PAGE_MOVE_Y_UP:
            actions.move_y_increase()
        elif widget_id == TJC_PAGE_MOVE_Y_DOWN:
            actions.move_y_decrease()
        elif widget_id == TJC_PAGE_MOVE_HOME:
            actions.move_home()
        elif widget_id == TJC_PAGE_MOVE_TO_FILAMENT:
            page_to(TJC_PAGE_FILAMENT)
            g.screen.adjust_mode = "Filament"
        elif widget_id == TJC_PAGE_ALL_TO_MAIN:
            page_to(TJC_PAGE_MAIN)
        elif widget_id == TJC_PAGE_ALL_TO_FILE_LIST:
            filelist.go_to_file_list()
        elif widget_id == TJC_PAGE_ALL_TO_ADJUST:
            pass
        elif widget_id == TJC_PAGE_ALL_TO_SETTING:
            actions.go_to_setting()

    elif page_id == TJC_PAGE_MOVE_POP_1:
        if widget_id == TJC_PAGE_MOVE_POP_1_YES:
            if (g.screen.previous_page == TJC_PAGE_PRINTING or g.screen.previous_page == TJC_PAGE_PRINT_ZOFFSET
                    or g.screen.previous_page == TJC_PAGE_PRINTING_2):
                actions.cancel_print()
                page_to(TJC_PAGE_PRINT_STOPPING)
            else:
                page_to(TJC_PAGE_MOVE)

    elif page_id == TJC_PAGE_MOVE_POP_2:
        if widget_id == TJC_PAGE_MOVE_POP_2_YES:
            page_to(TJC_PAGE_MOVE)
            actions.move_home()
        elif widget_id == TJC_PAGE_MOVE_POP_2_NO:
            page_to(TJC_PAGE_MOVE)

    elif page_id == TJC_PAGE_FILAMENT_SET_FAN:
        if widget_id == TJC_PAGE_ALL_TO_MAIN:
            page_to(TJC_PAGE_MAIN)
        elif widget_id == TJC_PAGE_ALL_TO_FILE_LIST:
            filelist.go_to_file_list()
        elif widget_id == TJC_PAGE_ALL_TO_ADJUST:
            pass
        elif widget_id == TJC_PAGE_ALL_TO_SETTING:
            actions.go_to_setting()
        elif widget_id == TJC_PAGE_FILAMENT_SET_FAN_BACK:
            page_to(TJC_PAGE_FILAMENT)
        elif widget_id == TJC_PAGE_FILAMENT_SET_FAN_SETTING:
            g.screen.move_fan_setting = True      # the slider is being dragged

    elif page_id == TJC_PAGE_FILAMENT_KB:
        if widget_id == TJC_PAGE_ALL_TO_MAIN:
            page_to(TJC_PAGE_MAIN)
        elif widget_id == TJC_PAGE_ALL_TO_FILE_LIST:
            filelist.go_to_file_list()
        elif widget_id == TJC_PAGE_ALL_TO_ADJUST:
            pass
        elif widget_id == TJC_PAGE_ALL_TO_SETTING:
            actions.go_to_setting()
        elif widget_id == TJC_PAGE_FILAMENT_KB_BACK:
            page_to(TJC_PAGE_FILAMENT)

    elif page_id == TJC_PAGE_FILAMENT:
        if widget_id == TJC_PAGE_ALL_TO_MAIN:
            page_to(TJC_PAGE_MAIN)
        elif widget_id == TJC_PAGE_ALL_TO_FILE_LIST:
            filelist.go_to_file_list()
        elif widget_id == TJC_PAGE_ALL_TO_ADJUST:
            pass
        elif widget_id == TJC_PAGE_ALL_TO_SETTING:
            actions.go_to_setting()
        elif widget_id in (TJC_PAGE_FILAMENT_SET_EXTRUDER, TJC_PAGE_FILAMENT_SET_HEATERBED, TJC_PAGE_FILAMENT_SET_HOT):
            page_to(TJC_PAGE_FILAMENT_KB)
        elif widget_id == TJC_PAGE_FILAMENT_EXTRUDER_UP:
            g.klippy.idle_timeout_state = "Printing"
            g.screen.filament_extrude_button = True
            actions.start_retract()
        elif widget_id == TJC_PAGE_FILAMENT_EXTRUDER_DOWN:
            g.klippy.idle_timeout_state = "Printing"
            g.screen.filament_extrude_button = True
            actions.start_extrude()
        elif widget_id == TJC_PAGE_FILAMENT_EXTRUDER_ON_OFF:
            actions.filament_extruder_target()
        elif widget_id == TJC_PAGE_FILAMENT_HEATERBED_ON_OFF:
            actions.filament_heater_bed_target()
        elif widget_id == TJC_PAGE_FILAMENT_HOT_ON_OFF:
            actions.filament_hot_target()
        elif widget_id == TJC_PAGE_FILAMENT_TO_FAN:
            page_to(TJC_PAGE_FILAMENT_SET_FAN)
        elif widget_id == TJC_PAGE_FILAMENT_LOAD:
            g.screen.load_mode = True
            page_to(TJC_PAGE_PRE_HEAT)
        elif widget_id == TJC_PAGE_FILAMENT_UNLOAD:
            g.screen.load_mode = False
            page_to(TJC_PAGE_PRE_HEAT)
        elif widget_id == TJC_PAGE_FILAMENT_SET_10:
            actions.set_print_filament_dist(10)
        elif widget_id == TJC_PAGE_FILAMENT_SET_50:
            actions.set_print_filament_dist(50)
        elif widget_id == TJC_PAGE_FILAMENT_SET_100:
            actions.set_print_filament_dist(100)
        elif widget_id == TJC_PAGE_FILAMENT_TO_MOVE:
            page_to(TJC_PAGE_MOVE)
            g.screen.adjust_mode = "Move"

    elif page_id == TJC_PAGE_FILAMENT_POP_1:
        if widget_id == TJC_PAGE_FILAMENT_POP_1_YES:
            g.klippy.idle_timeout_state = "Ready"
            page_to(TJC_PAGE_FILAMENT)

    elif page_id == TJC_PAGE_FILAMENT_POP_2:
        if widget_id == TJC_PAGE_FILAMENT_POP_2_YES:
            actions.send_gcode("SET_HEATER_TEMPERATURE HEATER=extruder TARGET=0\n")
            if g.klippy.print_stats_state == "paused":
                page_to(TJC_PAGE_PRINT_FILAMENT)
            else:
                page_to(TJC_PAGE_FILAMENT)
        elif widget_id == TJC_PAGE_FILAMENT_POP_2_TO_LOAD:
            g.screen.load_mode = True
            page_to(TJC_PAGE_PRE_HEAT)
        elif widget_id == TJC_PAGE_FILAMENT_POP_2_NEXT:
            actions.filament_load()
        elif widget_id == TJC_PAGE_FILAMENT_POP_2_BACK:
            page_to(TJC_PAGE_UNLOAD_MODE)

    elif page_id == TJC_PAGE_FILAMENT_POP_3:
        if widget_id == TJC_PAGE_FILAMENT_POP_3_NEXT:
            actions.filament_load()
        elif widget_id == TJC_PAGE_FILAMENT_POP_3_YES:
            actions.send_gcode("SET_HEATER_TEMPERATURE HEATER=extruder TARGET=0\n")
            if g.klippy.print_stats_state == "paused":
                page_to(TJC_PAGE_PRINT_FILAMENT)
            else:
                page_to(TJC_PAGE_FILAMENT)
        elif widget_id == TJC_PAGE_FILAMENT_POP_3_RETRY:
            g.screen.load_mode = True
            page_to(TJC_PAGE_FILAMENT_POP_3)
            actions.filament_load()
        elif widget_id == TJC_PAGE_FILAMENT_POP_3_BACK:
            page_to(TJC_PAGE_PRE_HEAT)

    elif page_id == TJC_PAGE_FILAMENT_UNLOAD_FINISH:
        if widget_id == TJC_PAGE_FILAMENT_UNLOAD_FINISH_YES:
            page_to(TJC_PAGE_FILAMENT)

    elif page_id == TJC_PAGE_LEVEL_MODE:
        if widget_id == TJC_PAGE_ALL_TO_MAIN:
            page_to(TJC_PAGE_MAIN)
        elif widget_id == TJC_PAGE_ALL_TO_FILE_LIST:
            filelist.go_to_file_list()
        elif widget_id == TJC_PAGE_ALL_TO_ADJUST:
            actions.go_to_adjust()
        elif widget_id == TJC_PAGE_ALL_TO_SETTING:
            pass
        elif widget_id == TJC_PAGE_LEVEL_MODE_AUTO_LEVEL:
            actions.get_object_status()
            page_to(TJC_PAGE_AUTO_HEATERBED)
        elif widget_id == TJC_PAGE_LEVEL_MODE_SYNTONY:
            actions.go_to_syntony_move()
        elif widget_id == TJC_PAGE_LEVEL_MODE_BED_CALIBRATION:
            page_to(TJC_PAGE_CALIBRATE_WARNING)
        elif widget_id == TJC_PAGE_LEVEL_MODE_TO_COMMON_SETTING:
            page_to(TJC_PAGE_COMMON_SETTING)
            g.screen.set_mode = "Common_setting"
        elif widget_id == TJC_PAGE_LEVEL_MODE_ZOFFSET:
            page_to(TJC_PAGE_ZOFFSET)

    elif page_id == TJC_PAGE_ZOFFSET:
        if widget_id == TJC_PAGE_ZOFFSET_BACK:
            page_to(TJC_PAGE_LEVEL_MODE)

    elif page_id == TJC_PAGE_AUTO_HEATERBED:
        if widget_id == TJC_PAGE_AUTO_HEATERBED_DOWN:
            actions.set_auto_level_heater_bed_target(False)
        elif widget_id == TJC_PAGE_AUTO_HEATERBED_UP:
            actions.set_auto_level_heater_bed_target(True)
        elif widget_id == TJC_PAGE_AUTO_HEATERBED_ON_OFF:
            actions.filament_heater_bed_target()
        elif widget_id == TJC_PAGE_AUTO_HEATERBED_BACK:
            page_to(TJC_PAGE_LEVEL_MODE)
        elif widget_id == TJC_PAGE_AUTO_HEATERBED_NEXT:
            if g.klippy.heater_bed_target < 35:
                page_to(TJC_PAGE_AUTO_WARNING)
            else:
                g.screen.auto_level_button_enabled = True
                g.klippy.idle_timeout_state = "Printing"
                actions.start_auto_level()

    elif page_id == TJC_PAGE_AUTO_FINISH:
        if widget_id == TJC_PAGE_AUTO_FINISH_YES:
            cout("Auto levelling finished")
            page_to(TJC_PAGE_LEVEL_MODE)

    elif page_id == TJC_PAGE_PRE_BED_CALIBRATION:
        if widget_id == TJC_PAGE_PRE_BED_CALIBRATION_SET_001:
            actions.set_auto_level_dist(0.01)
        elif widget_id == TJC_PAGE_PRE_BED_CALIBRATION_SET_005:
            actions.set_auto_level_dist(0.05)
        elif widget_id == TJC_PAGE_PRE_BED_CALIBRATION_SET_01:
            actions.set_auto_level_dist(0.1)
        elif widget_id == TJC_PAGE_PRE_BED_CALIBRATION_SET_05:
            actions.set_auto_level_dist(0.5)
        elif widget_id == TJC_PAGE_PRE_BED_CALIBRATION_UP:
            actions.bed_adjust(True)
        elif widget_id == TJC_PAGE_PRE_BED_CALIBRATION_DOWN:
            actions.bed_adjust(False)
        elif widget_id == TJC_PAGE_PRE_BED_CALIBRATION_ENTER:
            actions.bed_calibrate()

    elif page_id == TJC_PAGE_BED_CALIBRATION:
        if widget_id == TJC_PAGE_BED_CALIBRATION_NEXT:
            actions.bed_calibrate()

    elif page_id == TJC_PAGE_BED_FINISH:
        if widget_id == TJC_PAGE_BED_FINISH_OK:
            page_to(TJC_PAGE_LEVEL_MODE)
        elif widget_id == TJC_PAGE_BED_FINISH_SCREW1:
            g.klippy.idle_timeout_state = "Printing"
            actions.send_gcode("G1 Z10 F600\n")
            actions.send_gcode("G1 X10 Y10 F9000\n")
            actions.send_gcode("G1 Z0 F600\n")
            g.screen.manual_count = -1
            page_to(TJC_PAGE_BED_MOVING)
        elif widget_id == TJC_PAGE_BED_FINISH_SCREW2:
            g.klippy.idle_timeout_state = "Printing"
            actions.send_gcode("G1 Z10 F600\n")
            actions.send_gcode("G1 X230 Y10 F9000\n")
            actions.send_gcode("G1 Z0 F600\n")
            g.screen.manual_count = -1
            page_to(TJC_PAGE_BED_MOVING)
        elif widget_id == TJC_PAGE_BED_FINISH_SCREW3:
            g.klippy.idle_timeout_state = "Printing"
            actions.send_gcode("G1 Z10 F600\n")
            actions.send_gcode("G1 X125 Y240 F9000\n")
            actions.send_gcode("G1 Z0 F600\n")
            g.screen.manual_count = -1
            page_to(TJC_PAGE_BED_MOVING)
        elif widget_id == TJC_PAGE_BED_FINISH_Z_TILT:
            g.klippy.idle_timeout_state = "Printing"
            actions.send_gcode("G28\nZ_TILT_ADJUST\n")
            actions.send_gcode("G1 Z10 F600\nG1 X0 Y0 F9000\n")
            g.screen.manual_count = -2
            page_to(TJC_PAGE_BED_MOVING)

    elif page_id == TJC_PAGE_SYNTONY_MOVE:
        if widget_id == TJC_PAGE_SYNTONY_MOVE_JUMP_OUT:
            actions.send_gcode("SAVE_CONFIG\n")
            page_to(TJC_PAGE_SYNTONY_FINISH)

    elif page_id == TJC_PAGE_SYNTONY_FINISH:
        if widget_id == TJC_PAGE_SYNTONY_FINISH_YES:
            page_to(TJC_PAGE_LEVEL_MODE)
            system("sync")
            settings.get_babystep()           # 4.4.22 (was init_mks_status())
            actions.sub_object_status()
            actions.get_object_status()

    elif page_id == TJC_PAGE_INTERNET:
        if _nav_guarded(widget_id):
            pass
        elif widget_id == TJC_PAGE_ALL_TO_SETTING:
            pass
        elif widget_id == TJC_PAGE_INTERNET_REFRESH:
            cout("################## refresh button pressed")
            wifi_ui.scan_ssid_and_show()
            cout("Waiting 3s...")
            sleep(3)
            wifi_ui.scan_ssid_and_show()
        elif widget_id == TJC_PAGE_INTERNET_TO_WIFI:
            pass
        elif widget_id == TJC_PAGE_INTERNET_TO_SETTING:
            page_to(TJC_PAGE_COMMON_SETTING)

    elif page_id == TJC_PAGE_WIFI_LIST:
        if _nav_guarded(widget_id):
            pass
        elif widget_id == TJC_PAGE_ALL_TO_SETTING:
            pass
        elif widget_id in (TJC_PAGE_WIFI_LIST_SSID_1, TJC_PAGE_WIFI_LIST_SSID_2, TJC_PAGE_WIFI_LIST_SSID_3,
                           TJC_PAGE_WIFI_LIST_SSID_4, TJC_PAGE_WIFI_LIST_SSID_5):
            index = widget_id - TJC_PAGE_WIFI_LIST_SSID_1
            if g.screen.wifi_ssid_button_enabled[index] == True:
                wifi_ui.get_wifi_list_ssid(index)
                netui.open_keyboard(netui.KB_PSK_SCANNED, 8, g.net.get_wifi_name)
        elif widget_id == TJC_PAGE_WIFI_LIST_SAVED:
            netui.open_saved()
        elif widget_id == TJC_PAGE_WIFI_LIST_HIDDEN:
            netui.open_hidden()
        elif widget_id == TJC_PAGE_WIFI_LIST_REFRESH:
            cout("################## refresh button pressed")
            wifi_ui.scan_ssid_and_show()
            # 4.4.1 CLL wifi refresh fix
        elif widget_id == TJC_PAGE_WIFI_LIST_PREVIOUS:
            if g.net.wifi_current_pages > 0:
                cout("page_wifi_current_pages = ", g.net.wifi_current_pages)
                cout("page_wifi_ssid_list_pages = ", g.net.wifi_ssid_list_pages)
                g.net.wifi_current_pages -= 1
                set_page_wifi_ssid_list(g.net.wifi_current_pages)
                wifi_ui.refresh_wifi_list()
        elif widget_id == TJC_PAGE_WIFI_LIST_NEXT:
            if g.net.wifi_current_pages < g.net.wifi_ssid_list_pages - 1:
                cout("page_wifi_current_pages = ", g.net.wifi_current_pages)
                cout("page_wifi_ssid_list_pages = ", g.net.wifi_ssid_list_pages)
                g.net.wifi_current_pages += 1
                set_page_wifi_ssid_list(g.net.wifi_current_pages)
                wifi_ui.refresh_wifi_list()
        elif widget_id == TJC_PAGE_WIFI_LIST_TO_WIFI:
            pass
        elif widget_id == TJC_PAGE_WIFI_LIST_TO_SETTING:
            wifi_ui.refresh_ip_address()             # 4.4.22: the network page (was the QR code page)

    # 4.4.24: the timer of the page reports a connection that takes too long
    elif page_id == TJC_PAGE_WIFI_CONNECT:
        if widget_id == TJC_PAGE_WIFI_CONNECT_TIMEOUT:
            page_to(TJC_PAGE_WIFI_FAILED)

    elif page_id == TJC_PAGE_WIFI_SUCCESS:
        if widget_id == TJC_PAGE_WIFI_SUCCESS_YES:
            settings.wifi_save_config()

    elif page_id == TJC_PAGE_WIFI_FAILED:
        if widget_id == TJC_PAGE_WIFI_FAILED_YES:
            wifi_ui.go_to_network()                  # 4.4.22 (was page_to(TJC_PAGE_WIFI_LIST))

    elif page_id == TJC_PAGE_WIFI_KB:
        if widget_id == TJC_PAGE_WIFI_KB_BACK:
            netui.keyboard_back()

    elif page_id in (TJC_PAGE_NET_SAVED, TJC_PAGE_NET_DETAIL, TJC_PAGE_NET_CONFIRM, TJC_PAGE_NET_INFO):
        if _nav_guarded(widget_id):
            pass
        elif page_id == TJC_PAGE_NET_SAVED:
            netui.saved_clicked(widget_id)
        elif page_id == TJC_PAGE_NET_DETAIL:
            netui.detail_clicked(widget_id)
        elif page_id == TJC_PAGE_NET_CONFIRM:
            netui.confirm_clicked(widget_id)
        else:
            netui.info_clicked(widget_id)

    elif page_id == TJC_PAGE_COMMON_SETTING:
        if _nav_guarded(widget_id):
            pass
        elif widget_id == TJC_PAGE_ALL_TO_SETTING:
            pass
        elif widget_id == TJC_PAGE_COMMON_SETTING_LANGUAGE:
            page_to(TJC_PAGE_LANGUAGE)
        elif widget_id == TJC_PAGE_COMMON_SETTING_WIFI:
            wifi_ui.refresh_ip_address()             # 4.4.22: the network page (was the QR code page)
        elif widget_id == TJC_PAGE_COMMON_SETTING_SYSTEM:
            actions.go_to_reset()
        elif widget_id == TJC_PAGE_COMMON_SETTING_SERVICE:
            page_to(TJC_PAGE_SERVICE)
        elif widget_id == TJC_PAGE_COMMON_SETTING_SCREEN_SLEEP:
            page_to(TJC_PAGE_SLEEP_MODE)
        elif widget_id == TJC_PAGE_COMMON_SETTING_UPDATE:
            updates.go_to_update()
        elif widget_id == TJC_PAGE_COMMON_SETTING_RESTORE:
            page_to(TJC_PAGE_RESTORE_CONFIG)
        elif widget_id == TJC_PAGE_COMMON_SETTING_OOBE_OFF:
            settings.set_oobe_enabled(False)
            page_to(TJC_PAGE_COMMON_SETTING)
        elif widget_id == TJC_PAGE_COMMON_SETTING_OOBE_ON:
            settings.set_oobe_enabled(True)
        elif widget_id == TJC_PAGE_COMMON_SETTING_TO_LEVEL_MODE:
            page_to(TJC_PAGE_LEVEL_MODE)
            g.screen.set_mode = "Level_mode"

    elif page_id in (TJC_PAGE_LANGUAGE, TJC_PAGE_SERVICE, TJC_PAGE_SYS_OK, TJC_PAGE_RESET, TJC_PAGE_SLEEP_MODE):
        if _nav_guarded(widget_id):
            pass
        elif widget_id == TJC_PAGE_ALL_TO_SETTING:
            pass
        elif widget_id == TJC_PAGE_BACK_TO_COMMON_SETTING:
            page_to(TJC_PAGE_COMMON_SETTING)
        elif widget_id == TJC_PAGE_RESET_PRINT_LOG:
            filelist.print_log()
        elif widget_id == TJC_PAGE_RESET_RESTART_KLIPPER:
            actions.reset_klipper()
        elif widget_id == TJC_PAGE_RESET_RESTART_FIRMWARE:
            actions.reset_firmware()

    elif page_id == TJC_PAGE_UPDATE_SUCCESS:
        if widget_id == TJC_PAGE_UPDATE_SUCCESS_YES:
            updates.finish_tjc_update()
            page_to(TJC_PAGE_MAIN)

    elif page_id == TJC_PAGE_PRINT_LOG_F or page_id == TJC_PAGE_PRINT_LOG_S:
        if widget_id == TJC_PAGE_PRINT_LOG_YES:
            actions.go_to_reset()

    elif page_id == TJC_PAGE_DETECT_ERROR:
        if widget_id == TJC_PAGE_DETECT_ERROR_YES:
            if g.screen.previous_page == TJC_PAGE_AUTO_MOVING or g.screen.previous_page == TJC_PAGE_OPEN_CALIBRATE:
                actions.reset_klipper()
            page_to(TJC_PAGE_MAIN)
            actions.clear_previous_data()

    elif page_id == TJC_PAGE_GCODE_ERROR:
        if widget_id == TJC_PAGE_GCODE_ERROR_YES:
            page_to(TJC_PAGE_MAIN)

    # 4.4.2 CLL screen sleep feature
    elif page_id == TJC_PAGE_SCREEN_SLEEP:
        # 4.4.22: the case light is no longer switched off while the screen sleeps
        if widget_id == TJC_PAGE_SCREEN_SLEEP_ENTER:
            page_to(TJC_PAGE_SCREEN_SLEEP)
        elif widget_id == TJC_PAGE_SCREEN_SLEEP_EXIT:
            if g.screen.previous_page == TJC_PAGE_FILE_LIST:
                filelist.go_to_file_list()
            else:
                page_to(g.screen.previous_page)
                actions.get_object_status()

    # 4.4.3 CLL the update button is always shown
    elif page_id == TJC_PAGE_UPDATE_FOUND:
        if widget_id == TJC_PAGE_UPDATE_FOUND_YES:
            page_to(TJC_PAGE_UPDATING)
            actions.disable_page_about_successed()
            start_update()
        elif widget_id == TJC_PAGE_UPDATE_FOUND_NO:
            updates.go_to_update()

    elif page_id == TJC_PAGE_UPDATE_NOT_FOUND:
        if widget_id == TJC_PAGE_UPDATE_NOT_FOUND_YES:
            updates.go_to_update()

    elif page_id == TJC_PAGE_RESTORE_CONFIG:
        if widget_id == TJC_PAGE_RESTORE_CONFIG_YES:
            settings.restore_config()
        elif widget_id == TJC_PAGE_RESTORE_CONFIG_NO:
            page_to(TJC_PAGE_COMMON_SETTING)

    elif page_id == TJC_PAGE_LEVEL_ERROR:      # CLL dedicated pop-up for levelling errors
        if widget_id == TJC_PAGE_LEVEL_ERROR_YES:
            page_to(TJC_PAGE_MAIN)

    elif page_id == TJC_PAGE_MEMORY_WARNING:
        if widget_id == TJC_PAGE_MEMORY_WARNING_YES:
            page_to(TJC_PAGE_MAIN)

    elif page_id == TJC_PAGE_PRE_HEAT:
        if widget_id in (TJC_PAGE_PRE_HEAT_SET_220, TJC_PAGE_PRE_HEAT_SET_250, TJC_PAGE_PRE_HEAT_SET_300):
            g.screen.load_target = {TJC_PAGE_PRE_HEAT_SET_220: 220, TJC_PAGE_PRE_HEAT_SET_250: 250,
                             TJC_PAGE_PRE_HEAT_SET_300: 300}[widget_id]
            if g.screen.load_mode == True:
                page_to(TJC_PAGE_FILAMENT_POP_3)
            else:
                page_to(TJC_PAGE_UNLOAD_MODE)
        elif widget_id == TJC_PAGE_PRE_HEAT_BACK:
            if g.klippy.print_stats_state == "paused":
                page_to(TJC_PAGE_PRINT_FILAMENT)
            else:
                page_to(TJC_PAGE_FILAMENT)

    elif page_id == TJC_PAGE_RESUME_PRINT:
        if widget_id == TJC_PAGE_RESUME_PRINT_YES:
            page_to(TJC_PAGE_RE_PRINTING)
            actions.send_gcode("RESUME_INTERRUPTED\n")
        elif widget_id == TJC_PAGE_RESUME_PRINT_NO:
            page_to(TJC_PAGE_MAIN)
            actions.send_gcode("CLEAR_LAST_FILE")
        elif widget_id == TJC_PAGE_RESUME_PRINT_LOADED:
            g.screen.jump_resume_print = False      # 4.4.24: the page reports that it is shown

    # 4.4.24 network page (4.4.22 binary); the QIDI Link buttons are not implemented
    elif page_id == TJC_PAGE_INTERNET_PAGE:
        if _nav_guarded(widget_id):
            pass
        elif widget_id == TJC_PAGE_INTERNET_PAGE_BACK:
            page_to(TJC_PAGE_COMMON_SETTING)
        elif widget_id == TJC_PAGE_INTERNET_PAGE_ETHERNET:
            # 1: ethernet, 0: wifi (the page shows the address on the next refresh)
            settings.set_ethernet(0 if g.config.ethernet == 1 else 1)
        elif widget_id == TJC_PAGE_INTERNET_PAGE_WIFI:
            wifi_ui.go_to_network()
        elif widget_id == TJC_PAGE_INTERNET_PAGE_INFO:
            netui.open_info()
        elif widget_id == TJC_PAGE_INTERNET_PAGE_SAVED:
            netui.open_saved()
        elif widget_id == TJC_PAGE_INTERNET_PAGE_HIDDEN:
            netui.open_hidden()

    elif TJC_PAGE_LINK_FIRST <= page_id <= TJC_PAGE_LINK_LAST:
        pass        # QIDI Link pages: not reachable, the network page keeps the buttons disabled

    # 4.4.22: the server page belongs to QIDI Link (reached from the network page
    # only when QIDI Link is on), which the port does not implement
    elif page_id == TJC_PAGE_SERVER_SET:
        if _nav_guarded(widget_id):
            pass
        elif widget_id == TJC_PAGE_SERVER_SET_BACK:
            wifi_ui.refresh_ip_address()
    elif page_id == TJC_PAGE_UPDATE_MODE:
        if _nav_guarded(widget_id):
            pass
        elif widget_id == TJC_PAGE_UPDATE_MODE_BACK:
            page_to(TJC_PAGE_COMMON_SETTING)
        elif widget_id == TJC_PAGE_UPDATE_MODE_LOCAL:
            updates.local_update()
        elif widget_id == TJC_PAGE_UPDATE_MODE_ONLINE:
            updates.check_online_version()

    elif page_id == TJC_PAGE_ONLINE_UPDATE:
        if _nav_guarded(widget_id):
            pass
        elif widget_id == TJC_PAGE_ONLINE_UPDATE_BACK:
            page_to(TJC_PAGE_COMMON_SETTING)
        elif widget_id == TJC_PAGE_ONLINE_UPDATE_YES:
            updates.online_update()
        elif widget_id == TJC_PAGE_ONLINE_UPDATE_NO:
            updates.go_to_update()

    elif page_id == TJC_PAGE_UNLOAD_MODE:
        if widget_id == TJC_PAGE_UNLOAD_MODE_MANUAL:
            page_to(TJC_PAGE_FILAMENT_POP_2)
        elif widget_id == TJC_PAGE_UNLOAD_MODE_AUTO:
            page_to(TJC_PAGE_AUTO_UNLOAD)
            actions.filament_unload()
        elif widget_id == TJC_PAGE_UNLOAD_MODE_BACK:
            page_to(TJC_PAGE_PRE_HEAT)

    elif page_id == TJC_PAGE_AUTO_UNLOAD:
        if widget_id == TJC_PAGE_AUTO_UNLOAD_YES:
            actions.send_gcode("SET_HEATER_TEMPERATURE HEATER=extruder TARGET=0\n")
            if g.klippy.print_stats_state == "paused":
                page_to(TJC_PAGE_PRINT_FILAMENT)
            else:
                page_to(TJC_PAGE_FILAMENT)
        elif widget_id == TJC_PAGE_AUTO_UNLOAD_TO_LOAD:
            g.screen.load_mode = True
            page_to(TJC_PAGE_PRE_HEAT)

    elif page_id == TJC_PAGE_AUTO_WARNING:
        if widget_id == TJC_PAGE_AUTO_WARNING_YES:
            page_to(TJC_PAGE_AUTO_HEATERBED)

    elif page_id == TJC_PAGE_CALIBRATE_WARNING:
        if widget_id == TJC_PAGE_CALIBRATE_WARNING_NEXT:
            g.screen.manual_count = 4
            actions.bed_calibrate()
        elif widget_id == TJC_PAGE_CALIBRATE_WARNING_BACK:
            page_to(TJC_PAGE_LEVEL_MODE)


def tjc_event_setted_handler(page_id, widget_id, first, second):
    from . import actions, settings
    cout("!!!", page_id)
    cout("!!!", widget_id)
    cout("!!!", chr(first))
    cout("!!!", chr(second))
    number = (second << 8) + first
    if page_id == TJC_PAGE_PRINTING:
        if widget_id == TJC_PAGE_PRINTING_EXTRUDER:
            if number > 350:
                number = 350
            g.screen.printing_keyboard_enabled = False
            actions.set_extruder_target(number)
            send_cmd_val(g.tty_fd, "nozzle_set", to_string(number))
            settings.set_extruder_target(number)
        elif widget_id == TJC_PAGE_PRINTING_HEATER_BED:
            if number > 120:
                number = 120
            g.screen.printing_keyboard_enabled = False
            actions.set_heater_bed_target(number)
            send_cmd_val(g.tty_fd, "bed_set", to_string(number))
            settings.set_heater_bed_target(number)
        elif widget_id == TJC_PAGE_PRINTING_FAN_1:
            if number > 100:
                number = 100
            g.screen.printing_keyboard_enabled = False
            actions.set_fan0(number)
        # 4.4.2 CLL fan2 added
        elif widget_id == TJC_PAGE_PRINTING_FAN_2:
            if number > 100:
                number = 100
            g.screen.printing_keyboard_enabled = False
            actions.set_fan2(number)
        elif widget_id == TJC_PAGE_PRINTING_FAN_3:
            if number > 100:
                number = 100
            g.screen.printing_keyboard_enabled = False
            actions.set_fan3(number)
        # NOTE: the keyboard (keybdB) always reports page 20 for these two, the
        # values live on the second printing page (printing_2.n2 / n3)
        elif widget_id == TJC_PAGE_PRINTING_2_SPEED:
            if number > 150:
                number = 150
            g.screen.printing_keyboard_enabled = False
            actions.set_printer_speed(number)
            send_cmd_val(g.tty_fd, "speed_val", to_string(number))
        elif widget_id == TJC_PAGE_PRINTING_2_FLOW:
            if number > 150:
                number = 150
            g.screen.printing_keyboard_enabled = False
            actions.set_printer_flow(number)
            send_cmd_val(g.tty_fd, "flow_val", to_string(number))
        elif widget_id == TJC_PAGE_PRINTING_HOT:
            if number > 60:
                number = 60
            g.screen.printing_keyboard_enabled = False
            actions.set_hot_target(number)
            settings.set_hot_target(number)

    elif page_id == TJC_PAGE_FILAMENT:
        if widget_id == TJC_PAGE_FILAMENT_SET_EXTRUDER:
            if number > 350:
                number = 350
            actions.set_extruder_target(number)
            settings.set_extruder_target(number)
            page_to(TJC_PAGE_FILAMENT)
        elif widget_id == TJC_PAGE_FILAMENT_SET_HEATERBED:
            if number > 120:
                number = 120
            actions.set_heater_bed_target(number)
            settings.set_heater_bed_target(number)
            page_to(TJC_PAGE_FILAMENT)
        elif widget_id == TJC_PAGE_FILAMENT_SET_FAN_1:
            if number > 100:
                number = 100
            actions.set_fan0(number)
            g.screen.move_fan_setting = False     # the slider was released
        elif widget_id == TJC_PAGE_FILAMENT_SET_FAN_2:
            if number > 100:
                number = 100
            actions.set_fan2(number)
            g.screen.move_fan_setting = False
        elif widget_id == TJC_PAGE_FILAMENT_SET_FAN_3:
            if number > 100:
                number = 100
            actions.set_fan3(number)
            g.screen.move_fan_setting = False
        elif widget_id == TJC_PAGE_FILAMENT_SET_HOT:
            if number > 60:
                number = 60
            actions.set_hot_target(number)
            settings.set_hot_target(number)
            page_to(TJC_PAGE_FILAMENT)


def tjc_event_keyboard(cmd):
    pass
    MKSLOG("Keyboard value received, mode %d, row %d\n", cmd[1], cmd[2])        # the text may be a password
    psk = cstr(cmd[3:])         # char *psk = &cmd[3];
    # display_firmware: the keyboard page sends its mode (cmd[1]), see netui.py
    mode = netui.KB_PSK_SCANNED if cmd[1] == TJC_PAGE_WIFI_LIST else cmd[1]      # the stock keyboard sends the page id
    if mode in (netui.KB_PSK_SCANNED, netui.KB_PSK_SAVED, netui.KB_HIDDEN_SSID, netui.KB_HIDDEN_PSK):
        netui.keyboard_text(mode, b2s(psk))


from . import netui    # noqa: E402  (netui imports this module)
