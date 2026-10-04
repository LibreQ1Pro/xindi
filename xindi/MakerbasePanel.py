"""Port of src/MakerbasePanel.cpp"""

from .cpp import to_string
from .KlippyGcodes import HOME, HOME_XY, Z_TILT, QUAD_GANTRY_LEVEL, MOVE_RELATIVE, MOVE
from .MoonrakerAPI import json_run_a_gcode, json_query_printer_object_status

AXIS_X = "X"
AXIS_Y = "Y"
AXIS_Z = "Z"


def home():
    return json_run_a_gcode(HOME)


def homexy():
    return json_run_a_gcode(HOME_XY)


def z_tilt():
    return json_run_a_gcode(Z_TILT)


def quad_gantry_level():
    return json_run_a_gcode(QUAD_GANTRY_LEVEL)


def move(axis, dist, speed):
    """Relative move.

    axis:  AXIS_X, AXIS_Y or AXIS_Z
    dist:  distance with direction, e.g. "+10", "-100"
    speed: speed in mm/s
    """
    return json_run_a_gcode(MOVE_RELATIVE + "\n" + MOVE + " " + axis + dist + " F" + to_string(speed * 60) + "\nG90")


def get_printer_object_status():
    objects = {}
    objects["webhook"] = None
    objects["gcode_move"] = None
    objects["toolhead"] = None
    objects["configfile"] = None
    objects["extruder"] = None
    objects["heater_bed"] = None
    objects["fan"] = None
    objects["idle_timeout"] = None
    objects["virtual_sdcard"] = None
    objects["print_stats"] = None
    objects["display_status"] = None
    objects["bed_mesh"] = None
    return json_query_printer_object_status(objects)
