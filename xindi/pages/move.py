"""The move page and its pop-ups."""

from xindi import state as g
from xindi.pages.widgets import cut_after_point, segmented
from xindi.printer import job
from xindi.screen import pageids as ids
from xindi.util.cpp import f32, to_string


def move_page():
    x_pos = cut_after_point(to_string(g.klippy.x_position), 2)
    y_pos = cut_after_point(to_string(g.klippy.y_position), 2)
    z_pos = cut_after_point(to_string(g.klippy.z_position), 2)

    g.port.txt("x_pos", x_pos)
    g.port.txt("y_pos", y_pos)
    g.port.txt("z_pos", z_pos)

    # CLL highlight the selected distance
    for dist, look in ((0.1, "d01"), (1.0, "d1"), (10, "d10")):
        if g.klippy.move_dist == f32(dist):
            segmented("dist_seg", (("d01", "dist_01_lbl"), ("d1", "dist_1_lbl"), ("d10", "dist_10_lbl")), look)


def move_home_tips():
    g.screen.jump_move_pop_2 = True


def move_tips():
    g.screen.jump_move_pop_1 = True
    if g.screen.page in (ids.PRINTING, ids.PRINT_ZOFFSET, ids.PRINT_FILAMENT,
                             ids.PRINTING_2):
        job.cancel_print()
