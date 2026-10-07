"""The preview page of a file (details, thumbnail, pop-ups)."""

import logging
import time

from xindi import state as g
from xindi.moonraker.gcode_files import output_imgdata
from xindi.pages import file_list
from xindi.pages.widgets import cut_after_point, fast_screen_link, send_chunks_cp, send_chunks_txt, two_state_button
from xindi.printer import calibration, job
from xindi.screen import pageids as ids, pics, thumbnail
from xindi.screen.navigation import page_to
from xindi.util.cpp import f32, substr, to_string

log = logging.getLogger(__name__)


def preview_details():
    # 4.4.2 CLL only the file name is shown on the preview page
    g.port.txt("err_msg", file_list.file_name_only(g.files.meta_filename))
    if g.files.meta_estimated_time:
        g.port.txt("est_time", job.show_time(g.files.meta_estimated_time))
    else:
        g.port.txt("est_time", "-")

    if g.files.meta_filament_weight_total:
        temp = to_string(g.files.meta_filament_weight_total)
        g.port.txt("fil_weight", cut_after_point(temp, 2) + "g")
    else:
        g.port.txt("fil_weight", "-")

    if g.files.meta_filament_total:
        temp = to_string(f32(g.files.meta_filament_total / 1000))
        g.port.txt("fil_length", cut_after_point(temp, 2) + "m")
    else:
        g.port.txt("fil_length", "-")

    if g.files.meta_filament_type != "":
        g.port.txt("fil_type", g.files.meta_filament_type)
    elif g.files.meta_filament_name != "":
        g.port.txt("fil_type", g.files.meta_filament_name)
    else:
        g.port.txt("fil_type", "-")


def preview_picture_ref():
    """The gcode file with the thumbnail of the file, or "" when there is none.

    NOTE: the original looks for <dir>/.thumbs/<name>-160x160.png, then .jpg, made by QIDI's Moonraker; the port
    reads the thumbnail from the gcode file itself (see thumbnail.py).  For a print that was just started the
    original only looks at the .cache copy of the file.
    """
    if g.screen.jump_print:
        candidates = ["/.cache/" + file_list.name_of(g.klippy.print_stats_filename),
                      "/" + g.klippy.print_stats_filename]
    elif g.screen.cache_clicked:
        candidates = [job.stack_top(g.files.list_path_stack) + "/.cache/" + file_list.name_of(g.files.meta_filename)]
        g.screen.cache_clicked = False
    else:
        candidates = [job.stack_top(g.files.list_path_stack) + "/" + file_list.name_of(g.files.meta_filename)]
    for candidate in candidates:
        candidate = substr(candidate, 1)
        log.info("picture_path:%s", candidate)
        if thumbnail.find(candidate, 160, "PNG") is not None:
            return thumbnail.GcodeRef(candidate)
    return ""


def send_preview_pictures(picture_path):
    """Send the small and the big picture to the screen; False when the picture could not be converted."""
    # small picture
    output_imgdata(picture_path, 160)
    data = g.pictures.tjc_data
    if data is None:
        log.error("No converted picture (/home/mks/tjc)")
        return False
    g.files.meta_simage = data
    g.port.txt("preview.cp_data", "")
    g.port.txt("preview.cp_pad", "")
    if g.files.meta_simage != "":
        with fast_screen_link():
            log.debug("Sending the small picture")
            send_chunks_txt(g.files.meta_simage)

    # big picture
    if not g.screen.jump_print:
        data = g.pictures.tjc_data
        if data is None:
            log.error("No converted picture (/home/mks/tjc)")
            return False
        g.files.meta_gimage = data
        with fast_screen_link():
            g.port.cp_close("preview.preview_pic")
            if g.files.meta_gimage != "":
                log.debug("Sending the big picture")
                send_chunks_cp("preview_pic", g.files.meta_gimage)
        calibration.bed_leveling_switch(True)
    return True


def preview():
    # 4.4.22: pictures of the 4.4.24 screen, timelapse switch b3
    two_state_button("level_btn", g.screen.bed_leveling,
                      pics.preview_chk_on, pics.preview_chk_off, pics.preview_press_on, pics.preview_press_off)
    two_state_button("timelapse_btn", g.screen.timelapse_enabled,
                      pics.preview_chk_on, pics.preview_chk_off, pics.preview_press_on, pics.preview_press_off)
    if not g.files.meta_parse_finished or g.screen.show_preview_complete:
        return

    preview_details()
    picture_path = preview_picture_ref()
    log.debug("Picture path:%s", picture_path)
    if picture_path != "" and not g.screen.show_preview_gimage_completed:
        if not send_preview_pictures(picture_path):
            g.screen.show_preview_complete = True
            return
        g.screen.show_preview_gimage_completed = True

    g.port.vis("preview_pic", "1" if g.screen.show_preview_gimage_completed else "0")

    g.screen.show_preview_complete = True
    if g.screen.jump_print:
        job.check_filament_type()
        g.screen.jump_print = False


def clear_preview():
    g.files.meta_filename = ""
    g.files.meta_estimated_time = 0
    g.files.meta_filament_weight_total = 0.0
    g.files.meta_filament_name = ""
    g.files.meta_filament_type = ""
    g.files.meta_simage = ""
    g.files.meta_gimage = ""


def preview_pop():
    # 4.4.2 support mates and hall filament width sensors
    if not g.klippy.filament_detected:
        time.sleep(1)
        job.set_print_pause()
        page_to(ids.PRINT_NO_FILAMENT)
    if g.klippy.print_stats_state == "standby":
        page_to(ids.PRINT_STOPPING)
    if g.klippy.print_stats_state == "error":
        page_to(ids.GCODE_ERROR)
        job.cancel_print()
        job.clear_previous_data()
        g.port.txt("msg", "G-code error: " + g.screen.error_message)
