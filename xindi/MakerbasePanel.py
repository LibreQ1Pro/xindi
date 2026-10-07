"""Port of src/MakerbasePanel.cpp"""

from .cpp import to_string
from .KlippyGcodes import MOVE_RELATIVE, MOVE
from .MoonrakerAPI import json_run_a_gcode

AXIS_X = "X"
AXIS_Y = "Y"
AXIS_Z = "Z"


def move(axis, dist, speed):
    """Relative move.

    axis:  AXIS_X, AXIS_Y or AXIS_Z
    dist:  distance with direction, e.g. "+10", "-100"
    speed: speed in mm/s
    """
    return json_run_a_gcode(MOVE_RELATIVE + "\n" + MOVE + " " + axis + dist + " F" + to_string(speed * 60) + "\nG90")


