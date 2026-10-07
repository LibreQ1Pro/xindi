"""Port of src/event.cpp / include/event.h - page refresh functions and printer actions."""

import json as _json
import os
import threading
import urllib.request

from . import paths
from . import state as g
from . import pics
from . import ui
from .ui import page_to
from .cpp import (to_string, substr, f32, c_int, c_round, cdiv, cmod, stof, stoi, s2b, b2s, cstr,
                  access, system, sleep, usleep, popen_read, read_file, getline_all, json_parse,
                  stream_hex_int, str_lower_ascii, pthread_create, jget, jstr, i32)
from .mks_log import MKSLOG, MKSLOG_BLUE, MKSLOG_RED, MKSLOG_YELLOW, MKSLOG_GREEN, cout, cerr
from .send_msg import (send_cmd_txt, send_cmd_val, send_cmd_pco, send_cmd_picc, send_cmd_picc2,
                       send_cmd_vis, send_cmd_pic, send_cmd_cp_close, send_cmd_cp_image, send_cmd_baud,
                       send_cmd_txt_plus, send_cmd_tsw, send_cmd_pco2)
from .MakerbaseSerial import set_option
from .MoonrakerAPI import (json_run_a_gcode, json_subscribe_to_printer_object_status,
                           json_query_printer_object_status, json_get_gcode_metadata, json_file_delete,
                           json_print_a_file, json_emergency_stop, json_get_job_totals,
                           json_get_klippy_host_information)
from .MakerbasePanel import move
from .KlippyGcodes import (AXIS_X, AXIS_Y, AXIS_Z, set_heater_temp, set_fan_speed, set_fan0_speed,
                           set_fan2_speed, set_fan3_speed, set_speed_rate)
from .MakerbaseShell import execute_cmd
from .network import get_eth0_ip, get_wlan0_ip
from .MakerbaseParseIni import (mksini_load, mksini_free, mksini_getstring, mksini_getint,
                                mksini_getboolean, mksini_set, mksini_save, mksversion_load,
                                mksversion_free, mksversion_soc, mksversion_mcu, mksversion_ui,
                                updateini_load, progressini_load)
from .mks_printer import subscribe_objects_status, get_cal_printing_time
from . import mks_file
from .mks_file import output_imgdata
from . import thumbnail
from .send_jpg import delete_small_jpg
from .MakerbaseWiFi import (detected_wlan0, get_wlan0_status, get_ssid_list_pages,
                            set_page_wifi_ssid_list)
from . import network
from .mks_update import detect_update

DEFAULT_DIR = "gcodes/"

# Text written to the "t6" widget of the common settings page when the
# out-of-box guide is enabled.  It means "Startup guide"; the original
# (Chinese, UTF-8) bytes are kept because they are sent to the screen.
TEXT_STARTUP_GUIDE = "\u5f00\u673a\u5f15\u5bfc"


class Server_config(object):
    def __init__(self, address="", name=""):
        self.address = address
        self.name = name


def _ep():
    return g.ep


def _top(stack):
    """std::stack::top() (undefined behaviour on an empty stack in C++)"""
    return stack[-1] if stack else ""


def _replace_for_screen(text):
    text = text.replace("\n", ".")
    text = text.replace("'", " ")
    text = text.replace("\"", " ")
    return text


# ---------------------------------------------------------------------------
# Page refresh
# ---------------------------------------------------------------------------

def refresh_page_show():
    # 4.4.22: nothing is sent to the screen while the list pictures are transferred
    if g.send_jpg_status:
        return
    # CLL the jumps below are unconditional, the flags were set after the
    # checks were done (the flag has to be reset before switching the page,
    # otherwise this would loop forever)
    if g.jump_to_move_pop_1 == True:
        g.jump_to_move_pop_1 = False
        page_to(ui.TJC_PAGE_MOVE_POP_1)
    if g.jump_to_move_pop_2 == True:
        homing = "SET_KINEMATIC_POSITION Z=150\nSET_KINEMATIC_POSITION X=150\nSET_KINEMATIC_POSITION Y=150\n"
        moves = {
            1: "G91\nG1 X10 F3000\nG90\nM84\n",       # X_UP
            2: "G91\nG1 X-10 F3000\nG90\nM84\n",      # X_DOWN
            3: "G91\nG1 Y10 F3000\nG90\nM84\n",       # Y_UP
            4: "G91\nG1 Y-10 F3000\nG90\nM84\n",      # Y_DOWN
            5: "G91\nG1 Z-10 F600\nG90\nM84\n",       # Z_UP
            6: "G91\nG1 Z10 F600\nG90\nM84\n",        # Z_DOWN
        }
        if g.unhomed_move_mode in moves:
            g.ep.Send(json_run_a_gcode(homing))
            g.ep.Send(json_run_a_gcode(moves[g.unhomed_move_mode]))
        g.unhomed_move_mode = 0
        g.jump_to_move_pop_2 = False
        page_to(ui.TJC_PAGE_MOVE_POP_2)
    if g.jump_to_detect_error == True:
        g.jump_to_detect_error = False
        page_to(ui.TJC_PAGE_DETECT_ERROR)
        send_cmd_txt(g.tty_fd, "msg", g.error_message)
    if g.jump_to_level_error == True:
        g.jump_to_level_error = False
        page_to(ui.TJC_PAGE_LEVEL_ERROR)
    if g.jump_to_filament_pop_1 == True:
        g.jump_to_filament_pop_1 = False
        page_to(ui.TJC_PAGE_FILAMENT_POP_1)
    if g.jump_to_print_low_temp == True:
        g.jump_to_print_low_temp = False
        page_to(ui.TJC_PAGE_PRINT_LOW_TEMP)
    if g.jump_to_resume_print == True:
        # 4.4.24: the flag is reset when the page reports that it is shown
        page_to(ui.TJC_PAGE_RESUME_PRINT)
    if g.jump_to_memory_warning == True:
        g.jump_to_memory_warning = False
        page_to(ui.TJC_PAGE_MEMORY_WARNING)

    if g.current_page_id != ui.TJC_PAGE_PRINTING:
        if g.current_page_id in (ui.TJC_PAGE_PRINT_ZOFFSET, ui.TJC_PAGE_PRINT_FILAMENT):
            pass
        elif g.current_page_id in (ui.TJC_PAGE_PRINT_STOP, ui.TJC_PAGE_PRINT_NO_FILAMENT,
                                   ui.TJC_PAGE_PRINT_NO_FILAMENT_2, ui.TJC_PAGE_SHUTDOWN,
                                   ui.TJC_PAGE_PRINT_STOPPING, ui.TJC_PAGE_MOVE_POP_1,
                                   ui.TJC_PAGE_GCODE_ERROR, ui.TJC_PAGE_DETECT_ERROR, ui.TJC_PAGE_RESET,
                                   ui.TJC_PAGE_PREVIEW, ui.TJC_PAGE_PREVIEW_POP_1, ui.TJC_PAGE_PREVIEW_POP_2,
                                   ui.TJC_PAGE_PRINTING_2, ui.TJC_PAGE_FILAMENT_POP_2,
                                   ui.TJC_PAGE_FILAMENT_POP_3, ui.TJC_PAGE_STOP_CONFIRM,
                                   ui.TJC_PAGE_LINK_FIRST):
            pass
        else:
            if g.printer_print_stats_state == "printing":
                if g.printer_print_stats_filename != "":
                    g.main_picture_detected = False
                    g.main_picture_refreshed = False
                    g.printer_muted = False         # 4.4.22 silent mode is per print
                    MKSLOG_BLUE("Jumping to the print page\n")
                    sleep(1)
                    get_file_estimated_time(g.printer_print_stats_filename)
                    sleep(1)
                    g.jump_to_print = True
                    g.printer_ready = False
                    page_to(ui.TJC_PAGE_PREVIEW)

    if g.current_page_id != ui.TJC_PAGE_RESET:
        if g.current_page_id in (ui.TJC_PAGE_GCODE_ERROR, ui.TJC_PAGE_DETECT_ERROR, ui.TJC_PAGE_LEVEL_ERROR,
                                 ui.TJC_PAGE_SHUTDOWN, ui.TJC_PAGE_SERVICE, ui.TJC_PAGE_LANGUAGE,
                                 ui.TJC_PAGE_COMMON_SETTING, ui.TJC_PAGE_SLEEP_MODE, ui.TJC_PAGE_INTERNET,
                                 ui.TJC_PAGE_WIFI_LIST, ui.TJC_PAGE_WIFI_KB, ui.TJC_PAGE_WIFI_CONNECT,
                                 ui.TJC_PAGE_WIFI_FAILED, ui.TJC_PAGE_WIFI_SUCCESS, ui.TJC_PAGE_WIFI_SAVING,
                                 ui.TJC_PAGE_NET_SAVED, ui.TJC_PAGE_NET_DETAIL, ui.TJC_PAGE_NET_CONFIRM,
                                 ui.TJC_PAGE_NET_INFO,
                                 ui.TJC_PAGE_UPDATE_FOUND, ui.TJC_PAGE_UPDATE_NOT_FOUND, ui.TJC_PAGE_UPDATING,
                                 ui.TJC_PAGE_UPDATE_FINISH, ui.TJC_PAGE_RESTORE_CONFIG, ui.TJC_PAGE_INTERNET_PAGE,
                                 ui.TJC_PAGE_SERVER_SET, ui.TJC_PAGE_UPDATE_MODE, ui.TJC_PAGE_ONLINE_UPDATE,
                                 ui.TJC_PAGE_SEARCH_SERVER):
            pass
        else:
            # jump to the restart page when the toolhead board is disconnected
            if g.printer_webhooks_state == "shutdown" or g.printer_webhooks_state == "error":
                if g.printer_webhooks_state == "shutdown" and (g.current_page_id == ui.TJC_PAGE_AUTO_MOVING
                                                               or g.current_page_id == ui.TJC_PAGE_OPEN_CALIBRATE):
                    pass
                else:
                    page_to(ui.TJC_PAGE_RESET)
                    cout("Restart page")
                    if g.current_webhooks_state_message != g.printer_webhooks_state_message:
                        g.current_webhooks_state_message = g.printer_webhooks_state_message
                        send_cmd_txt(g.tty_fd, "err_msg", _replace_for_screen(g.printer_webhooks_state_message))
    elif g.current_page_id == ui.TJC_PAGE_RESET:
        if g.printer_webhooks_state == "shutdown" or g.printer_webhooks_state == "error":
            if g.current_webhooks_state_message != g.printer_webhooks_state_message:
                g.current_webhooks_state_message = g.printer_webhooks_state_message
                send_cmd_txt(g.tty_fd, "err_msg", _replace_for_screen(g.printer_webhooks_state_message))
        if g.printer_webhooks_state == "ready":
            page_to(ui.TJC_PAGE_SYS_OK)

    page = g.current_page_id
    if page == ui.TJC_PAGE_MAIN:
        refresh_page_main()
    elif page == ui.TJC_PAGE_PREVIEW:
        refresh_page_preview()
    elif page in (ui.TJC_PAGE_PRINTING, ui.TJC_PAGE_PRINTING_2):
        refresh_page_printing()
    elif page == ui.TJC_PAGE_PRINT_FILAMENT:
        refresh_page_print_filament()
    elif page == ui.TJC_PAGE_MOVE:
        refresh_page_move()
    elif page == ui.TJC_PAGE_PRINT_ZOFFSET:
        refresh_page_printing_zoffset()
    elif page == ui.TJC_PAGE_AUTO_MOVING:
        refresh_page_auto_moving()
    elif page == ui.TJC_PAGE_AUTO_FINISH:
        refresh_page_auto_finish()
    elif page == ui.TJC_PAGE_SYNTONY_MOVE:
        refresh_page_syntony_move()
    elif page == ui.TJC_PAGE_SYNTONY_FINISH:
        pass
    elif page == ui.TJC_PAGE_PRINT_STOPPING:
        refresh_page_stopping()
    elif page == ui.TJC_PAGE_PRE_BED_CALIBRATION:
        refresh_page_auto_level()
    elif page == ui.TJC_PAGE_OPEN_FILAMENTVIDEO_2:
        refresh_page_open_filament_video_2()
    elif page == ui.TJC_PAGE_ZOFFSET:
        refresh_page_zoffset()
    elif page == ui.TJC_PAGE_AUTO_HEATERBED:
        refresh_page_auto_heaterbed()
    elif page == ui.TJC_PAGE_OPEN_HEATERBED:
        refresh_page_open_heaterbed()
    elif page in (ui.TJC_PAGE_FILAMENT_POP_2, ui.TJC_PAGE_FILAMENT_POP_3):
        refresh_page_filament_pop()
    elif page in (ui.TJC_PAGE_PREVIEW_POP_1, ui.TJC_PAGE_PREVIEW_POP_2):
        refresh_page_preview_pop()
    elif page == ui.TJC_PAGE_FILE_LIST:
        pass        # 4.4.2 CLL local / USB buttons on the file list page
    elif page == ui.TJC_PAGE_BED_MOVING:
        refresh_page_bed_moving()
    elif page == ui.TJC_PAGE_OPEN_CALIBRATE:
        refresh_page_open_calibrate()
    elif page == ui.TJC_PAGE_COMMON_SETTING:
        refresh_page_common_setting()
    elif page == ui.TJC_PAGE_FILAMENT_SET_FAN:
        refresh_page_filament_set_fan()
    elif page == ui.TJC_PAGE_WIFI_KB:
        refresh_page_wifi_keyboard()
    elif page == ui.TJC_PAGE_FILAMENT:
        refresh_page_filament()
    elif page == ui.TJC_PAGE_INTERNET_PAGE:
        refresh_page_show_ip()
    elif page == ui.TJC_PAGE_AUTO_UNLOAD:
        refresh_page_auto_unload()
    elif page == ui.TJC_PAGE_OPEN_MOVING:
        refresh_page_open_moving()
    # NOTE: the server page (QIDI Link) and the QIDI Link pages are not refreshed


def refresh_page_open_filament_video_2():
    if g.printer_extruder_target == 0:
        send_cmd_pco(g.tty_fd, "temp_now", "65535")
        send_cmd_pco(g.tty_fd, "temp_target", "65535")
        send_cmd_picc(g.tty_fd, "heat_toggle", pics.open_heat_off)
        send_cmd_picc2(g.tty_fd, "heat_toggle", pics.open_heat_off_press)
    else:
        send_cmd_pco(g.tty_fd, "temp_now", "63488")
        send_cmd_pco(g.tty_fd, "temp_target", "63488")
        send_cmd_picc(g.tty_fd, "heat_toggle", pics.open_heat_on)
        send_cmd_picc2(g.tty_fd, "heat_toggle", pics.open_heat_on_press)

    send_cmd_txt(g.tty_fd, "temp_now", to_string(g.printer_extruder_temperature) + "/")
    send_cmd_val(g.tty_fd, "temp_target", to_string(g.printer_extruder_target))


def refresh_page_wifi_keyboard():
    if g.printing_wifi_keyboard_enabled == True:
        send_cmd_txt(g.tty_fd, "title", g.get_wifi_name)


def refresh_page_syntony_finish():
    MKSLOG_BLUE("Printer ide_timeout state: %s", g.printer_idle_timeout_state)
    MKSLOG_BLUE("Printer webhooks state: %s", g.printer_webhooks_state)
    if g.page_syntony_finished == False:
        g.page_syntony_finished = True
        g.all_level_saving = False

    if g.printer_idle_timeout_state == "Ready" and g.printer_webhooks_state == "ready":
        MKSLOG_BLUE("Printer webhooks state: %s", g.printer_webhooks_state)
        sleep(10)
        system("sync")      # make sure the config file is saved

        g.all_level_saving = False
        get_mks_babystep()  # 4.4.22 (was init_mks_status())
        sub_object_status()
        get_object_status()
        sleep(10)
        page_to(ui.TJC_PAGE_LEVEL_MODE)
        MKSLOG_RED("Left from line 739")


def _picc_group(names, selected, on_picc, off_picc, on_picc2, off_picc2):
    for i, name in enumerate(names):
        send_cmd_picc(g.tty_fd, name, on_picc if i == selected else off_picc)
    for i, name in enumerate(names):
        send_cmd_picc2(g.tty_fd, name, on_picc2 if i == selected else off_picc2)


def refresh_page_auto_level():
    names = ["step_001", "step_005", "step_01", "step_05"]
    if g.auto_level_dist == f32(0.01):
        _picc_group(names, 0, pics.prebed_step_on, pics.prebed_step_off, pics.prebed_press_on, pics.prebed_press_off)
    elif g.auto_level_dist == f32(0.05):
        _picc_group(names, 1, pics.prebed_step_on, pics.prebed_step_off, pics.prebed_press_on, pics.prebed_press_off)
    elif g.auto_level_dist == f32(0.1):
        _picc_group(names, 2, pics.prebed_step_on, pics.prebed_step_off, pics.prebed_press_on, pics.prebed_press_off)
    elif g.auto_level_dist == f32(0.5):
        _picc_group(names, 3, pics.prebed_step_on, pics.prebed_step_off, pics.prebed_press_on, pics.prebed_press_off)


def refresh_page_stopping():
    MKSLOG_BLUE("Printer ide_timeout state: %s", g.printer_idle_timeout_state)
    MKSLOG_BLUE("Printer webhooks state: %s", g.printer_webhooks_state)
    if g.printer_idle_timeout_state == "Ready":
        clear_previous_data()
        sleep(5)
        save_current_zoffset()
        page_to(ui.TJC_PAGE_MAIN)


def refresh_page_syntony_move():
    if g.temp_idle_state != g.printer_idle_timeout_state:
        g.temp_idle_state = g.printer_idle_timeout_state
        MKSLOG_BLUE("Printer ide_timeout state: %s", g.printer_idle_timeout_state)
        MKSLOG_BLUE("Printer webhooks state: %s", g.printer_webhooks_state)

    if g.step_1 == True:
        sleep(15)
        page_to(ui.TJC_PAGE_SYNTONY_FINISH)
        g.step_1 = False


def _file_name_only(path):
    return substr(path, path.rfind("/") + 1)


def refresh_page_print_filament():
    send_cmd_txt(g.tty_fd, "file_name", _file_name_only(g.printer_print_stats_filename))

    if g.printer_extruder_target == 0:
        send_cmd_pco(g.tty_fd, "temp_now", "65535")
        send_cmd_picc(g.tty_fd, "heat_btn", pics.printfil_heat_off)
        send_cmd_picc2(g.tty_fd, "heat_btn", pics.printfil_press_off)
    else:
        send_cmd_pco(g.tty_fd, "temp_now", "63488")
        send_cmd_picc(g.tty_fd, "heat_btn", pics.printfil_heat_on)
        send_cmd_picc2(g.tty_fd, "heat_btn", pics.printfil_press_on)

    send_cmd_val(g.tty_fd, "progress", to_string(g.printer_display_status_progress))
    send_cmd_val(g.tty_fd, "progress_pct", to_string(g.printer_display_status_progress))
    send_cmd_txt(g.tty_fd, "temp_now", to_string(g.printer_extruder_temperature))
    send_cmd_txt(g.tty_fd, "temp_set", to_string(g.printer_extruder_target))
    send_cmd_txt(g.tty_fd, "time_elapsed", show_time(c_int(g.printer_print_stats_print_duration)))
    send_cmd_txt(g.tty_fd, "time_left", show_time(get_cal_printing_time(c_int(g.printer_print_stats_print_duration),
                                                                 g.file_metadata_estimated_time,
                                                                 g.printer_display_status_progress)))

    if g.printer_print_stats_state == "paused":
        g.printer_ready = True

    # 4.4.2 CLL support mates and hall filament width sensors
    if g.filament_detected == False:
        sleep(1)
        g.printer_ready = False
        set_print_pause()
        page_to(ui.TJC_PAGE_PRINT_NO_FILAMENT)

    if g.printer_print_stats_state == "printing":
        if g.printer_ready == True:
            g.printer_ready = False
            page_to(ui.TJC_PAGE_PRINTING)

    if g.printer_print_stats_state == "standby":
        page_to(ui.TJC_PAGE_PRINT_STOPPING)

    if g.printer_print_stats_state == "error":
        page_to(ui.TJC_PAGE_GCODE_ERROR)
        cancel_print()
        clear_previous_data()
        send_cmd_txt(g.tty_fd, "msg", "gcode error:" + g.error_message)

    # 4.4.2 CLL a long pause that stops the print switches the page
    if g.printer_idle_timeout_state == "Idle":
        g.ep.Send(json_run_a_gcode("G28\n"))
        cancel_print()


def refresh_page_auto_finish():
    if g.printer_idle_timeout_state == "Idle" and g.printer_webhooks_state == "ready":
        g.auto_level_finished = True


def refresh_page_auto_moving():
    send_cmd_txt(g.tty_fd, "bed_temp", "(" + to_string(g.printer_heater_bed_temperature) + "/" +
                 to_string(g.printer_heater_bed_target) + ")")
    if g.step_1 == True:
        send_cmd_picc(g.tty_fd, "steps_bar", pics.auto_steps_1)
        send_cmd_pco(g.tty_fd, "step2_txt", "65535")
        send_cmd_pco(g.tty_fd, "step1_txt", "38066")
        send_cmd_vis(g.tty_fd, "spin1", "0")
        send_cmd_vis(g.tty_fd, "spin2", "1")
        g.step_1 = False
    if g.step_2 == True:
        send_cmd_picc(g.tty_fd, "steps_bar", pics.auto_steps_2)
        send_cmd_pco(g.tty_fd, "step3_txt", "65535")
        send_cmd_pco(g.tty_fd, "step2_txt", "38066")
        send_cmd_vis(g.tty_fd, "spin2", "0")
        send_cmd_vis(g.tty_fd, "spin3", "1")
        g.step_2 = False
    if g.step_3 == True:
        send_cmd_picc(g.tty_fd, "steps_bar", pics.auto_steps_3)
        send_cmd_pco(g.tty_fd, "step4_txt", "65535")
        send_cmd_pco(g.tty_fd, "step3_txt", "38066")
        send_cmd_vis(g.tty_fd, "spin3", "0")
        send_cmd_vis(g.tty_fd, "spin4", "1")
        g.step_3 = False
        g.printer_idle_timeout_state = "Printing"
        get_mks_heater_bed_target()
        set_heater_bed_target(g.mks_heater_bed_target)
        g.ep.Send(json_run_a_gcode("M190 S" + to_string(g.mks_heater_bed_target) + "\n"))
        sleep(1)
        g.ep.Send(json_run_a_gcode("M4027\n"))
    if g.step_4 == True:
        sleep(15)
        page_to(ui.TJC_PAGE_AUTO_FINISH)
        g.step_4 = False


def _cut_after_point(text, n):
    """``s.substr(0, s.find(".") + n)``"""
    return substr(text, 0, text.find(".") + n)


def refresh_page_move():
    x_pos = _cut_after_point(to_string(g.x_position), 2)
    y_pos = _cut_after_point(to_string(g.y_position), 2)
    z_pos = _cut_after_point(to_string(g.z_position), 2)

    send_cmd_txt(g.tty_fd, "x_pos", x_pos)
    send_cmd_txt(g.tty_fd, "y_pos", y_pos)
    send_cmd_txt(g.tty_fd, "z_pos", z_pos)

    # CLL highlight the selected distance
    if g.printer_move_dist == f32(0.1):
        send_cmd_picc(g.tty_fd, "dist_01", pics.move_dist_on)
        send_cmd_picc2(g.tty_fd, "dist_01", pics.move_dist_on_press)
        send_cmd_picc(g.tty_fd, "dist_1", pics.move_dist_off)
        send_cmd_picc2(g.tty_fd, "dist_1", pics.move_dist_off_press)
        send_cmd_picc(g.tty_fd, "dist_10", pics.move_dist_off)
        send_cmd_picc2(g.tty_fd, "dist_10", pics.move_dist_off_press)
    elif g.printer_move_dist == f32(1.0):
        send_cmd_picc(g.tty_fd, "dist_01", pics.move_dist_off)
        send_cmd_picc2(g.tty_fd, "dist_01", pics.move_dist_off_press)
        send_cmd_picc(g.tty_fd, "dist_1", pics.move_dist_on)
        send_cmd_picc2(g.tty_fd, "dist_1", pics.move_dist_on_press)
        send_cmd_picc(g.tty_fd, "dist_10", pics.move_dist_off)
        send_cmd_picc2(g.tty_fd, "dist_10", pics.move_dist_off_press)
    elif g.printer_move_dist == f32(10):
        send_cmd_picc(g.tty_fd, "dist_01", pics.move_dist_off)
        send_cmd_picc2(g.tty_fd, "dist_01", pics.move_dist_off_press)
        send_cmd_picc(g.tty_fd, "dist_1", pics.move_dist_off)
        send_cmd_picc2(g.tty_fd, "dist_1", pics.move_dist_off_press)
        send_cmd_picc(g.tty_fd, "dist_10", pics.move_dist_on)
        send_cmd_picc2(g.tty_fd, "dist_10", pics.move_dist_on_press)


def refresh_page_offset(intern_zoffset):
    g.printer_intern_z_offset = f32(intern_zoffset)
    g.printer_z_offset = f32(g.printer_intern_z_offset + g.printer_extern_z_offset)


def _zoffset_buttons():
    pairs = {
        0: (pics.zoffset_step_on, pics.zoffset_step_press_on),
        1: (pics.zoffset_step_off, pics.zoffset_step_press_off),
    }
    sel = None
    if g.printer_set_offset == f32(0.01):
        sel = 1
    elif g.printer_set_offset == f32(0.05):
        sel = 2
    elif g.printer_set_offset == f32(0.1):
        sel = 3
    elif g.printer_set_offset == f32(0.5):
        sel = 4
    if sel is None:
        return
    for b in range(1, 5):
        picc, picc2 = pairs[0] if b == sel else pairs[1]
        send_cmd_picc(g.tty_fd, ("step_001", "step_005", "step_01", "step_05")[b - 1], picc)
        send_cmd_picc2(g.tty_fd, ("step_001", "step_005", "step_01", "step_05")[b - 1], picc2)


def refresh_page_printing_zoffset():
    z_offset = to_string(g.printer_gcode_move_homing_origin[2])
    show_gcode_z = to_string(g.gcode_z_position)
    z_offset = _cut_after_point(z_offset, 4)
    show_gcode_z = _cut_after_point(show_gcode_z, 4)
    send_cmd_txt(g.tty_fd, "file_name", _file_name_only(g.printer_print_stats_filename))
    if z_offset != g.mks_babystep_value:
        g.mks_babystep_value = z_offset
        set_mks_babystep(g.mks_babystep_value)
    send_cmd_txt(g.tty_fd, "gcode_z", show_gcode_z)
    send_cmd_txt(g.tty_fd, "z_offset", z_offset)
    send_cmd_txt(g.tty_fd, "time_elapsed", show_time(c_int(g.printer_print_stats_print_duration)))
    send_cmd_val(g.tty_fd, "progress_pct", to_string(g.printer_display_status_progress))
    send_cmd_txt(g.tty_fd, "time_left", show_time(get_cal_printing_time(c_int(g.printer_print_stats_print_duration),
                                                                 g.file_metadata_estimated_time,
                                                                 g.printer_display_status_progress)))
    send_cmd_val(g.tty_fd, "progress", to_string(g.printer_display_status_progress))

    _zoffset_buttons()

    if g.printer_print_stats_state == "printing":
        g.printer_ready = True

    if g.filament_switch_sensor_fila_enabled == True:
        if g.filament_switch_sensor_fila_filament_detected == False:
            g.printer_ready = False
            set_print_pause()
            page_to(ui.TJC_PAGE_PRINT_NO_FILAMENT_2)

    # 4.4.2 CLL support mates and hall filament width sensors
    if g.filament_detected == False:
        sleep(1)
        g.printer_ready = False
        set_print_pause()
        page_to(ui.TJC_PAGE_PRINT_NO_FILAMENT)

    if g.printer_print_stats_state == "standby":
        page_to(ui.TJC_PAGE_PRINT_STOPPING)

    if g.printer_print_stats_state == "paused":
        if g.printer_ready == True:
            g.printer_ready = False
            page_to(ui.TJC_PAGE_PRINT_FILAMENT)

    if g.printer_print_stats_state == "complete":
        time_duration = show_time(c_int(g.printer_print_stats_print_duration))
        complete_print()
        clear_previous_data()
        sleep(5)
        save_current_zoffset()
        page_to(ui.TJC_PAGE_PRINT_FINISH)
        send_cmd_txt(g.tty_fd, "time_txt", time_duration)

    if g.printer_print_stats_state == "error":
        page_to(ui.TJC_PAGE_GCODE_ERROR)
        cancel_print()
        clear_previous_data()
        send_cmd_txt(g.tty_fd, "msg", "gcode error:" + g.error_message)


def refresh_page_printing():
    z_offset = to_string(g.printer_gcode_move_homing_origin[2])
    z_offset = _cut_after_point(z_offset, 4)

    send_cmd_val(g.tty_fd, "progress", to_string(g.printer_display_status_progress))
    send_cmd_val(g.tty_fd, "progress_pct", to_string(g.printer_display_status_progress))
    send_cmd_txt(g.tty_fd, "time_elapsed", show_time(c_int(g.printer_print_stats_print_duration)))
    send_cmd_txt(g.tty_fd, "time_left", show_time(get_cal_printing_time(c_int(g.printer_print_stats_print_duration),
                                                                 g.file_metadata_estimated_time,
                                                                 g.printer_display_status_progress)))
    send_cmd_txt(g.tty_fd, "file_name", _file_name_only(g.printer_print_stats_filename))

    # the z offset of the second page is always refreshed: the page starts with
    # the designer's "-1.000", it must not stay while the keyboard flag is set
    if g.current_page_id == ui.TJC_PAGE_PRINTING_2:
        send_cmd_txt(g.tty_fd, "zoffset_val", z_offset)

    if g.printing_keyboard_enabled == True:     # 4.4.22 silent mode button of the keyboard
        if g.printer_muted == False:
            send_cmd_picc(g.tty_fd, "mute_btn", pics.kb_mute_off)
            send_cmd_picc2(g.tty_fd, "mute_btn", pics.kb_mute_off_press)
        else:
            send_cmd_picc(g.tty_fd, "mute_btn", pics.kb_mute_on)
            send_cmd_picc2(g.tty_fd, "mute_btn", pics.kb_mute_on_press)
    else:                                       # CLL refresh only while the keyboard is not shown
        if g.current_page_id == ui.TJC_PAGE_PRINTING:
            # CLL fan speeds
            send_cmd_val(g.tty_fd, "fan1_val", to_string(c_int(f32(g.printer_out_pin_fan0_value * 100))))
            send_cmd_val(g.tty_fd, "fan2_val", to_string(c_int(f32(g.printer_out_pin_fan2_value * 100))))
            send_cmd_val(g.tty_fd, "fan3_val", to_string(c_int(f32(g.printer_out_pin_fan3_value * 100))))

            send_cmd_txt(g.tty_fd, "nozzle_temp", to_string(g.printer_extruder_temperature))
            send_cmd_val(g.tty_fd, "nozzle_set", to_string(g.printer_extruder_target))
            if g.printer_extruder_target == 0:  # CLL button and number colour depend on the nozzle heating
                send_cmd_pco(g.tty_fd, "nozzle_temp", "65535")
                send_cmd_picc(g.tty_fd, "nozzle_btn", pics.printing_row_off)
                send_cmd_picc2(g.tty_fd, "nozzle_btn", pics.printing_press_off)
            else:
                send_cmd_pco(g.tty_fd, "nozzle_temp", "63488")
                send_cmd_picc(g.tty_fd, "nozzle_btn", pics.printing_row_on)
                send_cmd_picc2(g.tty_fd, "nozzle_btn", pics.printing_press_on)

            send_cmd_txt(g.tty_fd, "bed_temp", to_string(g.printer_heater_bed_temperature))
            send_cmd_val(g.tty_fd, "bed_set", to_string(g.printer_heater_bed_target))
            if g.printer_heater_bed_target == 0:    # CLL button and number colour depend on the bed heating
                send_cmd_pco(g.tty_fd, "bed_temp", "65535")
                send_cmd_picc(g.tty_fd, "bed_btn", pics.printing_row_off)
                send_cmd_picc2(g.tty_fd, "bed_btn", pics.printing_press_off)
            else:
                send_cmd_pco(g.tty_fd, "bed_temp", "63488")
                send_cmd_picc(g.tty_fd, "bed_btn", pics.printing_row_on)
                send_cmd_picc2(g.tty_fd, "bed_btn", pics.printing_press_on)

            # 4.4.22: the LED button moved to the second printing page

            send_cmd_val(g.tty_fd, "chamber_set", to_string(g.printer_hot_target))      # CLL chamber temperature
            send_cmd_txt(g.tty_fd, "chamber_temp", to_string(g.printer_hot_temperature))
            if g.printer_hot_target == 0:
                send_cmd_pco(g.tty_fd, "chamber_temp", "65535")
                send_cmd_picc(g.tty_fd, "chamber_btn", pics.printing_row_off)
                send_cmd_picc2(g.tty_fd, "chamber_btn", pics.printing_press_off)
            else:
                send_cmd_pco(g.tty_fd, "chamber_temp", "63488")
                send_cmd_picc(g.tty_fd, "chamber_btn", pics.printing_row_on)
                send_cmd_picc2(g.tty_fd, "chamber_btn", pics.printing_press_on)

            if g.show_preview_gimage_completed == True:
                send_cmd_vis(g.tty_fd, "thumb", "1")
                send_cmd_val(g.tty_fd, "thumb_flag", "1")
            else:
                send_cmd_vis(g.tty_fd, "thumb", "0")
                send_cmd_val(g.tty_fd, "thumb_flag", "0")
        elif g.current_page_id == ui.TJC_PAGE_PRINTING_2:
            if g.current_speed_factor != g.printer_gcode_move_speed_factor:     # CLL speed factor
                g.current_speed_factor = g.printer_gcode_move_speed_factor
                send_cmd_val(g.tty_fd, "speed_val", to_string(c_int(c_round(f32(g.printer_gcode_move_speed_factor * 100)))))

            if g.current_extruder_factor != g.printer_gcode_move_extrude_factor:    # CLL extrusion factor
                g.current_extruder_factor = g.printer_gcode_move_extrude_factor
                send_cmd_val(g.tty_fd, "flow_val", to_string(c_int(c_round(f32(g.printer_gcode_move_extrude_factor * 100)))))

            if g.printer_caselight_value == 0:      # 4.4.22 LED state
                send_cmd_picc(g.tty_fd, "light_btn", pics.light_off)
                send_cmd_picc2(g.tty_fd, "light_btn", pics.printing2_press_off)
            else:
                send_cmd_picc(g.tty_fd, "light_btn", pics.light_on)
                send_cmd_picc2(g.tty_fd, "light_btn", pics.printing2_press_on)

    if g.printer_print_stats_state == "printing":
        g.printer_ready = True

    if g.filament_switch_sensor_fila_enabled == True:
        if g.filament_switch_sensor_fila_filament_detected == False:
            g.printer_ready = False
            set_print_pause()
            page_to(ui.TJC_PAGE_PRINT_NO_FILAMENT_2)

    if g.filament_detected == False:
        sleep(1)
        g.printer_ready = False
        set_print_pause()
        page_to(ui.TJC_PAGE_PRINT_NO_FILAMENT)

    if g.printer_print_stats_state == "complete":
        time_duration = show_time(c_int(g.printer_print_stats_print_duration))
        complete_print()
        clear_previous_data()
        sleep(5)
        save_current_zoffset()
        page_to(ui.TJC_PAGE_PRINT_FINISH)
        send_cmd_txt(g.tty_fd, "time_txt", time_duration)

    if g.printer_print_stats_state == "paused":
        if g.printer_ready == True:
            g.printer_ready = False
            page_to(ui.TJC_PAGE_PRINT_FILAMENT)

    if g.printer_print_stats_state == "standby":
        page_to(ui.TJC_PAGE_PRINT_STOPPING)

    if g.printer_print_stats_state == "error":
        page_to(ui.TJC_PAGE_GCODE_ERROR)
        cancel_print()
        clear_previous_data()
        send_cmd_txt(g.tty_fd, "msg", "gcode error:" + g.error_message)


def clear_page_printing_arg():
    g.current_extruder_temperature = 0
    g.current_extruder_target = 0
    g.current_heater_bed_target = 0
    g.current_heater_bed_temperature = 0
    g.current_hot_target = 0
    g.current_hot_temperature = 0
    g.current_out_pin_fan0_value = 0.0
    g.current_out_pin_fan2_value = 0.0
    g.current_out_pin_fan3_value = 0.0

    g.current_speed_factor = 0.0
    g.current_extruder_factor = 0.0


def _send_chunks_txt(data):
    """Sends a picture string in 2048 byte pieces through the "add" text variable."""
    num = 2048
    length = len(data)
    end = num
    start = 0
    while start < length:
        if end > length:
            s = substr(data, start, length - start)
            send_cmd_txt(g.tty_fd, "cp_pad", s)
            _tcdrain()
            send_cmd_txt_plus(g.tty_fd, "cp_data", "cp_data", "cp_pad")
            _tcdrain()
            break
        s = substr(data, start, num)
        start = end
        end = end + num
        send_cmd_txt(g.tty_fd, "cp_pad", s)
        _tcdrain()
        send_cmd_txt_plus(g.tty_fd, "cp_data", "cp_data", "cp_pad")
        _tcdrain()


def _send_chunks_cp(obj, data):
    """Writes a picture string in 2048 byte pieces into a picture widget."""
    num = 2048
    length = len(data)
    end = num
    start = 0
    while start < length:
        if end > length:
            part = substr(data, start, length - start)
            _tcdrain()
            send_cmd_cp_image(g.tty_fd, obj, part)
            break
        part = substr(data, start, num)
        start = end
        end = end + num
        _tcdrain()
        send_cmd_cp_image(g.tty_fd, obj, part)


def _tcdrain():
    import termios
    try:
        termios.tcdrain(g.tty_fd)
    except (termios.error, OSError, ValueError):
        pass


def _name_of(path):
    """File name without the directories"""
    return substr(path, path.rfind("/") + 1)


def _stem_of(path):
    """``path.substr(rfind("/") + 1, rfind(".") - (rfind("/") + 1))``"""
    start = path.rfind("/") + 1
    return substr(path, start, path.rfind(".") - start)


def refresh_page_preview():
    # 4.4.22: pictures of the 4.4.24 screen, timelapse switch b3
    if g.printer_bed_leveling == False:
        send_cmd_picc(g.tty_fd, "level_btn", pics.preview_chk_off)
        send_cmd_picc2(g.tty_fd, "level_btn", pics.preview_press_off)
    else:
        send_cmd_picc(g.tty_fd, "level_btn", pics.preview_chk_on)
        send_cmd_picc2(g.tty_fd, "level_btn", pics.preview_press_on)
    if g.timelapse_enabled == False:
        send_cmd_picc(g.tty_fd, "timelapse_btn", pics.preview_chk_off)
        send_cmd_picc2(g.tty_fd, "timelapse_btn", pics.preview_press_off)
    else:
        send_cmd_picc(g.tty_fd, "timelapse_btn", pics.preview_chk_on)
        send_cmd_picc2(g.tty_fd, "timelapse_btn", pics.preview_press_on)
    if g.mks_file_parse_finished == True:
        if g.show_preview_complete == False:
            # 4.4.2 CLL only the file name is shown on the preview page
            send_cmd_txt(g.tty_fd, "err_msg", _file_name_only(g.file_metadata_filename))
            if g.file_metadata_estimated_time:
                send_cmd_txt(g.tty_fd, "est_time", show_time(g.file_metadata_estimated_time))
            else:
                send_cmd_txt(g.tty_fd, "est_time", "-")

            if g.file_metadata_filament_weight_total:
                temp = to_string(g.file_metadata_filament_weight_total)
                send_cmd_txt(g.tty_fd, "fil_weight", _cut_after_point(temp, 2) + "g")
            else:
                send_cmd_txt(g.tty_fd, "fil_weight", "-")

            if g.file_metadata_filament_total:
                temp = to_string(f32(g.file_metadata_filament_total / 1000))
                send_cmd_txt(g.tty_fd, "fil_length", _cut_after_point(temp, 2) + "m")
            else:
                send_cmd_txt(g.tty_fd, "fil_length", "-")

            if g.file_metadata_filament_type != "":
                send_cmd_txt(g.tty_fd, "fil_type", g.file_metadata_filament_type)
            elif g.file_metadata_filament_name != "":
                send_cmd_txt(g.tty_fd, "fil_type", g.file_metadata_filament_name)
            else:
                send_cmd_txt(g.tty_fd, "fil_type", "-")

            path_found = False
            # NOTE: the original looks for <dir>/.thumbs/<name>-160x160.png, then
            # .jpg, made by QIDI's Moonraker; the port reads the thumbnail from the
            # gcode file itself (see thumbnail.py).  For a print that was just
            # started the original only looks at the .cache copy of the file.
            if g.jump_to_print == True:
                candidates = ["/.cache/" + _name_of(g.printer_print_stats_filename),
                              "/" + g.printer_print_stats_filename]
            elif g.cache_clicked == True:
                candidates = [_top(g.page_files_path_stack) + "/.cache/" + _name_of(g.file_metadata_filename)]
                g.cache_clicked = False
            else:
                candidates = [_top(g.page_files_path_stack) + "/" + _name_of(g.file_metadata_filename)]
            picture_path = ""
            for candidate in candidates:
                candidate = substr(candidate, 1)
                MKSLOG_RED("picture_path:%s", candidate)
                if thumbnail.find(candidate, 160, "PNG") is not None:
                    path_found = True
                    picture_path = thumbnail.GcodeRef(candidate)
                    break
            MKSLOG_BLUE("Picture path:%s", picture_path)
            if picture_path == "":
                path_found = False

            if path_found == True:
                # small picture
                if g.show_preview_gimage_completed == False:
                    output_imgdata(picture_path, 160)
                    data = g.tjc_data
                    if data is None:
                        cerr("No converted picture (/home/mks/tjc)", "\n")
                        g.show_preview_complete = True
                        return
                    g.file_metadata_simage = data
                    send_cmd_txt(g.tty_fd, "preview.cp_data", "")
                    send_cmd_txt(g.tty_fd, "preview.cp_pad", "")
                    if g.file_metadata_simage != "":
                        send_cmd_baud(g.tty_fd, 921600)
                        usleep(50000)
                        set_option(g.tty_fd, 921600, 8, 'N', 1)
                        cout("Sending the small picture")
                        _send_chunks_txt(g.file_metadata_simage)
                        send_cmd_baud(g.tty_fd, 115200)
                        usleep(50000)
                        set_option(g.tty_fd, 115200, 8, 'N', 1)

                    # big picture
                    if g.jump_to_print == False:
                        data = g.tjc_data
                        if data is None:
                            cerr("No converted picture (/home/mks/tjc)", "\n")
                            g.show_preview_complete = True
                            return
                        g.file_metadata_gimage = data
                        send_cmd_baud(g.tty_fd, 921600)
                        usleep(50000)
                        set_option(g.tty_fd, 921600, 8, 'N', 1)
                        send_cmd_cp_close(g.tty_fd, "preview.preview_pic")
                        if g.file_metadata_gimage != "":
                            cout("Sending the big picture")
                            _send_chunks_cp("preview_pic", g.file_metadata_gimage)
                        send_cmd_baud(g.tty_fd, 115200)
                        usleep(50000)
                        set_option(g.tty_fd, 115200, 8, 'N', 1)
                        bed_leveling_switch(True)
                    g.show_preview_gimage_completed = True

            if g.show_preview_gimage_completed == True:
                send_cmd_vis(g.tty_fd, "preview_pic", "1")
            else:
                send_cmd_vis(g.tty_fd, "preview_pic", "0")

            g.show_preview_complete = True
            if g.jump_to_print == True:
                check_filament_type()
                g.jump_to_print = False


def refresh_page_main():
    send_cmd_val(g.tty_fd, "nozzle_temp", to_string(g.printer_extruder_temperature))
    send_cmd_val(g.tty_fd, "bed_temp", to_string(g.printer_heater_bed_temperature))
    send_cmd_val(g.tty_fd, "chamber_temp", to_string(g.printer_hot_temperature))

    if detect_disk() == 0:      # CLL USB drive inserted?
        send_cmd_picc(g.tty_fd, "usb_icon", pics.main_off)
    else:
        send_cmd_picc(g.tty_fd, "usb_icon", pics.main_on)

    if g.status_result.wpa_state == "COMPLETED":    # CLL wifi connected?
        send_cmd_picc(g.tty_fd, "wifi_icon", pics.main_off)
    else:
        send_cmd_picc(g.tty_fd, "wifi_icon", pics.main_on)

    if g.printer_caselight_value == 0:      # LED logo
        send_cmd_picc(g.tty_fd, "light_btn", pics.main_off)
        send_cmd_picc2(g.tty_fd, "light_btn", pics.nav_btn_press)
    else:
        send_cmd_picc(g.tty_fd, "light_btn", pics.main_on)
        send_cmd_picc2(g.tty_fd, "light_btn", pics.main_on_press)

    if g.printer_out_pin_beep_value == 0:
        send_cmd_picc(g.tty_fd, "beep_btn", pics.main_off)
        send_cmd_picc2(g.tty_fd, "beep_btn", pics.nav_btn_press)
    else:
        send_cmd_picc(g.tty_fd, "beep_btn", pics.main_on)
        send_cmd_picc2(g.tty_fd, "beep_btn", pics.main_on_press)

    if g.printer_extruder_target == 0:      # CLL nozzle heating state on the main page
        send_cmd_pco(g.tty_fd, "nozzle_temp", "65535")
        send_cmd_picc(g.tty_fd, "nozzle_btn", pics.main_off)
        send_cmd_picc2(g.tty_fd, "nozzle_btn", pics.nav_btn_press)
    else:
        send_cmd_pco(g.tty_fd, "nozzle_temp", "63488")
        send_cmd_picc(g.tty_fd, "nozzle_btn", pics.main_on)
        send_cmd_picc2(g.tty_fd, "nozzle_btn", pics.main_on_press)

    if g.printer_heater_bed_target == 0:    # CLL bed heating state on the main page
        send_cmd_pco(g.tty_fd, "bed_temp", "65535")
        send_cmd_picc(g.tty_fd, "bed_btn", pics.main_off)
        send_cmd_picc2(g.tty_fd, "bed_btn", pics.nav_btn_press)
    else:
        send_cmd_pco(g.tty_fd, "bed_temp", "63488")
        send_cmd_picc(g.tty_fd, "bed_btn", pics.main_on)
        send_cmd_picc2(g.tty_fd, "bed_btn", pics.main_on_press)

    if g.printer_hot_target == 0:           # CLL chamber heating state on the main page
        send_cmd_pco(g.tty_fd, "chamber_temp", "65535")
        send_cmd_picc(g.tty_fd, "chamber_btn", pics.main_off)
        send_cmd_picc2(g.tty_fd, "chamber_btn", pics.nav_btn_press)
    else:
        send_cmd_pco(g.tty_fd, "chamber_temp", "63488")
        send_cmd_picc(g.tty_fd, "chamber_btn", pics.main_on)
        send_cmd_picc2(g.tty_fd, "chamber_btn", pics.main_on_press)

    # CLL refresh the picture after every boot or print
    if g.main_picture_refreshed == False:
        # CLL get the file information
        g.page_files_pages = 0
        g.page_files_current_pages = 0
        g.page_files_folder_layers = 0
        g.page_files_previous_path = ""
        g.page_files_root_path = DEFAULT_DIR
        g.page_files_path = ""
        refresh_page_files(g.page_files_current_pages)
        if g.page_files_list_show_type[0] == "[c]":
            send_cmd_txt(g.tty_fd, "last_file_name", g.page_files_list_show_name[0])
            name0 = g.page_files_list_show_name[0]
            # NOTE: thumbnail from the gcode file instead of .cache/.thumbs/<name>-160x160.png / .jpg
            picture_path = thumbnail.GcodeRef(substr(g.page_files_path + "/.cache/" + name0, 1))
            MKSLOG_RED("Picture path:%s", picture_path)
            thumb = thumbnail.find(picture_path, 160, "PNG")
            if thumb is not None and thumb.fmt == "PNG":
                MKSLOG_RED("Found png picture")
                send_cmd_pic(g.tty_fd, "b[0]", pics.main_bg_photo)
                send_cmd_picc(g.tty_fd, "last_file_btn", pics.main_bg_photo)
                send_cmd_picc2(g.tty_fd, "last_file_btn", pics.nav_btn_press)
                send_cmd_vis(g.tty_fd, "last_file_pic", "1")
                refresh_files_list_picture(picture_path, 160, 0)
                g.main_picture_detected = True
            else:
                if thumb is not None:
                    MKSLOG_RED("Found jpg picture")
                    send_cmd_pic(g.tty_fd, "b[0]", pics.main_bg_photo)
                    send_cmd_picc(g.tty_fd, "last_file_btn", pics.main_bg_photo)
                    send_cmd_picc2(g.tty_fd, "last_file_btn", pics.nav_btn_press)
                    refresh_files_list_picture(picture_path, 160, 0)
                    g.main_picture_detected = True
                else:
                    send_cmd_pic(g.tty_fd, "b[0]", pics.main_bg_noimg)
                    send_cmd_picc(g.tty_fd, "last_file_btn", pics.main_bg_noimg)
                    send_cmd_picc2(g.tty_fd, "last_file_btn", pics.main_on_press)
                    send_cmd_vis(g.tty_fd, "last_file_pic", "0")
        else:
            send_cmd_pic(g.tty_fd, "b[0]", pics.main_bg_noimg)
            send_cmd_picc(g.tty_fd, "last_file_btn", pics.main_bg_noimg)
            send_cmd_picc2(g.tty_fd, "last_file_btn", pics.main_on_press)
            send_cmd_txt(g.tty_fd, "last_file_name", "")
            send_cmd_vis(g.tty_fd, "last_file_pic", "0")
        g.main_picture_refreshed = True

    # CLL ask for the power loss recovery once after boot
    if g.open_reprint_asked == False:
        check_print_interrupted()
        g.open_reprint_asked = True


def refresh_page_files_list():
    # 4.4.22: the pictures are only sent again when the list changed
    # (file_list_refreshed), the folder and page are kept meanwhile
    if g.file_list_refreshed == False:
        delete_small_jpg()
    if detect_disk_2() == 1 and g.file_mode == "USB":
        send_cmd_txt(g.tty_fd, "empty_msg", "")
    elif detect_disk_2() == 0 and g.file_mode == "USB":
        send_cmd_txt(g.tty_fd, "empty_msg", "\u7a7a")     # "empty"
    send_cmd_vis(g.tty_fd, "file1_mark", "0")
    for i in range(4):
        send_cmd_txt(g.tty_fd, "file" + to_string(i + 1) + "_name", g.page_files_list_show_name[i])
        send_cmd_vis(g.tty_fd, "cp" + to_string(i), "0")
        t = g.page_files_list_show_type[i]
        if t == "[c]":
            send_cmd_picc(g.tty_fd, "file" + to_string(i + 1), pics.files_item_img)
            send_cmd_picc2(g.tty_fd, "file" + to_string(i + 1), pics.files_tab_local_press)
            send_cmd_vis(g.tty_fd, "file1_mark", "1")
        elif t == "[d]":
            send_cmd_picc(g.tty_fd, "file" + to_string(i + 1), pics.files_item_dir)
            send_cmd_picc2(g.tty_fd, "file" + to_string(i + 1), pics.files_dir_press)
        elif t == "[f]":
            send_cmd_picc(g.tty_fd, "file" + to_string(i + 1), pics.files_item_img)
            send_cmd_picc2(g.tty_fd, "file" + to_string(i + 1), pics.files_tab_local_press)
        elif t == "[n]":
            send_cmd_picc(g.tty_fd, "file" + to_string(i + 1), pics.files_tab_usb)
            send_cmd_picc2(g.tty_fd, "file" + to_string(i + 1), pics.files_tab_usb)

    # 4.4.2 CLL local / USB buttons on the file list page
    if g.file_mode == "Local":
        send_cmd_picc(g.tty_fd, "local_tab", pics.files_tab_local)
        send_cmd_picc2(g.tty_fd, "local_tab", pics.files_tab_local_press)
        send_cmd_picc(g.tty_fd, "usb_tab", pics.files_tab_local)
        send_cmd_picc2(g.tty_fd, "usb_tab", pics.files_tab_local_press)
    elif g.file_mode == "USB":
        send_cmd_picc(g.tty_fd, "local_tab", pics.files_tab_usb)
        send_cmd_picc2(g.tty_fd, "local_tab", pics.files_tab_usb_press)
        send_cmd_picc(g.tty_fd, "usb_tab", pics.files_tab_usb)
        send_cmd_picc2(g.tty_fd, "usb_tab", pics.files_tab_usb_press)
        if detect_disk() == -1:
            send_cmd_vis(g.tty_fd, "empty_msg", "1")
    if g.page_files_current_pages == 0:
        send_cmd_picc(g.tty_fd, "prev", pics.files_item_img)
        send_cmd_picc2(g.tty_fd, "prev", pics.files_dir_press)
    else:
        send_cmd_picc(g.tty_fd, "prev", pics.files_item_dir)
        send_cmd_picc2(g.tty_fd, "prev", pics.files_tab_local_press)
    if g.page_files_current_pages == g.page_files_pages:
        send_cmd_picc(g.tty_fd, "next", pics.files_item_img)
        send_cmd_picc2(g.tty_fd, "next", pics.files_dir_press)
    else:
        send_cmd_picc(g.tty_fd, "next", pics.files_item_dir)
        send_cmd_picc2(g.tty_fd, "next", pics.files_tab_local_press)
    if g.page_files_folder_layers == 0 or (g.page_files_folder_layers == 1 and g.file_mode != "Local"):
        send_cmd_picc(g.tty_fd, "up_dir", pics.files_item_img)
        send_cmd_picc2(g.tty_fd, "up_dir", pics.files_dir_press)
    else:
        send_cmd_picc(g.tty_fd, "up_dir", pics.files_item_dir)
        send_cmd_picc2(g.tty_fd, "up_dir", pics.files_tab_local_press)
    if g.file_list_refreshed == True:
        send_cmd_tsw(g.tty_fd, "255", "1")      # pictures still in the screen memory: enable touch
    else:
        for i in range(4):      # CLL refresh the pictures after all the other widgets
            g.have_64_jpg[i] = False
            g.have_64_png_path[i] = ""
            t = g.page_files_list_show_type[i]
            if t == "[c]" or t == "[f]":
                name = g.page_files_list_show_name[i]
                # NOTE: the original sends <dir>/.thumbs/<name>-112x112_QD.jpg (made only
                # by QIDI's slicer / Moonraker) to the screen; the port takes the
                # thumbnail from the gcode file itself (see thumbnail.py).
                if t == "[c]":
                    picture_path = g.page_files_path + "/.cache/" + name
                else:
                    picture_path = g.page_files_path + "/" + name
                picture_path = thumbnail.GcodeRef(substr(picture_path, 1))
                MKSLOG_RED("Picture path:%s", picture_path)
                if thumbnail.find(picture_path, 112, "JPEG") is not None:
                    g.have_64_jpg[i] = True
                    g.have_64_png_path[i] = picture_path
            # the picture thread also enables the touch again when there is no picture
            g.begin_show_64_jpg = True
        g.file_list_refreshed = True


def refresh_page_files(pages):
    mks_file.get_page_files_filelist(g.page_files_root_path + g.page_files_path)
    mks_file.set_page_files_show_list(pages)


# ---------------------------------------------------------------------------
# Subscriptions / printer actions
# ---------------------------------------------------------------------------

def sub_object_status():
    g.ep.Send(json_subscribe_to_printer_object_status(subscribe_objects_status()))


def get_object_status():
    g.ep.Send(json_query_printer_object_status(subscribe_objects_status()))


def get_file_estimated_time(filename):
    g.ep.Send(json_get_gcode_metadata(filename))


def delete_file(filepath):
    import time
    g.filelist_changed = False
    g.ep.Send(json_file_delete(filepath))
    while not g.filelist_changed:
        time.sleep(0)


def start_printing(filepath):
    g.ep.Send(json_print_a_file(filepath))


def set_target(heater, target):
    g.ep.Send(json_run_a_gcode(set_heater_temp(heater, target)))


def set_extruder_target(target):
    set_target("extruder", target)


def set_heater_bed_target(target):
    set_target("heater_bed", target)


def set_hot_target(target):
    g.ep.Send(json_run_a_gcode("M141 S" + to_string(target)))


def set_fan(speed):
    g.ep.Send(json_run_a_gcode(set_fan_speed(speed)))


def set_fan0(speed):
    g.ep.Send(json_run_a_gcode(set_fan0_speed(speed)))


def set_fan2(speed):
    g.ep.Send(json_run_a_gcode(set_fan2_speed(speed)))


def set_fan3(speed):
    g.ep.Send(json_run_a_gcode(set_fan3_speed(speed)))


def set_intern_zoffset(offset):
    g.printer_set_offset = f32(offset)


def set_zoffset(positive):
    if positive == True:
        g.ep.Send(json_run_a_gcode("SET_GCODE_OFFSET Z_ADJUST=+" + to_string(g.printer_set_offset) + " MOVE=1"))
    else:
        g.ep.Send(json_run_a_gcode("SET_GCODE_OFFSET Z_ADJUST=-" + to_string(g.printer_set_offset) + " MOVE=1"))


def set_move_dist(dist):
    g.printer_move_dist = f32(dist)


def set_printer_speed(speed):
    cout("Rate = ", to_string(speed))
    g.ep.Send(json_run_a_gcode(set_speed_rate(to_string(speed))))


def set_printer_flow(rate):
    g.ep.Send(json_run_a_gcode("M221 S" + to_string(rate)))


def show_time(seconds):
    return to_string(cdiv(seconds, 3600)) + "h" + to_string(cdiv(cmod(seconds, 3600), 60)) + "m"


def move_home():
    g.ep.Send(json_run_a_gcode("G28\n"))


def move_x_decrease():
    g.ep.Send(move(AXIS_X, "-" + to_string(g.printer_move_dist), 130))
    g.unhomed_move_mode = 2


def move_x_increase():
    g.ep.Send(move(AXIS_X, "+" + to_string(g.printer_move_dist), 130))
    g.unhomed_move_mode = 1


def move_y_decrease():
    g.ep.Send(move(AXIS_Y, "-" + to_string(g.printer_move_dist), 130))
    g.unhomed_move_mode = 4


def move_y_increase():
    g.ep.Send(move(AXIS_Y, "+" + to_string(g.printer_move_dist), 130))
    g.unhomed_move_mode = 3


def move_z_decrease():
    g.ep.Send(move(AXIS_Z, "-" + to_string(g.printer_move_dist), 10))
    g.unhomed_move_mode = 5


def move_z_increase():
    g.ep.Send(move(AXIS_Z, "+" + to_string(g.printer_move_dist), 10))
    g.unhomed_move_mode = 6


def get_filament_detected():
    return g.filament_switch_sensor_fila_filament_detected


def get_filament_detected_enable():
    return g.filament_switch_sensor_fila_enabled


def get_print_pause_resume():
    return g.printer_pause_resume_is_paused


def set_print_pause_resume():
    if g.printer_pause_resume_is_paused == False:
        g.ep.Send(json_run_a_gcode("PAUSE"))
    else:
        g.ep.Send(json_run_a_gcode("RESUME"))


def set_print_pause():
    g.ep.Send(json_run_a_gcode("PAUSE"))


def set_print_resume():
    g.ep.Send(json_run_a_gcode("RESUME"))


def cancel_print():
    g.printer_print_stats_filename = ""
    system("curl -X POST http://127.0.0.1:7125/printer/breakmacro")
    system("curl -X POST http://127.0.0.1:7125/printer/breakheater")
    g.ep.Send(json_run_a_gcode("CANCEL_PRINT"))
    # 4.4.22: the total print time is no longer kept in config.mksini
    usleep(10000)
    sdcard_reset_file()


def sdcard_reset_file():
    g.ep.Send(json_run_a_gcode("SDCARD_RESET_FILE"))


def set_auto_level_dist(dist):
    MKSLOG_BLUE("SET")
    g.auto_level_dist = f32(dist)


def start_auto_level():
    g.step_1 = False
    g.step_2 = False
    g.step_3 = False
    g.step_4 = False
    if g.start_pre_auto_level == False:
        g.printer_idle_timeout_state = "Printing"
    page_to(ui.TJC_PAGE_AUTO_MOVING)
    set_heater_bed_target(g.mks_heater_bed_target)
    g.ep.Send(json_run_a_gcode("M4029"))


def start_auto_level_dist(positive):
    """4.4.1 CLL levelling changes"""
    if positive == True:
        g.ep.Send(json_run_a_gcode("SET_GCODE_OFFSET Z_ADJUST=" + to_string(g.auto_level_dist) + " MOVE=1"))
    else:
        g.ep.Send(json_run_a_gcode("SET_GCODE_OFFSET Z_ADJUST=-" + to_string(g.auto_level_dist) + " MOVE=1"))


def set_filament_extruder_target(positive):
    get_mks_extruder_target()
    g.printer_filament_extruder_target = g.mks_extruder_target
    if positive == True:
        g.printer_filament_extruder_target += 3
    else:
        g.printer_filament_extruder_target -= 3

    if g.printer_filament_extruder_target >= 350:
        g.printer_filament_extruder_target = 350

    if g.printer_filament_extruder_target < 0:
        g.printer_filament_extruder_target = 0
        set_extruder_target(0)
        set_mks_extruder_target(0)
    else:
        set_extruder_target(g.printer_filament_extruder_target)
        set_mks_extruder_target(g.printer_filament_extruder_target)


def set_print_filament_dist(dist):
    g.printer_filament_extruedr_dist = c_int(f32(dist))


def start_retract():
    g.ep.Send(json_run_a_gcode("M83\nG1 E-" + to_string(g.printer_filament_extruedr_dist) + " F300\n"))


def start_extrude():
    g.ep.Send(json_run_a_gcode("M83\nG1 E" + to_string(g.printer_filament_extruedr_dist) + " F300\n"))


def get_ip(net):
    cmd = "ifconfig " + net + " | awk 'NR==2{print $2}' | tr -d '\n\r'"
    return execute_cmd(cmd)


def move_home_tips():
    g.jump_to_move_pop_2 = True


def filament_tips():
    if g.current_page_id == ui.TJC_PAGE_OPEN_FILAMENTVIDEO_3:
        pass
    elif g.current_page_id == ui.TJC_PAGE_PRINT_FILAMENT:
        g.jump_to_print_low_temp = True
    else:
        g.jump_to_filament_pop_1 = True


def move_tips():
    g.jump_to_move_pop_1 = True
    if g.current_page_id in (ui.TJC_PAGE_PRINTING, ui.TJC_PAGE_PRINT_ZOFFSET, ui.TJC_PAGE_PRINT_FILAMENT,
                             ui.TJC_PAGE_PRINTING_2):
        cancel_print()


def reset_klipper():
    g.ep.Send(json_run_a_gcode("RESTART\n"))


def reset_firmware():
    g.ep.Send(json_run_a_gcode("FIRMWARE_RESTART\n"))


def finish_print():
    sdcard_reset_file()
    clear_cp0_image()
    clear_page_preview()
    g.show_preview_complete = False
    page_to(ui.TJC_PAGE_MAIN)


def set_filament_sensor():
    cout("filament_switch_sensor fila = ", int(g.filament_switch_sensor_fila_enabled))
    if g.filament_switch_sensor_fila_enabled == 0:
        g.ep.Send(json_run_a_gcode("SET_FILAMENT_SENSOR SENSOR=fila ENABLE=1\n"))
        g.mks_fila_status = True
        set_mks_fila_status()
    else:
        g.ep.Send(json_run_a_gcode("SET_FILAMENT_SENSOR SENSOR=fila ENABLE=0\n"))
        g.mks_fila_status = False
        set_mks_fila_status()


def motors_off():
    g.ep.Send(json_emergency_stop())
    sleep(1)
    g.ep.Send(json_run_a_gcode("FIRMWARE_RESTART\n"))     # "motors off" was turned into an emergency stop


def beep_on_off():
    if g.printer_out_pin_beep_value == 0:
        g.ep.Send(json_run_a_gcode("beep_on"))
        g.mks_beep_status = True
        set_mks_beep_status()
    else:
        g.ep.Send(json_run_a_gcode("beep_off"))
        g.mks_beep_status = False
        set_mks_beep_status()


def led_on_off():
    if g.printer_caselight_value == 0:
        g.ep.Send(json_run_a_gcode("SET_PIN PIN=caselight VALUE=1"))
        if g.current_page_id != ui.TJC_PAGE_SCREEN_SLEEP:
            g.mks_led_status = True
            set_mks_led_status()
    else:
        g.ep.Send(json_run_a_gcode("SET_PIN PIN=caselight VALUE=0"))
        if g.current_page_id != ui.TJC_PAGE_SCREEN_SLEEP:
            g.mks_led_status = False
            set_mks_led_status()


def shutdown_mcu():
    system("echo \"SET_PIN PIN=pwc VALUE=0\" > /root/mcu_shutdown.txt")
    g.ep.Send(json_run_a_gcode("SET_PIN PIN=pwc VALUE=0"))


def firmware_reset():
    g.ep.Send(json_run_a_gcode("FIRMWARE_RESTART\n"))


def go_to_page_power_off():
    page_to(ui.TJC_PAGE_SHUTDOWN)


# ---------------------------------------------------------------------------
# config.mksini values
# ---------------------------------------------------------------------------

def get_mks_led_status():
    mksini_load()
    g.mks_led_status = mksini_getboolean("led", "enable", 0)
    mksini_free()
    return int(g.mks_led_status)


def set_mks_led_status():
    mksini_load()
    mksini_set("led", "enable", to_string(g.mks_led_status))
    mksini_save()
    mksini_free()


def get_mks_beep_status():
    mksini_load()
    g.mks_beep_status = mksini_getboolean("beep", "enable", 0)
    mksini_free()
    return int(g.mks_beep_status)


def set_mks_beep_status():
    mksini_load()
    mksini_set("beep", "enable", to_string(g.mks_beep_status))
    mksini_save()
    mksini_free()
    system("sync")


def get_mks_language_status():
    mksini_load()
    g.mks_language_status = mksini_getint("system", "language", 0)
    mksini_free()


def set_mks_language_status():
    mksini_load()
    mksini_set("system", "language", to_string(g.mks_language_status))
    mksini_save()
    mksini_free()


def get_mks_extruder_target():
    mksini_load()
    g.mks_extruder_target = mksini_getint("target", "extruder", 200)
    mksini_free()


def set_mks_extruder_target(target):
    if target != 0:
        mksini_load()
        mksini_set("target", "extruder", to_string(target))
        mksini_save()
        mksini_free()
        system("sync")


def get_mks_heater_bed_target():
    mksini_load()
    g.mks_heater_bed_target = mksini_getint("target", "heaterbed", 40)
    mksini_free()


def set_mks_heater_bed_target(target):
    if target != 0:
        mksini_load()
        cout("######## ", target)
        mksini_set("target", "heaterbed", to_string(target))
        mksini_save()
        mksini_free()
        system("sync")


def get_mks_hot_target():
    mksini_load()
    g.mks_hot_target = mksini_getint("target", "hot", 40)
    mksini_free()


def set_mks_hot_target(target):
    mksini_load()
    cout("######## ", target)
    mksini_set("target", "hot", to_string(target))
    mksini_save()
    mksini_free()
    system("sync")


def filament_extruder_target():
    get_mks_extruder_target()
    if g.printer_extruder_target == 0:
        set_extruder_target(g.mks_extruder_target)
    else:
        set_extruder_target(0)


def filament_heater_bed_target():
    get_mks_heater_bed_target()
    if 0 == g.printer_heater_bed_target:
        set_heater_bed_target(g.mks_heater_bed_target)
    else:
        set_heater_bed_target(0)


def filament_hot_target():
    get_mks_hot_target()
    if 0 == g.printer_hot_target:
        set_hot_target(g.mks_hot_target)
    else:
        set_hot_target(0)


def filament_fan0():
    if g.printer_out_pin_fan0_value == 0:
        set_fan0(100)
    else:
        set_fan0(0)


def filament_fan2():
    if g.printer_out_pin_fan2_value == 0:
        set_fan2(100)
    else:
        set_fan2(0)


def filament_fan3():
    if g.printer_out_pin_fan3_value == 0:
        set_fan3(100)
    else:
        set_fan3(0)


# ---------------------------------------------------------------------------
# System / network pages
# ---------------------------------------------------------------------------

def go_to_reset():
    if g.printer_webhooks_state == "shutdown":
        page_to(ui.TJC_PAGE_RESET)
    else:
        # 4.4.22: fixed name (was read from /dev_info.txt)
        page_to(ui.TJC_PAGE_SYS_OK)
        send_cmd_txt(g.tty_fd, "info_txt", "Q1 Pro")


def go_to_network():
    if detected_wlan0():
        get_wlan0_status()
        g.page_wifi_list_ssid_button_enabled[0] = False
        g.page_wifi_list_ssid_button_enabled[1] = False
        g.page_wifi_list_ssid_button_enabled[2] = False
        g.page_wifi_list_ssid_button_enabled[3] = False
        g.page_wifi_list_ssid_button_enabled[4] = False
        g.page_wifi_ssid_list_pages = 0
        g.page_wifi_current_pages = 0
        if g.status_result.wpa_state == "COMPLETED":
            g.current_connected_ssid_name = g.status_result.ssid   # name of the connected wifi
        elif g.status_result.wpa_state != "INACTIVE":
            g.current_connected_ssid_name = ""      # not connected: forget the name of the connected wifi
        page_to(ui.TJC_PAGE_WIFI_LIST)
        scan_ssid_and_show()
    else:
        page_to(ui.TJC_PAGE_INTERNET)


def scan_ssid_and_show():
    if detected_wlan0():
        get_wlan0_status()
        network.mks_wpa_scan_scanresults()
        get_ssid_list_pages()
        g.page_wifi_current_pages = 0
        set_page_wifi_ssid_list(g.page_wifi_current_pages)
        refresh_page_wifi_list()
    else:
        page_to(ui.TJC_PAGE_INTERNET)


def refresh_page_wifi_list():
    # 4.4.22: the names come from the list, the first entry of the first page is
    # the connected network; the page buttons are set once after the list
    MKSLOG_BLUE("pages: %d / %d", g.page_wifi_current_pages + 1, g.page_wifi_ssid_list_pages)
    for i in range(5):
        cout("Refreshed wifi: ", g.page_wifi_ssid_list[i])
        send_cmd_txt(g.tty_fd, "row" + to_string(i + 1) + "_txt", g.page_wifi_ssid_list[i])
        if g.status_result.wpa_state == "COMPLETED" and g.page_wifi_current_pages == 0 and i == 0:
            send_cmd_picc(g.tty_fd, "row1", pics.rows_check)
            send_cmd_picc2(g.tty_fd, "row" + to_string(i + 1), pics.rows_check_press)
            g.page_wifi_list_ssid_button_enabled[i] = False
        elif g.page_wifi_ssid_list[i] != "":
            send_cmd_picc(g.tty_fd, "row" + to_string(i + 1), pics.rows_lock)
            send_cmd_picc2(g.tty_fd, "row" + to_string(i + 1), pics.bg_settings_press)
            g.page_wifi_list_ssid_button_enabled[i] = True
        else:
            send_cmd_picc(g.tty_fd, "row" + to_string(i + 1), pics.bg_settings_panel)
            send_cmd_picc2(g.tty_fd, "row" + to_string(i + 1), pics.bg_settings_panel)
            g.page_wifi_list_ssid_button_enabled[i] = False

    if g.page_wifi_ssid_list_pages == 0:
        send_cmd_picc(g.tty_fd, "prev_btn", pics.rows_check)
        send_cmd_picc2(g.tty_fd, "prev_btn", pics.bg_settings_press)
        send_cmd_picc(g.tty_fd, "next_btn", pics.rows_check)
        send_cmd_picc2(g.tty_fd, "next_btn", pics.bg_settings_press)
    else:
        if g.page_wifi_current_pages == 0:
            send_cmd_picc(g.tty_fd, "prev_btn", pics.rows_check)
            send_cmd_picc2(g.tty_fd, "prev_btn", pics.bg_settings_press)
        else:
            send_cmd_picc(g.tty_fd, "prev_btn", pics.rows_lock)
            send_cmd_picc2(g.tty_fd, "prev_btn", pics.rows_check_press)
        if g.page_wifi_ssid_list_pages - 1 == g.page_wifi_current_pages:
            send_cmd_picc(g.tty_fd, "next_btn", pics.rows_check)
            send_cmd_picc2(g.tty_fd, "next_btn", pics.bg_settings_press)
        else:
            send_cmd_picc(g.tty_fd, "next_btn", pics.rows_lock)
            send_cmd_picc2(g.tty_fd, "next_btn", pics.rows_check_press)


def get_wifi_list_ssid(index):
    g.get_wifi_name = ""
    g.get_wifi_name = g.page_wifi_ssid_list[index]


def set_print_filament_target():
    if 0 == g.printer_extruder_target:
        get_mks_extruder_target()
        set_extruder_target(g.mks_extruder_target)
    else:
        set_extruder_target(0)


def complete_print():
    if g.page_printing_shutdown_enable == False:
        g.ep.Send(json_run_a_gcode("PRINT_END"))
    else:
        g.ep.Send(json_run_a_gcode("PRINT_END_POWEROFF"))
    # 4.4.22: the total print time is no longer kept in config.mksini


def back_to_main():
    clear_previous_data()
    page_to(ui.TJC_PAGE_MAIN)


def go_to_syntony_move():
    g.step_1 = False
    g.page_syntony_finished = False
    g.printer_idle_timeout_state = "Printing"
    page_to(ui.TJC_PAGE_SYNTONY_MOVE)
    g.ep.Send(json_run_a_gcode("M901\n"))


def print_ssid_psk(psk):
    """psk: bytes received from the screen keyboard"""
    MKSLOG_RED("SSID is %s", g.get_wifi_name)
    network.mks_start_connect(g.get_wifi_name, b2s(psk))


def clear_page_preview():
    g.file_metadata_filename = ""
    g.file_metadata_estimated_time = 0
    g.file_metadata_filament_weight_total = 0.0
    g.file_metadata_filament_name = ""
    g.file_metadata_filament_type = ""
    g.file_metadata_simage = ""
    g.file_metadata_gimage = ""


def set_mks_babystep(value):
    mksini_load()
    mksini_set("babystep", "value", value)
    mksini_save()
    mksini_free()
    system("sync")


def get_mks_babystep():
    mksini_load()
    g.mks_babystep_value = mksini_getstring("babystep", "value", "0.000")
    g.mks_adxl_offset = mksini_getstring("babystep", "adxl_offset", "0.000")
    mksini_free()


def clear_cp0_image():
    send_cmd_cp_close(g.tty_fd, "preview.preview_pic")
    send_cmd_txt(g.tty_fd, "preview.cp_data", "")
    send_cmd_txt(g.tty_fd, "preview.cp_pad", "")
    g.show_preview_gimage_completed = False
    g.mks_file_parse_finished = False
    g.file_metadata_simage = ""
    g.file_metadata_gimage = ""


def printer_set_babystep():
    get_mks_babystep()
    g.ep.Send(json_run_a_gcode("SET_GCODE_OFFSET Z=" + g.mks_babystep_value + " MOVE=0"))


def get_mks_fila_status():
    mksini_load()
    g.mks_fila_status = mksini_getboolean("fila", "enable", 0)
    mksini_free()
    return int(g.mks_fila_status)


def set_mks_fila_status():
    mksini_load()
    mksini_set("fila", "enable", to_string(g.mks_fila_status))
    mksini_save()
    mksini_free()
    system("sync")


def system_setting_init():
    """4.4.22 start-up settings (the QIDI Link part is not implemented)."""
    get_mks_babystep()
    get_mks_ethernet()


def init_mks_status():
    get_mks_total_printed_time()
    get_mks_babystep()
    get_mks_connection_method()
    get_mks_ethernet()
    # the z-offset is no longer set by xindi (printer_set_babystep() not called)


def is_mounted(path):
    """4.4.22: 1 if path is a mount point, 0 if not, -1 on errors."""
    try:
        return 1 if os.stat("/").st_dev != os.stat(path).st_dev else 0
    except OSError as e:
        cerr("is_mounted ", path, ": ", str(e), "\n")
        return -1


def detect_disk_2():
    """4.4.22: is the USB drive mounted (1), not mounted (0), or missing (-1)?"""
    result = is_mounted(paths.gcode_files() + "/sda1")
    if result == 1:
        MKSLOG("%s is mounted", paths.gcode_files() + "/sda1")
    elif result == 0:
        MKSLOG("%s is not mounted", paths.gcode_files() + "/sda1")
    return result


def detect_disk():
    if access("/dev/sda") == 0:
        if access("/dev/sda1") == 0:
            if access(paths.gcode_files() + "/sda1") != 0:
                system("/usr/bin/systemctl --no-block restart makerbase-automount@sda1.service")
                sleep(1)
        return 0
    else:
        return -1


def set_printing_shutdown():
    if g.page_printing_shutdown_enable == False:
        g.page_printing_shutdown_enable = True
    else:
        g.page_printing_shutdown_enable = False


def mks_get_version():
    mksversion_load()
    g.mks_version_soc = mksversion_soc("V1.1.1")
    g.mks_version_mcu = mksversion_mcu("V0.10.0")
    g.mks_version_ui = mksversion_ui("V1.1.1")
    mksversion_free()


def wifi_save_config():
    page_to(ui.TJC_PAGE_WIFI_SAVING)
    network.mks_save_config()
    sleep(2)
    get_wlan0_status()


def disable_page_about_successed():
    g.page_about_successed = True


def finish_tjc_update():
    if access("/root/800_480.tft") == 0:
        system("mv /root/800_480.tft /root/800_480.tft.bak; sync")


def filament_load():
    send_cmd_vis(g.tty_fd, "next_btn", "0")
    send_cmd_vis(g.tty_fd, "temp_txt", "1")
    send_cmd_vis(g.tty_fd, "back_btn", "0")
    send_cmd_picc(g.tty_fd, "steps_bar", pics.pop_steps_1)
    send_cmd_pco(g.tty_fd, "step1_txt", "65535")
    send_cmd_pco(g.tty_fd, "hint", "38066")
    send_cmd_vis(g.tty_fd, "spin1", "0")
    send_cmd_vis(g.tty_fd, "spin2", "1")
    g.printer_idle_timeout_state = "Printing"
    g.ep.Send(json_run_a_gcode("M109 S" + to_string(g.load_target) + "\n"))
    g.ep.Send(json_run_a_gcode("M604\n"))


def filament_unload():
    g.printer_idle_timeout_state = "Printing"
    g.ep.Send(json_run_a_gcode("M109 S" + to_string(g.load_target) + "\n"))
    g.ep.Send(json_run_a_gcode("M603\n"))


def get_cal_printed_time(print_time):
    printed_time = 0
    printed_time = cdiv(print_time, 60)
    return printed_time


def get_mks_total_printed_time():
    mksini_load()
    g.mks_total_printed_minutes = mksini_getint("total", "time", 0)
    mksini_free()
    return g.mks_total_printed_minutes


def set_mks_total_printed_time(printed_time):
    mksini_load()
    cout("######## ", printed_time)
    mksini_set("total", "time", to_string(printed_time))
    mksini_save()
    mksini_free()
    system("sync")


def get_total_time():
    g.ep.Send(json_get_job_totals())


def do_not_x_clear():
    set_mks_total_printed_time(36000)


def do_x_clear():
    set_mks_total_printed_time(0)


def level_mode_printing_set_target():
    set_heater_bed_target(g.level_mode_printing_heater_bed_target)
    g.ep.Send(json_run_a_gcode("M190 S" + to_string(g.level_mode_printing_heater_bed_target)))
    set_extruder_target(g.level_mode_printing_extruder_target)
    g.ep.Send(json_run_a_gcode("M109 S" + to_string(g.level_mode_printing_extruder_target)))


def level_mode_printing_print_file():
    start_printing("LEVEL_PRINTING.gcode")


def update_finished_tips():
    sleep(5)
    system("sync")
    system("systemctl restart makerbase-client.service")


def get_mks_oobe_enabled():
    mksini_load()
    g.mks_oobe_enabled = mksini_getboolean("oobe", "enable", 0)
    mksini_free()
    return g.mks_oobe_enabled


def set_mks_oobe_enabled(enable):
    mksini_load()
    mksini_set("oobe", "enable", to_string(bool(enable)))
    mksini_save()
    mksini_free()
    system("sync")


def move_motors_off():
    g.ep.Send(json_run_a_gcode("M84\n"))


def open_more_level_finish():
    get_mks_babystep()      # 4.4.22 (was init_mks_status())
    set_mks_oobe_enabled(False)     # turn the out-of-box guide off
    get_object_status()
    page_to(ui.TJC_PAGE_MAIN)


def open_move_tip():
    g.ep.Send(json_run_a_gcode("G91\nG1 Z-100 F600\nG1 X-100 Y-100 F1200\nG90"))


def open_set_print_filament_target():
    if 0 == g.printer_extruder_target:
        get_mks_extruder_target()
        set_extruder_target(g.mks_extruder_target)
    else:
        set_extruder_target(0)


def open_start_extrude():
    g.ep.Send(json_run_a_gcode("M83\nG1 E20 F300\n"))


def open_calibrate_start():
    g.step_1 = False    # CLL True: platform and nozzle position initialised
    g.step_2 = False    # CLL True: compensation values collected
    g.step_3 = False    # CLL True: input shaping done
    g.printer_idle_timeout_state = "Printing"
    page_to(ui.TJC_PAGE_OPEN_CALIBRATE)
    g.ep.Send(json_run_a_gcode("M4028"))   # custom gcode "M4028" in printer.cfg


def close_mcu_port():
    g.ep.Send(json_run_a_gcode("CLOSE_MCU_PORT\n"))


def oobe_set_intern_zoffset(offset):
    g.oobe_printer_set_offset = f32(offset)


def oobe_set_zoffset(positive):
    if positive == True:
        g.ep.Send(json_run_a_gcode("SET_GCODE_OFFSET Z_ADJUST=+" + to_string(g.oobe_printer_set_offset) + " MOVE=1"))
    else:
        g.ep.Send(json_run_a_gcode("SET_GCODE_OFFSET Z_ADJUST=-" + to_string(g.oobe_printer_set_offset) + " MOVE=1"))


def refresh_page_zoffset():
    i = 0
    while i < g.printer_bed_mesh_profiles_mks_mesh_params_y_count:
        if i == 5:
            break
        j = 0
        while j < g.printer_bed_mesh_profiles_mks_mesh_params_x_count:
            if j == 5:
                break
            temp = to_string(g.printer_bed_mesh_profiles_mks_points[i][j])
            temp = _cut_after_point(temp, 3)
            send_cmd_txt(g.tty_fd, "cell_" + to_string(5 * i + j), temp)
            j += 1
        i += 1


def refresh_page_auto_heaterbed():
    send_cmd_txt(g.tty_fd, "temp_now", to_string(g.printer_heater_bed_temperature) + "/")
    send_cmd_val(g.tty_fd, "temp_target", to_string(g.printer_heater_bed_target))
    if g.printer_heater_bed_target > 0:
        send_cmd_picc(g.tty_fd, "heat_toggle", pics.autobed_on)
        send_cmd_picc2(g.tty_fd, "heat_toggle", pics.autobed_press_on)
        send_cmd_pco(g.tty_fd, "temp_now", "63488")
        send_cmd_pco(g.tty_fd, "temp_target", "63488")
    else:
        send_cmd_picc(g.tty_fd, "heat_toggle", pics.autobed_off)
        send_cmd_picc2(g.tty_fd, "heat_toggle", pics.autobed_press_off)
        send_cmd_pco(g.tty_fd, "temp_now", "65535")
        send_cmd_pco(g.tty_fd, "temp_target", "65535")


def set_auto_level_heater_bed_target(positive):
    get_mks_heater_bed_target()
    g.printer_auto_level_heater_bed_target = g.mks_heater_bed_target
    if positive == True:
        g.printer_auto_level_heater_bed_target += 3
    else:
        g.printer_auto_level_heater_bed_target -= 3
    if g.printer_auto_level_heater_bed_target > 120:
        g.printer_auto_level_heater_bed_target = 120
    if g.printer_auto_level_heater_bed_target < 0:
        g.printer_auto_level_heater_bed_target = 0
    set_heater_bed_target(g.printer_auto_level_heater_bed_target)
    set_mks_heater_bed_target(g.printer_auto_level_heater_bed_target)


def detect_error():
    if g.current_page_id in (ui.TJC_PAGE_PRINTING, ui.TJC_PAGE_PRINT_ZOFFSET, ui.TJC_PAGE_PRINT_FILAMENT,
                             ui.TJC_PAGE_PRINTING_2, ui.TJC_PAGE_GCODE_ERROR, ui.TJC_PAGE_LEVEL_ERROR,
                             ui.TJC_PAGE_DETECT_ERROR, ui.TJC_PAGE_UPDATING):
        pass
    elif g.current_page_id in (ui.TJC_PAGE_OPEN_CALIBRATE, ui.TJC_PAGE_AUTO_MOVING):
        g.ep.Send(json_run_a_gcode("RESTART"))
        g.jump_to_level_error = True
    else:
        if g.printer_webhooks_state != "shutdown" and g.printer_webhooks_state != "error":
            g.jump_to_detect_error = True


def clear_previous_data():
    sdcard_reset_file()
    clear_cp0_image()
    clear_page_preview()
    g.show_preview_complete = False
    g.printing_keyboard_enabled = False


def print_start():
    if g.printer_bed_leveling == True:
        g.ep.Send(json_run_a_gcode("G31\n"))
    else:
        g.ep.Send(json_run_a_gcode("G32\n"))


def open_heater_bed_up():
    # 4.4.22: the caller shows the "moving" page, which waits until Klipper is idle
    # again (refresh_page_open_moving()); the bed is homed and moved up and down
    g.printer_idle_timeout_state = "Printing"
    g.ep.Send(json_run_a_gcode("SET_KINEMATIC_POSITION Z=150\nSET_KINEMATIC_POSITION X=150\nSET_KINEMATIC_POSITION Y=150\n"))
    g.ep.Send(json_run_a_gcode("G91\nG1 Z-30 F600\nG1 X-30 Y-30 F1200\nG90\nM84\n"))
    g.ep.Send(json_run_a_gcode("M4031\n"))
    g.ep.Send(json_run_a_gcode("G28\n"))
    g.ep.Send(json_run_a_gcode("G1 Z240 F600\nG1 Z10 F600\n G1 Z240 F600\n G1 Z20 F600\n"))


def refresh_page_open_moving():
    """4.4.22: leave the "moving" page of the guide once Klipper is idle again."""
    if g.printer_idle_timeout_state != "Printing":
        page_to(ui.TJC_PAGE_OPEN_FILAMENTVIDEO_0)


def refresh_page_open_heaterbed():
    send_cmd_txt(g.tty_fd, "t0", to_string(g.printer_heater_bed_temperature) + "/")
    send_cmd_val(g.tty_fd, "n0", to_string(g.printer_heater_bed_target))
    if g.printer_heater_bed_target > 0:
        send_cmd_picc(g.tty_fd, "b0", pics.bedtemp_on)
        send_cmd_picc2(g.tty_fd, "b0", pics.bedtemp_press_on)
        send_cmd_pco(g.tty_fd, "t0", "63488")
        send_cmd_pco(g.tty_fd, "n0", "63488")
    else:
        send_cmd_picc(g.tty_fd, "b0", pics.bedtemp_off)
        send_cmd_picc2(g.tty_fd, "b0", pics.bedtemp_press_off)
        send_cmd_pco(g.tty_fd, "t0", "65535")
        send_cmd_pco(g.tty_fd, "n0", "65535")


def bed_leveling_switch(positive):
    if positive == True:
        g.ep.Send(json_run_a_gcode("G31"))
        g.printer_bed_leveling = True
    if positive == False:
        g.ep.Send(json_run_a_gcode("G32"))
        g.printer_bed_leveling = False


def save_current_zoffset():
    z_offset = to_string(g.printer_gcode_move_homing_origin[2])
    z_offset = _cut_after_point(z_offset, 4)
    if g.current_page_id in (ui.TJC_PAGE_AUTO_MOVING, ui.TJC_PAGE_OPEN_CALIBRATE):
        g.printer_idle_timeout_state = "Printing"
        get_mks_babystep()
        z = f32(stof(g.mks_babystep_value) + stof(g.mks_adxl_offset))
        if z > -5 and z < 5:    # CLL only z-offsets between -5 and 5 are saved
            g.mks_babystep_value = to_string(z)
            set_mks_babystep(g.mks_babystep_value)
            MKSLOG_RED("Current z-offset saved as %s", g.mks_babystep_value)
    else:
        if z_offset != g.mks_babystep_value and z_offset.find("0.000") != -1:
            if stof(z_offset) > -5 and stof(z_offset) < 5:
                g.mks_babystep_value = z_offset
                set_mks_babystep(g.mks_babystep_value)
                MKSLOG_RED("Current z-offset saved as:%s", g.mks_babystep_value)


def refresh_page_filament_pop():
    send_cmd_txt(g.tty_fd, "temp_txt", "(" + to_string(g.printer_extruder_temperature) + "/" +
                 to_string(g.printer_extruder_target) + "℃)")
    if g.step_1 == True:
        g.step_1 = False
        send_cmd_picc(g.tty_fd, "steps_bar", pics.pop_steps_2)
        send_cmd_pco(g.tty_fd, "step2_txt", "65535")
        send_cmd_pco(g.tty_fd, "step1_txt", "38066")
        send_cmd_pco(g.tty_fd, "temp_txt", "38066")
        send_cmd_vis(g.tty_fd, "spin2", "0")
        send_cmd_vis(g.tty_fd, "spin3", "1")
    if g.step_2 == True and g.printer_idle_timeout_state == "Ready":
        g.step_2 = False
        send_cmd_picc(g.tty_fd, "steps_bar", pics.pop_steps_3)
        send_cmd_pco(g.tty_fd, "step3_txt", "65535")
        send_cmd_pco(g.tty_fd, "step2_txt", "38066")
        send_cmd_vis(g.tty_fd, "done_btn", "1")
        send_cmd_vis(g.tty_fd, "alt_btn", "1")
        send_cmd_vis(g.tty_fd, "spin3", "0")


def check_filament_type():
    if g.file_metadata_filament_type != "":
        filament_type = g.file_metadata_filament_type
    else:
        filament_type = g.file_metadata_filament_name
    filament_type = str_lower_ascii(filament_type)
    MKSLOG_YELLOW("filament_type : %s", filament_type)
    # 4.4.1 CLL "do not show again" button on the filament confirmation pop-ups
    if (filament_type.find("pla") != -1 or filament_type.find("petg") != -1) and g.preview_pop_1_on == True:
        page_to(ui.TJC_PAGE_PREVIEW_POP_1)
    elif filament_type.find("abs") != -1 and g.preview_pop_2_on == True:
        page_to(ui.TJC_PAGE_PREVIEW_POP_2)
    else:
        page_to(ui.TJC_PAGE_PRINTING)


def refresh_page_preview_pop():
    # 4.4.2 support mates and hall filament width sensors
    if g.filament_detected == False:
        sleep(1)
        set_print_pause()
        page_to(ui.TJC_PAGE_PRINT_NO_FILAMENT)
    if g.printer_print_stats_state == "standby":
        page_to(ui.TJC_PAGE_PRINT_STOPPING)
    if g.printer_print_stats_state == "error":
        page_to(ui.TJC_PAGE_GCODE_ERROR)
        cancel_print()
        clear_previous_data()
        send_cmd_txt(g.tty_fd, "msg", "gcode error:" + g.error_message)


def replaceCharacters(path, searchChars, replacement):
    result = path
    for c in searchChars:
        found = result.find(c)
        while found != -1:
            result = result[:found] + replacement + result[found + 1:]
            found = result.find(c, found + len(replacement))
    return result


def check_filament_width():
    """4.4.2 support for the hall filament width sensor"""
    if g.filament_message.find("// Filament dia (measured mm):") != -1:
        filament_width = stof(substr(g.filament_message, 31))
        MKSLOG("Filament width: %f", filament_width)
        if filament_width < 0.3:
            g.filament_detected = False
        else:
            g.filament_detected = True
    elif g.filament_message.find("// Filament NOT present") != -1 or g.filament_message.find("echo: Filament run out") != -1:
        g.filament_detected = False


def refresh_page_files_list_2():
    """4.4.2 CLL refresh of the file list page"""
    if g.file_mode == "USB":
        if detect_disk() == -1:
            g.file_mode = "NULL"
            page_to(ui.TJC_PAGE_FILE_LIST)
            g.page_files_pages = 0
            g.page_files_current_pages = 0
            g.page_files_folder_layers = 1
            g.page_files_previous_path = ""
            g.page_files_root_path = "gcodes/"
            g.page_files_path = "/sda1"
            refresh_page_files(g.page_files_current_pages)
            refresh_page_files_list()
            get_object_status()
    elif g.file_mode == "NULL":
        if detect_disk() == 0:
            sleep(1)
            g.file_mode = "USB"
            page_to(ui.TJC_PAGE_FILE_LIST)
            g.page_files_pages = 0
            g.page_files_current_pages = 0
            g.page_files_folder_layers = 1
            g.page_files_previous_path = ""
            g.page_files_root_path = "gcodes/"
            g.page_files_path = "/sda1"
            refresh_page_files(g.page_files_current_pages)
            refresh_page_files_list()
            get_object_status()


def go_to_update():
    page_to(ui.TJC_PAGE_UPDATE_MODE)
    send_cmd_txt(g.tty_fd, "ver_cur", g.mks_version_soc)
    # 4.4.22: the online update needs QIDI Link, which the port does not
    # implement: the button is disabled (LAN only)
    send_cmd_tsw(g.tty_fd, "online_btn", "0")
    send_cmd_picc(g.tty_fd, "online_btn", pics.update_mode_press)
    send_cmd_pco(g.tty_fd, "online_btn", "38066")
    send_cmd_pco2(g.tty_fd, "online_btn", "38066")


def restore_config():
    system("rm " + paths.gcode_files() + "/.cache/*")
    g.main_picture_refreshed = False
    system("curl -X POST http://127.0.0.1:7125/server/history/reset_totals")
    system("curl -X DELETE 'http://127.0.0.1:7125/server/history/job?all=true'")
    system("cp /root/config.mksini " + paths.klipper_config() + "/config.mksini")
    system("cp " + paths.klipper_config() + "/saved_variables.cfg.bak " + paths.klipper_config() + "/saved_variables.cfg")
    g.ep.Send(json_run_a_gcode("SAVE_VARIABLE VARIABLE=z_offset VALUE=0"))
    page_to(ui.TJC_PAGE_MAIN)


def refresh_page_bed_moving():
    if g.printer_idle_timeout_state == "Ready":
        if g.manual_count == 3:
            page_to(ui.TJC_PAGE_PRE_BED_CALIBRATION)
        elif g.manual_count == -2:
            page_to(ui.TJC_PAGE_BED_FINISH)
        else:
            page_to(ui.TJC_PAGE_BED_CALIBRATION)


def bed_calibrate():
    if g.manual_count == 4:
        g.bed_offset = 0.0
        g.printer_idle_timeout_state = "Printing"
        g.ep.Send(json_run_a_gcode("ABORT\n"))
        g.ep.Send(json_run_a_gcode("M4031\n"))     # 4.4.22
        g.ep.Send(json_run_a_gcode("M4030\n"))
        page_to(ui.TJC_PAGE_BED_MOVING)
    elif g.manual_count == 3:
        g.printer_idle_timeout_state = "Printing"
        g.ep.Send(json_run_a_gcode("G1 Z10 F600"))
        g.ep.Send(json_run_a_gcode("BED_SCREWS_ADJUST\n"))
        g.ep.Send(json_run_a_gcode("G1 Z" + to_string(g.bed_offset) + " F600\n"))
        MKSLOG_BLUE("Current bed_offset:%f", g.bed_offset)
        page_to(ui.TJC_PAGE_BED_MOVING)
    elif g.manual_count > 0:
        g.printer_idle_timeout_state = "Printing"
        g.ep.Send(json_run_a_gcode("ACCEPT\n"))
        g.ep.Send(json_run_a_gcode("G1 Z" + to_string(g.bed_offset) + " F600\n"))
        page_to(ui.TJC_PAGE_BED_MOVING)
    elif g.manual_count == 0:
        g.ep.Send(json_run_a_gcode("ACCEPT\n"))
        g.ep.Send(json_run_a_gcode("G1 Z10 F600\nG1 X0 Y0 F9000\n"))
        get_mks_babystep()      # 4.4.22 (was init_mks_status())
        page_to(ui.TJC_PAGE_BED_FINISH)
    else:
        g.ep.Send(json_run_a_gcode("G1 Z10 F600\n"))
        page_to(ui.TJC_PAGE_BED_FINISH)
    g.manual_count -= 1


def bed_adjust(status):
    if status == True:
        g.ep.Send(json_run_a_gcode("G91\nG1 Z" + to_string(-g.auto_level_dist) + " F600\nG90\n"))
        g.bed_offset = f32(g.bed_offset - g.auto_level_dist)
        MKSLOG_BLUE("Current bed_offset:%f", g.bed_offset)
    elif status == False:
        g.ep.Send(json_run_a_gcode("G91\nG1 Z" + to_string(g.auto_level_dist) + " F600\nG90\n"))
        g.bed_offset = f32(g.bed_offset + g.auto_level_dist)
        MKSLOG_BLUE("Current bed_offset:%f", g.bed_offset)


def go_to_file_list():
    # 4.4.22: the folder and page are kept while the list is up to date
    if g.file_mode == "Local":
        page_to(ui.TJC_PAGE_FILE_LIST)
        if g.file_list_refreshed == False:
            g.page_files_pages = 0
            g.page_files_current_pages = 0
            g.page_files_folder_layers = 0
            g.page_files_previous_path = ""
            g.page_files_root_path = DEFAULT_DIR
            g.page_files_path = ""
        refresh_page_files(g.page_files_current_pages)
        refresh_page_files_list()
        get_object_status()
    else:
        page_to(ui.TJC_PAGE_FILE_LIST)
        if g.file_list_refreshed == False:
            g.page_files_pages = 0
            g.page_files_current_pages = 0
            g.page_files_folder_layers = 1
            g.page_files_previous_path = ""
            g.page_files_root_path = DEFAULT_DIR
            g.page_files_path = "/sda1"
        refresh_page_files(g.page_files_current_pages)
        refresh_page_files_list()
        get_object_status()


def send_gcode(command):
    g.ep.Send(json_run_a_gcode(command))


def refresh_page_open_calibrate():
    if g.step_3 == True:
        g.step_3 = False
        system("sync")      # CLL save the system information, then go to the filament loading page
        sleep(10)
        get_object_status()
        sub_object_status()
        page_to(ui.TJC_PAGE_OPEN_FILAMENTVIDEO_0)
    if g.step_2 == True and g.printer_webhooks_state == "ready":
        g.step_2 = False
        sleep(5)
        g.ep.Send(json_run_a_gcode("M901"))    # CLL input shaping after the bed levelling
    if g.step_1 == True and g.printer_idle_timeout_state == "Ready":
        g.step_1 = False
        get_mks_heater_bed_target()
        set_heater_bed_target(g.mks_heater_bed_target)
        g.ep.Send(json_run_a_gcode("M190 S" + to_string(g.mks_heater_bed_target) + "\n"))
        sleep(5)
        g.ep.Send(json_run_a_gcode("M4027"))   # CLL levelling after the platform / nozzle initialisation


def refresh_page_filament_set_fan():
    if g.move_fan_setting == False:     # CLL refresh only while the slider is not being dragged
        fan0 = to_string(c_int(f32(g.printer_out_pin_fan0_value * 100)))
        fan2 = to_string(c_int(f32(g.printer_out_pin_fan2_value * 100)))
        fan3 = to_string(c_int(f32(g.printer_out_pin_fan3_value * 100)))
        send_cmd_val(g.tty_fd, "fan1_slider", fan0)
        send_cmd_val(g.tty_fd, "fan1_val", fan0)
        send_cmd_val(g.tty_fd, "fan2_slider", fan2)
        send_cmd_val(g.tty_fd, "fan2_val", fan2)
        send_cmd_val(g.tty_fd, "fan3_slider", fan3)
        send_cmd_val(g.tty_fd, "fan3_val", fan3)
        for name, value in (("fan1_toggle", g.printer_out_pin_fan0_value), ("fan2_toggle", g.printer_out_pin_fan2_value),
                            ("fan3_toggle", g.printer_out_pin_fan3_value)):
            if value == 0:
                send_cmd_picc(g.tty_fd, name, pics.fan_row_off)
                send_cmd_picc2(g.tty_fd, name, pics.fan_press_off)
            else:
                send_cmd_picc(g.tty_fd, name, pics.fan_row_on)
                send_cmd_picc2(g.tty_fd, name, pics.fan_press_on)


def go_to_adjust():
    """CLL remember the last choice of the adjust page"""
    if g.adjust_mode == "Filament":
        page_to(ui.TJC_PAGE_FILAMENT)
    else:
        page_to(ui.TJC_PAGE_MOVE)


def go_to_setting():
    if g.set_mode == "Level_mode":
        page_to(ui.TJC_PAGE_LEVEL_MODE)
    else:
        page_to(ui.TJC_PAGE_COMMON_SETTING)


def refresh_page_common_setting():
    g.current_mks_oobe_enabled = get_mks_oobe_enabled()
    send_cmd_txt(g.tty_fd, "version_txt", g.mks_version_soc)
    if g.current_mks_oobe_enabled == False:
        send_cmd_picc(g.tty_fd, "reset_btn", pics.reset_row)
        send_cmd_picc2(g.tty_fd, "reset_btn", pics.settings_press)
    else:
        send_cmd_picc(g.tty_fd, "reset_btn", pics.reset_row_on)
        send_cmd_picc2(g.tty_fd, "reset_btn", pics.settings_press_on)
        send_cmd_txt(g.tty_fd, "reset_lbl", TEXT_STARTUP_GUIDE)


def print_log():
    """CLL export the logs to the USB drive"""
    if detect_disk() == -1:
        page_to(ui.TJC_PAGE_PRINT_LOG_F)    # CLL no USB drive: tell the user the export failed
    else:
        system("mkdir " + paths.gcode_files() + "/sda1/QD_Log")
        system("bash -c 'cp " + paths.klipper_logs() + "/klippy.log* " + paths.gcode_files() + "/sda1/QD_Log/'")
        system("bash -c 'cp " + paths.klipper_logs() + "/moonraker.log* " + paths.gcode_files() + "/sda1/QD_Log/'")
        system("bash -c 'cp " + paths.klipper_logs() + "/auto_update.log* " + paths.gcode_files() + "/sda1/QD_Log/'")
        system("bash -c 'cp /root/frp/frpc.log* " + paths.gcode_files() + "/sda1/QD_Log/'")
        system("bash -c 'cp /root/frp/frpc.*.log " + paths.gcode_files() + "/sda1/QD_Log/'")
        system("cp /root/frp/frpc.toml " + paths.gcode_files() + "/sda1/QD_Log/server.cfg")
        page_to(ui.TJC_PAGE_PRINT_LOG_S)


def refresh_files_list_picture(path, pixel, i):
    g.file_metadata_simage = ""
    g.file_metadata_gimage = ""
    g.mks_file_parse_finished = False
    output_imgdata(path, pixel)
    data = g.tjc_data
    if data is None:
        cerr("No converted picture (/home/mks/tjc)", "\n")
        g.show_preview_complete = True
        return
    g.file_metadata_gimage = data
    send_cmd_baud(g.tty_fd, 921600)
    usleep(10000)
    set_option(g.tty_fd, 921600, 8, 'N', 1)
    send_cmd_cp_close(g.tty_fd, "cp" + to_string(i))
    if g.file_metadata_gimage != "":
        cout("Sending the file picture")
        _send_chunks_cp("cp" + to_string(i), g.file_metadata_gimage)
    send_cmd_baud(g.tty_fd, 115200)
    usleep(10000)
    set_option(g.tty_fd, 115200, 8, 'N', 1)
    send_cmd_vis(g.tty_fd, "cp" + to_string(i), "1")


def refresh_files_list_picture_2(path, size, i):
    g.input_path = path
    g.input_size = size
    g.begin_show_64_jpg = True


def refresh_files_list_picture_3(inputPath, size, i):
    return 0


def refresh_page_filament():
    send_cmd_txt(g.tty_fd, "nozzle_temp", to_string(g.printer_extruder_temperature))
    send_cmd_val(g.tty_fd, "nozzle_set", to_string(g.printer_extruder_target))
    send_cmd_txt(g.tty_fd, "bed_temp", to_string(g.printer_heater_bed_temperature))
    send_cmd_val(g.tty_fd, "bed_set", to_string(g.printer_heater_bed_target))
    send_cmd_txt(g.tty_fd, "chamber_temp", to_string(g.printer_hot_temperature))
    send_cmd_val(g.tty_fd, "chamber_set", to_string(g.printer_hot_target))
    if g.printer_extruder_target > 0:   # CLL button state depends on the nozzle heating
        send_cmd_picc(g.tty_fd, "nozzle_toggle", pics.filament_row_on)
        send_cmd_picc2(g.tty_fd, "nozzle_toggle", pics.filament_press_on)
        send_cmd_picc(g.tty_fd, "nozzle_row", pics.filament_row_on)
        send_cmd_picc2(g.tty_fd, "nozzle_row", pics.filament_press_on)
        send_cmd_pco(g.tty_fd, "nozzle_temp", "63488")
    else:
        send_cmd_picc(g.tty_fd, "nozzle_toggle", pics.filament_row_off)
        send_cmd_picc2(g.tty_fd, "nozzle_toggle", pics.filament_press_off)
        send_cmd_picc(g.tty_fd, "nozzle_row", pics.filament_row_off)
        send_cmd_picc2(g.tty_fd, "nozzle_row", pics.filament_press_off)
        send_cmd_pco(g.tty_fd, "nozzle_temp", "65535")

    if g.printer_heater_bed_target > 0:     # CLL button state depends on the bed heating
        send_cmd_picc(g.tty_fd, "bed_toggle", pics.filament_row_on)
        send_cmd_picc2(g.tty_fd, "bed_toggle", pics.filament_press_on)
        send_cmd_picc(g.tty_fd, "bed_row", pics.filament_row_on)
        send_cmd_picc2(g.tty_fd, "bed_row", pics.filament_press_on)
        send_cmd_pco(g.tty_fd, "bed_temp", "63488")
    else:
        send_cmd_picc(g.tty_fd, "bed_toggle", pics.filament_row_off)
        send_cmd_picc2(g.tty_fd, "bed_toggle", pics.filament_press_off)
        send_cmd_picc(g.tty_fd, "bed_row", pics.filament_row_off)
        send_cmd_picc2(g.tty_fd, "bed_row", pics.filament_press_off)
        send_cmd_pco(g.tty_fd, "bed_temp", "65535")

    if g.printer_hot_target > 0:
        send_cmd_picc(g.tty_fd, "chamber_toggle", pics.filament_row_on)
        send_cmd_picc2(g.tty_fd, "chamber_toggle", pics.filament_press_on)
        send_cmd_picc(g.tty_fd, "chamber_row", pics.filament_row_on)
        send_cmd_picc2(g.tty_fd, "chamber_row", pics.filament_press_on)
        send_cmd_pco(g.tty_fd, "chamber_temp", "63488")
    else:
        send_cmd_picc(g.tty_fd, "chamber_toggle", pics.filament_row_off)
        send_cmd_picc2(g.tty_fd, "chamber_toggle", pics.filament_press_off)
        send_cmd_picc(g.tty_fd, "chamber_row", pics.filament_row_off)
        send_cmd_picc2(g.tty_fd, "chamber_row", pics.filament_press_off)
        send_cmd_pco(g.tty_fd, "chamber_temp", "65535")

    sel = {10: 0, 50: 1, 100: 2}.get(g.printer_filament_extruedr_dist)
    if sel is not None:
        for k, name in enumerate(("step_10", "step_50", "step_100")):
            if k == sel:
                send_cmd_picc(g.tty_fd, name, pics.filament_row_on)
                send_cmd_picc2(g.tty_fd, name, pics.filament_press_on)
            else:
                send_cmd_picc(g.tty_fd, name, pics.filament_row_off)
                send_cmd_picc2(g.tty_fd, name, pics.filament_press_off)


def get_mks_connection_method():
    mksini_load()
    g.connection_method = mksini_getint("app_connection", "method", 0)
    mksini_free()


def set_mks_connection_method(target):
    g.qr_refreshed = False
    mksini_load()
    cout("######## ", target)
    mksini_set("app_connection", "method", to_string(target))
    mksini_save()
    mksini_free()
    system("sync")


def refresh_ip_address():
    """4.4.22: show the network page with the address of wlan0."""
    page_to(ui.TJC_PAGE_INTERNET_PAGE)
    ip_address = get_wlan0_ip()
    if ip_address != "":
        MKSLOG_GREEN("ip_address updated")
        send_cmd_txt(g.tty_fd, "ip_txt", ip_address)


def refresh_page_show_ip():
    """4.4.22 refresh of the network page."""
    if g.mks_ethernet == 1:
        ip_address = get_eth0_ip()
        send_cmd_txt(g.tty_fd, "ip_txt", ip_address if ip_address.find(":") == -1 else "")
        send_cmd_picc(g.tty_fd, "source_switch", pics.ip_switch_on)
        send_cmd_picc2(g.tty_fd, "source_switch", pics.ip_press_on)
    else:
        send_cmd_txt(g.tty_fd, "ip_txt", g.status_result.ip_address)
        send_cmd_picc(g.tty_fd, "source_switch", pics.ip_switch_off)
        send_cmd_picc2(g.tty_fd, "source_switch", pics.ip_press_off)


TIMELAPSE_URL = "http://127.0.0.1:7125/machine/timelapse/settings"


def check_timelapse_state():
    """4.4.22: state of Moonraker's timelapse plugin (off when it is not installed)."""
    try:
        with urllib.request.urlopen(TIMELAPSE_URL, timeout=2) as resp:
            g.timelapse_enabled = bool(_json.loads(resp.read().decode("utf-8"))["result"]["enabled"])
    except Exception as e:
        cerr("Timelapse state: ", str(e), "\n")
        g.timelapse_enabled = False
    return g.timelapse_enabled


def switch_timelapse_state():
    """4.4.22: turn Moonraker's timelapse on / off (preview page)."""
    url = TIMELAPSE_URL + ("?enabled=False" if g.timelapse_enabled else "?enabled=True")
    try:
        urllib.request.urlopen(urllib.request.Request(url, data=b"", method="POST"), timeout=2).close()
        g.timelapse_enabled = not g.timelapse_enabled
    except Exception as e:
        cerr("Timelapse switch: ", str(e), "\n")     # no plugin: the switch stays off


def get_mks_selected_server():
    mksini_load()
    g.selected_server = mksini_getstring("app_server", "name", "")
    mksini_free()
    cout(g.selected_server)


def go_to_server_set(n):
    g.current_server_page = n
    g.total_server_count = 0
    g.serverConfigs.clear()
    if g.connection_method == 1 and g.status_result.wpa_state == "COMPLETED":
        page_to(ui.TJC_PAGE_SEARCH_SERVER)
        update_server(0)
        get_mks_selected_server()
        get_mks_connection_method()
    page_to(ui.TJC_PAGE_SERVER_SET)


def updateServerConfig(lines, config):
    for i in range(len(lines)):
        if lines[i] == "[app_server]":
            # make sure we are not at the end of the file
            if i + 1 < len(lines):
                # simply replace the next line
                lines[i + 1] = "name = " + config.name
                return

    # no [app_server] section: append it at the end of the file
    lines.append("[app_server]")
    lines.append("name = " + config.name)


def _server_config(id_):
    """std::map<int, Server_config>::operator[]"""
    if id_ not in g.serverConfigs:
        g.serverConfigs[id_] = Server_config()
    return g.serverConfigs[id_]


def update_server(choice):
    # CLL download the server list (json)
    if choice == 0:
        get_mks_selected_server()
        server_for_command = "aws" if g.selected_server == "" else g.selected_server
        command = ("curl -s -S -L -o /root/frp/server_list.json http://www." + server_for_command +
                   ".qidi3dprinter.com:5050/downloads/server_list.json")
        cout("Executing command: ", command)
        system(command)
    else:
        g.qr_refreshed = False      # CLL switching the server requires a new QR code

    g.total_server_count = 0
    FRPC_CONFIG_PATH = "/root/frp/frpc.toml"
    MKSCONFIG_PATH = paths.klipper_config() + "/config.mksini"
    SERVER_LIST_PATH = "/root/frp/server_list.json"     # path of the JSON file

    try:
        # read the JSON file and parse the server configurations
        data = read_file(SERVER_LIST_PATH)
        serverList = json_parse(data if data is not None else "")
        if isinstance(serverList, dict):
            items = [(k, serverList[k]) for k in sorted(serverList, key=s2b)]
        elif isinstance(serverList, list):
            items = [(str(k), v) for k, v in enumerate(serverList)]
        else:
            items = [("", serverList)] if serverList is not None else []
        for key, value in items:
            id_ = stoi(key)
            config = Server_config(jstr(jget(value, "address")), jstr(jget(value, "name")))
            cout(id_, ":", config.name)
            g.serverConfigs[id_] = config
            g.total_server_count += 1
    except Exception as e:
        cerr("fail_to_read:", str(e), "\n")

    if choice != 0:
        if choice not in g.serverConfigs:
            cout("Invalid choice. Please enter a valid option.")
            return

        config = g.serverConfigs[choice]

        # stop frpc.service
        cout("Stopping frpc.service...")
        system("sudo systemctl stop frpc.service")

        # update frpc.toml
        content = read_file(FRPC_CONFIG_PATH)
        if content is None:
            content = ""

        pos = content.find("serverAddr = ")
        if pos != -1:
            endPos = content.find("\n", pos)
            new = "serverAddr = \"" + config.address + "\""
            if endPos == -1:
                content = content[:pos] + new
            else:
                content = content[:pos] + new + content[endPos:]

        try:
            with open(FRPC_CONFIG_PATH, "wb") as frpcOut:
                frpcOut.write(s2b(content))
        except OSError:
            pass

        # read config.mksini into a list
        lines = getline_all(MKSCONFIG_PATH)

        # update the app_server configuration
        updateServerConfig(lines, config)

        # write the updated content back to config.mksini
        try:
            with open(MKSCONFIG_PATH, "wb") as mksOut:
                for outputLine in lines:
                    mksOut.write(s2b(outputLine) + b"\n")
        except OSError:
            pass

        # restart frpc.service
        cout("Starting frpc.service...")
        system("sudo systemctl start frpc.service")

        cout("Configuration updated to ", config.name, " successfully.")
        get_mks_selected_server()


def refresh_page_server_set():
    if g.connection_method == 0 or g.status_result.wpa_state != "COMPLETED":
        send_cmd_picc(g.tty_fd, "b2", pics.server_row_off)
        send_cmd_picc2(g.tty_fd, "b2", pics.server_press_off)
        send_cmd_vis(g.tty_fd, "msg", "1")
        send_cmd_vis(g.tty_fd, "t0", "0")
        send_cmd_vis(g.tty_fd, "prev_btn", "0")
        send_cmd_vis(g.tty_fd, "next_btn", "0")
        send_cmd_vis(g.tty_fd, "refresh_btn", "0")
    else:
        send_cmd_picc(g.tty_fd, "b2", pics.server_row_on)
        send_cmd_picc2(g.tty_fd, "b2", pics.server_press_on)
        send_cmd_vis(g.tty_fd, "msg", "0")
        send_cmd_vis(g.tty_fd, "t0", "1")
        send_cmd_vis(g.tty_fd, "prev_btn", "1")
        send_cmd_vis(g.tty_fd, "next_btn", "1")
        send_cmd_vis(g.tty_fd, "refresh_btn", "1")

    if g.current_server_page == 0:
        send_cmd_picc(g.tty_fd, "prev_btn", pics.server_row_on)
        send_cmd_picc2(g.tty_fd, "prev_btn", pics.server_press_on)
    else:
        send_cmd_picc(g.tty_fd, "prev_btn", pics.server_row_off)
        send_cmd_picc2(g.tty_fd, "prev_btn", pics.server_press_off)

    if (g.current_server_page + 1) * 4 >= g.total_server_count:
        send_cmd_picc(g.tty_fd, "next_btn", pics.server_row_on)
        send_cmd_picc2(g.tty_fd, "next_btn", pics.server_press_on)
    else:
        send_cmd_picc(g.tty_fd, "next_btn", pics.server_row_off)
        send_cmd_picc2(g.tty_fd, "next_btn", pics.server_press_off)
    for i in range(4):
        if i + g.current_server_page * 4 + 1 > g.total_server_count:
            break
        send_cmd_txt(g.tty_fd, "srv" + to_string(i + 1) + "_txt", _server_config(1 + i + g.current_server_page * 4).name)
        if g.selected_server == _server_config(1 + i + g.current_server_page * 4).name:
            cout("selected_server:", _server_config(i + 1 + g.current_server_page * 4).name)
            send_cmd_picc(g.tty_fd, "srv" + to_string(i + 1), pics.server_row_off)
            send_cmd_picc2(g.tty_fd, "srv" + to_string(i + 1), pics.server_press_on)
        else:
            cout("unselected_server:", _server_config(i + 1 + g.current_server_page * 4).name)
            send_cmd_picc(g.tty_fd, "srv" + to_string(i + 1), pics.server_row_on)
            send_cmd_picc2(g.tty_fd, "srv" + to_string(i + 1), pics.server_press_off)


def local_update():
    g.ep.Send(json_get_klippy_host_information())
    if detect_update():
        page_to(ui.TJC_PAGE_UPDATE_FOUND)
    else:
        page_to(ui.TJC_PAGE_UPDATE_NOT_FOUND)


def run_python_code(cmd):
    """CLL runs a command and returns its output"""
    out = popen_read(cmd)
    if out is None:
        raise RuntimeError("popen() failed!")
    result = b""
    pos = 0
    while pos < len(out):
        # fgets(buffer.data(), 128, pipe) + result += buffer.data()
        end = out.find(b"\n", pos, pos + 127)
        end = (pos + 127) if end == -1 else end + 1
        result += cstr(out[pos:end])
        pos = end
    return b2s(result)


def check_online_version():
    page_to(ui.TJC_PAGE_SEARCH_SERVER)
    if g.connection_method == 0:
        return
    g.target_soc_version = run_python_code("python3 /root/auto_update/version_check.py")
    cout("Server version:", g.target_soc_version)
    if g.target_soc_version.find("0") == 0:
        page_to(ui.TJC_PAGE_UPDATE_MODE)
        send_cmd_vis(g.tty_fd, "msg_latest", "1")
        send_cmd_vis(g.tty_fd, "msg_failed", "0")
    elif g.target_soc_version.find("-1") == 0:
        page_to(ui.TJC_PAGE_UPDATE_MODE)
        send_cmd_vis(g.tty_fd, "msg_failed", "1")
        send_cmd_vis(g.tty_fd, "msg_latest", "0")
    else:
        page_to(ui.TJC_PAGE_ONLINE_UPDATE)
        send_cmd_txt(g.tty_fd, "ver_cur", g.mks_version_soc)
        send_cmd_txt(g.tty_fd, "ver_new", g.target_soc_version)
        updateini_load()
        # CLL update notes in Chinese, Russian, English, Japanese, French, German,
        # Italian, Spanish, Korean, Portuguese, Arabic, Turkish and Hebrew
        langs = ["cn", "ru", "en", "jp", "fr", "gr", "it", "sp", "kr", "pr", "ar", "tr", "hb"]
        infos = [mksini_getstring(lang, "content", "NULL") for lang in langs]
        for lang, info in zip(langs, infos):
            send_cmd_txt(g.tty_fd, "notes_" + lang, info)
        mksini_free()


def online_update():
    page_to(ui.TJC_PAGE_UPDATING)
    send_cmd_vis(g.tty_fd, "progress", "1")
    send_cmd_vis(g.tty_fd, "pct_txt", "1")
    pthread_create(recevice_progress_handle, None)
    system("rm " + paths.gcode_files() + "/.cache/*\n")
    system("python3 /root/auto_update/download_update.py\n")
    system("sync\n")
    system("systemctl restart makerbase-client\n")


def recevice_progress_handle(arg=None):
    """CLL thread that shows the progress of the online update"""
    import time
    while True:
        if g.current_page_id == ui.TJC_PAGE_UPDATING:
            progressini_load()
            update_progress = mksini_getint("progress", "value", 0)        # (uninitialised default in C++)
            progress_name = mksini_getstring("filename", "name", "")
            mksini_free()
            if progress_name.find("Installing") == -1:
                send_cmd_txt(g.tty_fd, "info_txt", progress_name)
                send_cmd_val(g.tty_fd, "progress", to_string(update_progress))
                send_cmd_txt(g.tty_fd, "pct_txt", to_string(update_progress) + "%")
            else:
                page_to(ui.TJC_PAGE_INSTALLING)
                break
        time.sleep(0)   # the C++ thread spins without sleeping; yield the GIL here
    return None


def refresh_page_auto_unload():
    send_cmd_txt(g.tty_fd, "temp_txt", "(" + to_string(g.printer_extruder_temperature) + "/" +
                 to_string(g.printer_extruder_target) + "℃)")
    if g.step_1 == True:
        g.step_1 = False
        send_cmd_vis(g.tty_fd, "spin1", "0")
        send_cmd_vis(g.tty_fd, "spin2", "1")
        send_cmd_picc(g.tty_fd, "steps_bar", pics.unload_steps_1)
        send_cmd_pco(g.tty_fd, "step2_txt", "65535")
        send_cmd_pco(g.tty_fd, "step1_txt", "38066")
    if g.step_2 == True:
        g.step_2 = False
        send_cmd_vis(g.tty_fd, "spin2", "0")
        send_cmd_picc(g.tty_fd, "steps_bar", pics.unload_steps_2)
        send_cmd_pco(g.tty_fd, "step3_txt", "65535")
        send_cmd_pco(g.tty_fd, "step2_txt", "38066")
        send_cmd_vis(g.tty_fd, "load_btn", "1")
        send_cmd_vis(g.tty_fd, "ok", "1")


def get_mks_ethernet():
    mksini_load()
    g.mks_ethernet = int(mksini_getboolean("mks_ethernet", "enable", 0))
    mksini_free()
    return g.mks_ethernet


def set_mks_ethernet(target):
    cout("Setting ethernet:", target)
    mksini_load()
    mksini_set("mks_ethernet", "enable", to_string(target))
    mksini_save()
    mksini_free()
    g.mks_ethernet = target


def check_print_interrupted():
    printer_variables = read_file(paths.klipper_config() + "/saved_variables.cfg")
    if printer_variables is None:
        cerr("Can't open the file ", paths.klipper_config() + "/saved_variables.cfg", "\n")
        return
    print_interrupted_status = substr(printer_variables, printer_variables.find("was_interrupted =") + 18, 5)
    if print_interrupted_status != "False":
        g.ep.Send(json_run_a_gcode("DETECT_INTERRUPTION\n"))
        g.jump_to_resume_print = True
