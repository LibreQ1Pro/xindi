"""What every screen page shows: the refresh functions are called with the page that is open."""

from . import state as g
from . import pageids as ids
from . import pics
from . import thumbnail
from .ui import page_to
from .cpp import to_string, substr, f32, c_int, c_round, system, sleep, usleep
from .mks_log import MKSLOG_BLUE, MKSLOG_RED, cout, cerr
from .send_msg import (send_cmd_txt, send_cmd_val, send_cmd_pco, send_cmd_picc, send_cmd_picc2,
                       send_cmd_vis, send_cmd_pic, send_cmd_cp_close, send_cmd_cp_image,
                       send_cmd_baud, send_cmd_txt_plus)
from .MakerbaseSerial import set_option
from .MoonrakerAPI import json_run_a_gcode
from .mks_printer import get_cal_printing_time
from .mks_file import output_imgdata
from . import actions, filelist, settings, wifi_ui


def _replace_for_screen(text):
    text = text.replace("\n", ".")
    text = text.replace("'", " ")
    text = text.replace("\"", " ")
    return text


def show():
    # 4.4.22: nothing is sent to the screen while the list pictures are transferred
    if g.pictures.send_jpg_status:
        return
    # CLL the jumps below are unconditional, the flags were set after the
    # checks were done (the flag has to be reset before switching the page,
    # otherwise this would loop forever)
    if g.screen.jump_move_pop_1 == True:
        g.screen.jump_move_pop_1 = False
        page_to(ids.MOVE_POP_1)
    if g.screen.jump_move_pop_2 == True:
        homing = "SET_KINEMATIC_POSITION Z=150\nSET_KINEMATIC_POSITION X=150\nSET_KINEMATIC_POSITION Y=150\n"
        moves = {
            1: "G91\nG1 X10 F3000\nG90\nM84\n",       # X_UP
            2: "G91\nG1 X-10 F3000\nG90\nM84\n",      # X_DOWN
            3: "G91\nG1 Y10 F3000\nG90\nM84\n",       # Y_UP
            4: "G91\nG1 Y-10 F3000\nG90\nM84\n",      # Y_DOWN
            5: "G91\nG1 Z-10 F600\nG90\nM84\n",       # Z_UP
            6: "G91\nG1 Z10 F600\nG90\nM84\n",        # Z_DOWN
        }
        if g.screen.unhomed_move_mode in moves:
            g.ep.Send(json_run_a_gcode(homing))
            g.ep.Send(json_run_a_gcode(moves[g.screen.unhomed_move_mode]))
        g.screen.unhomed_move_mode = 0
        g.screen.jump_move_pop_2 = False
        page_to(ids.MOVE_POP_2)
    if g.screen.jump_detect_error == True:
        g.screen.jump_detect_error = False
        page_to(ids.DETECT_ERROR)
        send_cmd_txt(g.tty_fd, "msg", g.screen.error_message)
    if g.screen.jump_level_error == True:
        g.screen.jump_level_error = False
        page_to(ids.LEVEL_ERROR)
    if g.screen.jump_filament_pop_1 == True:
        g.screen.jump_filament_pop_1 = False
        page_to(ids.FILAMENT_POP_1)
    if g.screen.jump_print_low_temp == True:
        g.screen.jump_print_low_temp = False
        page_to(ids.PRINT_LOW_TEMP)
    if g.screen.jump_resume_print == True:
        # 4.4.24: the flag is reset when the page reports that it is shown
        page_to(ids.RESUME_PRINT)
    if g.screen.jump_memory_warning == True:
        g.screen.jump_memory_warning = False
        page_to(ids.MEMORY_WARNING)

    if g.screen.page != ids.PRINTING:
        if g.screen.page in (ids.PRINT_ZOFFSET, ids.PRINT_FILAMENT):
            pass
        elif g.screen.page in (ids.PRINT_STOP, ids.PRINT_NO_FILAMENT,
                                   ids.PRINT_NO_FILAMENT_2, ids.SHUTDOWN,
                                   ids.PRINT_STOPPING, ids.MOVE_POP_1,
                                   ids.GCODE_ERROR, ids.DETECT_ERROR, ids.RESET,
                                   ids.PREVIEW, ids.PREVIEW_POP_1, ids.PREVIEW_POP_2,
                                   ids.PRINTING_2, ids.FILAMENT_POP_2,
                                   ids.FILAMENT_POP_3, ids.STOP_CONFIRM):
            pass
        else:
            if g.klippy.print_stats_state == "printing":
                if g.klippy.print_stats_filename != "":
                    g.screen.main_picture_detected = False
                    g.screen.main_picture_refreshed = False
                    g.screen.muted = False         # 4.4.22 silent mode is per print
                    MKSLOG_BLUE("Jumping to the print page\n")
                    sleep(1)
                    filelist.get_file_estimated_time(g.klippy.print_stats_filename)
                    sleep(1)
                    g.screen.jump_print = True
                    g.klippy.ready = False
                    page_to(ids.PREVIEW)

    if g.screen.page != ids.RESET:
        if g.screen.page in (ids.GCODE_ERROR, ids.DETECT_ERROR, ids.LEVEL_ERROR,
                                 ids.SHUTDOWN, ids.SERVICE, ids.LANGUAGE,
                                 ids.COMMON_SETTING, ids.SLEEP_MODE, ids.INTERNET,
                                 ids.WIFI_LIST, ids.WIFI_KB, ids.WIFI_CONNECT,
                                 ids.WIFI_FAILED, ids.WIFI_SUCCESS, ids.WIFI_SAVING,
                                 ids.NET_SAVED, ids.NET_DETAIL, ids.NET_CONFIRM,
                                 ids.NET_INFO,
                                 ids.RESTORE_CONFIG, ids.INTERNET_PAGE):
            pass
        else:
            # jump to the restart page when the toolhead board is disconnected
            if g.klippy.webhooks_state == "shutdown" or g.klippy.webhooks_state == "error":
                if g.klippy.webhooks_state == "shutdown" and (g.screen.page == ids.AUTO_MOVING
                                                               or g.screen.page == ids.OPEN_CALIBRATE):
                    pass
                else:
                    page_to(ids.RESET)
                    cout("Restart page")
                    if g.shown.webhooks_state_message != g.klippy.webhooks_state_message:
                        g.shown.webhooks_state_message = g.klippy.webhooks_state_message
                        send_cmd_txt(g.tty_fd, "err_msg", _replace_for_screen(g.klippy.webhooks_state_message))
    elif g.screen.page == ids.RESET:
        if g.klippy.webhooks_state == "shutdown" or g.klippy.webhooks_state == "error":
            if g.shown.webhooks_state_message != g.klippy.webhooks_state_message:
                g.shown.webhooks_state_message = g.klippy.webhooks_state_message
                send_cmd_txt(g.tty_fd, "err_msg", _replace_for_screen(g.klippy.webhooks_state_message))
        if g.klippy.webhooks_state == "ready":
            page_to(ids.SYS_OK)

    page = g.screen.page
    if page == ids.MAIN:
        main()
    elif page == ids.PREVIEW:
        preview()
    elif page in (ids.PRINTING, ids.PRINTING_2):
        printing()
    elif page == ids.PRINT_FILAMENT:
        print_filament()
    elif page == ids.MOVE:
        move_page()
    elif page == ids.PRINT_ZOFFSET:
        printing_zoffset()
    elif page == ids.AUTO_MOVING:
        auto_moving()
    elif page == ids.AUTO_FINISH:
        auto_finish()
    elif page == ids.SYNTONY_MOVE:
        syntony_move()
    elif page == ids.SYNTONY_FINISH:
        pass
    elif page == ids.PRINT_STOPPING:
        stopping()
    elif page == ids.PRE_BED_CALIBRATION:
        auto_level()
    elif page == ids.OPEN_FILAMENTVIDEO_2:
        open_filament_video_2()
    elif page == ids.ZOFFSET:
        zoffset()
    elif page == ids.AUTO_HEATERBED:
        auto_heaterbed()
    elif page == ids.OPEN_HEATERBED:
        open_heaterbed()
    elif page in (ids.FILAMENT_POP_2, ids.FILAMENT_POP_3):
        filament_pop()
    elif page in (ids.PREVIEW_POP_1, ids.PREVIEW_POP_2):
        preview_pop()
    elif page == ids.FILE_LIST:
        pass        # 4.4.2 CLL local / USB buttons on the file list page
    elif page == ids.BED_MOVING:
        bed_moving()
    elif page == ids.OPEN_CALIBRATE:
        open_calibrate()
    elif page == ids.COMMON_SETTING:
        common_setting()
    elif page == ids.FILAMENT_SET_FAN:
        filament_set_fan()
    elif page == ids.WIFI_KB:
        wifi_ui.refresh_wifi_keyboard()
    elif page == ids.FILAMENT:
        filament()
    elif page == ids.INTERNET_PAGE:
        wifi_ui.refresh_show_ip()
    elif page == ids.AUTO_UNLOAD:
        auto_unload()
    elif page == ids.OPEN_MOVING:
        open_moving()


def open_filament_video_2():
    if g.klippy.extruder_target == 0:
        send_cmd_pco(g.tty_fd, "temp_now", "65535")
        send_cmd_pco(g.tty_fd, "temp_target", "65535")
        send_cmd_picc(g.tty_fd, "heat_toggle", pics.open_heat_off)
        send_cmd_picc2(g.tty_fd, "heat_toggle", pics.open_heat_off_press)
    else:
        send_cmd_pco(g.tty_fd, "temp_now", "63488")
        send_cmd_pco(g.tty_fd, "temp_target", "63488")
        send_cmd_picc(g.tty_fd, "heat_toggle", pics.open_heat_on)
        send_cmd_picc2(g.tty_fd, "heat_toggle", pics.open_heat_on_press)

    send_cmd_txt(g.tty_fd, "temp_now", to_string(g.klippy.extruder_temperature) + "/")
    send_cmd_val(g.tty_fd, "temp_target", to_string(g.klippy.extruder_target))


def syntony_finish():
    MKSLOG_BLUE("Printer ide_timeout state: %s", g.klippy.idle_timeout_state)
    MKSLOG_BLUE("Printer webhooks state: %s", g.klippy.webhooks_state)
    if g.levelling.syntony_finished == False:
        g.levelling.syntony_finished = True
        g.levelling.all_level_saving = False

    if g.klippy.idle_timeout_state == "Ready" and g.klippy.webhooks_state == "ready":
        MKSLOG_BLUE("Printer webhooks state: %s", g.klippy.webhooks_state)
        sleep(10)
        system("sync")      # make sure the config file is saved

        g.levelling.all_level_saving = False
        settings.get_babystep()  # 4.4.22 (was init_mks_status())
        actions.sub_object_status()
        actions.get_object_status()
        sleep(10)
        page_to(ids.LEVEL_MODE)
        MKSLOG_RED("Left from line 739")


def _picc_group(names, selected, on_picc, off_picc, on_picc2, off_picc2):
    for i, name in enumerate(names):
        send_cmd_picc(g.tty_fd, name, on_picc if i == selected else off_picc)
    for i, name in enumerate(names):
        send_cmd_picc2(g.tty_fd, name, on_picc2 if i == selected else off_picc2)


def auto_level():
    names = ["step_001", "step_005", "step_01", "step_05"]
    if g.levelling.auto_level_dist == f32(0.01):
        _picc_group(names, 0, pics.prebed_step_on, pics.prebed_step_off, pics.prebed_press_on, pics.prebed_press_off)
    elif g.levelling.auto_level_dist == f32(0.05):
        _picc_group(names, 1, pics.prebed_step_on, pics.prebed_step_off, pics.prebed_press_on, pics.prebed_press_off)
    elif g.levelling.auto_level_dist == f32(0.1):
        _picc_group(names, 2, pics.prebed_step_on, pics.prebed_step_off, pics.prebed_press_on, pics.prebed_press_off)
    elif g.levelling.auto_level_dist == f32(0.5):
        _picc_group(names, 3, pics.prebed_step_on, pics.prebed_step_off, pics.prebed_press_on, pics.prebed_press_off)


def stopping():
    MKSLOG_BLUE("Printer ide_timeout state: %s", g.klippy.idle_timeout_state)
    MKSLOG_BLUE("Printer webhooks state: %s", g.klippy.webhooks_state)
    if g.klippy.idle_timeout_state == "Ready":
        actions.clear_previous_data()
        sleep(5)
        actions.save_current_zoffset()
        page_to(ids.MAIN)


def syntony_move():
    if g.screen.temp_idle_state != g.klippy.idle_timeout_state:
        g.screen.temp_idle_state = g.klippy.idle_timeout_state
        MKSLOG_BLUE("Printer ide_timeout state: %s", g.klippy.idle_timeout_state)
        MKSLOG_BLUE("Printer webhooks state: %s", g.klippy.webhooks_state)

    if g.levelling.step_1 == True:
        sleep(15)
        page_to(ids.SYNTONY_FINISH)
        g.levelling.step_1 = False


def print_filament():
    send_cmd_txt(g.tty_fd, "file_name", filelist._file_name_only(g.klippy.print_stats_filename))

    if g.klippy.extruder_target == 0:
        send_cmd_pco(g.tty_fd, "temp_now", "65535")
        send_cmd_picc(g.tty_fd, "heat_btn", pics.printfil_heat_off)
        send_cmd_picc2(g.tty_fd, "heat_btn", pics.printfil_press_off)
    else:
        send_cmd_pco(g.tty_fd, "temp_now", "63488")
        send_cmd_picc(g.tty_fd, "heat_btn", pics.printfil_heat_on)
        send_cmd_picc2(g.tty_fd, "heat_btn", pics.printfil_press_on)

    send_cmd_val(g.tty_fd, "progress", to_string(g.klippy.display_status_progress))
    send_cmd_val(g.tty_fd, "progress_pct", to_string(g.klippy.display_status_progress))
    send_cmd_txt(g.tty_fd, "temp_now", to_string(g.klippy.extruder_temperature))
    send_cmd_txt(g.tty_fd, "temp_set", to_string(g.klippy.extruder_target))
    send_cmd_txt(g.tty_fd, "time_elapsed", actions.show_time(c_int(g.klippy.print_stats_print_duration)))
    send_cmd_txt(g.tty_fd, "time_left", actions.show_time(get_cal_printing_time(c_int(g.klippy.print_stats_print_duration),
                                                                 g.files.meta_estimated_time,
                                                                 g.klippy.display_status_progress)))

    if g.klippy.print_stats_state == "paused":
        g.klippy.ready = True

    # 4.4.2 CLL support mates and hall filament width sensors
    if g.klippy.filament_detected == False:
        sleep(1)
        g.klippy.ready = False
        actions.set_print_pause()
        page_to(ids.PRINT_NO_FILAMENT)

    if g.klippy.print_stats_state == "printing":
        if g.klippy.ready == True:
            g.klippy.ready = False
            page_to(ids.PRINTING)

    if g.klippy.print_stats_state == "standby":
        page_to(ids.PRINT_STOPPING)

    if g.klippy.print_stats_state == "error":
        page_to(ids.GCODE_ERROR)
        actions.cancel_print()
        actions.clear_previous_data()
        send_cmd_txt(g.tty_fd, "msg", "G-code error: " + g.screen.error_message)

    # 4.4.2 CLL a long pause that stops the print switches the page
    if g.klippy.idle_timeout_state == "Idle":
        g.ep.Send(json_run_a_gcode("G28\n"))
        actions.cancel_print()


def auto_finish():
    if g.klippy.idle_timeout_state == "Idle" and g.klippy.webhooks_state == "ready":
        g.levelling.auto_level_finished = True


def auto_moving():
    send_cmd_txt(g.tty_fd, "bed_temp", "(" + to_string(g.klippy.heater_bed_temperature) + "/" +
                 to_string(g.klippy.heater_bed_target) + ")")
    if g.levelling.step_1 == True:
        send_cmd_picc(g.tty_fd, "steps_bar", pics.auto_steps_1)
        send_cmd_pco(g.tty_fd, "step2_txt", "65535")
        send_cmd_pco(g.tty_fd, "step1_txt", "38066")
        send_cmd_vis(g.tty_fd, "spin1", "0")
        send_cmd_vis(g.tty_fd, "spin2", "1")
        g.levelling.step_1 = False
    if g.levelling.step_2 == True:
        send_cmd_picc(g.tty_fd, "steps_bar", pics.auto_steps_2)
        send_cmd_pco(g.tty_fd, "step3_txt", "65535")
        send_cmd_pco(g.tty_fd, "step2_txt", "38066")
        send_cmd_vis(g.tty_fd, "spin2", "0")
        send_cmd_vis(g.tty_fd, "spin3", "1")
        g.levelling.step_2 = False
    if g.levelling.step_3 == True:
        send_cmd_picc(g.tty_fd, "steps_bar", pics.auto_steps_3)
        send_cmd_pco(g.tty_fd, "step4_txt", "65535")
        send_cmd_pco(g.tty_fd, "step3_txt", "38066")
        send_cmd_vis(g.tty_fd, "spin3", "0")
        send_cmd_vis(g.tty_fd, "spin4", "1")
        g.levelling.step_3 = False
        g.klippy.idle_timeout_state = "Printing"
        settings.get_heater_bed_target()
        actions.set_heater_bed_target(g.config.heater_bed_target)
        g.ep.Send(json_run_a_gcode("M190 S" + to_string(g.config.heater_bed_target) + "\n"))
        sleep(1)
        g.ep.Send(json_run_a_gcode("M4027\n"))
    if g.levelling.step_4 == True:
        sleep(15)
        page_to(ids.AUTO_FINISH)
        g.levelling.step_4 = False


def _cut_after_point(text, n):
    """``s.substr(0, s.find(".") + n)``"""
    return substr(text, 0, text.find(".") + n)


def move_page():
    x_pos = _cut_after_point(to_string(g.klippy.x_position), 2)
    y_pos = _cut_after_point(to_string(g.klippy.y_position), 2)
    z_pos = _cut_after_point(to_string(g.klippy.z_position), 2)

    send_cmd_txt(g.tty_fd, "x_pos", x_pos)
    send_cmd_txt(g.tty_fd, "y_pos", y_pos)
    send_cmd_txt(g.tty_fd, "z_pos", z_pos)

    # CLL highlight the selected distance
    if g.klippy.move_dist == f32(0.1):
        send_cmd_picc(g.tty_fd, "dist_01", pics.move_dist_on)
        send_cmd_picc2(g.tty_fd, "dist_01", pics.move_dist_on_press)
        send_cmd_picc(g.tty_fd, "dist_1", pics.move_dist_off)
        send_cmd_picc2(g.tty_fd, "dist_1", pics.move_dist_off_press)
        send_cmd_picc(g.tty_fd, "dist_10", pics.move_dist_off)
        send_cmd_picc2(g.tty_fd, "dist_10", pics.move_dist_off_press)
    elif g.klippy.move_dist == f32(1.0):
        send_cmd_picc(g.tty_fd, "dist_01", pics.move_dist_off)
        send_cmd_picc2(g.tty_fd, "dist_01", pics.move_dist_off_press)
        send_cmd_picc(g.tty_fd, "dist_1", pics.move_dist_on)
        send_cmd_picc2(g.tty_fd, "dist_1", pics.move_dist_on_press)
        send_cmd_picc(g.tty_fd, "dist_10", pics.move_dist_off)
        send_cmd_picc2(g.tty_fd, "dist_10", pics.move_dist_off_press)
    elif g.klippy.move_dist == f32(10):
        send_cmd_picc(g.tty_fd, "dist_01", pics.move_dist_off)
        send_cmd_picc2(g.tty_fd, "dist_01", pics.move_dist_off_press)
        send_cmd_picc(g.tty_fd, "dist_1", pics.move_dist_off)
        send_cmd_picc2(g.tty_fd, "dist_1", pics.move_dist_off_press)
        send_cmd_picc(g.tty_fd, "dist_10", pics.move_dist_on)
        send_cmd_picc2(g.tty_fd, "dist_10", pics.move_dist_on_press)


def offset(intern_zoffset):
    g.klippy.intern_z_offset = f32(intern_zoffset)
    g.klippy.z_offset = f32(g.klippy.intern_z_offset + g.klippy.extern_z_offset)


def _zoffset_buttons():
    pairs = {
        0: (pics.zoffset_step_on, pics.zoffset_step_press_on),
        1: (pics.zoffset_step_off, pics.zoffset_step_press_off),
    }
    sel = None
    if g.klippy.set_offset == f32(0.01):
        sel = 1
    elif g.klippy.set_offset == f32(0.05):
        sel = 2
    elif g.klippy.set_offset == f32(0.1):
        sel = 3
    elif g.klippy.set_offset == f32(0.5):
        sel = 4
    if sel is None:
        return
    for b in range(1, 5):
        picc, picc2 = pairs[0] if b == sel else pairs[1]
        send_cmd_picc(g.tty_fd, ("step_001", "step_005", "step_01", "step_05")[b - 1], picc)
        send_cmd_picc2(g.tty_fd, ("step_001", "step_005", "step_01", "step_05")[b - 1], picc2)


def printing_zoffset():
    z_offset = to_string(g.klippy.gcode_move_homing_origin[2])
    show_gcode_z = to_string(g.klippy.gcode_z_position)
    z_offset = _cut_after_point(z_offset, 4)
    show_gcode_z = _cut_after_point(show_gcode_z, 4)
    send_cmd_txt(g.tty_fd, "file_name", filelist._file_name_only(g.klippy.print_stats_filename))
    if z_offset != g.config.babystep_value:
        g.config.babystep_value = z_offset
        settings.set_babystep(g.config.babystep_value)
    send_cmd_txt(g.tty_fd, "gcode_z", show_gcode_z)
    send_cmd_txt(g.tty_fd, "z_offset", z_offset)
    send_cmd_txt(g.tty_fd, "time_elapsed", actions.show_time(c_int(g.klippy.print_stats_print_duration)))
    send_cmd_val(g.tty_fd, "progress_pct", to_string(g.klippy.display_status_progress))
    send_cmd_txt(g.tty_fd, "time_left", actions.show_time(get_cal_printing_time(c_int(g.klippy.print_stats_print_duration),
                                                                 g.files.meta_estimated_time,
                                                                 g.klippy.display_status_progress)))
    send_cmd_val(g.tty_fd, "progress", to_string(g.klippy.display_status_progress))

    _zoffset_buttons()

    if g.klippy.print_stats_state == "printing":
        g.klippy.ready = True

    if g.klippy.fila_sensor_enabled == True:
        if g.klippy.fila_sensor_detected == False:
            g.klippy.ready = False
            actions.set_print_pause()
            page_to(ids.PRINT_NO_FILAMENT_2)

    # 4.4.2 CLL support mates and hall filament width sensors
    if g.klippy.filament_detected == False:
        sleep(1)
        g.klippy.ready = False
        actions.set_print_pause()
        page_to(ids.PRINT_NO_FILAMENT)

    if g.klippy.print_stats_state == "standby":
        page_to(ids.PRINT_STOPPING)

    if g.klippy.print_stats_state == "paused":
        if g.klippy.ready == True:
            g.klippy.ready = False
            page_to(ids.PRINT_FILAMENT)

    if g.klippy.print_stats_state == "complete":
        time_duration = actions.show_time(c_int(g.klippy.print_stats_print_duration))
        actions.complete_print()
        actions.clear_previous_data()
        sleep(5)
        actions.save_current_zoffset()
        page_to(ids.PRINT_FINISH)
        send_cmd_txt(g.tty_fd, "time_txt", time_duration)

    if g.klippy.print_stats_state == "error":
        page_to(ids.GCODE_ERROR)
        actions.cancel_print()
        actions.clear_previous_data()
        send_cmd_txt(g.tty_fd, "msg", "G-code error: " + g.screen.error_message)


def printing():
    z_offset = to_string(g.klippy.gcode_move_homing_origin[2])
    z_offset = _cut_after_point(z_offset, 4)

    send_cmd_val(g.tty_fd, "progress", to_string(g.klippy.display_status_progress))
    send_cmd_val(g.tty_fd, "progress_pct", to_string(g.klippy.display_status_progress))
    send_cmd_txt(g.tty_fd, "time_elapsed", actions.show_time(c_int(g.klippy.print_stats_print_duration)))
    send_cmd_txt(g.tty_fd, "time_left", actions.show_time(get_cal_printing_time(c_int(g.klippy.print_stats_print_duration),
                                                                 g.files.meta_estimated_time,
                                                                 g.klippy.display_status_progress)))
    send_cmd_txt(g.tty_fd, "file_name", filelist._file_name_only(g.klippy.print_stats_filename))

    # the z offset of the second page is always refreshed: the page starts with
    # the designer's "-1.000", it must not stay while the keyboard flag is set
    if g.screen.page == ids.PRINTING_2:
        send_cmd_txt(g.tty_fd, "zoffset_val", z_offset)

    if g.screen.printing_keyboard_enabled == True:     # 4.4.22 silent mode button of the keyboard
        if g.screen.muted == False:
            send_cmd_picc(g.tty_fd, "mute_btn", pics.kb_mute_off)
            send_cmd_picc2(g.tty_fd, "mute_btn", pics.kb_mute_off_press)
        else:
            send_cmd_picc(g.tty_fd, "mute_btn", pics.kb_mute_on)
            send_cmd_picc2(g.tty_fd, "mute_btn", pics.kb_mute_on_press)
    else:                                       # CLL refresh only while the keyboard is not shown
        if g.screen.page == ids.PRINTING:
            # CLL fan speeds
            send_cmd_val(g.tty_fd, "fan1_val", to_string(c_int(f32(g.klippy.out_pin_fan0_value * 100))))
            send_cmd_val(g.tty_fd, "fan2_val", to_string(c_int(f32(g.klippy.out_pin_fan2_value * 100))))
            send_cmd_val(g.tty_fd, "fan3_val", to_string(c_int(f32(g.klippy.out_pin_fan3_value * 100))))

            send_cmd_txt(g.tty_fd, "nozzle_temp", to_string(g.klippy.extruder_temperature))
            send_cmd_val(g.tty_fd, "nozzle_set", to_string(g.klippy.extruder_target))
            if g.klippy.extruder_target == 0:  # CLL button and number colour depend on the nozzle heating
                send_cmd_pco(g.tty_fd, "nozzle_temp", "65535")
                send_cmd_picc(g.tty_fd, "nozzle_btn", pics.printing_row_off)
                send_cmd_picc2(g.tty_fd, "nozzle_btn", pics.printing_press_off)
            else:
                send_cmd_pco(g.tty_fd, "nozzle_temp", "63488")
                send_cmd_picc(g.tty_fd, "nozzle_btn", pics.printing_row_on)
                send_cmd_picc2(g.tty_fd, "nozzle_btn", pics.printing_press_on)

            send_cmd_txt(g.tty_fd, "bed_temp", to_string(g.klippy.heater_bed_temperature))
            send_cmd_val(g.tty_fd, "bed_set", to_string(g.klippy.heater_bed_target))
            if g.klippy.heater_bed_target == 0:    # CLL button and number colour depend on the bed heating
                send_cmd_pco(g.tty_fd, "bed_temp", "65535")
                send_cmd_picc(g.tty_fd, "bed_btn", pics.printing_row_off)
                send_cmd_picc2(g.tty_fd, "bed_btn", pics.printing_press_off)
            else:
                send_cmd_pco(g.tty_fd, "bed_temp", "63488")
                send_cmd_picc(g.tty_fd, "bed_btn", pics.printing_row_on)
                send_cmd_picc2(g.tty_fd, "bed_btn", pics.printing_press_on)

            # 4.4.22: the LED button moved to the second printing page

            send_cmd_val(g.tty_fd, "chamber_set", to_string(g.klippy.hot_target))      # CLL chamber temperature
            send_cmd_txt(g.tty_fd, "chamber_temp", to_string(g.klippy.hot_temperature))
            if g.klippy.hot_target == 0:
                send_cmd_pco(g.tty_fd, "chamber_temp", "65535")
                send_cmd_picc(g.tty_fd, "chamber_btn", pics.printing_row_off)
                send_cmd_picc2(g.tty_fd, "chamber_btn", pics.printing_press_off)
            else:
                send_cmd_pco(g.tty_fd, "chamber_temp", "63488")
                send_cmd_picc(g.tty_fd, "chamber_btn", pics.printing_row_on)
                send_cmd_picc2(g.tty_fd, "chamber_btn", pics.printing_press_on)

            if g.screen.show_preview_gimage_completed == True:
                send_cmd_vis(g.tty_fd, "thumb", "1")
                send_cmd_val(g.tty_fd, "thumb_flag", "1")
            else:
                send_cmd_vis(g.tty_fd, "thumb", "0")
                send_cmd_val(g.tty_fd, "thumb_flag", "0")
        elif g.screen.page == ids.PRINTING_2:
            if g.shown.speed_factor != g.klippy.gcode_move_speed_factor:     # CLL speed factor
                g.shown.speed_factor = g.klippy.gcode_move_speed_factor
                send_cmd_val(g.tty_fd, "speed_val", to_string(c_int(c_round(f32(g.klippy.gcode_move_speed_factor * 100)))))

            if g.shown.extruder_factor != g.klippy.gcode_move_extrude_factor:    # CLL extrusion factor
                g.shown.extruder_factor = g.klippy.gcode_move_extrude_factor
                send_cmd_val(g.tty_fd, "flow_val", to_string(c_int(c_round(f32(g.klippy.gcode_move_extrude_factor * 100)))))

            if g.klippy.caselight_value == 0:      # 4.4.22 LED state
                send_cmd_picc(g.tty_fd, "light_btn", pics.light_off)
                send_cmd_picc2(g.tty_fd, "light_btn", pics.printing2_press_off)
            else:
                send_cmd_picc(g.tty_fd, "light_btn", pics.light_on)
                send_cmd_picc2(g.tty_fd, "light_btn", pics.printing2_press_on)

    if g.klippy.print_stats_state == "printing":
        g.klippy.ready = True

    if g.klippy.fila_sensor_enabled == True:
        if g.klippy.fila_sensor_detected == False:
            g.klippy.ready = False
            actions.set_print_pause()
            page_to(ids.PRINT_NO_FILAMENT_2)

    if g.klippy.filament_detected == False:
        sleep(1)
        g.klippy.ready = False
        actions.set_print_pause()
        page_to(ids.PRINT_NO_FILAMENT)

    if g.klippy.print_stats_state == "complete":
        time_duration = actions.show_time(c_int(g.klippy.print_stats_print_duration))
        actions.complete_print()
        actions.clear_previous_data()
        sleep(5)
        actions.save_current_zoffset()
        page_to(ids.PRINT_FINISH)
        send_cmd_txt(g.tty_fd, "time_txt", time_duration)

    if g.klippy.print_stats_state == "paused":
        if g.klippy.ready == True:
            g.klippy.ready = False
            page_to(ids.PRINT_FILAMENT)

    if g.klippy.print_stats_state == "standby":
        page_to(ids.PRINT_STOPPING)

    if g.klippy.print_stats_state == "error":
        page_to(ids.GCODE_ERROR)
        actions.cancel_print()
        actions.clear_previous_data()
        send_cmd_txt(g.tty_fd, "msg", "G-code error: " + g.screen.error_message)


def clear_printing_arg():
    g.shown.extruder_temperature = 0
    g.shown.extruder_target = 0
    g.shown.heater_bed_target = 0
    g.shown.heater_bed_temperature = 0
    g.shown.hot_target = 0
    g.shown.hot_temperature = 0
    g.shown.out_pin_fan0_value = 0.0
    g.shown.out_pin_fan2_value = 0.0
    g.shown.out_pin_fan3_value = 0.0

    g.shown.speed_factor = 0.0
    g.shown.extruder_factor = 0.0


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


def preview():
    # 4.4.22: pictures of the 4.4.24 screen, timelapse switch b3
    if g.screen.bed_leveling == False:
        send_cmd_picc(g.tty_fd, "level_btn", pics.preview_chk_off)
        send_cmd_picc2(g.tty_fd, "level_btn", pics.preview_press_off)
    else:
        send_cmd_picc(g.tty_fd, "level_btn", pics.preview_chk_on)
        send_cmd_picc2(g.tty_fd, "level_btn", pics.preview_press_on)
    if g.screen.timelapse_enabled == False:
        send_cmd_picc(g.tty_fd, "timelapse_btn", pics.preview_chk_off)
        send_cmd_picc2(g.tty_fd, "timelapse_btn", pics.preview_press_off)
    else:
        send_cmd_picc(g.tty_fd, "timelapse_btn", pics.preview_chk_on)
        send_cmd_picc2(g.tty_fd, "timelapse_btn", pics.preview_press_on)
    if g.files.meta_parse_finished == True:
        if g.screen.show_preview_complete == False:
            # 4.4.2 CLL only the file name is shown on the preview page
            send_cmd_txt(g.tty_fd, "err_msg", filelist._file_name_only(g.files.meta_filename))
            if g.files.meta_estimated_time:
                send_cmd_txt(g.tty_fd, "est_time", actions.show_time(g.files.meta_estimated_time))
            else:
                send_cmd_txt(g.tty_fd, "est_time", "-")

            if g.files.meta_filament_weight_total:
                temp = to_string(g.files.meta_filament_weight_total)
                send_cmd_txt(g.tty_fd, "fil_weight", _cut_after_point(temp, 2) + "g")
            else:
                send_cmd_txt(g.tty_fd, "fil_weight", "-")

            if g.files.meta_filament_total:
                temp = to_string(f32(g.files.meta_filament_total / 1000))
                send_cmd_txt(g.tty_fd, "fil_length", _cut_after_point(temp, 2) + "m")
            else:
                send_cmd_txt(g.tty_fd, "fil_length", "-")

            if g.files.meta_filament_type != "":
                send_cmd_txt(g.tty_fd, "fil_type", g.files.meta_filament_type)
            elif g.files.meta_filament_name != "":
                send_cmd_txt(g.tty_fd, "fil_type", g.files.meta_filament_name)
            else:
                send_cmd_txt(g.tty_fd, "fil_type", "-")

            path_found = False
            # NOTE: the original looks for <dir>/.thumbs/<name>-160x160.png, then
            # .jpg, made by QIDI's Moonraker; the port reads the thumbnail from the
            # gcode file itself (see thumbnail.py).  For a print that was just
            # started the original only looks at the .cache copy of the file.
            if g.screen.jump_print == True:
                candidates = ["/.cache/" + filelist._name_of(g.klippy.print_stats_filename),
                              "/" + g.klippy.print_stats_filename]
            elif g.screen.cache_clicked == True:
                candidates = [actions._top(g.files.list_path_stack) + "/.cache/" + filelist._name_of(g.files.meta_filename)]
                g.screen.cache_clicked = False
            else:
                candidates = [actions._top(g.files.list_path_stack) + "/" + filelist._name_of(g.files.meta_filename)]
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
                if g.screen.show_preview_gimage_completed == False:
                    output_imgdata(picture_path, 160)
                    data = g.pictures.tjc_data
                    if data is None:
                        cerr("No converted picture (/home/mks/tjc)", "\n")
                        g.screen.show_preview_complete = True
                        return
                    g.files.meta_simage = data
                    send_cmd_txt(g.tty_fd, "preview.cp_data", "")
                    send_cmd_txt(g.tty_fd, "preview.cp_pad", "")
                    if g.files.meta_simage != "":
                        send_cmd_baud(g.tty_fd, 921600)
                        usleep(50000)
                        set_option(g.tty_fd, 921600, 8, 'N', 1)
                        cout("Sending the small picture")
                        _send_chunks_txt(g.files.meta_simage)
                        send_cmd_baud(g.tty_fd, 115200)
                        usleep(50000)
                        set_option(g.tty_fd, 115200, 8, 'N', 1)

                    # big picture
                    if g.screen.jump_print == False:
                        data = g.pictures.tjc_data
                        if data is None:
                            cerr("No converted picture (/home/mks/tjc)", "\n")
                            g.screen.show_preview_complete = True
                            return
                        g.files.meta_gimage = data
                        send_cmd_baud(g.tty_fd, 921600)
                        usleep(50000)
                        set_option(g.tty_fd, 921600, 8, 'N', 1)
                        send_cmd_cp_close(g.tty_fd, "preview.preview_pic")
                        if g.files.meta_gimage != "":
                            cout("Sending the big picture")
                            _send_chunks_cp("preview_pic", g.files.meta_gimage)
                        send_cmd_baud(g.tty_fd, 115200)
                        usleep(50000)
                        set_option(g.tty_fd, 115200, 8, 'N', 1)
                        actions.bed_leveling_switch(True)
                    g.screen.show_preview_gimage_completed = True

            if g.screen.show_preview_gimage_completed == True:
                send_cmd_vis(g.tty_fd, "preview_pic", "1")
            else:
                send_cmd_vis(g.tty_fd, "preview_pic", "0")

            g.screen.show_preview_complete = True
            if g.screen.jump_print == True:
                actions.check_filament_type()
                g.screen.jump_print = False


def main():
    send_cmd_val(g.tty_fd, "nozzle_temp", to_string(g.klippy.extruder_temperature))
    send_cmd_val(g.tty_fd, "bed_temp", to_string(g.klippy.heater_bed_temperature))
    send_cmd_val(g.tty_fd, "chamber_temp", to_string(g.klippy.hot_temperature))

    if filelist.detect_disk() == 0:      # CLL USB drive inserted?
        send_cmd_picc(g.tty_fd, "usb_icon", pics.main_off)
    else:
        send_cmd_picc(g.tty_fd, "usb_icon", pics.main_on)

    if g.net.status_result.wpa_state == "COMPLETED":    # CLL wifi connected?
        send_cmd_picc(g.tty_fd, "wifi_icon", pics.main_off)
    else:
        send_cmd_picc(g.tty_fd, "wifi_icon", pics.main_on)

    if g.klippy.caselight_value == 0:      # LED logo
        send_cmd_picc(g.tty_fd, "light_btn", pics.main_off)
        send_cmd_picc2(g.tty_fd, "light_btn", pics.nav_btn_press)
    else:
        send_cmd_picc(g.tty_fd, "light_btn", pics.main_on)
        send_cmd_picc2(g.tty_fd, "light_btn", pics.main_on_press)

    if g.klippy.out_pin_beep_value == 0:
        send_cmd_picc(g.tty_fd, "beep_btn", pics.main_off)
        send_cmd_picc2(g.tty_fd, "beep_btn", pics.nav_btn_press)
    else:
        send_cmd_picc(g.tty_fd, "beep_btn", pics.main_on)
        send_cmd_picc2(g.tty_fd, "beep_btn", pics.main_on_press)

    if g.klippy.extruder_target == 0:      # CLL nozzle heating state on the main page
        send_cmd_pco(g.tty_fd, "nozzle_temp", "65535")
        send_cmd_picc(g.tty_fd, "nozzle_btn", pics.main_off)
        send_cmd_picc2(g.tty_fd, "nozzle_btn", pics.nav_btn_press)
    else:
        send_cmd_pco(g.tty_fd, "nozzle_temp", "63488")
        send_cmd_picc(g.tty_fd, "nozzle_btn", pics.main_on)
        send_cmd_picc2(g.tty_fd, "nozzle_btn", pics.main_on_press)

    if g.klippy.heater_bed_target == 0:    # CLL bed heating state on the main page
        send_cmd_pco(g.tty_fd, "bed_temp", "65535")
        send_cmd_picc(g.tty_fd, "bed_btn", pics.main_off)
        send_cmd_picc2(g.tty_fd, "bed_btn", pics.nav_btn_press)
    else:
        send_cmd_pco(g.tty_fd, "bed_temp", "63488")
        send_cmd_picc(g.tty_fd, "bed_btn", pics.main_on)
        send_cmd_picc2(g.tty_fd, "bed_btn", pics.main_on_press)

    if g.klippy.hot_target == 0:           # CLL chamber heating state on the main page
        send_cmd_pco(g.tty_fd, "chamber_temp", "65535")
        send_cmd_picc(g.tty_fd, "chamber_btn", pics.main_off)
        send_cmd_picc2(g.tty_fd, "chamber_btn", pics.nav_btn_press)
    else:
        send_cmd_pco(g.tty_fd, "chamber_temp", "63488")
        send_cmd_picc(g.tty_fd, "chamber_btn", pics.main_on)
        send_cmd_picc2(g.tty_fd, "chamber_btn", pics.main_on_press)

    # CLL refresh the picture after every boot or print
    if g.screen.main_picture_refreshed == False:
        # CLL get the file information
        g.files.list_pages = 0
        g.files.list_current_pages = 0
        g.files.list_folder_layers = 0
        g.files.list_previous_path = ""
        g.files.list_root_path = filelist.DEFAULT_DIR
        g.files.list_path = ""
        filelist.refresh_page_files(g.files.list_current_pages)
        if g.files.list_list_show_type[0] == "[c]":
            send_cmd_txt(g.tty_fd, "last_file_name", g.files.list_list_show_name[0])
            name0 = g.files.list_list_show_name[0]
            # NOTE: thumbnail from the gcode file instead of .cache/.thumbs/<name>-160x160.png / .jpg
            picture_path = thumbnail.GcodeRef(substr(g.files.list_path + "/.cache/" + name0, 1))
            MKSLOG_RED("Picture path:%s", picture_path)
            thumb = thumbnail.find(picture_path, 160, "PNG")
            if thumb is not None and thumb.fmt == "PNG":
                MKSLOG_RED("Found png picture")
                send_cmd_pic(g.tty_fd, "b[0]", pics.main_bg_photo)
                send_cmd_picc(g.tty_fd, "last_file_btn", pics.main_bg_photo)
                send_cmd_picc2(g.tty_fd, "last_file_btn", pics.nav_btn_press)
                send_cmd_vis(g.tty_fd, "last_file_pic", "1")
                filelist.send_file_picture(picture_path, 160, "last_file_pic")
                g.screen.main_picture_detected = True
            else:
                if thumb is not None:
                    MKSLOG_RED("Found jpg picture")
                    send_cmd_pic(g.tty_fd, "b[0]", pics.main_bg_photo)
                    send_cmd_picc(g.tty_fd, "last_file_btn", pics.main_bg_photo)
                    send_cmd_picc2(g.tty_fd, "last_file_btn", pics.nav_btn_press)
                    filelist.send_file_picture(picture_path, 160, "last_file_pic")
                    g.screen.main_picture_detected = True
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
        g.screen.main_picture_refreshed = True

    # CLL ask for the power loss recovery once after boot
    if g.screen.open_reprint_asked == False:
        actions.check_print_interrupted()
        g.screen.open_reprint_asked = True


def move_home_tips():
    g.screen.jump_move_pop_2 = True


def filament_tips():
    if g.screen.page == ids.OPEN_FILAMENTVIDEO_3:
        pass
    elif g.screen.page == ids.PRINT_FILAMENT:
        g.screen.jump_print_low_temp = True
    else:
        g.screen.jump_filament_pop_1 = True


def move_tips():
    g.screen.jump_move_pop_1 = True
    if g.screen.page in (ids.PRINTING, ids.PRINT_ZOFFSET, ids.PRINT_FILAMENT,
                             ids.PRINTING_2):
        actions.cancel_print()


def clear_preview():
    g.files.meta_filename = ""
    g.files.meta_estimated_time = 0
    g.files.meta_filament_weight_total = 0.0
    g.files.meta_filament_name = ""
    g.files.meta_filament_type = ""
    g.files.meta_simage = ""
    g.files.meta_gimage = ""


def open_move_tip():
    g.ep.Send(json_run_a_gcode("G91\nG1 Z-100 F600\nG1 X-100 Y-100 F1200\nG90"))


def zoffset():
    i = 0
    while i < g.levelling.mesh_y_count:
        if i == 5:
            break
        j = 0
        while j < g.levelling.mesh_x_count:
            if j == 5:
                break
            temp = to_string(g.levelling.mesh_points[i][j])
            temp = _cut_after_point(temp, 3)
            send_cmd_txt(g.tty_fd, "cell_" + to_string(5 * i + j), temp)
            j += 1
        i += 1


def auto_heaterbed():
    send_cmd_txt(g.tty_fd, "temp_now", to_string(g.klippy.heater_bed_temperature) + "/")
    send_cmd_val(g.tty_fd, "temp_target", to_string(g.klippy.heater_bed_target))
    if g.klippy.heater_bed_target > 0:
        send_cmd_picc(g.tty_fd, "heat_toggle", pics.autobed_on)
        send_cmd_picc2(g.tty_fd, "heat_toggle", pics.autobed_press_on)
        send_cmd_pco(g.tty_fd, "temp_now", "63488")
        send_cmd_pco(g.tty_fd, "temp_target", "63488")
    else:
        send_cmd_picc(g.tty_fd, "heat_toggle", pics.autobed_off)
        send_cmd_picc2(g.tty_fd, "heat_toggle", pics.autobed_press_off)
        send_cmd_pco(g.tty_fd, "temp_now", "65535")
        send_cmd_pco(g.tty_fd, "temp_target", "65535")


def open_moving():
    """4.4.22: leave the "moving" page of the guide once Klipper is idle again."""
    if g.klippy.idle_timeout_state != "Printing":
        page_to(ids.OPEN_FILAMENTVIDEO_0)


def open_heaterbed():
    send_cmd_txt(g.tty_fd, "t0", to_string(g.klippy.heater_bed_temperature) + "/")
    send_cmd_val(g.tty_fd, "n0", to_string(g.klippy.heater_bed_target))
    if g.klippy.heater_bed_target > 0:
        send_cmd_picc(g.tty_fd, "b0", pics.bedtemp_on)
        send_cmd_picc2(g.tty_fd, "b0", pics.bedtemp_press_on)
        send_cmd_pco(g.tty_fd, "t0", "63488")
        send_cmd_pco(g.tty_fd, "n0", "63488")
    else:
        send_cmd_picc(g.tty_fd, "b0", pics.bedtemp_off)
        send_cmd_picc2(g.tty_fd, "b0", pics.bedtemp_press_off)
        send_cmd_pco(g.tty_fd, "t0", "65535")
        send_cmd_pco(g.tty_fd, "n0", "65535")


def filament_pop():
    send_cmd_txt(g.tty_fd, "temp_txt", "(" + to_string(g.klippy.extruder_temperature) + "/" +
                 to_string(g.klippy.extruder_target) + "℃)")
    if g.levelling.step_1 == True:
        g.levelling.step_1 = False
        send_cmd_picc(g.tty_fd, "steps_bar", pics.pop_steps_2)
        send_cmd_pco(g.tty_fd, "step2_txt", "65535")
        send_cmd_pco(g.tty_fd, "step1_txt", "38066")
        send_cmd_pco(g.tty_fd, "temp_txt", "38066")
        send_cmd_vis(g.tty_fd, "spin2", "0")
        send_cmd_vis(g.tty_fd, "spin3", "1")
    if g.levelling.step_2 == True and g.klippy.idle_timeout_state == "Ready":
        g.levelling.step_2 = False
        send_cmd_picc(g.tty_fd, "steps_bar", pics.pop_steps_3)
        send_cmd_pco(g.tty_fd, "step3_txt", "65535")
        send_cmd_pco(g.tty_fd, "step2_txt", "38066")
        send_cmd_vis(g.tty_fd, "done_btn", "1")
        send_cmd_vis(g.tty_fd, "alt_btn", "1")
        send_cmd_vis(g.tty_fd, "spin3", "0")


def preview_pop():
    # 4.4.2 support mates and hall filament width sensors
    if g.klippy.filament_detected == False:
        sleep(1)
        actions.set_print_pause()
        page_to(ids.PRINT_NO_FILAMENT)
    if g.klippy.print_stats_state == "standby":
        page_to(ids.PRINT_STOPPING)
    if g.klippy.print_stats_state == "error":
        page_to(ids.GCODE_ERROR)
        actions.cancel_print()
        actions.clear_previous_data()
        send_cmd_txt(g.tty_fd, "msg", "G-code error: " + g.screen.error_message)


def replace_characters(path, searchChars, replacement):
    result = path
    for c in searchChars:
        found = result.find(c)
        while found != -1:
            result = result[:found] + replacement + result[found + 1:]
            found = result.find(c, found + len(replacement))
    return result


def bed_moving():
    if g.klippy.idle_timeout_state == "Ready":
        if g.screen.manual_count == 3:
            page_to(ids.PRE_BED_CALIBRATION)
        elif g.screen.manual_count == -2:
            page_to(ids.BED_FINISH)
        else:
            page_to(ids.BED_CALIBRATION)


def open_calibrate():
    if g.levelling.step_3 == True:
        g.levelling.step_3 = False
        system("sync")      # CLL save the system information, then go to the filament loading page
        sleep(10)
        actions.get_object_status()
        actions.sub_object_status()
        page_to(ids.OPEN_FILAMENTVIDEO_0)
    if g.levelling.step_2 == True and g.klippy.webhooks_state == "ready":
        g.levelling.step_2 = False
        sleep(5)
        g.ep.Send(json_run_a_gcode("M901"))    # CLL input shaping after the bed levelling
    if g.levelling.step_1 == True and g.klippy.idle_timeout_state == "Ready":
        g.levelling.step_1 = False
        settings.get_heater_bed_target()
        actions.set_heater_bed_target(g.config.heater_bed_target)
        g.ep.Send(json_run_a_gcode("M190 S" + to_string(g.config.heater_bed_target) + "\n"))
        sleep(5)
        g.ep.Send(json_run_a_gcode("M4027"))   # CLL levelling after the platform / nozzle initialisation


def filament_set_fan():
    if g.screen.move_fan_setting == False:     # CLL refresh only while the slider is not being dragged
        fan0 = to_string(c_int(f32(g.klippy.out_pin_fan0_value * 100)))
        fan2 = to_string(c_int(f32(g.klippy.out_pin_fan2_value * 100)))
        fan3 = to_string(c_int(f32(g.klippy.out_pin_fan3_value * 100)))
        send_cmd_val(g.tty_fd, "fan1_slider", fan0)
        send_cmd_val(g.tty_fd, "fan1_val", fan0)
        send_cmd_val(g.tty_fd, "fan2_slider", fan2)
        send_cmd_val(g.tty_fd, "fan2_val", fan2)
        send_cmd_val(g.tty_fd, "fan3_slider", fan3)
        send_cmd_val(g.tty_fd, "fan3_val", fan3)
        for name, value in (("fan1_toggle", g.klippy.out_pin_fan0_value), ("fan2_toggle", g.klippy.out_pin_fan2_value),
                            ("fan3_toggle", g.klippy.out_pin_fan3_value)):
            if value == 0:
                send_cmd_picc(g.tty_fd, name, pics.fan_row_off)
                send_cmd_picc2(g.tty_fd, name, pics.fan_press_off)
            else:
                send_cmd_picc(g.tty_fd, name, pics.fan_row_on)
                send_cmd_picc2(g.tty_fd, name, pics.fan_press_on)


def common_setting():
    g.shown.oobe_enabled = settings.get_oobe_enabled()
    send_cmd_txt(g.tty_fd, "version_txt", g.config.version_soc)
    if g.shown.oobe_enabled == False:
        send_cmd_picc(g.tty_fd, "reset_btn", pics.reset_row)
        send_cmd_picc2(g.tty_fd, "reset_btn", pics.settings_press)
    else:
        send_cmd_picc(g.tty_fd, "reset_btn", pics.reset_row_on)
        send_cmd_picc2(g.tty_fd, "reset_btn", pics.settings_press_on)


def filament():
    send_cmd_txt(g.tty_fd, "nozzle_temp", to_string(g.klippy.extruder_temperature))
    send_cmd_val(g.tty_fd, "nozzle_set", to_string(g.klippy.extruder_target))
    send_cmd_txt(g.tty_fd, "bed_temp", to_string(g.klippy.heater_bed_temperature))
    send_cmd_val(g.tty_fd, "bed_set", to_string(g.klippy.heater_bed_target))
    send_cmd_txt(g.tty_fd, "chamber_temp", to_string(g.klippy.hot_temperature))
    send_cmd_val(g.tty_fd, "chamber_set", to_string(g.klippy.hot_target))
    if g.klippy.extruder_target > 0:   # CLL button state depends on the nozzle heating
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

    if g.klippy.heater_bed_target > 0:     # CLL button state depends on the bed heating
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

    if g.klippy.hot_target > 0:
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

    sel = {10: 0, 50: 1, 100: 2}.get(g.klippy.filament_extruder_dist)
    if sel is not None:
        for k, name in enumerate(("step_10", "step_50", "step_100")):
            if k == sel:
                send_cmd_picc(g.tty_fd, name, pics.filament_row_on)
                send_cmd_picc2(g.tty_fd, name, pics.filament_press_on)
            else:
                send_cmd_picc(g.tty_fd, name, pics.filament_row_off)
                send_cmd_picc2(g.tty_fd, name, pics.filament_press_off)


def auto_unload():
    send_cmd_txt(g.tty_fd, "temp_txt", "(" + to_string(g.klippy.extruder_temperature) + "/" +
                 to_string(g.klippy.extruder_target) + "℃)")
    if g.levelling.step_1 == True:
        g.levelling.step_1 = False
        send_cmd_vis(g.tty_fd, "spin1", "0")
        send_cmd_vis(g.tty_fd, "spin2", "1")
        send_cmd_picc(g.tty_fd, "steps_bar", pics.unload_steps_1)
        send_cmd_pco(g.tty_fd, "step2_txt", "65535")
        send_cmd_pco(g.tty_fd, "step1_txt", "38066")
    if g.levelling.step_2 == True:
        g.levelling.step_2 = False
        send_cmd_vis(g.tty_fd, "spin2", "0")
        send_cmd_picc(g.tty_fd, "steps_bar", pics.unload_steps_2)
        send_cmd_pco(g.tty_fd, "step3_txt", "65535")
        send_cmd_pco(g.tty_fd, "step2_txt", "38066")
        send_cmd_vis(g.tty_fd, "load_btn", "1")
        send_cmd_vis(g.tty_fd, "ok", "1")
