"""Moving the toolhead, homing, the z offset and the extruder."""

import logging

from xindi import state as g
from xindi.config import settings
from xindi.moonraker.gcodes import AXIS_X, AXIS_Y, AXIS_Z, move_relative
from xindi.moonraker.rpc_requests import json_emergency_stop
from xindi.pages import widgets
from xindi.screen import pageids as ids
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
    """The emergency stop. The firmware is not restarted here: Klipper stays shut down and the screen shows its error page, where the user restarts it."""
    g.ep.send(json_emergency_stop())


def filament_load():
    for name in ("next_btn", "back_btn"):
        g.port.vis(name, "0")
    widgets.show_readout("nozzle", True)
    g.port.face("steps_bar", "load_1")
    g.port.pco("step1_txt", "65535")
    g.port.pco("hint", "42294")
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
    if g.screen.page == ids.AUTO_MOVING:
        g.klippy.idle_timeout_state = "Printing"
        settings.get_babystep()
    else:
        if z_offset != g.config.babystep_value and z_offset.find("0.000") != -1:
            if stof(z_offset) > -5 and stof(z_offset) < 5:
                g.config.babystep_value = z_offset
                settings.set_babystep(g.config.babystep_value)
                log.info("Current z-offset saved as:%s", g.config.babystep_value)
