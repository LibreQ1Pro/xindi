"""What the user and the screen start: commands to Klipper / Moonraker, the printing flow, the levelling and filament steps."""

import json as _json
import urllib.request

from . import paths
from . import state as g
from . import pageids as ids
from . import pics
from .ui import page_to
from .cpp import to_string, substr, f32, c_int, cdiv, cmod, stof, access, read_file, system, sleep, usleep, str_lower_ascii
from .mks_log import MKSLOG, MKSLOG_BLUE, MKSLOG_RED, MKSLOG_YELLOW, cout, cerr
from .screen_tx import send_cmd_txt, send_cmd_pco, send_cmd_picc, send_cmd_vis
from .moonraker_api import (json_run_a_gcode, json_subscribe_to_printer_object_status,
                           json_query_printer_object_status, json_print_a_file, json_emergency_stop)
from .gcodes import (AXIS_X, AXIS_Y, AXIS_Z, move_relative, set_heater_temp, set_fan0_speed, set_fan2_speed,
                           set_fan3_speed, set_speed_rate)
from .printer_status import subscribe_objects_status
from . import filelist, pages, settings


def _top(stack):
    """std::stack::top() (undefined behaviour on an empty stack in C++)"""
    return stack[-1] if stack else ""


def sub_object_status():
    g.ep.Send(json_subscribe_to_printer_object_status(subscribe_objects_status()))


def get_object_status():
    g.ep.Send(json_query_printer_object_status(subscribe_objects_status()))


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


def set_fan0(speed):
    g.ep.Send(json_run_a_gcode(set_fan0_speed(speed)))


def set_fan2(speed):
    g.ep.Send(json_run_a_gcode(set_fan2_speed(speed)))


def set_fan3(speed):
    g.ep.Send(json_run_a_gcode(set_fan3_speed(speed)))


def set_intern_zoffset(offset):
    g.klippy.set_offset = f32(offset)


def set_zoffset(positive):
    if positive:
        g.ep.Send(json_run_a_gcode("SET_GCODE_OFFSET Z_ADJUST=+" + to_string(g.klippy.set_offset) + " MOVE=1"))
    else:
        g.ep.Send(json_run_a_gcode("SET_GCODE_OFFSET Z_ADJUST=-" + to_string(g.klippy.set_offset) + " MOVE=1"))


def set_move_dist(dist):
    g.klippy.move_dist = f32(dist)


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
    g.ep.Send(move_relative(AXIS_X, "-" + to_string(g.klippy.move_dist), 130))
    g.screen.unhomed_move_mode = 2


def move_x_increase():
    g.ep.Send(move_relative(AXIS_X, "+" + to_string(g.klippy.move_dist), 130))
    g.screen.unhomed_move_mode = 1


def move_y_decrease():
    g.ep.Send(move_relative(AXIS_Y, "-" + to_string(g.klippy.move_dist), 130))
    g.screen.unhomed_move_mode = 4


def move_y_increase():
    g.ep.Send(move_relative(AXIS_Y, "+" + to_string(g.klippy.move_dist), 130))
    g.screen.unhomed_move_mode = 3


def move_z_decrease():
    g.ep.Send(move_relative(AXIS_Z, "-" + to_string(g.klippy.move_dist), 10))
    g.screen.unhomed_move_mode = 5


def move_z_increase():
    g.ep.Send(move_relative(AXIS_Z, "+" + to_string(g.klippy.move_dist), 10))
    g.screen.unhomed_move_mode = 6


def get_filament_detected():
    return g.klippy.fila_sensor_detected


def get_filament_detected_enable():
    return g.klippy.fila_sensor_enabled


def set_print_pause():
    g.ep.Send(json_run_a_gcode("PAUSE"))


def set_print_resume():
    g.ep.Send(json_run_a_gcode("RESUME"))


def cancel_print():
    g.klippy.print_stats_filename = ""
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
    g.levelling.auto_level_dist = f32(dist)


def start_auto_level():
    g.levelling.step_1 = False
    g.levelling.step_2 = False
    g.levelling.step_3 = False
    g.levelling.step_4 = False
    if not g.levelling.start_pre_auto_level:
        g.klippy.idle_timeout_state = "Printing"
    page_to(ids.AUTO_MOVING)
    set_heater_bed_target(g.config.heater_bed_target)
    g.ep.Send(json_run_a_gcode("M4029"))


def set_filament_extruder_target(positive):
    settings.get_extruder_target()
    g.klippy.filament_extruder_target = g.config.extruder_target
    if positive:
        g.klippy.filament_extruder_target += 3
    else:
        g.klippy.filament_extruder_target -= 3

    if g.klippy.filament_extruder_target >= 350:
        g.klippy.filament_extruder_target = 350

    if g.klippy.filament_extruder_target < 0:
        g.klippy.filament_extruder_target = 0
        set_extruder_target(0)
        settings.set_extruder_target(0)
    else:
        set_extruder_target(g.klippy.filament_extruder_target)
        settings.set_extruder_target(g.klippy.filament_extruder_target)


def set_print_filament_dist(dist):
    g.klippy.filament_extruder_dist = c_int(f32(dist))


def start_retract():
    g.ep.Send(json_run_a_gcode("M83\nG1 E-" + to_string(g.klippy.filament_extruder_dist) + " F300\n"))


def start_extrude():
    g.ep.Send(json_run_a_gcode("M83\nG1 E" + to_string(g.klippy.filament_extruder_dist) + " F300\n"))


def reset_klipper():
    g.ep.Send(json_run_a_gcode("RESTART\n"))


def reset_firmware():
    g.ep.Send(json_run_a_gcode("FIRMWARE_RESTART\n"))


def finish_print():
    sdcard_reset_file()
    filelist.clear_cp0_image()
    pages.clear_preview()
    g.screen.show_preview_complete = False
    page_to(ids.MAIN)


def motors_off():
    g.ep.Send(json_emergency_stop())
    sleep(1)
    g.ep.Send(json_run_a_gcode("FIRMWARE_RESTART\n"))     # "motors off" was turned into an emergency stop


def beep_on_off():
    if g.klippy.out_pin_beep_value == 0:
        g.ep.Send(json_run_a_gcode("beep_on"))
        g.config.beep_status = True
        settings.set_beep_status()
    else:
        g.ep.Send(json_run_a_gcode("beep_off"))
        g.config.beep_status = False
        settings.set_beep_status()


def led_on_off():
    if g.klippy.caselight_value == 0:
        g.ep.Send(json_run_a_gcode("SET_PIN PIN=caselight VALUE=1"))
        if g.screen.page != ids.SCREEN_SLEEP:
            g.config.led_status = True
            settings.set_led_status()
    else:
        g.ep.Send(json_run_a_gcode("SET_PIN PIN=caselight VALUE=0"))
        if g.screen.page != ids.SCREEN_SLEEP:
            g.config.led_status = False
            settings.set_led_status()


def filament_extruder_target():
    settings.get_extruder_target()
    if g.klippy.extruder_target == 0:
        set_extruder_target(g.config.extruder_target)
    else:
        set_extruder_target(0)


def filament_heater_bed_target():
    settings.get_heater_bed_target()
    if 0 == g.klippy.heater_bed_target:
        set_heater_bed_target(g.config.heater_bed_target)
    else:
        set_heater_bed_target(0)


def filament_hot_target():
    settings.get_hot_target()
    if 0 == g.klippy.hot_target:
        set_hot_target(g.config.hot_target)
    else:
        set_hot_target(0)


def go_to_reset():
    if g.klippy.webhooks_state == "shutdown":
        page_to(ids.RESET)
    else:
        # 4.4.22: fixed name (was read from /dev_info.txt)
        page_to(ids.SYS_OK)
        send_cmd_txt(g.tty_fd, "info_txt", "Q1 Pro")


def set_print_filament_target():
    if 0 == g.klippy.extruder_target:
        settings.get_extruder_target()
        set_extruder_target(g.config.extruder_target)
    else:
        set_extruder_target(0)


def complete_print():
    if not g.screen.shutdown_after_print:
        g.ep.Send(json_run_a_gcode("PRINT_END"))
    else:
        g.ep.Send(json_run_a_gcode("PRINT_END_POWEROFF"))
    # 4.4.22: the total print time is no longer kept in config.mksini


def go_to_syntony_move():
    g.levelling.step_1 = False
    g.levelling.syntony_finished = False
    g.klippy.idle_timeout_state = "Printing"
    page_to(ids.SYNTONY_MOVE)
    g.ep.Send(json_run_a_gcode("M901\n"))


def filament_load():
    send_cmd_vis(g.tty_fd, "next_btn", "0")
    send_cmd_vis(g.tty_fd, "temp_txt", "1")
    send_cmd_vis(g.tty_fd, "back_btn", "0")
    send_cmd_picc(g.tty_fd, "steps_bar", pics.pop_steps_1)
    send_cmd_pco(g.tty_fd, "step1_txt", "65535")
    send_cmd_pco(g.tty_fd, "hint", "38066")
    send_cmd_vis(g.tty_fd, "spin1", "0")
    send_cmd_vis(g.tty_fd, "spin2", "1")
    g.klippy.idle_timeout_state = "Printing"
    g.ep.Send(json_run_a_gcode("M109 S" + to_string(g.screen.load_target) + "\n"))
    g.ep.Send(json_run_a_gcode("M604\n"))


def filament_unload():
    g.klippy.idle_timeout_state = "Printing"
    g.ep.Send(json_run_a_gcode("M109 S" + to_string(g.screen.load_target) + "\n"))
    g.ep.Send(json_run_a_gcode("M603\n"))


def move_motors_off():
    g.ep.Send(json_run_a_gcode("M84\n"))


def open_more_level_finish():
    settings.get_babystep()      # 4.4.22 (was init_mks_status())
    settings.set_oobe_enabled(False)     # turn the out-of-box guide off
    get_object_status()
    page_to(ids.MAIN)


def open_set_print_filament_target():
    if 0 == g.klippy.extruder_target:
        settings.get_extruder_target()
        set_extruder_target(g.config.extruder_target)
    else:
        set_extruder_target(0)


def open_start_extrude():
    g.ep.Send(json_run_a_gcode("M83\nG1 E20 F300\n"))


def open_calibrate_start():
    g.levelling.step_1 = False    # CLL True: platform and nozzle position initialised
    g.levelling.step_2 = False    # CLL True: compensation values collected
    g.levelling.step_3 = False    # CLL True: input shaping done
    g.klippy.idle_timeout_state = "Printing"
    page_to(ids.OPEN_CALIBRATE)
    g.ep.Send(json_run_a_gcode("M4028"))   # custom gcode "M4028" in printer.cfg


def set_auto_level_heater_bed_target(positive):
    settings.get_heater_bed_target()
    g.levelling.auto_level_heater_bed_target = g.config.heater_bed_target
    if positive:
        g.levelling.auto_level_heater_bed_target += 3
    else:
        g.levelling.auto_level_heater_bed_target -= 3
    if g.levelling.auto_level_heater_bed_target > 120:
        g.levelling.auto_level_heater_bed_target = 120
    if g.levelling.auto_level_heater_bed_target < 0:
        g.levelling.auto_level_heater_bed_target = 0
    set_heater_bed_target(g.levelling.auto_level_heater_bed_target)
    settings.set_heater_bed_target(g.levelling.auto_level_heater_bed_target)


def detect_error():
    if g.screen.page in (ids.PRINTING, ids.PRINT_ZOFFSET, ids.PRINT_FILAMENT,
                             ids.PRINTING_2, ids.GCODE_ERROR, ids.LEVEL_ERROR,
                             ids.DETECT_ERROR):
        pass
    elif g.screen.page in (ids.OPEN_CALIBRATE, ids.AUTO_MOVING):
        g.ep.Send(json_run_a_gcode("RESTART"))
        g.screen.jump_level_error = True
    else:
        if g.klippy.webhooks_state != "shutdown" and g.klippy.webhooks_state != "error":
            g.screen.jump_detect_error = True


def clear_previous_data():
    sdcard_reset_file()
    filelist.clear_cp0_image()
    pages.clear_preview()
    g.screen.show_preview_complete = False
    g.screen.printing_keyboard_enabled = False


def print_start():
    if g.screen.bed_leveling:
        g.ep.Send(json_run_a_gcode("G31\n"))
    else:
        g.ep.Send(json_run_a_gcode("G32\n"))


def open_heater_bed_up():
    # 4.4.22: the caller shows the "moving" page, which waits until Klipper is idle
    # again (refresh_page_open_moving()); the bed is homed and moved up and down
    g.klippy.idle_timeout_state = "Printing"
    g.ep.Send(json_run_a_gcode("SET_KINEMATIC_POSITION Z=150\nSET_KINEMATIC_POSITION X=150\nSET_KINEMATIC_POSITION Y=150\n"))
    g.ep.Send(json_run_a_gcode("G91\nG1 Z-30 F600\nG1 X-30 Y-30 F1200\nG90\nM84\n"))
    g.ep.Send(json_run_a_gcode("M4031\n"))
    g.ep.Send(json_run_a_gcode("G28\n"))
    g.ep.Send(json_run_a_gcode("G1 Z240 F600\nG1 Z10 F600\n G1 Z240 F600\n G1 Z20 F600\n"))


def bed_leveling_switch(positive):
    if positive:
        g.ep.Send(json_run_a_gcode("G31"))
        g.screen.bed_leveling = True
    else:
        g.ep.Send(json_run_a_gcode("G32"))
        g.screen.bed_leveling = False


def save_current_zoffset():
    z_offset = to_string(g.klippy.gcode_move_homing_origin[2])
    z_offset = pages._cut_after_point(z_offset, 4)
    if g.screen.page in (ids.AUTO_MOVING, ids.OPEN_CALIBRATE):
        g.klippy.idle_timeout_state = "Printing"
        settings.get_babystep()
        z = f32(stof(g.config.babystep_value) + stof(g.config.adxl_offset))
        if z > -5 and z < 5:    # CLL only z-offsets between -5 and 5 are saved
            g.config.babystep_value = to_string(z)
            settings.set_babystep(g.config.babystep_value)
            MKSLOG_RED("Current z-offset saved as %s", g.config.babystep_value)
    else:
        if z_offset != g.config.babystep_value and z_offset.find("0.000") != -1:
            if stof(z_offset) > -5 and stof(z_offset) < 5:
                g.config.babystep_value = z_offset
                settings.set_babystep(g.config.babystep_value)
                MKSLOG_RED("Current z-offset saved as:%s", g.config.babystep_value)


def check_filament_type():
    if g.files.meta_filament_type != "":
        filament_type = g.files.meta_filament_type
    else:
        filament_type = g.files.meta_filament_name
    filament_type = str_lower_ascii(filament_type)
    MKSLOG_YELLOW("filament_type : %s", filament_type)
    # 4.4.1 CLL "do not show again" button on the filament confirmation pop-ups
    if (filament_type.find("pla") != -1 or filament_type.find("petg") != -1) and g.screen.preview_pop_1_on:
        page_to(ids.PREVIEW_POP_1)
    elif filament_type.find("abs") != -1 and g.screen.preview_pop_2_on:
        page_to(ids.PREVIEW_POP_2)
    else:
        page_to(ids.PRINTING)


def check_filament_width():
    """4.4.2 support for the hall filament width sensor"""
    if g.files.filament_message.find("// Filament dia (measured mm):") != -1:
        filament_width = stof(substr(g.files.filament_message, 31))
        MKSLOG("Filament width: %f", filament_width)
        if filament_width < 0.3:
            g.klippy.filament_detected = False
        else:
            g.klippy.filament_detected = True
    elif g.files.filament_message.find("// Filament NOT present") != -1 or g.files.filament_message.find("echo: Filament run out") != -1:
        g.klippy.filament_detected = False


def bed_calibrate():
    if g.screen.manual_count == 4:
        g.levelling.bed_offset = 0.0
        g.klippy.idle_timeout_state = "Printing"
        g.ep.Send(json_run_a_gcode("ABORT\n"))
        g.ep.Send(json_run_a_gcode("M4031\n"))     # 4.4.22
        g.ep.Send(json_run_a_gcode("M4030\n"))
        page_to(ids.BED_MOVING)
    elif g.screen.manual_count == 3:
        g.klippy.idle_timeout_state = "Printing"
        g.ep.Send(json_run_a_gcode("G1 Z10 F600"))
        g.ep.Send(json_run_a_gcode("BED_SCREWS_ADJUST\n"))
        g.ep.Send(json_run_a_gcode("G1 Z" + to_string(g.levelling.bed_offset) + " F600\n"))
        MKSLOG_BLUE("Current bed_offset:%f", g.levelling.bed_offset)
        page_to(ids.BED_MOVING)
    elif g.screen.manual_count > 0:
        g.klippy.idle_timeout_state = "Printing"
        g.ep.Send(json_run_a_gcode("ACCEPT\n"))
        g.ep.Send(json_run_a_gcode("G1 Z" + to_string(g.levelling.bed_offset) + " F600\n"))
        page_to(ids.BED_MOVING)
    elif g.screen.manual_count == 0:
        g.ep.Send(json_run_a_gcode("ACCEPT\n"))
        g.ep.Send(json_run_a_gcode("G1 Z10 F600\nG1 X0 Y0 F9000\n"))
        settings.get_babystep()      # 4.4.22 (was init_mks_status())
        page_to(ids.BED_FINISH)
    else:
        g.ep.Send(json_run_a_gcode("G1 Z10 F600\n"))
        page_to(ids.BED_FINISH)
    g.screen.manual_count -= 1


def bed_adjust(status):
    if status:
        g.ep.Send(json_run_a_gcode("G91\nG1 Z" + to_string(-g.levelling.auto_level_dist) + " F600\nG90\n"))
        g.levelling.bed_offset = f32(g.levelling.bed_offset - g.levelling.auto_level_dist)
        MKSLOG_BLUE("Current bed_offset:%f", g.levelling.bed_offset)
    else:
        g.ep.Send(json_run_a_gcode("G91\nG1 Z" + to_string(g.levelling.auto_level_dist) + " F600\nG90\n"))
        g.levelling.bed_offset = f32(g.levelling.bed_offset + g.levelling.auto_level_dist)
        MKSLOG_BLUE("Current bed_offset:%f", g.levelling.bed_offset)


def send_gcode(command):
    g.ep.Send(json_run_a_gcode(command))


def go_to_adjust():
    """CLL remember the last choice of the adjust page"""
    if g.screen.adjust_mode == "Filament":
        page_to(ids.FILAMENT)
    else:
        page_to(ids.MOVE)


def go_to_setting():
    if g.screen.set_mode == "Level_mode":
        page_to(ids.LEVEL_MODE)
    else:
        page_to(ids.COMMON_SETTING)


TIMELAPSE_URL = "http://127.0.0.1:7125/machine/timelapse/settings"


def check_timelapse_state():
    """4.4.22: state of Moonraker's timelapse plugin (off when it is not installed)."""
    try:
        with urllib.request.urlopen(TIMELAPSE_URL, timeout=2) as resp:
            g.screen.timelapse_enabled = bool(_json.loads(resp.read().decode("utf-8"))["result"]["enabled"])
    except Exception as e:
        cerr("Timelapse state: ", str(e), "\n")
        g.screen.timelapse_enabled = False
    return g.screen.timelapse_enabled


def switch_timelapse_state():
    """4.4.22: turn Moonraker's timelapse on / off (preview page)."""
    url = TIMELAPSE_URL + ("?enabled=False" if g.screen.timelapse_enabled else "?enabled=True")
    try:
        urllib.request.urlopen(urllib.request.Request(url, data=b"", method="POST"), timeout=2).close()
        g.screen.timelapse_enabled = not g.screen.timelapse_enabled
    except Exception as e:
        cerr("Timelapse switch: ", str(e), "\n")     # no plugin: the switch stays off


def finish_screen_update():
    """The screen has flashed its firmware: the file is kept as .bak."""
    if access("/root/800_480.tft") == 0:
        system("mv /root/800_480.tft /root/800_480.tft.bak; sync")


def check_print_interrupted():
    printer_variables = read_file(paths.klipper_config() + "/saved_variables.cfg")
    if printer_variables is None:
        cerr("Can't open the file ", paths.klipper_config() + "/saved_variables.cfg", "\n")
        return
    print_interrupted_status = substr(printer_variables, printer_variables.find("was_interrupted =") + 18, 5)
    if print_interrupted_status != "False":
        g.ep.Send(json_run_a_gcode("DETECT_INTERRUPTION\n"))
        g.screen.jump_resume_print = True
