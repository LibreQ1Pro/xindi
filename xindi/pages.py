"""What every screen page shows: the refresh functions are called with the page that is open."""

import time
import logging

from . import state as g
from . import pageids as ids
from . import pics
from . import thumbnail
from .ui import page_to
from .cpp import to_string, substr, f32, c_int, c_round, system
from .moonraker_api import json_run_a_gcode
from .printer_status import get_cal_printing_time
from .file_browser import output_imgdata
from . import actions, filelist, settings, wifi_ui

log = logging.getLogger(__name__)


def _replace_for_screen(text):
    text = text.replace("\n", ".")
    text = text.replace("'", " ")
    text = text.replace("\"", " ")
    return text


# pages that stay where they are when a print starts
NO_PRINT_JUMP_PAGES = frozenset((
    ids.PRINTING, ids.PRINT_ZOFFSET, ids.PRINT_FILAMENT,
    ids.PRINT_STOP, ids.PRINT_NO_FILAMENT, ids.PRINT_NO_FILAMENT_2, ids.SHUTDOWN, ids.PRINT_STOPPING, ids.MOVE_POP_1,
    ids.GCODE_ERROR, ids.DETECT_ERROR, ids.RESET, ids.PREVIEW, ids.PREVIEW_POP_1, ids.PREVIEW_POP_2,
    ids.PRINTING_2, ids.FILAMENT_POP_2, ids.FILAMENT_POP_3, ids.STOP_CONFIRM))

# pages that stay where they are when Klipper fails
NO_RESET_JUMP_PAGES = frozenset((
    ids.GCODE_ERROR, ids.DETECT_ERROR, ids.LEVEL_ERROR, ids.SHUTDOWN, ids.SERVICE, ids.LANGUAGE,
    ids.COMMON_SETTING, ids.SLEEP_MODE, ids.INTERNET, ids.WIFI_LIST, ids.WIFI_KB, ids.WIFI_CONNECT,
    ids.WIFI_FAILED, ids.WIFI_SUCCESS, ids.WIFI_SAVING, ids.NET_SAVED, ids.NET_DETAIL, ids.NET_CONFIRM,
    ids.NET_INFO, ids.RESTORE_CONFIG, ids.INTERNET_PAGE))

# moves of the "move without homing" pop-up, by the button that started it
UNHOMED_HOMING = "SET_KINEMATIC_POSITION Z=150\nSET_KINEMATIC_POSITION X=150\nSET_KINEMATIC_POSITION Y=150\n"
UNHOMED_MOVES = {
    1: "G91\nG1 X10 F3000\nG90\nM84\n",       # X_UP
    2: "G91\nG1 X-10 F3000\nG90\nM84\n",      # X_DOWN
    3: "G91\nG1 Y10 F3000\nG90\nM84\n",       # Y_UP
    4: "G91\nG1 Y-10 F3000\nG90\nM84\n",      # Y_DOWN
    5: "G91\nG1 Z-10 F600\nG90\nM84\n",       # Z_UP
    6: "G91\nG1 Z10 F600\nG90\nM84\n",        # Z_DOWN
}


def _jump_to(flag, page):
    """Reset the flag, then switch the page (the flag has to be reset first, otherwise this would loop forever)."""
    setattr(g.screen, flag, False)
    page_to(page)


def _unhomed_move_pop():
    if g.screen.unhomed_move_mode in UNHOMED_MOVES:
        g.ep.send(json_run_a_gcode(UNHOMED_HOMING))
        g.ep.send(json_run_a_gcode(UNHOMED_MOVES[g.screen.unhomed_move_mode]))
    g.screen.unhomed_move_mode = 0
    _jump_to("jump_move_pop_2", ids.MOVE_POP_2)


def _detect_error_pop():
    _jump_to("jump_detect_error", ids.DETECT_ERROR)
    g.port.txt("msg", g.screen.error_message)


def _requested_jumps():
    """The other threads ask for a page by setting a flag; the page is switched here, in the main thread.

    CLL the jumps are unconditional, the flags were set after the checks were done.
    """
    if g.screen.jump_move_pop_1:
        _jump_to("jump_move_pop_1", ids.MOVE_POP_1)
    if g.screen.jump_move_pop_2:
        _unhomed_move_pop()
    if g.screen.jump_detect_error:
        _detect_error_pop()
    if g.screen.jump_level_error:
        _jump_to("jump_level_error", ids.LEVEL_ERROR)
    if g.screen.jump_filament_pop_1:
        _jump_to("jump_filament_pop_1", ids.FILAMENT_POP_1)
    if g.screen.jump_print_low_temp:
        _jump_to("jump_print_low_temp", ids.PRINT_LOW_TEMP)
    if g.screen.jump_resume_print:
        # 4.4.24: the flag is reset when the page reports that it is shown
        page_to(ids.RESUME_PRINT)
    if g.screen.jump_memory_warning:
        _jump_to("jump_memory_warning", ids.MEMORY_WARNING)


def _open_print_page_when_printing():
    """A print was started from elsewhere (the web UI): show it."""
    if g.screen.page in NO_PRINT_JUMP_PAGES:
        return
    if g.klippy.print_stats_state == "printing" and g.klippy.print_stats_filename != "":
        g.screen.main_picture_detected = False
        g.screen.main_picture_refreshed = False
        g.screen.muted = False         # 4.4.22 silent mode is per print
        log.debug("Jumping to the print page\n")
        time.sleep(1)
        filelist.get_file_estimated_time(g.klippy.print_stats_filename)
        time.sleep(1)
        g.screen.jump_print = True
        g.klippy.ready = False
        page_to(ids.PREVIEW)


def _show_failure_message():
    if g.shown.webhooks_state_message != g.klippy.webhooks_state_message:
        g.shown.webhooks_state_message = g.klippy.webhooks_state_message
        g.port.txt("err_msg", _replace_for_screen(g.klippy.webhooks_state_message))


def _open_reset_page_on_failure():
    """Jump to the restart page when the toolhead board is disconnected (Klipper shut down)."""
    state = g.klippy.webhooks_state
    if g.screen.page == ids.RESET:
        if state in ("shutdown", "error"):
            _show_failure_message()
        if state == "ready":
            page_to(ids.SYS_OK)
    elif g.screen.page not in NO_RESET_JUMP_PAGES and state in ("shutdown", "error"):
        if state == "shutdown" and g.screen.page in (ids.AUTO_MOVING, ids.OPEN_CALIBRATE):
            return
        page_to(ids.RESET)
        log.debug("Restart page")
        _show_failure_message()


def show():
    """Refresh the page that is open (called about every 50 ms)."""
    # 4.4.22: nothing is sent to the screen while the list pictures are transferred
    if g.pictures.send_jpg_status:
        return
    _requested_jumps()
    _open_print_page_when_printing()
    _open_reset_page_on_failure()

    refresh = REFRESH.get(g.screen.page)
    if refresh:
        refresh()


def open_filament_video_2():
    if g.klippy.extruder_target == 0:
        g.port.pco("temp_now", "65535")
        g.port.pco("temp_target", "65535")
        g.port.picc("heat_toggle", pics.open_heat_off)
        g.port.picc2("heat_toggle", pics.open_heat_off_press)
    else:
        g.port.pco("temp_now", "63488")
        g.port.pco("temp_target", "63488")
        g.port.picc("heat_toggle", pics.open_heat_on)
        g.port.picc2("heat_toggle", pics.open_heat_on_press)

    g.port.txt("temp_now", to_string(g.klippy.extruder_temperature) + "/")
    g.port.val("temp_target", to_string(g.klippy.extruder_target))


def syntony_finish():
    log.debug("Printer ide_timeout state: %s", g.klippy.idle_timeout_state)
    log.debug("Printer webhooks state: %s", g.klippy.webhooks_state)
    if not g.levelling.syntony_finished:
        g.levelling.syntony_finished = True
        g.levelling.all_level_saving = False

    if g.klippy.idle_timeout_state == "Ready" and g.klippy.webhooks_state == "ready":
        log.debug("Printer webhooks state: %s", g.klippy.webhooks_state)
        time.sleep(10)
        system("sync")      # make sure the config file is saved

        g.levelling.all_level_saving = False
        settings.get_babystep()  # 4.4.22 (was init_mks_status())
        actions.sub_object_status()
        actions.get_object_status()
        time.sleep(10)
        page_to(ids.LEVEL_MODE)
        log.info("Left from line 739")


def _picc_group(names, selected, on_picc, off_picc, on_picc2, off_picc2):
    for i, name in enumerate(names):
        g.port.picc(name, on_picc if i == selected else off_picc)
    for i, name in enumerate(names):
        g.port.picc2(name, on_picc2 if i == selected else off_picc2)


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
    log.debug("Printer ide_timeout state: %s", g.klippy.idle_timeout_state)
    log.debug("Printer webhooks state: %s", g.klippy.webhooks_state)
    if g.klippy.idle_timeout_state == "Ready":
        actions.clear_previous_data()
        time.sleep(5)
        actions.save_current_zoffset()
        page_to(ids.MAIN)


def syntony_move():
    if g.screen.temp_idle_state != g.klippy.idle_timeout_state:
        g.screen.temp_idle_state = g.klippy.idle_timeout_state
        log.debug("Printer ide_timeout state: %s", g.klippy.idle_timeout_state)
        log.debug("Printer webhooks state: %s", g.klippy.webhooks_state)

    if g.levelling.step_1:
        time.sleep(15)
        page_to(ids.SYNTONY_FINISH)
        g.levelling.step_1 = False


def print_filament():
    g.port.txt("file_name", filelist._file_name_only(g.klippy.print_stats_filename))

    if g.klippy.extruder_target == 0:
        g.port.pco("temp_now", "65535")
        g.port.picc("heat_btn", pics.printfil_heat_off)
        g.port.picc2("heat_btn", pics.printfil_press_off)
    else:
        g.port.pco("temp_now", "63488")
        g.port.picc("heat_btn", pics.printfil_heat_on)
        g.port.picc2("heat_btn", pics.printfil_press_on)

    g.port.val("progress", to_string(g.klippy.display_status_progress))
    g.port.val("progress_pct", to_string(g.klippy.display_status_progress))
    g.port.txt("temp_now", to_string(g.klippy.extruder_temperature))
    g.port.txt("temp_set", to_string(g.klippy.extruder_target))
    g.port.txt("time_elapsed", actions.show_time(c_int(g.klippy.print_stats_print_duration)))
    g.port.txt("time_left", actions.show_time(get_cal_printing_time(c_int(g.klippy.print_stats_print_duration),
                                                                 g.files.meta_estimated_time,
                                                                 g.klippy.display_status_progress)))

    if g.klippy.print_stats_state == "paused":
        g.klippy.ready = True

    # 4.4.2 CLL support mates and hall filament width sensors
    if not g.klippy.filament_detected:
        time.sleep(1)
        g.klippy.ready = False
        actions.set_print_pause()
        page_to(ids.PRINT_NO_FILAMENT)

    if g.klippy.print_stats_state == "printing":
        if g.klippy.ready:
            g.klippy.ready = False
            page_to(ids.PRINTING)

    if g.klippy.print_stats_state == "standby":
        page_to(ids.PRINT_STOPPING)

    if g.klippy.print_stats_state == "error":
        page_to(ids.GCODE_ERROR)
        actions.cancel_print()
        actions.clear_previous_data()
        g.port.txt("msg", "G-code error: " + g.screen.error_message)

    # 4.4.2 CLL a long pause that stops the print switches the page
    if g.klippy.idle_timeout_state == "Idle":
        g.ep.send(json_run_a_gcode("G28\n"))
        actions.cancel_print()


def auto_finish():
    if g.klippy.idle_timeout_state == "Idle" and g.klippy.webhooks_state == "ready":
        g.levelling.auto_level_finished = True


def auto_moving():
    g.port.txt("bed_temp", "(" + to_string(g.klippy.heater_bed_temperature) + "/" +
                 to_string(g.klippy.heater_bed_target) + ")")
    if g.levelling.step_1:
        g.port.picc("steps_bar", pics.auto_steps_1)
        g.port.pco("step2_txt", "65535")
        g.port.pco("step1_txt", "38066")
        g.port.vis("spin1", "0")
        g.port.vis("spin2", "1")
        g.levelling.step_1 = False
    if g.levelling.step_2:
        g.port.picc("steps_bar", pics.auto_steps_2)
        g.port.pco("step3_txt", "65535")
        g.port.pco("step2_txt", "38066")
        g.port.vis("spin2", "0")
        g.port.vis("spin3", "1")
        g.levelling.step_2 = False
    if g.levelling.step_3:
        g.port.picc("steps_bar", pics.auto_steps_3)
        g.port.pco("step4_txt", "65535")
        g.port.pco("step3_txt", "38066")
        g.port.vis("spin3", "0")
        g.port.vis("spin4", "1")
        g.levelling.step_3 = False
        g.klippy.idle_timeout_state = "Printing"
        settings.get_heater_bed_target()
        actions.set_heater_bed_target(g.config.heater_bed_target)
        g.ep.send(json_run_a_gcode("M190 S" + to_string(g.config.heater_bed_target) + "\n"))
        time.sleep(1)
        g.ep.send(json_run_a_gcode("M4027\n"))
    if g.levelling.step_4:
        time.sleep(15)
        page_to(ids.AUTO_FINISH)
        g.levelling.step_4 = False


def _cut_after_point(text, n):
    """``s.substr(0, s.find(".") + n)``"""
    return substr(text, 0, text.find(".") + n)


def move_page():
    x_pos = _cut_after_point(to_string(g.klippy.x_position), 2)
    y_pos = _cut_after_point(to_string(g.klippy.y_position), 2)
    z_pos = _cut_after_point(to_string(g.klippy.z_position), 2)

    g.port.txt("x_pos", x_pos)
    g.port.txt("y_pos", y_pos)
    g.port.txt("z_pos", z_pos)

    # CLL highlight the selected distance
    if g.klippy.move_dist == f32(0.1):
        g.port.picc("dist_01", pics.move_dist_on)
        g.port.picc2("dist_01", pics.move_dist_on_press)
        g.port.picc("dist_1", pics.move_dist_off)
        g.port.picc2("dist_1", pics.move_dist_off_press)
        g.port.picc("dist_10", pics.move_dist_off)
        g.port.picc2("dist_10", pics.move_dist_off_press)
    elif g.klippy.move_dist == f32(1.0):
        g.port.picc("dist_01", pics.move_dist_off)
        g.port.picc2("dist_01", pics.move_dist_off_press)
        g.port.picc("dist_1", pics.move_dist_on)
        g.port.picc2("dist_1", pics.move_dist_on_press)
        g.port.picc("dist_10", pics.move_dist_off)
        g.port.picc2("dist_10", pics.move_dist_off_press)
    elif g.klippy.move_dist == f32(10):
        g.port.picc("dist_01", pics.move_dist_off)
        g.port.picc2("dist_01", pics.move_dist_off_press)
        g.port.picc("dist_1", pics.move_dist_off)
        g.port.picc2("dist_1", pics.move_dist_off_press)
        g.port.picc("dist_10", pics.move_dist_on)
        g.port.picc2("dist_10", pics.move_dist_on_press)


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
        g.port.picc(("step_001", "step_005", "step_01", "step_05")[b - 1], picc)
        g.port.picc2(("step_001", "step_005", "step_01", "step_05")[b - 1], picc2)


def printing_zoffset():
    z_offset = to_string(g.klippy.gcode_move_homing_origin[2])
    show_gcode_z = to_string(g.klippy.gcode_z_position)
    z_offset = _cut_after_point(z_offset, 4)
    show_gcode_z = _cut_after_point(show_gcode_z, 4)
    g.port.txt("file_name", filelist._file_name_only(g.klippy.print_stats_filename))
    if z_offset != g.config.babystep_value:
        g.config.babystep_value = z_offset
        settings.set_babystep(g.config.babystep_value)
    g.port.txt("gcode_z", show_gcode_z)
    g.port.txt("z_offset", z_offset)
    g.port.txt("time_elapsed", actions.show_time(c_int(g.klippy.print_stats_print_duration)))
    g.port.val("progress_pct", to_string(g.klippy.display_status_progress))
    g.port.txt("time_left", actions.show_time(get_cal_printing_time(c_int(g.klippy.print_stats_print_duration),
                                                                 g.files.meta_estimated_time,
                                                                 g.klippy.display_status_progress)))
    g.port.val("progress", to_string(g.klippy.display_status_progress))

    _zoffset_buttons()

    if g.klippy.print_stats_state == "printing":
        g.klippy.ready = True

    if g.klippy.fila_sensor_enabled:
        if not g.klippy.fila_sensor_detected:
            g.klippy.ready = False
            actions.set_print_pause()
            page_to(ids.PRINT_NO_FILAMENT_2)

    # 4.4.2 CLL support mates and hall filament width sensors
    if not g.klippy.filament_detected:
        time.sleep(1)
        g.klippy.ready = False
        actions.set_print_pause()
        page_to(ids.PRINT_NO_FILAMENT)

    if g.klippy.print_stats_state == "standby":
        page_to(ids.PRINT_STOPPING)

    if g.klippy.print_stats_state == "paused":
        if g.klippy.ready:
            g.klippy.ready = False
            page_to(ids.PRINT_FILAMENT)

    if g.klippy.print_stats_state == "complete":
        time_duration = actions.show_time(c_int(g.klippy.print_stats_print_duration))
        actions.complete_print()
        actions.clear_previous_data()
        time.sleep(5)
        actions.save_current_zoffset()
        page_to(ids.PRINT_FINISH)
        g.port.txt("time_txt", time_duration)

    if g.klippy.print_stats_state == "error":
        page_to(ids.GCODE_ERROR)
        actions.cancel_print()
        actions.clear_previous_data()
        g.port.txt("msg", "G-code error: " + g.screen.error_message)


def printing():
    z_offset = to_string(g.klippy.gcode_move_homing_origin[2])
    z_offset = _cut_after_point(z_offset, 4)

    g.port.val("progress", to_string(g.klippy.display_status_progress))
    g.port.val("progress_pct", to_string(g.klippy.display_status_progress))
    g.port.txt("time_elapsed", actions.show_time(c_int(g.klippy.print_stats_print_duration)))
    g.port.txt("time_left", actions.show_time(get_cal_printing_time(c_int(g.klippy.print_stats_print_duration),
                                                                 g.files.meta_estimated_time,
                                                                 g.klippy.display_status_progress)))
    g.port.txt("file_name", filelist._file_name_only(g.klippy.print_stats_filename))

    # the z offset of the second page is always refreshed: the page starts with
    # the designer's "-1.000", it must not stay while the keyboard flag is set
    if g.screen.page == ids.PRINTING_2:
        g.port.txt("zoffset_val", z_offset)

    if g.screen.printing_keyboard_enabled:     # 4.4.22 silent mode button of the keyboard
        if not g.screen.muted:
            g.port.picc("mute_btn", pics.kb_mute_off)
            g.port.picc2("mute_btn", pics.kb_mute_off_press)
        else:
            g.port.picc("mute_btn", pics.kb_mute_on)
            g.port.picc2("mute_btn", pics.kb_mute_on_press)
    else:                                       # CLL refresh only while the keyboard is not shown
        if g.screen.page == ids.PRINTING:
            # CLL fan speeds
            g.port.val("fan1_val", to_string(c_int(f32(g.klippy.out_pin_fan0_value * 100))))
            g.port.val("fan2_val", to_string(c_int(f32(g.klippy.out_pin_fan2_value * 100))))
            g.port.val("fan3_val", to_string(c_int(f32(g.klippy.out_pin_fan3_value * 100))))

            g.port.txt("nozzle_temp", to_string(g.klippy.extruder_temperature))
            g.port.val("nozzle_set", to_string(g.klippy.extruder_target))
            if g.klippy.extruder_target == 0:  # CLL button and number colour depend on the nozzle heating
                g.port.pco("nozzle_temp", "65535")
                g.port.picc("nozzle_btn", pics.printing_row_off)
                g.port.picc2("nozzle_btn", pics.printing_press_off)
            else:
                g.port.pco("nozzle_temp", "63488")
                g.port.picc("nozzle_btn", pics.printing_row_on)
                g.port.picc2("nozzle_btn", pics.printing_press_on)

            g.port.txt("bed_temp", to_string(g.klippy.heater_bed_temperature))
            g.port.val("bed_set", to_string(g.klippy.heater_bed_target))
            if g.klippy.heater_bed_target == 0:    # CLL button and number colour depend on the bed heating
                g.port.pco("bed_temp", "65535")
                g.port.picc("bed_btn", pics.printing_row_off)
                g.port.picc2("bed_btn", pics.printing_press_off)
            else:
                g.port.pco("bed_temp", "63488")
                g.port.picc("bed_btn", pics.printing_row_on)
                g.port.picc2("bed_btn", pics.printing_press_on)

            # 4.4.22: the LED button moved to the second printing page

            g.port.val("chamber_set", to_string(g.klippy.hot_target))      # CLL chamber temperature
            g.port.txt("chamber_temp", to_string(g.klippy.hot_temperature))
            if g.klippy.hot_target == 0:
                g.port.pco("chamber_temp", "65535")
                g.port.picc("chamber_btn", pics.printing_row_off)
                g.port.picc2("chamber_btn", pics.printing_press_off)
            else:
                g.port.pco("chamber_temp", "63488")
                g.port.picc("chamber_btn", pics.printing_row_on)
                g.port.picc2("chamber_btn", pics.printing_press_on)

            if g.screen.show_preview_gimage_completed:
                g.port.vis("thumb", "1")
                g.port.val("thumb_flag", "1")
            else:
                g.port.vis("thumb", "0")
                g.port.val("thumb_flag", "0")
        elif g.screen.page == ids.PRINTING_2:
            if g.shown.speed_factor != g.klippy.gcode_move_speed_factor:     # CLL speed factor
                g.shown.speed_factor = g.klippy.gcode_move_speed_factor
                g.port.val("speed_val", to_string(c_int(c_round(f32(g.klippy.gcode_move_speed_factor * 100)))))

            if g.shown.extruder_factor != g.klippy.gcode_move_extrude_factor:    # CLL extrusion factor
                g.shown.extruder_factor = g.klippy.gcode_move_extrude_factor
                g.port.val("flow_val", to_string(c_int(c_round(f32(g.klippy.gcode_move_extrude_factor * 100)))))

            if g.klippy.caselight_value == 0:      # 4.4.22 LED state
                g.port.picc("light_btn", pics.light_off)
                g.port.picc2("light_btn", pics.printing2_press_off)
            else:
                g.port.picc("light_btn", pics.light_on)
                g.port.picc2("light_btn", pics.printing2_press_on)

    if g.klippy.print_stats_state == "printing":
        g.klippy.ready = True

    if g.klippy.fila_sensor_enabled:
        if not g.klippy.fila_sensor_detected:
            g.klippy.ready = False
            actions.set_print_pause()
            page_to(ids.PRINT_NO_FILAMENT_2)

    if not g.klippy.filament_detected:
        time.sleep(1)
        g.klippy.ready = False
        actions.set_print_pause()
        page_to(ids.PRINT_NO_FILAMENT)

    if g.klippy.print_stats_state == "complete":
        time_duration = actions.show_time(c_int(g.klippy.print_stats_print_duration))
        actions.complete_print()
        actions.clear_previous_data()
        time.sleep(5)
        actions.save_current_zoffset()
        page_to(ids.PRINT_FINISH)
        g.port.txt("time_txt", time_duration)

    if g.klippy.print_stats_state == "paused":
        if g.klippy.ready:
            g.klippy.ready = False
            page_to(ids.PRINT_FILAMENT)

    if g.klippy.print_stats_state == "standby":
        page_to(ids.PRINT_STOPPING)

    if g.klippy.print_stats_state == "error":
        page_to(ids.GCODE_ERROR)
        actions.cancel_print()
        actions.clear_previous_data()
        g.port.txt("msg", "G-code error: " + g.screen.error_message)


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
            g.port.txt("cp_pad", s)
            g.port.drain()
            g.port.txt_plus("cp_data", "cp_data", "cp_pad")
            g.port.drain()
            break
        s = substr(data, start, num)
        start = end
        end = end + num
        g.port.txt("cp_pad", s)
        g.port.drain()
        g.port.txt_plus("cp_data", "cp_data", "cp_pad")
        g.port.drain()


def _send_chunks_cp(obj, data):
    """Writes a picture string in 2048 byte pieces into a picture widget."""
    num = 2048
    length = len(data)
    end = num
    start = 0
    while start < length:
        if end > length:
            part = substr(data, start, length - start)
            g.port.drain()
            g.port.cp_image(obj, part)
            break
        part = substr(data, start, num)
        start = end
        end = end + num
        g.port.drain()
        g.port.cp_image(obj, part)


def preview():
    # 4.4.22: pictures of the 4.4.24 screen, timelapse switch b3
    if not g.screen.bed_leveling:
        g.port.picc("level_btn", pics.preview_chk_off)
        g.port.picc2("level_btn", pics.preview_press_off)
    else:
        g.port.picc("level_btn", pics.preview_chk_on)
        g.port.picc2("level_btn", pics.preview_press_on)
    if not g.screen.timelapse_enabled:
        g.port.picc("timelapse_btn", pics.preview_chk_off)
        g.port.picc2("timelapse_btn", pics.preview_press_off)
    else:
        g.port.picc("timelapse_btn", pics.preview_chk_on)
        g.port.picc2("timelapse_btn", pics.preview_press_on)
    if g.files.meta_parse_finished:
        if not g.screen.show_preview_complete:
            # 4.4.2 CLL only the file name is shown on the preview page
            g.port.txt("err_msg", filelist._file_name_only(g.files.meta_filename))
            if g.files.meta_estimated_time:
                g.port.txt("est_time", actions.show_time(g.files.meta_estimated_time))
            else:
                g.port.txt("est_time", "-")

            if g.files.meta_filament_weight_total:
                temp = to_string(g.files.meta_filament_weight_total)
                g.port.txt("fil_weight", _cut_after_point(temp, 2) + "g")
            else:
                g.port.txt("fil_weight", "-")

            if g.files.meta_filament_total:
                temp = to_string(f32(g.files.meta_filament_total / 1000))
                g.port.txt("fil_length", _cut_after_point(temp, 2) + "m")
            else:
                g.port.txt("fil_length", "-")

            if g.files.meta_filament_type != "":
                g.port.txt("fil_type", g.files.meta_filament_type)
            elif g.files.meta_filament_name != "":
                g.port.txt("fil_type", g.files.meta_filament_name)
            else:
                g.port.txt("fil_type", "-")

            path_found = False
            # NOTE: the original looks for <dir>/.thumbs/<name>-160x160.png, then
            # .jpg, made by QIDI's Moonraker; the port reads the thumbnail from the
            # gcode file itself (see thumbnail.py).  For a print that was just
            # started the original only looks at the .cache copy of the file.
            if g.screen.jump_print:
                candidates = ["/.cache/" + filelist._name_of(g.klippy.print_stats_filename),
                              "/" + g.klippy.print_stats_filename]
            elif g.screen.cache_clicked:
                candidates = [actions._top(g.files.list_path_stack) + "/.cache/" + filelist._name_of(g.files.meta_filename)]
                g.screen.cache_clicked = False
            else:
                candidates = [actions._top(g.files.list_path_stack) + "/" + filelist._name_of(g.files.meta_filename)]
            picture_path = ""
            for candidate in candidates:
                candidate = substr(candidate, 1)
                log.info("picture_path:%s", candidate)
                if thumbnail.find(candidate, 160, "PNG") is not None:
                    path_found = True
                    picture_path = thumbnail.GcodeRef(candidate)
                    break
            log.debug("Picture path:%s", picture_path)
            if picture_path == "":
                path_found = False

            if path_found:
                # small picture
                if not g.screen.show_preview_gimage_completed:
                    output_imgdata(picture_path, 160)
                    data = g.pictures.tjc_data
                    if data is None:
                        log.error("No converted picture (/home/mks/tjc)")
                        g.screen.show_preview_complete = True
                        return
                    g.files.meta_simage = data
                    g.port.txt("preview.cp_data", "")
                    g.port.txt("preview.cp_pad", "")
                    if g.files.meta_simage != "":
                        g.port.baud(921600)
                        time.sleep(0.05)
                        g.port.set_baud(921600)
                        log.debug("Sending the small picture")
                        _send_chunks_txt(g.files.meta_simage)
                        g.port.baud(115200)
                        time.sleep(0.05)
                        g.port.set_baud(115200)

                    # big picture
                    if not g.screen.jump_print:
                        data = g.pictures.tjc_data
                        if data is None:
                            log.error("No converted picture (/home/mks/tjc)")
                            g.screen.show_preview_complete = True
                            return
                        g.files.meta_gimage = data
                        g.port.baud(921600)
                        time.sleep(0.05)
                        g.port.set_baud(921600)
                        g.port.cp_close("preview.preview_pic")
                        if g.files.meta_gimage != "":
                            log.debug("Sending the big picture")
                            _send_chunks_cp("preview_pic", g.files.meta_gimage)
                        g.port.baud(115200)
                        time.sleep(0.05)
                        g.port.set_baud(115200)
                        actions.bed_leveling_switch(True)
                    g.screen.show_preview_gimage_completed = True

            if g.screen.show_preview_gimage_completed:
                g.port.vis("preview_pic", "1")
            else:
                g.port.vis("preview_pic", "0")

            g.screen.show_preview_complete = True
            if g.screen.jump_print:
                actions.check_filament_type()
                g.screen.jump_print = False


def main():
    g.port.val("nozzle_temp", to_string(g.klippy.extruder_temperature))
    g.port.val("bed_temp", to_string(g.klippy.heater_bed_temperature))
    g.port.val("chamber_temp", to_string(g.klippy.hot_temperature))

    if filelist.detect_disk() == 0:      # CLL USB drive inserted?
        g.port.picc("usb_icon", pics.main_off)
    else:
        g.port.picc("usb_icon", pics.main_on)

    if g.net.status_result.wpa_state == "COMPLETED":    # CLL wifi connected?
        g.port.picc("wifi_icon", pics.main_off)
    else:
        g.port.picc("wifi_icon", pics.main_on)

    if g.klippy.caselight_value == 0:      # LED logo
        g.port.picc("light_btn", pics.main_off)
        g.port.picc2("light_btn", pics.nav_btn_press)
    else:
        g.port.picc("light_btn", pics.main_on)
        g.port.picc2("light_btn", pics.main_on_press)

    if g.klippy.out_pin_beep_value == 0:
        g.port.picc("beep_btn", pics.main_off)
        g.port.picc2("beep_btn", pics.nav_btn_press)
    else:
        g.port.picc("beep_btn", pics.main_on)
        g.port.picc2("beep_btn", pics.main_on_press)

    if g.klippy.extruder_target == 0:      # CLL nozzle heating state on the main page
        g.port.pco("nozzle_temp", "65535")
        g.port.picc("nozzle_btn", pics.main_off)
        g.port.picc2("nozzle_btn", pics.nav_btn_press)
    else:
        g.port.pco("nozzle_temp", "63488")
        g.port.picc("nozzle_btn", pics.main_on)
        g.port.picc2("nozzle_btn", pics.main_on_press)

    if g.klippy.heater_bed_target == 0:    # CLL bed heating state on the main page
        g.port.pco("bed_temp", "65535")
        g.port.picc("bed_btn", pics.main_off)
        g.port.picc2("bed_btn", pics.nav_btn_press)
    else:
        g.port.pco("bed_temp", "63488")
        g.port.picc("bed_btn", pics.main_on)
        g.port.picc2("bed_btn", pics.main_on_press)

    if g.klippy.hot_target == 0:           # CLL chamber heating state on the main page
        g.port.pco("chamber_temp", "65535")
        g.port.picc("chamber_btn", pics.main_off)
        g.port.picc2("chamber_btn", pics.nav_btn_press)
    else:
        g.port.pco("chamber_temp", "63488")
        g.port.picc("chamber_btn", pics.main_on)
        g.port.picc2("chamber_btn", pics.main_on_press)

    # CLL refresh the picture after every boot or print
    if not g.screen.main_picture_refreshed:
        # CLL get the file information
        g.files.list_pages = 0
        g.files.list_current_pages = 0
        g.files.list_folder_layers = 0
        g.files.list_previous_path = ""
        g.files.list_root_path = filelist.DEFAULT_DIR
        g.files.list_path = ""
        filelist.refresh_page_files(g.files.list_current_pages)
        if g.files.list_list_show_type[0] == "[c]":
            g.port.txt("last_file_name", g.files.list_list_show_name[0])
            name0 = g.files.list_list_show_name[0]
            # NOTE: thumbnail from the gcode file instead of .cache/.thumbs/<name>-160x160.png / .jpg
            picture_path = thumbnail.GcodeRef(substr(g.files.list_path + "/.cache/" + name0, 1))
            log.info("Picture path:%s", picture_path)
            thumb = thumbnail.find(picture_path, 160, "PNG")
            if thumb is not None and thumb.fmt == "PNG":
                log.info("Found png picture")
                g.port.pic("b[0]", pics.main_bg_photo)
                g.port.picc("last_file_btn", pics.main_bg_photo)
                g.port.picc2("last_file_btn", pics.nav_btn_press)
                g.port.vis("last_file_pic", "1")
                filelist.send_file_picture(picture_path, 160, "last_file_pic")
                g.screen.main_picture_detected = True
            else:
                if thumb is not None:
                    log.info("Found jpg picture")
                    g.port.pic("b[0]", pics.main_bg_photo)
                    g.port.picc("last_file_btn", pics.main_bg_photo)
                    g.port.picc2("last_file_btn", pics.nav_btn_press)
                    filelist.send_file_picture(picture_path, 160, "last_file_pic")
                    g.screen.main_picture_detected = True
                else:
                    g.port.pic("b[0]", pics.main_bg_noimg)
                    g.port.picc("last_file_btn", pics.main_bg_noimg)
                    g.port.picc2("last_file_btn", pics.main_on_press)
                    g.port.vis("last_file_pic", "0")
        else:
            g.port.pic("b[0]", pics.main_bg_noimg)
            g.port.picc("last_file_btn", pics.main_bg_noimg)
            g.port.picc2("last_file_btn", pics.main_on_press)
            g.port.txt("last_file_name", "")
            g.port.vis("last_file_pic", "0")
        g.screen.main_picture_refreshed = True

    # CLL ask for the power loss recovery once after boot
    if not g.screen.open_reprint_asked:
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
            g.port.txt("cell_" + to_string(5 * i + j), temp)
            j += 1
        i += 1


def auto_heaterbed():
    g.port.txt("temp_now", to_string(g.klippy.heater_bed_temperature) + "/")
    g.port.val("temp_target", to_string(g.klippy.heater_bed_target))
    if g.klippy.heater_bed_target > 0:
        g.port.picc("heat_toggle", pics.autobed_on)
        g.port.picc2("heat_toggle", pics.autobed_press_on)
        g.port.pco("temp_now", "63488")
        g.port.pco("temp_target", "63488")
    else:
        g.port.picc("heat_toggle", pics.autobed_off)
        g.port.picc2("heat_toggle", pics.autobed_press_off)
        g.port.pco("temp_now", "65535")
        g.port.pco("temp_target", "65535")


def open_moving():
    """4.4.22: leave the "moving" page of the guide once Klipper is idle again."""
    if g.klippy.idle_timeout_state != "Printing":
        page_to(ids.OPEN_FILAMENTVIDEO_0)


def open_heaterbed():
    g.port.txt("t0", to_string(g.klippy.heater_bed_temperature) + "/")
    g.port.val("n0", to_string(g.klippy.heater_bed_target))
    if g.klippy.heater_bed_target > 0:
        g.port.picc("b0", pics.bedtemp_on)
        g.port.picc2("b0", pics.bedtemp_press_on)
        g.port.pco("t0", "63488")
        g.port.pco("n0", "63488")
    else:
        g.port.picc("b0", pics.bedtemp_off)
        g.port.picc2("b0", pics.bedtemp_press_off)
        g.port.pco("t0", "65535")
        g.port.pco("n0", "65535")


def filament_pop():
    g.port.txt("temp_txt", "(" + to_string(g.klippy.extruder_temperature) + "/" +
                 to_string(g.klippy.extruder_target) + "℃)")
    if g.levelling.step_1:
        g.levelling.step_1 = False
        g.port.picc("steps_bar", pics.pop_steps_2)
        g.port.pco("step2_txt", "65535")
        g.port.pco("step1_txt", "38066")
        g.port.pco("temp_txt", "38066")
        g.port.vis("spin2", "0")
        g.port.vis("spin3", "1")
    if g.levelling.step_2 and g.klippy.idle_timeout_state == "Ready":
        g.levelling.step_2 = False
        g.port.picc("steps_bar", pics.pop_steps_3)
        g.port.pco("step3_txt", "65535")
        g.port.pco("step2_txt", "38066")
        g.port.vis("done_btn", "1")
        g.port.vis("alt_btn", "1")
        g.port.vis("spin3", "0")


def preview_pop():
    # 4.4.2 support mates and hall filament width sensors
    if not g.klippy.filament_detected:
        time.sleep(1)
        actions.set_print_pause()
        page_to(ids.PRINT_NO_FILAMENT)
    if g.klippy.print_stats_state == "standby":
        page_to(ids.PRINT_STOPPING)
    if g.klippy.print_stats_state == "error":
        page_to(ids.GCODE_ERROR)
        actions.cancel_print()
        actions.clear_previous_data()
        g.port.txt("msg", "G-code error: " + g.screen.error_message)


def bed_moving():
    if g.klippy.idle_timeout_state == "Ready":
        if g.screen.manual_count == 3:
            page_to(ids.PRE_BED_CALIBRATION)
        elif g.screen.manual_count == -2:
            page_to(ids.BED_FINISH)
        else:
            page_to(ids.BED_CALIBRATION)


def open_calibrate():
    if g.levelling.step_3:
        g.levelling.step_3 = False
        system("sync")      # CLL save the system information, then go to the filament loading page
        time.sleep(10)
        actions.get_object_status()
        actions.sub_object_status()
        page_to(ids.OPEN_FILAMENTVIDEO_0)
    if g.levelling.step_2 and g.klippy.webhooks_state == "ready":
        g.levelling.step_2 = False
        time.sleep(5)
        g.ep.send(json_run_a_gcode("M901"))    # CLL input shaping after the bed levelling
    if g.levelling.step_1 and g.klippy.idle_timeout_state == "Ready":
        g.levelling.step_1 = False
        settings.get_heater_bed_target()
        actions.set_heater_bed_target(g.config.heater_bed_target)
        g.ep.send(json_run_a_gcode("M190 S" + to_string(g.config.heater_bed_target) + "\n"))
        time.sleep(5)
        g.ep.send(json_run_a_gcode("M4027"))   # CLL levelling after the platform / nozzle initialisation


def filament_set_fan():
    if not g.screen.move_fan_setting:     # CLL refresh only while the slider is not being dragged
        fan0 = to_string(c_int(f32(g.klippy.out_pin_fan0_value * 100)))
        fan2 = to_string(c_int(f32(g.klippy.out_pin_fan2_value * 100)))
        fan3 = to_string(c_int(f32(g.klippy.out_pin_fan3_value * 100)))
        g.port.val("fan1_slider", fan0)
        g.port.val("fan1_val", fan0)
        g.port.val("fan2_slider", fan2)
        g.port.val("fan2_val", fan2)
        g.port.val("fan3_slider", fan3)
        g.port.val("fan3_val", fan3)
        for name, value in (("fan1_toggle", g.klippy.out_pin_fan0_value), ("fan2_toggle", g.klippy.out_pin_fan2_value),
                            ("fan3_toggle", g.klippy.out_pin_fan3_value)):
            if value == 0:
                g.port.picc(name, pics.fan_row_off)
                g.port.picc2(name, pics.fan_press_off)
            else:
                g.port.picc(name, pics.fan_row_on)
                g.port.picc2(name, pics.fan_press_on)


def common_setting():
    g.shown.oobe_enabled = settings.get_oobe_enabled()
    g.port.txt("version_txt", g.config.version_soc)
    if not g.shown.oobe_enabled:
        g.port.picc("reset_btn", pics.reset_row)
        g.port.picc2("reset_btn", pics.settings_press)
    else:
        g.port.picc("reset_btn", pics.reset_row_on)
        g.port.picc2("reset_btn", pics.settings_press_on)


def filament():
    g.port.txt("nozzle_temp", to_string(g.klippy.extruder_temperature))
    g.port.val("nozzle_set", to_string(g.klippy.extruder_target))
    g.port.txt("bed_temp", to_string(g.klippy.heater_bed_temperature))
    g.port.val("bed_set", to_string(g.klippy.heater_bed_target))
    g.port.txt("chamber_temp", to_string(g.klippy.hot_temperature))
    g.port.val("chamber_set", to_string(g.klippy.hot_target))
    if g.klippy.extruder_target > 0:   # CLL button state depends on the nozzle heating
        g.port.picc("nozzle_toggle", pics.filament_row_on)
        g.port.picc2("nozzle_toggle", pics.filament_press_on)
        g.port.picc("nozzle_row", pics.filament_row_on)
        g.port.picc2("nozzle_row", pics.filament_press_on)
        g.port.pco("nozzle_temp", "63488")
    else:
        g.port.picc("nozzle_toggle", pics.filament_row_off)
        g.port.picc2("nozzle_toggle", pics.filament_press_off)
        g.port.picc("nozzle_row", pics.filament_row_off)
        g.port.picc2("nozzle_row", pics.filament_press_off)
        g.port.pco("nozzle_temp", "65535")

    if g.klippy.heater_bed_target > 0:     # CLL button state depends on the bed heating
        g.port.picc("bed_toggle", pics.filament_row_on)
        g.port.picc2("bed_toggle", pics.filament_press_on)
        g.port.picc("bed_row", pics.filament_row_on)
        g.port.picc2("bed_row", pics.filament_press_on)
        g.port.pco("bed_temp", "63488")
    else:
        g.port.picc("bed_toggle", pics.filament_row_off)
        g.port.picc2("bed_toggle", pics.filament_press_off)
        g.port.picc("bed_row", pics.filament_row_off)
        g.port.picc2("bed_row", pics.filament_press_off)
        g.port.pco("bed_temp", "65535")

    if g.klippy.hot_target > 0:
        g.port.picc("chamber_toggle", pics.filament_row_on)
        g.port.picc2("chamber_toggle", pics.filament_press_on)
        g.port.picc("chamber_row", pics.filament_row_on)
        g.port.picc2("chamber_row", pics.filament_press_on)
        g.port.pco("chamber_temp", "63488")
    else:
        g.port.picc("chamber_toggle", pics.filament_row_off)
        g.port.picc2("chamber_toggle", pics.filament_press_off)
        g.port.picc("chamber_row", pics.filament_row_off)
        g.port.picc2("chamber_row", pics.filament_press_off)
        g.port.pco("chamber_temp", "65535")

    sel = {10: 0, 50: 1, 100: 2}.get(g.klippy.filament_extruder_dist)
    if sel is not None:
        for k, name in enumerate(("step_10", "step_50", "step_100")):
            if k == sel:
                g.port.picc(name, pics.filament_row_on)
                g.port.picc2(name, pics.filament_press_on)
            else:
                g.port.picc(name, pics.filament_row_off)
                g.port.picc2(name, pics.filament_press_off)


def auto_unload():
    g.port.txt("temp_txt", "(" + to_string(g.klippy.extruder_temperature) + "/" +
                 to_string(g.klippy.extruder_target) + "℃)")
    if g.levelling.step_1:
        g.levelling.step_1 = False
        g.port.vis("spin1", "0")
        g.port.vis("spin2", "1")
        g.port.picc("steps_bar", pics.unload_steps_1)
        g.port.pco("step2_txt", "65535")
        g.port.pco("step1_txt", "38066")
    if g.levelling.step_2:
        g.levelling.step_2 = False
        g.port.vis("spin2", "0")
        g.port.picc("steps_bar", pics.unload_steps_2)
        g.port.pco("step3_txt", "65535")
        g.port.pco("step2_txt", "38066")
        g.port.vis("load_btn", "1")
        g.port.vis("ok", "1")


# the page that is open -> what it shows (pages not listed have nothing to refresh)
REFRESH = {
    ids.MAIN: main,
    ids.PREVIEW: preview,
    ids.PRINTING: printing,
    ids.PRINTING_2: printing,
    ids.PRINT_FILAMENT: print_filament,
    ids.MOVE: move_page,
    ids.PRINT_ZOFFSET: printing_zoffset,
    ids.AUTO_MOVING: auto_moving,
    ids.AUTO_FINISH: auto_finish,
    ids.SYNTONY_MOVE: syntony_move,
    ids.PRINT_STOPPING: stopping,
    ids.PRE_BED_CALIBRATION: auto_level,
    ids.OPEN_FILAMENTVIDEO_2: open_filament_video_2,
    ids.ZOFFSET: zoffset,
    ids.AUTO_HEATERBED: auto_heaterbed,
    ids.OPEN_HEATERBED: open_heaterbed,
    ids.FILAMENT_POP_2: filament_pop,
    ids.FILAMENT_POP_3: filament_pop,
    ids.PREVIEW_POP_1: preview_pop,
    ids.PREVIEW_POP_2: preview_pop,
    ids.BED_MOVING: bed_moving,
    ids.OPEN_CALIBRATE: open_calibrate,
    ids.COMMON_SETTING: common_setting,
    ids.FILAMENT_SET_FAN: filament_set_fan,
    ids.WIFI_KB: wifi_ui.refresh_wifi_keyboard,
    ids.FILAMENT: filament,
    ids.INTERNET_PAGE: wifi_ui.refresh_show_ip,
    ids.AUTO_UNLOAD: auto_unload,
    ids.OPEN_MOVING: open_moving,
}
