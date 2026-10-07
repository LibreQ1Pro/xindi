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
from .cpp import b2s, cstr, to_string, system, sleep
from .mks_log import MKSLOG, MKSLOG_BLUE, MKSLOG_RED, cout
from .send_msg import send_cmd_page, send_cmd_val, send_cmd_tsw


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


def _printer_not_failed():
    return g.klippy.webhooks_state != "shutdown" and g.klippy.webhooks_state != "error"


def _nav_guarded(widget_id):
    """ALL_TO_* buttons of the pages that are reachable while Klipper is in an error state."""
    from . import actions, filelist
    if widget_id == ids.ALL_TO_MAIN:
        if _printer_not_failed():
            page_to(ids.MAIN)
        return True
    if widget_id == ids.ALL_TO_FILE_LIST:
        if _printer_not_failed():
            filelist.go_to_file_list()
        return True
    if widget_id == ids.ALL_TO_ADJUST:
        if _printer_not_failed():
            actions.go_to_adjust()
        return True
    return False


def tjc_event_clicked_handler(page_id, widget_id, type_id):
    from . import mks_file
    from .MakerbaseWiFi import set_page_wifi_ssid_list
    from . import actions, filelist, pages, settings, wifi_ui
    cout("+++++++++++++++++++", page_id)
    cout("+++++++++++++++++++", widget_id)
    cout("+++++++++++++++++++", type_id)

    # first page of the out-of-box guide
    if page_id == ids.OPEN_LANGUAGE:
        if widget_id == ids.OPEN_LANGUAGE_NEXT:
            page_to(ids.OPEN_VIDEO_1)
            actions.get_object_status()
        elif widget_id == ids.OPEN_LANGUAGE_SKIP:
            page_to(ids.OPEN_POP)

    elif page_id == ids.OPEN_POP:
        if widget_id == ids.OPEN_POP_YES:
            page_to(ids.MAIN)
            settings.set_oobe_enabled(False)
        elif widget_id == ids.OPEN_POP_NO:
            page_to(ids.OPEN_LANGUAGE)

    # second page of the guide
    elif page_id == ids.OPEN_VIDEO_1:
        if widget_id == ids.OPEN_VIDEO_1_NEXT:
            page_to(ids.OPEN_VIDEO_2)

    # third page of the guide
    elif page_id == ids.OPEN_VIDEO_2:
        if widget_id == ids.OPEN_VIDEO_2_NEXT:
            page_to(ids.OPEN_WARNING)

    # fourth page of the guide
    elif page_id == ids.OPEN_WARNING:
        if widget_id == ids.OPEN_WARNING_NEXT:
            actions.open_heater_bed_up()
            page_to(ids.OPEN_MOVING)       # 4.4.22: wait until the bed has moved

    # 4.4.22 "the bed is moving" page of the guide; its timer sends 0
    elif page_id == ids.OPEN_MOVING:
        if widget_id == ids.OPEN_MOVING_TIMER:
            page_to(ids.OPEN_FILAMENTVIDEO_0)

    # fifth page of the guide
    elif page_id == ids.OPEN_VIDEO_3:
        if widget_id == ids.OPEN_VIDEO_3_NEXT:
            page_to(ids.OPEN_FILAMENTVIDEO_1)     # CLL levelling and input shaping removed from the guide
        elif widget_id == ids.OPEN_VIDEO_3_UP:
            actions.set_move_dist(10.0)
            actions.move_z_decrease()
        elif widget_id == ids.OPEN_VIDEO_3_DOWN:
            actions.set_move_dist(10.0)
            actions.move_z_increase()

    elif page_id == ids.OPEN_HEATERBED:
        if widget_id == ids.OPEN_HEATERBED_DOWN:
            actions.set_auto_level_heater_bed_target(False)
        elif widget_id == ids.OPEN_HEATERBED_UP:
            actions.set_auto_level_heater_bed_target(True)
        elif widget_id == ids.OPEN_HEATERBED_ON_OFF:
            actions.filament_heater_bed_target()
        elif widget_id == ids.OPEN_HEATERBED_NEXT:
            actions.open_calibrate_start()

    elif page_id == ids.OPEN_FILAMENTVIDEO_0 or page_id == ids.OPEN_FILAMENTVIDEO_1:
        if page_id == ids.OPEN_FILAMENTVIDEO_0:
            if widget_id == ids.OPEN_FILAMENTVIDEO_0_NEXT:
                page_to(ids.OPEN_FILAMENTVIDEO_1)
            # NOTE: no "break" in the original - falls through into the next case
        if widget_id == ids.OPEN_FILAMENTVIDEO_1_NEXT:
            page_to(ids.OPEN_FILAMENTVIDEO_2)

    elif page_id == ids.OPEN_FILAMENTVIDEO_2:
        if widget_id == ids.OPEN_FILAMENTVIDEO_2_UP:
            actions.set_filament_extruder_target(True)
        elif widget_id == ids.OPEN_FILAMENTVIDEO_2_DOWN:
            actions.set_filament_extruder_target(False)
        elif widget_id == ids.OPEN_FILAMENTVIDEO_2_NEXT:
            page_to(ids.OPEN_FILAMENTVIDEO_3)
        elif widget_id == ids.OPEN_FILAMENTVIDEO_2_ON_OFF:
            actions.open_set_print_filament_target()

    elif page_id == ids.OPEN_FILAMENTVIDEO_3:
        if widget_id == ids.OPEN_FILAMENTVIDEO_3_NEXT:
            actions.set_extruder_target(0)
            page_to(ids.OPEN_FINISH)
        elif widget_id == ids.OPEN_FILAMENTVIDEO_3_EXTRUDE:
            actions.open_start_extrude()

    elif page_id == ids.OPEN_FINISH:
        if widget_id == ids.OPEN_FINISH_YES:
            actions.open_more_level_finish()

    elif page_id == ids.MAIN:
        if widget_id == ids.ALL_TO_MAIN:
            pass
        elif widget_id == ids.ALL_TO_FILE_LIST:
            filelist.go_to_file_list()
        elif widget_id == ids.ALL_TO_ADJUST:
            actions.go_to_adjust()
        elif widget_id == ids.ALL_TO_SETTING:
            actions.go_to_setting()
        elif widget_id == ids.MAIN_CASELIGHT:
            actions.led_on_off()
        elif widget_id == ids.MAIN_BEEP:
            actions.beep_on_off()
        elif widget_id == ids.MAIN_STOP:
            actions.motors_off()
        elif widget_id in (ids.MAIN_SET_TEMP, ids.MAIN_SET_TEMP_2, ids.MAIN_SET_TEMP_3):
            g.screen.adjust_mode = "Filament"
            page_to(ids.FILAMENT)
        elif widget_id == ids.MAIN_CACHE:
            g.files.list_pages = 0
            g.files.list_current_pages = 0
            g.files.list_folder_layers = 0
            g.files.list_previous_path = ""
            g.files.list_root_path = filelist.DEFAULT_DIR
            g.files.list_path = ""
            filelist.refresh_page_files(g.files.list_current_pages)
            if g.files.list_list_show_type[0] == "[c]":
                filelist.clear_cp0_image()
                mks_file.get_sub_dir_files_list(0)
                g.screen.file_mode = "Local"

    elif page_id == ids.FILE_LIST:
        if widget_id == ids.ALL_TO_MAIN:
            page_to(ids.MAIN)
        elif widget_id == ids.ALL_TO_FILE_LIST:
            pass
        elif widget_id == ids.ALL_TO_ADJUST:
            actions.go_to_adjust()
        elif widget_id == ids.ALL_TO_SETTING:
            actions.go_to_setting()
        elif widget_id == ids.FILE_LIST_BACK:
            if g.files.list_folder_layers == 0 or (g.files.list_folder_layers == 1 and g.screen.file_mode != "Local"):
                pass
            else:
                mks_file.get_parenet_dir_files_list()
        elif widget_id in (ids.FILE_LIST_BTN_1, ids.FILE_LIST_BTN_2, ids.FILE_LIST_BTN_3,
                           ids.FILE_LIST_BTN_4):
            filelist.clear_cp0_image()
            mks_file.get_sub_dir_files_list(widget_id - ids.FILE_LIST_BTN_1)
            g.screen.bed_leveling = True
        # 4.4.22: the list is marked as changed and the touch is disabled
        # until the pictures of the new page are sent
        elif widget_id == ids.FILE_LIST_PREVIOUS:
            if filelist.detect_disk() == -1 and g.screen.file_mode == "USB":
                g.screen.file_list_refreshed = False
                filelist.go_to_file_list()
            elif g.files.list_current_pages > 0:
                g.screen.file_list_refreshed = False
                g.files.list_current_pages -= 1
                page_to(ids.FILE_LIST)
                send_cmd_tsw(g.tty_fd, "255", "0")
                filelist.refresh_page_files(g.files.list_current_pages)
                filelist.refresh_files_list()
            MKSLOG_BLUE("%d", g.files.list_folder_layers)
        elif widget_id == ids.FILE_LIST_NEXT:
            if filelist.detect_disk() == -1 and g.screen.file_mode == "USB":
                g.screen.file_list_refreshed = False
                filelist.go_to_file_list()
            elif g.files.list_current_pages < g.files.list_pages:
                g.screen.file_list_refreshed = False
                g.files.list_current_pages += 1
                page_to(ids.FILE_LIST)
                send_cmd_tsw(g.tty_fd, "255", "0")
                filelist.refresh_page_files(g.files.list_current_pages)
                filelist.refresh_files_list()
            MKSLOG_BLUE("%d", g.files.list_folder_layers)
        # 4.4.2 CLL local / USB buttons on the file list page
        elif widget_id == ids.FILE_LIST_LOCAL:
            if g.screen.file_mode != "Local":
                g.screen.file_mode = "Local"
                g.screen.file_list_refreshed = False
                filelist.go_to_file_list()
        elif widget_id == ids.FILE_LIST_USB:
            if g.screen.file_mode != "USB":
                g.screen.file_mode = "USB"
                g.screen.file_list_refreshed = False
                filelist.go_to_file_list()

    elif page_id == ids.PREVIEW:
        if g.screen.page == ids.PREVIEW:
            printing_or_paused = (g.klippy.print_stats_state == "printing" or g.klippy.print_stats_state == "paused")
            if widget_id == ids.ALL_TO_MAIN:
                if printing_or_paused:
                    page_to(ids.PRINTING)
                    g.screen.jump_print = False
                else:
                    page_to(ids.MAIN)
            elif widget_id == ids.ALL_TO_FILE_LIST:
                pass
            elif widget_id == ids.ALL_TO_ADJUST:
                if printing_or_paused:
                    page_to(ids.PRINTING)
                    g.screen.jump_print = False
                else:
                    actions.go_to_adjust()
            elif widget_id == ids.ALL_TO_SETTING:
                if printing_or_paused:
                    page_to(ids.PRINTING)
                    g.screen.jump_print = False
                else:
                    actions.go_to_setting()
            elif widget_id == ids.PREVIEW_BACK:
                # 4.4.3 CLL keep the preview page from getting stuck
                if printing_or_paused:
                    page_to(ids.PRINTING)
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
            elif widget_id == ids.PREVIEW_START:
                if printing_or_paused:
                    page_to(ids.PRINTING)
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
                        page_to(ids.PRINT_NO_FILAMENT)
                g.screen.main_picture_detected = False
                g.screen.main_picture_refreshed = False
            elif widget_id == ids.PREVIEW_BED_LEVELING:
                if printing_or_paused:
                    page_to(ids.PRINTING)
                    g.screen.jump_print = False
                else:
                    if g.screen.bed_leveling == True:
                        g.screen.bed_leveling = False
                    else:
                        g.screen.bed_leveling = True
            elif widget_id == ids.PREVIEW_TIMELAPSE:
                actions.switch_timelapse_state()

    elif page_id == ids.PREVIEW_POP_1 or page_id == ids.PREVIEW_POP_2:
        if widget_id == ids.PREVIEW_POP_YES:
            page_to(ids.PRINTING)
        elif widget_id == ids.PREVIEW_POP_NO_POP:
            if g.screen.page == ids.PREVIEW_POP_1:
                g.screen.preview_pop_1_on = False
            elif g.screen.page == ids.PREVIEW_POP_2:
                g.screen.preview_pop_2_on = False
            page_to(ids.PRINTING)

    elif page_id == ids.PRINTING:
        if widget_id in (ids.PRINTING_EXTRUDER, ids.PRINTING_HEATER_BED, ids.PRINTING_FAN_1,
                         ids.PRINTING_FAN_2, ids.PRINTING_FAN_3, ids.PRINTING_HOT):
            g.screen.printing_keyboard_enabled = True
            pages.clear_printing_arg()
        elif widget_id == ids.PRINTING_NEXT:
            page_to(ids.PRINTING_2)
        elif widget_id == ids.PRINTING_EMERGENCY_STOP:
            page_to(ids.STOP_CONFIRM)
        elif widget_id == ids.PRINTING_PAUSE_RESUME:
            g.klippy.ready = False
            actions.set_print_pause()
            page_to(ids.PRINT_FILAMENT)
            pages.clear_printing_arg()
        elif widget_id == ids.PRINTING_STOP:
            page_to(ids.PRINT_STOP)
            pages.clear_printing_arg()

    elif page_id == ids.PRINTING_KB:
        if widget_id == ids.PRINTING_KB_BACK:
            g.screen.printing_keyboard_enabled = False
            MKSLOG_BLUE("Restored")
        elif widget_id == ids.PRINTING_KB_MUTE:
            MKSLOG_BLUE("Silent mode switched")
            if g.screen.muted == False:
                g.screen.muted = True
                actions.set_printer_speed(50)
            else:
                g.screen.muted = False
                actions.set_printer_speed(100)
        elif widget_id == ids.PRINTING_KB_PAUSE_RESUME:
            g.screen.printing_keyboard_enabled = False
            actions.set_print_pause()
            page_to(ids.PRINT_FILAMENT)
            pages.clear_printing_arg()
        elif widget_id == ids.PRINTING_KB_STOP:
            g.screen.printing_keyboard_enabled = False
            page_to(ids.PRINT_STOP)
            pages.clear_printing_arg()

    elif page_id == ids.PRINT_ZOFFSET:
        if widget_id == ids.PRINT_ZOFFSET_BACK:
            g.screen.printing_keyboard_enabled = False
            page_to(ids.PRINTING_2)
        elif widget_id == ids.PRINT_ZOFFSET_SET_001:
            actions.set_intern_zoffset(0.01)
        elif widget_id == ids.PRINT_ZOFFSET_SET_005:
            actions.set_intern_zoffset(0.05)
        elif widget_id == ids.PRINT_ZOFFSET_SET_01:
            actions.set_intern_zoffset(0.1)
        elif widget_id == ids.PRINT_ZOFFSET_SET_05:
            actions.set_intern_zoffset(0.5)
        elif widget_id == ids.PRINT_ZOFFSET_UP:
            actions.set_zoffset(False)
        elif widget_id == ids.PRINT_ZOFFSET_DOWN:
            actions.set_zoffset(True)
        elif widget_id == ids.PRINT_ZOFFSET_PAUSE_RESUME:
            g.klippy.ready = False
            actions.set_print_pause()
            page_to(ids.PRINT_FILAMENT)
            pages.clear_printing_arg()
        elif widget_id == ids.PRINT_ZOFFSET_STOP:
            page_to(ids.PRINT_STOP)

    elif page_id == ids.PRINT_FILAMENT:
        if widget_id == ids.PRINT_FILAMENT_ON_OFF:
            actions.set_print_filament_target()
        elif widget_id == ids.PRINT_FILAMENT_T_UP:
            actions.set_filament_extruder_target(True)
        elif widget_id == ids.PRINT_FILAMENT_T_DOWN:
            actions.set_filament_extruder_target(False)
        elif widget_id == ids.PRINT_FILAMENT_LOAD:
            g.screen.load_mode = True
            page_to(ids.PRE_HEAT)
        elif widget_id == ids.PRINT_FILAMENT_UNLOAD:
            g.screen.load_mode = False
            page_to(ids.PRE_HEAT)
        elif widget_id == ids.PRINT_FILAMENT_PAUSE_RESUME:
            MKSLOG_BLUE("get_filament_detected_enable: %d", int(actions.get_filament_detected_enable()))
            MKSLOG_BLUE("get_filament_detected: %d", int(actions.get_filament_detected()))
            g.klippy.ready = False
            page_to(ids.PRINTING)
            actions.set_print_resume()
        elif widget_id == ids.PRINT_FILAMENT_STOP:
            page_to(ids.PRINT_STOP)
            pages.clear_printing_arg()
        elif widget_id == ids.PRINT_FILAMENT_RETRACT:
            actions.send_gcode("M603\n")
        elif widget_id == ids.PRINT_FILAMENT_EXTRUDE:
            actions.set_print_filament_dist(50)
            actions.start_extrude()

    elif page_id == ids.PRINTING_2:
        if widget_id == ids.PRINTING_2_BACK:
            page_to(ids.PRINTING)
        elif widget_id in (ids.PRINTING_2_SPEED, ids.PRINTING_2_FLOW):
            g.screen.printing_keyboard_enabled = True
            pages.clear_printing_arg()
        elif widget_id == ids.PRINTING_2_ZOFFSET:
            page_to(ids.PRINT_ZOFFSET)
        elif widget_id == ids.PRINTING_2_PAUSE_RESUME:
            g.klippy.ready = False
            actions.set_print_pause()
            page_to(ids.PRINT_FILAMENT)
            pages.clear_printing_arg()
        elif widget_id == ids.PRINTING_2_STOP:
            page_to(ids.PRINT_STOP)
        elif widget_id == ids.PRINTING_2_CASE_LIGHT:
            actions.led_on_off()

    elif page_id == ids.PRINT_FINISH:
        if widget_id == ids.PRINT_FINISH_YES:
            actions.finish_print()

    elif page_id == ids.PRINT_STOP:
        if widget_id == ids.PRINT_STOP_YES:
            g.klippy.idle_timeout_state = "Printing"
            page_to(ids.PRINT_STOPPING)
            actions.cancel_print()
        elif widget_id == ids.PRINT_STOP_NO:
            page_to(g.screen.previous_page)

    # 4.4.22 emergency stop from the printing page
    elif page_id == ids.STOP_CONFIRM:
        if widget_id == ids.STOP_CONFIRM_YES:
            page_to(ids.PRINT_STOPPING)
            g.klippy.print_stats_state = "paused"
            actions.motors_off()
        elif widget_id == ids.STOP_CONFIRM_NO:
            page_to(ids.PRINTING)

    elif page_id == ids.PRINT_NO_FILAMENT:
        if widget_id == ids.PRINT_NO_FILAMENT_YES:
            g.klippy.filament_detected = True
            if g.screen.previous_page == ids.PREVIEW:
                actions.get_object_status()
                page_to(ids.MOVE)
            else:
                actions.get_object_status()
                page_to(ids.PRINT_FILAMENT)

    elif page_id == ids.PRINT_NO_FILAMENT_2 or page_id == ids.PRINT_LOW_TEMP:
        if page_id == ids.PRINT_NO_FILAMENT_2:
            if widget_id == ids.PRINT_NO_FILAMENT_2_YES:
                actions.get_object_status()
                page_to(ids.PRINT_FILAMENT)
            # NOTE: no "break" in the original - falls through into the next case
        if widget_id == ids.PRINT_LOW_TEMP_YES:
            g.klippy.idle_timeout_state = "Ready"
            page_to(ids.PRINT_FILAMENT)

    elif page_id == ids.MOVE:
        if widget_id == ids.MOVE_SET_01:
            actions.set_move_dist(0.1)
        elif widget_id == ids.MOVE_SET_1:
            actions.set_move_dist(1.0)
        elif widget_id == ids.MOVE_SET_10:
            actions.set_move_dist(10.0)
        elif widget_id == ids.MOVE_Z_UP:
            actions.move_z_decrease()
        elif widget_id == ids.MOVE_Z_DOWN:
            actions.move_z_increase()
        elif widget_id == ids.MOVE_MOTOR:
            actions.move_motors_off()
        elif widget_id == ids.MOVE_X_UP:
            actions.move_x_increase()
        elif widget_id == ids.MOVE_X_DOWN:
            actions.move_x_decrease()
        elif widget_id == ids.MOVE_Y_UP:
            actions.move_y_increase()
        elif widget_id == ids.MOVE_Y_DOWN:
            actions.move_y_decrease()
        elif widget_id == ids.MOVE_HOME:
            actions.move_home()
        elif widget_id == ids.MOVE_TO_FILAMENT:
            page_to(ids.FILAMENT)
            g.screen.adjust_mode = "Filament"
        elif widget_id == ids.ALL_TO_MAIN:
            page_to(ids.MAIN)
        elif widget_id == ids.ALL_TO_FILE_LIST:
            filelist.go_to_file_list()
        elif widget_id == ids.ALL_TO_ADJUST:
            pass
        elif widget_id == ids.ALL_TO_SETTING:
            actions.go_to_setting()

    elif page_id == ids.MOVE_POP_1:
        if widget_id == ids.MOVE_POP_1_YES:
            if (g.screen.previous_page == ids.PRINTING or g.screen.previous_page == ids.PRINT_ZOFFSET
                    or g.screen.previous_page == ids.PRINTING_2):
                actions.cancel_print()
                page_to(ids.PRINT_STOPPING)
            else:
                page_to(ids.MOVE)

    elif page_id == ids.MOVE_POP_2:
        if widget_id == ids.MOVE_POP_2_YES:
            page_to(ids.MOVE)
            actions.move_home()
        elif widget_id == ids.MOVE_POP_2_NO:
            page_to(ids.MOVE)

    elif page_id == ids.FILAMENT_SET_FAN:
        if widget_id == ids.ALL_TO_MAIN:
            page_to(ids.MAIN)
        elif widget_id == ids.ALL_TO_FILE_LIST:
            filelist.go_to_file_list()
        elif widget_id == ids.ALL_TO_ADJUST:
            pass
        elif widget_id == ids.ALL_TO_SETTING:
            actions.go_to_setting()
        elif widget_id == ids.FILAMENT_SET_FAN_BACK:
            page_to(ids.FILAMENT)
        elif widget_id == ids.FILAMENT_SET_FAN_SETTING:
            g.screen.move_fan_setting = True      # the slider is being dragged

    elif page_id == ids.FILAMENT_KB:
        if widget_id == ids.ALL_TO_MAIN:
            page_to(ids.MAIN)
        elif widget_id == ids.ALL_TO_FILE_LIST:
            filelist.go_to_file_list()
        elif widget_id == ids.ALL_TO_ADJUST:
            pass
        elif widget_id == ids.ALL_TO_SETTING:
            actions.go_to_setting()
        elif widget_id == ids.FILAMENT_KB_BACK:
            page_to(ids.FILAMENT)

    elif page_id == ids.FILAMENT:
        if widget_id == ids.ALL_TO_MAIN:
            page_to(ids.MAIN)
        elif widget_id == ids.ALL_TO_FILE_LIST:
            filelist.go_to_file_list()
        elif widget_id == ids.ALL_TO_ADJUST:
            pass
        elif widget_id == ids.ALL_TO_SETTING:
            actions.go_to_setting()
        elif widget_id in (ids.FILAMENT_SET_EXTRUDER, ids.FILAMENT_SET_HEATERBED, ids.FILAMENT_SET_HOT):
            page_to(ids.FILAMENT_KB)
        elif widget_id == ids.FILAMENT_EXTRUDER_UP:
            g.klippy.idle_timeout_state = "Printing"
            g.screen.filament_extrude_button = True
            actions.start_retract()
        elif widget_id == ids.FILAMENT_EXTRUDER_DOWN:
            g.klippy.idle_timeout_state = "Printing"
            g.screen.filament_extrude_button = True
            actions.start_extrude()
        elif widget_id == ids.FILAMENT_EXTRUDER_ON_OFF:
            actions.filament_extruder_target()
        elif widget_id == ids.FILAMENT_HEATERBED_ON_OFF:
            actions.filament_heater_bed_target()
        elif widget_id == ids.FILAMENT_HOT_ON_OFF:
            actions.filament_hot_target()
        elif widget_id == ids.FILAMENT_TO_FAN:
            page_to(ids.FILAMENT_SET_FAN)
        elif widget_id == ids.FILAMENT_LOAD:
            g.screen.load_mode = True
            page_to(ids.PRE_HEAT)
        elif widget_id == ids.FILAMENT_UNLOAD:
            g.screen.load_mode = False
            page_to(ids.PRE_HEAT)
        elif widget_id == ids.FILAMENT_SET_10:
            actions.set_print_filament_dist(10)
        elif widget_id == ids.FILAMENT_SET_50:
            actions.set_print_filament_dist(50)
        elif widget_id == ids.FILAMENT_SET_100:
            actions.set_print_filament_dist(100)
        elif widget_id == ids.FILAMENT_TO_MOVE:
            page_to(ids.MOVE)
            g.screen.adjust_mode = "Move"

    elif page_id == ids.FILAMENT_POP_1:
        if widget_id == ids.FILAMENT_POP_1_YES:
            g.klippy.idle_timeout_state = "Ready"
            page_to(ids.FILAMENT)

    elif page_id == ids.FILAMENT_POP_2:
        if widget_id == ids.FILAMENT_POP_2_YES:
            actions.send_gcode("SET_HEATER_TEMPERATURE HEATER=extruder TARGET=0\n")
            if g.klippy.print_stats_state == "paused":
                page_to(ids.PRINT_FILAMENT)
            else:
                page_to(ids.FILAMENT)
        elif widget_id == ids.FILAMENT_POP_2_TO_LOAD:
            g.screen.load_mode = True
            page_to(ids.PRE_HEAT)
        elif widget_id == ids.FILAMENT_POP_2_NEXT:
            actions.filament_load()
        elif widget_id == ids.FILAMENT_POP_2_BACK:
            page_to(ids.UNLOAD_MODE)

    elif page_id == ids.FILAMENT_POP_3:
        if widget_id == ids.FILAMENT_POP_3_NEXT:
            actions.filament_load()
        elif widget_id == ids.FILAMENT_POP_3_YES:
            actions.send_gcode("SET_HEATER_TEMPERATURE HEATER=extruder TARGET=0\n")
            if g.klippy.print_stats_state == "paused":
                page_to(ids.PRINT_FILAMENT)
            else:
                page_to(ids.FILAMENT)
        elif widget_id == ids.FILAMENT_POP_3_RETRY:
            g.screen.load_mode = True
            page_to(ids.FILAMENT_POP_3)
            actions.filament_load()
        elif widget_id == ids.FILAMENT_POP_3_BACK:
            page_to(ids.PRE_HEAT)

    elif page_id == ids.FILAMENT_UNLOAD_FINISH:
        if widget_id == ids.FILAMENT_UNLOAD_FINISH_YES:
            page_to(ids.FILAMENT)

    elif page_id == ids.LEVEL_MODE:
        if widget_id == ids.ALL_TO_MAIN:
            page_to(ids.MAIN)
        elif widget_id == ids.ALL_TO_FILE_LIST:
            filelist.go_to_file_list()
        elif widget_id == ids.ALL_TO_ADJUST:
            actions.go_to_adjust()
        elif widget_id == ids.ALL_TO_SETTING:
            pass
        elif widget_id == ids.LEVEL_MODE_AUTO_LEVEL:
            actions.get_object_status()
            page_to(ids.AUTO_HEATERBED)
        elif widget_id == ids.LEVEL_MODE_SYNTONY:
            actions.go_to_syntony_move()
        elif widget_id == ids.LEVEL_MODE_BED_CALIBRATION:
            page_to(ids.CALIBRATE_WARNING)
        elif widget_id == ids.LEVEL_MODE_TO_COMMON_SETTING:
            page_to(ids.COMMON_SETTING)
            g.screen.set_mode = "Common_setting"
        elif widget_id == ids.LEVEL_MODE_ZOFFSET:
            page_to(ids.ZOFFSET)

    elif page_id == ids.ZOFFSET:
        if widget_id == ids.ZOFFSET_BACK:
            page_to(ids.LEVEL_MODE)

    elif page_id == ids.AUTO_HEATERBED:
        if widget_id == ids.AUTO_HEATERBED_DOWN:
            actions.set_auto_level_heater_bed_target(False)
        elif widget_id == ids.AUTO_HEATERBED_UP:
            actions.set_auto_level_heater_bed_target(True)
        elif widget_id == ids.AUTO_HEATERBED_ON_OFF:
            actions.filament_heater_bed_target()
        elif widget_id == ids.AUTO_HEATERBED_BACK:
            page_to(ids.LEVEL_MODE)
        elif widget_id == ids.AUTO_HEATERBED_NEXT:
            if g.klippy.heater_bed_target < 35:
                page_to(ids.AUTO_WARNING)
            else:
                g.screen.auto_level_button_enabled = True
                g.klippy.idle_timeout_state = "Printing"
                actions.start_auto_level()

    elif page_id == ids.AUTO_FINISH:
        if widget_id == ids.AUTO_FINISH_YES:
            cout("Auto levelling finished")
            page_to(ids.LEVEL_MODE)

    elif page_id == ids.PRE_BED_CALIBRATION:
        if widget_id == ids.PRE_BED_CALIBRATION_SET_001:
            actions.set_auto_level_dist(0.01)
        elif widget_id == ids.PRE_BED_CALIBRATION_SET_005:
            actions.set_auto_level_dist(0.05)
        elif widget_id == ids.PRE_BED_CALIBRATION_SET_01:
            actions.set_auto_level_dist(0.1)
        elif widget_id == ids.PRE_BED_CALIBRATION_SET_05:
            actions.set_auto_level_dist(0.5)
        elif widget_id == ids.PRE_BED_CALIBRATION_UP:
            actions.bed_adjust(True)
        elif widget_id == ids.PRE_BED_CALIBRATION_DOWN:
            actions.bed_adjust(False)
        elif widget_id == ids.PRE_BED_CALIBRATION_ENTER:
            actions.bed_calibrate()

    elif page_id == ids.BED_CALIBRATION:
        if widget_id == ids.BED_CALIBRATION_NEXT:
            actions.bed_calibrate()

    elif page_id == ids.BED_FINISH:
        if widget_id == ids.BED_FINISH_OK:
            page_to(ids.LEVEL_MODE)
        elif widget_id == ids.BED_FINISH_SCREW1:
            g.klippy.idle_timeout_state = "Printing"
            actions.send_gcode("G1 Z10 F600\n")
            actions.send_gcode("G1 X10 Y10 F9000\n")
            actions.send_gcode("G1 Z0 F600\n")
            g.screen.manual_count = -1
            page_to(ids.BED_MOVING)
        elif widget_id == ids.BED_FINISH_SCREW2:
            g.klippy.idle_timeout_state = "Printing"
            actions.send_gcode("G1 Z10 F600\n")
            actions.send_gcode("G1 X230 Y10 F9000\n")
            actions.send_gcode("G1 Z0 F600\n")
            g.screen.manual_count = -1
            page_to(ids.BED_MOVING)
        elif widget_id == ids.BED_FINISH_SCREW3:
            g.klippy.idle_timeout_state = "Printing"
            actions.send_gcode("G1 Z10 F600\n")
            actions.send_gcode("G1 X125 Y240 F9000\n")
            actions.send_gcode("G1 Z0 F600\n")
            g.screen.manual_count = -1
            page_to(ids.BED_MOVING)
        elif widget_id == ids.BED_FINISH_Z_TILT:
            g.klippy.idle_timeout_state = "Printing"
            actions.send_gcode("G28\nZ_TILT_ADJUST\n")
            actions.send_gcode("G1 Z10 F600\nG1 X0 Y0 F9000\n")
            g.screen.manual_count = -2
            page_to(ids.BED_MOVING)

    elif page_id == ids.SYNTONY_MOVE:
        if widget_id == ids.SYNTONY_MOVE_JUMP_OUT:
            actions.send_gcode("SAVE_CONFIG\n")
            page_to(ids.SYNTONY_FINISH)

    elif page_id == ids.SYNTONY_FINISH:
        if widget_id == ids.SYNTONY_FINISH_YES:
            page_to(ids.LEVEL_MODE)
            system("sync")
            settings.get_babystep()           # 4.4.22 (was init_mks_status())
            actions.sub_object_status()
            actions.get_object_status()

    elif page_id == ids.INTERNET:
        if _nav_guarded(widget_id):
            pass
        elif widget_id == ids.ALL_TO_SETTING:
            pass
        elif widget_id == ids.INTERNET_REFRESH:
            cout("################## refresh button pressed")
            wifi_ui.scan_ssid_and_show()
            cout("Waiting 3s...")
            sleep(3)
            wifi_ui.scan_ssid_and_show()
        elif widget_id == ids.INTERNET_TO_WIFI:
            pass
        elif widget_id == ids.INTERNET_TO_SETTING:
            page_to(ids.COMMON_SETTING)

    elif page_id == ids.WIFI_LIST:
        if _nav_guarded(widget_id):
            pass
        elif widget_id == ids.ALL_TO_SETTING:
            pass
        elif widget_id in (ids.WIFI_LIST_SSID_1, ids.WIFI_LIST_SSID_2, ids.WIFI_LIST_SSID_3,
                           ids.WIFI_LIST_SSID_4, ids.WIFI_LIST_SSID_5):
            index = widget_id - ids.WIFI_LIST_SSID_1
            if g.screen.wifi_ssid_button_enabled[index] == True:
                wifi_ui.get_wifi_list_ssid(index)
                netui.open_keyboard(netui.KB_PSK_SCANNED, 8, g.net.get_wifi_name)
        elif widget_id == ids.WIFI_LIST_SAVED:
            netui.open_saved()
        elif widget_id == ids.WIFI_LIST_HIDDEN:
            netui.open_hidden()
        elif widget_id == ids.WIFI_LIST_REFRESH:
            cout("################## refresh button pressed")
            wifi_ui.scan_ssid_and_show()
            # 4.4.1 CLL wifi refresh fix
        elif widget_id == ids.WIFI_LIST_PREVIOUS:
            if g.net.wifi_current_pages > 0:
                cout("page_wifi_current_pages = ", g.net.wifi_current_pages)
                cout("page_wifi_ssid_list_pages = ", g.net.wifi_ssid_list_pages)
                g.net.wifi_current_pages -= 1
                set_page_wifi_ssid_list(g.net.wifi_current_pages)
                wifi_ui.refresh_wifi_list()
        elif widget_id == ids.WIFI_LIST_NEXT:
            if g.net.wifi_current_pages < g.net.wifi_ssid_list_pages - 1:
                cout("page_wifi_current_pages = ", g.net.wifi_current_pages)
                cout("page_wifi_ssid_list_pages = ", g.net.wifi_ssid_list_pages)
                g.net.wifi_current_pages += 1
                set_page_wifi_ssid_list(g.net.wifi_current_pages)
                wifi_ui.refresh_wifi_list()
        elif widget_id == ids.WIFI_LIST_TO_WIFI:
            pass
        elif widget_id == ids.WIFI_LIST_TO_SETTING:
            wifi_ui.refresh_ip_address()             # 4.4.22: the network page (was the QR code page)

    # 4.4.24: the timer of the page reports a connection that takes too long
    elif page_id == ids.WIFI_CONNECT:
        if widget_id == ids.WIFI_CONNECT_TIMEOUT:
            page_to(ids.WIFI_FAILED)

    elif page_id == ids.WIFI_SUCCESS:
        if widget_id == ids.WIFI_SUCCESS_YES:
            settings.wifi_save_config()

    elif page_id == ids.WIFI_FAILED:
        if widget_id == ids.WIFI_FAILED_YES:
            wifi_ui.go_to_network()                  # 4.4.22 (was page_to(ids.WIFI_LIST))

    elif page_id == ids.WIFI_KB:
        if widget_id == ids.WIFI_KB_BACK:
            netui.keyboard_back()

    elif page_id in (ids.NET_SAVED, ids.NET_DETAIL, ids.NET_CONFIRM, ids.NET_INFO):
        if _nav_guarded(widget_id):
            pass
        elif page_id == ids.NET_SAVED:
            netui.saved_clicked(widget_id)
        elif page_id == ids.NET_DETAIL:
            netui.detail_clicked(widget_id)
        elif page_id == ids.NET_CONFIRM:
            netui.confirm_clicked(widget_id)
        else:
            netui.info_clicked(widget_id)

    elif page_id == ids.COMMON_SETTING:
        if _nav_guarded(widget_id):
            pass
        elif widget_id == ids.ALL_TO_SETTING:
            pass
        elif widget_id == ids.COMMON_SETTING_LANGUAGE:
            page_to(ids.LANGUAGE)
        elif widget_id == ids.COMMON_SETTING_WIFI:
            wifi_ui.refresh_ip_address()             # 4.4.22: the network page (was the QR code page)
        elif widget_id == ids.COMMON_SETTING_SYSTEM:
            actions.go_to_reset()
        elif widget_id == ids.COMMON_SETTING_SERVICE:
            page_to(ids.SERVICE)
        elif widget_id == ids.COMMON_SETTING_SCREEN_SLEEP:
            page_to(ids.SLEEP_MODE)
        elif widget_id == ids.COMMON_SETTING_RESTORE:
            page_to(ids.RESTORE_CONFIG)
        elif widget_id == ids.COMMON_SETTING_OOBE_OFF:
            settings.set_oobe_enabled(False)
            page_to(ids.COMMON_SETTING)
        elif widget_id == ids.COMMON_SETTING_OOBE_ON:
            settings.set_oobe_enabled(True)
        elif widget_id == ids.COMMON_SETTING_TO_LEVEL_MODE:
            page_to(ids.LEVEL_MODE)
            g.screen.set_mode = "Level_mode"

    elif page_id in (ids.LANGUAGE, ids.SERVICE, ids.SYS_OK, ids.RESET, ids.SLEEP_MODE):
        if _nav_guarded(widget_id):
            pass
        elif widget_id == ids.ALL_TO_SETTING:
            pass
        elif widget_id == ids.BACK_TO_COMMON_SETTING:
            page_to(ids.COMMON_SETTING)
        elif widget_id == ids.RESET_PRINT_LOG:
            filelist.print_log()
        elif widget_id == ids.RESET_RESTART_KLIPPER:
            actions.reset_klipper()
        elif widget_id == ids.RESET_RESTART_FIRMWARE:
            actions.reset_firmware()

    elif page_id == ids.UPDATE_SUCCESS:
        if widget_id == ids.UPDATE_SUCCESS_YES:
            actions.finish_screen_update()
            page_to(ids.MAIN)

    elif page_id == ids.PRINT_LOG_F or page_id == ids.PRINT_LOG_S:
        if widget_id == ids.PRINT_LOG_YES:
            actions.go_to_reset()

    elif page_id == ids.DETECT_ERROR:
        if widget_id == ids.DETECT_ERROR_YES:
            if g.screen.previous_page == ids.AUTO_MOVING or g.screen.previous_page == ids.OPEN_CALIBRATE:
                actions.reset_klipper()
            page_to(ids.MAIN)
            actions.clear_previous_data()

    elif page_id == ids.GCODE_ERROR:
        if widget_id == ids.GCODE_ERROR_YES:
            page_to(ids.MAIN)

    # 4.4.2 CLL screen sleep feature
    elif page_id == ids.SCREEN_SLEEP:
        # 4.4.22: the case light is no longer switched off while the screen sleeps
        if widget_id == ids.SCREEN_SLEEP_ENTER:
            page_to(ids.SCREEN_SLEEP)
        elif widget_id == ids.SCREEN_SLEEP_EXIT:
            if g.screen.previous_page == ids.FILE_LIST:
                filelist.go_to_file_list()
            else:
                page_to(g.screen.previous_page)
                actions.get_object_status()

    elif page_id == ids.RESTORE_CONFIG:
        if widget_id == ids.RESTORE_CONFIG_YES:
            settings.restore_config()
        elif widget_id == ids.RESTORE_CONFIG_NO:
            page_to(ids.COMMON_SETTING)

    elif page_id == ids.LEVEL_ERROR:      # CLL dedicated pop-up for levelling errors
        if widget_id == ids.LEVEL_ERROR_YES:
            page_to(ids.MAIN)

    elif page_id == ids.MEMORY_WARNING:
        if widget_id == ids.MEMORY_WARNING_YES:
            page_to(ids.MAIN)

    elif page_id == ids.PRE_HEAT:
        if widget_id in (ids.PRE_HEAT_SET_220, ids.PRE_HEAT_SET_250, ids.PRE_HEAT_SET_300):
            g.screen.load_target = {ids.PRE_HEAT_SET_220: 220, ids.PRE_HEAT_SET_250: 250,
                             ids.PRE_HEAT_SET_300: 300}[widget_id]
            if g.screen.load_mode == True:
                page_to(ids.FILAMENT_POP_3)
            else:
                page_to(ids.UNLOAD_MODE)
        elif widget_id == ids.PRE_HEAT_BACK:
            if g.klippy.print_stats_state == "paused":
                page_to(ids.PRINT_FILAMENT)
            else:
                page_to(ids.FILAMENT)

    elif page_id == ids.RESUME_PRINT:
        if widget_id == ids.RESUME_PRINT_YES:
            page_to(ids.RE_PRINTING)
            actions.send_gcode("RESUME_INTERRUPTED\n")
        elif widget_id == ids.RESUME_PRINT_NO:
            page_to(ids.MAIN)
            actions.send_gcode("CLEAR_LAST_FILE")
        elif widget_id == ids.RESUME_PRINT_LOADED:
            g.screen.jump_resume_print = False      # 4.4.24: the page reports that it is shown

    # 4.4.24 network page (4.4.22 binary); the QIDI Link buttons are not implemented
    elif page_id == ids.INTERNET_PAGE:
        if _nav_guarded(widget_id):
            pass
        elif widget_id == ids.INTERNET_PAGE_BACK:
            page_to(ids.COMMON_SETTING)
        elif widget_id == ids.INTERNET_PAGE_ETHERNET:
            # 1: ethernet, 0: wifi (the page shows the address on the next refresh)
            settings.set_ethernet(0 if g.config.ethernet == 1 else 1)
        elif widget_id == ids.INTERNET_PAGE_WIFI:
            wifi_ui.go_to_network()
        elif widget_id == ids.INTERNET_PAGE_INFO:
            netui.open_info()
        elif widget_id == ids.INTERNET_PAGE_SAVED:
            netui.open_saved()
        elif widget_id == ids.INTERNET_PAGE_HIDDEN:
            netui.open_hidden()

    elif page_id == ids.UNLOAD_MODE:
        if widget_id == ids.UNLOAD_MODE_MANUAL:
            page_to(ids.FILAMENT_POP_2)
        elif widget_id == ids.UNLOAD_MODE_AUTO:
            page_to(ids.AUTO_UNLOAD)
            actions.filament_unload()
        elif widget_id == ids.UNLOAD_MODE_BACK:
            page_to(ids.PRE_HEAT)

    elif page_id == ids.AUTO_UNLOAD:
        if widget_id == ids.AUTO_UNLOAD_YES:
            actions.send_gcode("SET_HEATER_TEMPERATURE HEATER=extruder TARGET=0\n")
            if g.klippy.print_stats_state == "paused":
                page_to(ids.PRINT_FILAMENT)
            else:
                page_to(ids.FILAMENT)
        elif widget_id == ids.AUTO_UNLOAD_TO_LOAD:
            g.screen.load_mode = True
            page_to(ids.PRE_HEAT)

    elif page_id == ids.AUTO_WARNING:
        if widget_id == ids.AUTO_WARNING_YES:
            page_to(ids.AUTO_HEATERBED)

    elif page_id == ids.CALIBRATE_WARNING:
        if widget_id == ids.CALIBRATE_WARNING_NEXT:
            g.screen.manual_count = 4
            actions.bed_calibrate()
        elif widget_id == ids.CALIBRATE_WARNING_BACK:
            page_to(ids.LEVEL_MODE)


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
