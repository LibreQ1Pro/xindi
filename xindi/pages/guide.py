"""The pages of the first-start guide that show printer state."""

from xindi import state as g
from xindi.screen import pageids as ids, pics
from xindi.screen.navigation import page_to
from xindi.util.cpp import to_string


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


def open_moving():
    """4.4.22: leave the "moving" page of the guide once Klipper is idle again."""
    if g.klippy.idle_timeout_state != "Printing":
        page_to(ids.OPEN_FILAMENTVIDEO_0)
