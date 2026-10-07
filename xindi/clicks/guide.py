"""Clicks on the pages of the out-of-box guide. Each function gets the page id and the widget id the screen sent; HANDLERS maps pages to them."""

from .. import actions, settings
from .. import pageids as ids
from ..ui import page_to


def open_language(page_id, widget_id):
    if widget_id == ids.OPEN_LANGUAGE_NEXT:
        page_to(ids.OPEN_VIDEO_1)
        actions.get_object_status()
    elif widget_id == ids.OPEN_LANGUAGE_SKIP:
        page_to(ids.OPEN_POP)


def open_pop(page_id, widget_id):
    if widget_id == ids.OPEN_POP_YES:
        page_to(ids.MAIN)
        settings.set_oobe_enabled(False)
    elif widget_id == ids.OPEN_POP_NO:
        page_to(ids.OPEN_LANGUAGE)


# second page of the guide
def open_video_1(page_id, widget_id):
    if widget_id == ids.OPEN_VIDEO_1_NEXT:
        page_to(ids.OPEN_VIDEO_2)


# third page of the guide
def open_video_2(page_id, widget_id):
    if widget_id == ids.OPEN_VIDEO_2_NEXT:
        page_to(ids.OPEN_WARNING)


# fourth page of the guide
def open_warning(page_id, widget_id):
    if widget_id == ids.OPEN_WARNING_NEXT:
        actions.open_heater_bed_up()
        page_to(ids.OPEN_MOVING)       # 4.4.22: wait until the bed has moved


# 4.4.22 "the bed is moving" page of the guide; its timer sends 0
def open_moving(page_id, widget_id):
    if widget_id == ids.OPEN_MOVING_TIMER:
        page_to(ids.OPEN_FILAMENTVIDEO_0)


# fifth page of the guide
def open_video_3(page_id, widget_id):
    if widget_id == ids.OPEN_VIDEO_3_NEXT:
        page_to(ids.OPEN_FILAMENTVIDEO_1)     # CLL levelling and input shaping removed from the guide
    elif widget_id == ids.OPEN_VIDEO_3_UP:
        actions.set_move_dist(10.0)
        actions.move_z_decrease()
    elif widget_id == ids.OPEN_VIDEO_3_DOWN:
        actions.set_move_dist(10.0)
        actions.move_z_increase()


def open_heaterbed(page_id, widget_id):
    if widget_id == ids.OPEN_HEATERBED_DOWN:
        actions.set_auto_level_heater_bed_target(False)
    elif widget_id == ids.OPEN_HEATERBED_UP:
        actions.set_auto_level_heater_bed_target(True)
    elif widget_id == ids.OPEN_HEATERBED_ON_OFF:
        actions.filament_heater_bed_target()
    elif widget_id == ids.OPEN_HEATERBED_NEXT:
        actions.open_calibrate_start()


def open_filamentvideo(page_id, widget_id):
    if page_id == ids.OPEN_FILAMENTVIDEO_0:
        if widget_id == ids.OPEN_FILAMENTVIDEO_0_NEXT:
            page_to(ids.OPEN_FILAMENTVIDEO_1)
        # NOTE: no "break" in the original - falls through into the next case
    if widget_id == ids.OPEN_FILAMENTVIDEO_1_NEXT:
        page_to(ids.OPEN_FILAMENTVIDEO_2)


def open_filamentvideo_2(page_id, widget_id):
    if widget_id == ids.OPEN_FILAMENTVIDEO_2_UP:
        actions.set_filament_extruder_target(True)
    elif widget_id == ids.OPEN_FILAMENTVIDEO_2_DOWN:
        actions.set_filament_extruder_target(False)
    elif widget_id == ids.OPEN_FILAMENTVIDEO_2_NEXT:
        page_to(ids.OPEN_FILAMENTVIDEO_3)
    elif widget_id == ids.OPEN_FILAMENTVIDEO_2_ON_OFF:
        actions.open_set_print_filament_target()


def open_filamentvideo_3(page_id, widget_id):
    if widget_id == ids.OPEN_FILAMENTVIDEO_3_NEXT:
        actions.set_extruder_target(0)
        page_to(ids.OPEN_FINISH)
    elif widget_id == ids.OPEN_FILAMENTVIDEO_3_EXTRUDE:
        actions.open_start_extrude()


def open_finish(page_id, widget_id):
    if widget_id == ids.OPEN_FINISH_YES:
        actions.open_more_level_finish()


HANDLERS = {
    ids.OPEN_LANGUAGE: open_language,
    ids.OPEN_POP: open_pop,
    ids.OPEN_VIDEO_1: open_video_1,
    ids.OPEN_VIDEO_2: open_video_2,
    ids.OPEN_WARNING: open_warning,
    ids.OPEN_MOVING: open_moving,
    ids.OPEN_VIDEO_3: open_video_3,
    ids.OPEN_HEATERBED: open_heaterbed,
    ids.OPEN_FILAMENTVIDEO_0: open_filamentvideo,
    ids.OPEN_FILAMENTVIDEO_1: open_filamentvideo,
    ids.OPEN_FILAMENTVIDEO_2: open_filamentvideo_2,
    ids.OPEN_FILAMENTVIDEO_3: open_filamentvideo_3,
    ids.OPEN_FINISH: open_finish,
}
