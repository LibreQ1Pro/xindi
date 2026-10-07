"""The pages of a print: progress, temperatures, z offset, pause / filament."""

import logging
import time

from xindi import state as g
from xindi.config import settings
from xindi.moonraker.printer_status import get_cal_printing_time
from xindi.pages import file_list
from xindi.pages.widgets import cut_after_point, heating_widget
from xindi.printer import job, motion
from xindi.screen import pageids as ids, pics
from xindi.screen.navigation import page_to
from xindi.util.cpp import c_int, c_round, f32, to_string

log = logging.getLogger(__name__)


def stopping():
    log.debug("Printer ide_timeout state: %s", g.klippy.idle_timeout_state)
    log.debug("Printer webhooks state: %s", g.klippy.webhooks_state)
    if g.klippy.idle_timeout_state == "Ready":
        job.clear_previous_data()
        time.sleep(5)
        motion.save_current_zoffset()
        page_to(ids.MAIN)


def print_filament():
    g.port.txt("file_name", file_list.file_name_only(g.klippy.print_stats_filename))

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
    g.port.txt("time_elapsed", job.show_time(c_int(g.klippy.print_stats_print_duration)))
    g.port.txt("time_left", job.show_time(get_cal_printing_time(c_int(g.klippy.print_stats_print_duration),
                                                                 g.files.meta_estimated_time,
                                                                 g.klippy.display_status_progress)))

    if g.klippy.print_stats_state == "paused":
        g.klippy.ready = True

    # 4.4.2 CLL support mates and hall filament width sensors
    if not g.klippy.filament_detected:
        time.sleep(1)
        g.klippy.ready = False
        job.set_print_pause()
        page_to(ids.PRINT_NO_FILAMENT)

    if g.klippy.print_stats_state == "printing":
        if g.klippy.ready:
            g.klippy.ready = False
            page_to(ids.PRINTING)

    if g.klippy.print_stats_state == "standby":
        page_to(ids.PRINT_STOPPING)

    if g.klippy.print_stats_state == "error":
        page_to(ids.GCODE_ERROR)
        job.cancel_print()
        job.clear_previous_data()
        g.port.txt("msg", "G-code error: " + g.screen.error_message)

    # 4.4.2 CLL a long pause that stops the print switches the page
    if g.klippy.idle_timeout_state == "Idle":
        g.ep.run_gcode("G28\n")
        job.cancel_print()


def offset(intern_zoffset):
    g.klippy.intern_z_offset = f32(intern_zoffset)
    g.klippy.z_offset = f32(g.klippy.intern_z_offset + g.klippy.extern_z_offset)


def zoffset_buttons():
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
    z_offset = cut_after_point(z_offset, 4)
    show_gcode_z = cut_after_point(show_gcode_z, 4)
    g.port.txt("file_name", file_list.file_name_only(g.klippy.print_stats_filename))
    if z_offset != g.config.babystep_value:
        g.config.babystep_value = z_offset
        settings.set_babystep(g.config.babystep_value)
    g.port.txt("gcode_z", show_gcode_z)
    g.port.txt("z_offset", z_offset)
    g.port.txt("time_elapsed", job.show_time(c_int(g.klippy.print_stats_print_duration)))
    g.port.val("progress_pct", to_string(g.klippy.display_status_progress))
    g.port.txt("time_left", job.show_time(get_cal_printing_time(c_int(g.klippy.print_stats_print_duration),
                                                                 g.files.meta_estimated_time,
                                                                 g.klippy.display_status_progress)))
    g.port.val("progress", to_string(g.klippy.display_status_progress))

    zoffset_buttons()

    if g.klippy.print_stats_state == "printing":
        g.klippy.ready = True

    if g.klippy.fila_sensor_enabled:
        if not g.klippy.fila_sensor_detected:
            g.klippy.ready = False
            job.set_print_pause()
            page_to(ids.PRINT_NO_FILAMENT_2)

    # 4.4.2 CLL support mates and hall filament width sensors
    if not g.klippy.filament_detected:
        time.sleep(1)
        g.klippy.ready = False
        job.set_print_pause()
        page_to(ids.PRINT_NO_FILAMENT)

    if g.klippy.print_stats_state == "standby":
        page_to(ids.PRINT_STOPPING)

    if g.klippy.print_stats_state == "paused":
        if g.klippy.ready:
            g.klippy.ready = False
            page_to(ids.PRINT_FILAMENT)

    if g.klippy.print_stats_state == "complete":
        time_duration = job.show_time(c_int(g.klippy.print_stats_print_duration))
        job.complete_print()
        job.clear_previous_data()
        time.sleep(5)
        motion.save_current_zoffset()
        page_to(ids.PRINT_FINISH)
        g.port.txt("time_txt", time_duration)

    if g.klippy.print_stats_state == "error":
        page_to(ids.GCODE_ERROR)
        job.cancel_print()
        job.clear_previous_data()
        g.port.txt("msg", "G-code error: " + g.screen.error_message)


def printing_keyboard_mute_button():
    # 4.4.22 silent mode button of the keyboard
    if not g.screen.muted:
        g.port.picc("mute_btn", pics.kb_mute_off)
        g.port.picc2("mute_btn", pics.kb_mute_off_press)
    else:
        g.port.picc("mute_btn", pics.kb_mute_on)
        g.port.picc2("mute_btn", pics.kb_mute_on_press)


def printing_first_page():
    # CLL fan speeds
    g.port.val("fan1_val", to_string(c_int(f32(g.klippy.out_pin_fan0_value * 100))))
    g.port.val("fan2_val", to_string(c_int(f32(g.klippy.out_pin_fan2_value * 100))))
    g.port.val("fan3_val", to_string(c_int(f32(g.klippy.out_pin_fan3_value * 100))))

    g.port.txt("nozzle_temp", to_string(g.klippy.extruder_temperature))
    g.port.val("nozzle_set", to_string(g.klippy.extruder_target))
    heating_widget("nozzle_temp", "nozzle_btn", g.klippy.extruder_target)

    g.port.txt("bed_temp", to_string(g.klippy.heater_bed_temperature))
    g.port.val("bed_set", to_string(g.klippy.heater_bed_target))
    heating_widget("bed_temp", "bed_btn", g.klippy.heater_bed_target)

    # 4.4.22: the LED button moved to the second printing page

    g.port.val("chamber_set", to_string(g.klippy.hot_target))      # CLL chamber temperature
    g.port.txt("chamber_temp", to_string(g.klippy.hot_temperature))
    heating_widget("chamber_temp", "chamber_btn", g.klippy.hot_target)

    shown = "1" if g.screen.show_preview_gimage_completed else "0"
    g.port.vis("thumb", shown)
    g.port.val("thumb_flag", shown)


def printing_second_page():
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


def printing_state_changes():
    """Filament runout and the end of the print, as Klipper reports them."""
    if g.klippy.print_stats_state == "printing":
        g.klippy.ready = True

    if g.klippy.fila_sensor_enabled:
        if not g.klippy.fila_sensor_detected:
            g.klippy.ready = False
            job.set_print_pause()
            page_to(ids.PRINT_NO_FILAMENT_2)

    if not g.klippy.filament_detected:
        time.sleep(1)
        g.klippy.ready = False
        job.set_print_pause()
        page_to(ids.PRINT_NO_FILAMENT)

    state = g.klippy.print_stats_state
    if state == "complete":
        time_duration = job.show_time(c_int(g.klippy.print_stats_print_duration))
        job.complete_print()
        job.clear_previous_data()
        time.sleep(5)
        motion.save_current_zoffset()
        page_to(ids.PRINT_FINISH)
        g.port.txt("time_txt", time_duration)
    elif state == "paused":
        if g.klippy.ready:
            g.klippy.ready = False
            page_to(ids.PRINT_FILAMENT)
    elif state == "standby":
        page_to(ids.PRINT_STOPPING)
    elif state == "error":
        page_to(ids.GCODE_ERROR)
        job.cancel_print()
        job.clear_previous_data()
        g.port.txt("msg", "G-code error: " + g.screen.error_message)


def printing():
    z_offset = to_string(g.klippy.gcode_move_homing_origin[2])
    z_offset = cut_after_point(z_offset, 4)

    g.port.val("progress", to_string(g.klippy.display_status_progress))
    g.port.val("progress_pct", to_string(g.klippy.display_status_progress))
    g.port.txt("time_elapsed", job.show_time(c_int(g.klippy.print_stats_print_duration)))
    g.port.txt("time_left", job.show_time(get_cal_printing_time(c_int(g.klippy.print_stats_print_duration),
                                                                 g.files.meta_estimated_time,
                                                                 g.klippy.display_status_progress)))
    g.port.txt("file_name", file_list.file_name_only(g.klippy.print_stats_filename))

    # the z offset of the second page is always refreshed: the page starts with
    # the designer's "-1.000", it must not stay while the keyboard flag is set
    if g.screen.page == ids.PRINTING_2:
        g.port.txt("zoffset_val", z_offset)

    if g.screen.printing_keyboard_enabled:
        printing_keyboard_mute_button()
    elif g.screen.page == ids.PRINTING:         # CLL refresh only while the keyboard is not shown
        printing_first_page()
    elif g.screen.page == ids.PRINTING_2:
        printing_second_page()

    printing_state_changes()


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
