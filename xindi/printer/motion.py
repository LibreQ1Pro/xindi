"""Moving the toolhead, homing, the z offset and the extruder."""

import logging
import time

from xindi import state as g
from xindi.config import settings
from xindi.moonraker.gcodes import AXIS_X, AXIS_Y, AXIS_Z, move_relative
from xindi.moonraker.rpc_requests import json_emergency_stop
from xindi.pages import widgets
from xindi.screen import pageids as ids, pics
from xindi.util.cpp import c_int, f32, stof, to_string

log = logging.getLogger(__name__)


def set_intern_zoffset(offset):
    g.klippy.set_offset = f32(offset)


def set_zoffset(positive):
    if positive:
        g.ep.run_gcode("SET_GCODE_OFFSET Z_ADJUST=+" + to_string(g.klippy.set_offset) + " MOVE=1")
    else:
        g.ep.run_gcode("SET_GCODE_OFFSET Z_ADJUST=-" + to_string(g.klippy.set_offset) + " MOVE=1")


def set_move_dist(dist):
    g.klippy.move_dist = f32(dist)


def move_home():
    g.ep.run_gcode("G28\n")


def move_x_decrease():
    g.ep.send(move_relative(AXIS_X, "-" + to_string(g.klippy.move_dist), 130))
    g.screen.unhomed_move_mode = 2


def move_x_increase():
    g.ep.send(move_relative(AXIS_X, "+" + to_string(g.klippy.move_dist), 130))
    g.screen.unhomed_move_mode = 1


def move_y_decrease():
    g.ep.send(move_relative(AXIS_Y, "-" + to_string(g.klippy.move_dist), 130))
    g.screen.unhomed_move_mode = 4


def move_y_increase():
    g.ep.send(move_relative(AXIS_Y, "+" + to_string(g.klippy.move_dist), 130))
    g.screen.unhomed_move_mode = 3


def move_z_decrease():
    g.ep.send(move_relative(AXIS_Z, "-" + to_string(g.klippy.move_dist), 10))
    g.screen.unhomed_move_mode = 5


def move_z_increase():
    g.ep.send(move_relative(AXIS_Z, "+" + to_string(g.klippy.move_dist), 10))
    g.screen.unhomed_move_mode = 6


def set_print_filament_dist(dist):
    g.klippy.filament_extruder_dist = c_int(f32(dist))


def start_retract():
    g.ep.run_gcode("M83\nG1 E-" + to_string(g.klippy.filament_extruder_dist) + " F300\n")


def start_extrude():
    g.ep.run_gcode("M83\nG1 E" + to_string(g.klippy.filament_extruder_dist) + " F300\n")


def motors_off():
    g.ep.send(json_emergency_stop())
    time.sleep(1)
    g.ep.run_gcode("FIRMWARE_RESTART\n")     # "motors off" was turned into an emergency stop


def filament_load():
    g.port.vis("next_btn", "0")
    g.port.vis("temp_txt", "1")
    g.port.vis("back_btn", "0")
    g.port.picc("steps_bar", pics.pop_steps_1)
    g.port.pco("step1_txt", "65535")
    g.port.pco("hint", "38066")
    g.port.vis("spin1", "0")
    g.port.vis("spin2", "1")
    g.klippy.idle_timeout_state = "Printing"
    g.ep.run_gcode("M109 S" + to_string(g.screen.load_target) + "\n")
    g.ep.run_gcode("M604\n")


def filament_unload():
    g.klippy.idle_timeout_state = "Printing"
    g.ep.run_gcode("M109 S" + to_string(g.screen.load_target) + "\n")
    g.ep.run_gcode("M603\n")


def move_motors_off():
    g.ep.run_gcode("M84\n")


def open_start_extrude():
    g.ep.run_gcode("M83\nG1 E20 F300\n")


def save_current_zoffset():
    z_offset = to_string(g.klippy.gcode_move_homing_origin[2])
    z_offset = widgets.cut_after_point(z_offset, 4)
    if g.screen.page in (ids.AUTO_MOVING, ids.OPEN_CALIBRATE):
        g.klippy.idle_timeout_state = "Printing"
        settings.get_babystep()
        z = f32(stof(g.config.babystep_value) + stof(g.config.adxl_offset))
        if z > -5 and z < 5:    # CLL only z-offsets between -5 and 5 are saved
            g.config.babystep_value = to_string(z)
            settings.set_babystep(g.config.babystep_value)
            log.info("Current z-offset saved as %s", g.config.babystep_value)
    else:
        if z_offset != g.config.babystep_value and z_offset.find("0.000") != -1:
            if stof(z_offset) > -5 and stof(z_offset) < 5:
                g.config.babystep_value = z_offset
                settings.set_babystep(g.config.babystep_value)
                log.info("Current z-offset saved as:%s", g.config.babystep_value)
