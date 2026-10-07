"""The file list pages and their pictures, the USB drive."""

import logging
import os
import time

from xindi import state as g
from xindi.moonraker import gcode_files
from xindi.moonraker.gcode_files import output_imgdata
from xindi.moonraker.rpc_requests import json_get_gcode_metadata
from xindi.pages import widgets
from xindi.printer import klipper
from xindi.screen import pageids as ids, pics, thumbnail
from xindi.screen.navigation import page_to
from xindi.screen.transfer import delete_small_jpg
from xindi.util import paths
from xindi.util.cpp import substr, system, to_string

log = logging.getLogger(__name__)


DEFAULT_DIR = "gcodes/"


def file_name_only(path):
    return substr(path, path.rfind("/") + 1)


def name_of(path):
    """File name without the directories"""
    return substr(path, path.rfind("/") + 1)


# entry type of the list -> pictures of its row (released, pressed)
def list_row_pictures():
    return {
        "[c]": (pics.files_item_img, pics.files_tab_local_press),      # the last printed file
        "[d]": (pics.files_item_dir, pics.files_dir_press),
        "[f]": (pics.files_item_img, pics.files_tab_local_press),
        "[n]": (pics.files_tab_usb, pics.files_tab_usb),                # no drive
    }


def nav_button(button, disabled):
    """The page / folder buttons look different when there is nothing to go to."""
    if disabled:
        g.port.picc(button, pics.files_item_img)
        g.port.picc2(button, pics.files_dir_press)
    else:
        g.port.picc(button, pics.files_item_dir)
        g.port.picc2(button, pics.files_tab_local_press)


def queue_list_pictures():
    """CLL refresh the pictures after all the other widgets: the picture thread sends them."""
    for i in range(4):
        g.pictures.have_64_jpg[i] = False
        g.pictures.have_64_png_path[i] = ""
        t = g.files.list_list_show_type[i]
        if t == "[c]" or t == "[f]":
            name = g.files.list_list_show_name[i]
            # NOTE: the original sends <dir>/.thumbs/<name>-112x112_QD.jpg (made only
            # by QIDI's slicer / Moonraker) to the screen; the port takes the
            # thumbnail from the gcode file itself (see thumbnail.py).
            if t == "[c]":
                picture_path = g.files.list_path + "/.cache/" + name
            else:
                picture_path = g.files.list_path + "/" + name
            picture_path = thumbnail.GcodeRef(substr(picture_path, 1))
            log.info("Picture path:%s", picture_path)
            if thumbnail.find(picture_path, 112, "JPEG") is not None:
                g.pictures.have_64_jpg[i] = True
                g.pictures.have_64_png_path[i] = picture_path
        # the picture thread also enables the touch again when there is no picture
        g.pictures.begin_show_64_jpg = True


def refresh_files_list():
    # 4.4.22: the pictures are only sent again when the list changed
    # (file_list_refreshed), the folder and page are kept meanwhile
    if not g.screen.file_list_refreshed:
        delete_small_jpg()
    if detect_disk_2() == 1 and g.screen.file_mode == "USB":
        g.port.txt("empty_msg", "")
    elif detect_disk_2() == 0 and g.screen.file_mode == "USB":
        g.port.txt("empty_msg", "\u7a7a")     # "empty"
    g.port.vis("file1_mark", "0")
    row_pictures = list_row_pictures()
    for i in range(4):
        row = "file" + to_string(i + 1)
        g.port.txt(row + "_name", g.files.list_list_show_name[i])
        g.port.vis("cp" + to_string(i), "0")
        t = g.files.list_list_show_type[i]
        if t in row_pictures:
            g.port.picc(row, row_pictures[t][0])
            g.port.picc2(row, row_pictures[t][1])
        if t == "[c]":
            g.port.vis("file1_mark", "1")

    # 4.4.2 CLL local / USB buttons on the file list page
    if g.screen.file_mode == "Local":
        for tab in ("local_tab", "usb_tab"):
            g.port.picc(tab, pics.files_tab_local)
            g.port.picc2(tab, pics.files_tab_local_press)
    elif g.screen.file_mode == "USB":
        for tab in ("local_tab", "usb_tab"):
            g.port.picc(tab, pics.files_tab_usb)
            g.port.picc2(tab, pics.files_tab_usb_press)
        if detect_disk() == -1:
            g.port.vis("empty_msg", "1")
    nav_button("prev", g.files.list_current_pages == 0)
    nav_button("next", g.files.list_current_pages == g.files.list_pages)
    nav_button("up_dir", g.files.list_folder_layers == 0
                or (g.files.list_folder_layers == 1 and g.screen.file_mode != "Local"))
    if g.screen.file_list_refreshed:
        g.port.tsw("255", "1")      # pictures still in the screen memory: enable touch
    else:
        queue_list_pictures()
        g.screen.file_list_refreshed = True


def refresh_page_files(page_index):
    gcode_files.get_page_files_filelist(g.files.list_root_path + g.files.list_path)
    gcode_files.set_page_files_show_list(page_index)


def get_file_estimated_time(filename):
    g.ep.send(json_get_gcode_metadata(filename))


def clear_cp0_image():
    g.port.cp_close("preview.preview_pic")
    g.port.txt("preview.cp_data", "")
    g.port.txt("preview.cp_pad", "")
    g.screen.show_preview_gimage_completed = False
    g.files.meta_parse_finished = False
    g.files.meta_simage = ""
    g.files.meta_gimage = ""
    # the z-offset is no longer set by xindi (printer_set_babystep() not called)


def is_mounted(path):
    """4.4.22: 1 if path is a mount point, 0 if not, -1 on errors."""
    try:
        return 1 if os.stat("/").st_dev != os.stat(path).st_dev else 0
    except OSError as e:
        log.error("is_mounted %s: %s", path, str(e))
        return -1


def detect_disk_2():
    """4.4.22: is the USB drive mounted (1), not mounted (0), or missing (-1)?"""
    result = is_mounted(paths.gcode_files() + "/sda1")
    if result == 1:
        log.info("%s is mounted", paths.gcode_files() + "/sda1")
    elif result == 0:
        log.info("%s is not mounted", paths.gcode_files() + "/sda1")
    return result


def detect_disk():
    if os.path.exists("/dev/sda"):
        if os.path.exists("/dev/sda1"):
            if not os.path.exists(paths.gcode_files() + "/sda1"):
                system("/usr/bin/systemctl --no-block restart makerbase-automount@sda1.service")
                time.sleep(1)
        return 0
    else:
        return -1


def go_to_file_list():
    # 4.4.22: the folder and page are kept while the list is up to date
    if g.screen.file_mode == "Local":
        page_to(ids.FILE_LIST)
        if not g.screen.file_list_refreshed:
            g.files.list_pages = 0
            g.files.list_current_pages = 0
            g.files.list_folder_layers = 0
            g.files.list_previous_path = ""
            g.files.list_root_path = DEFAULT_DIR
            g.files.list_path = ""
        refresh_page_files(g.files.list_current_pages)
        refresh_files_list()
        klipper.get_object_status()
    else:
        page_to(ids.FILE_LIST)
        if not g.screen.file_list_refreshed:
            g.files.list_pages = 0
            g.files.list_current_pages = 0
            g.files.list_folder_layers = 1
            g.files.list_previous_path = ""
            g.files.list_root_path = DEFAULT_DIR
            g.files.list_path = "/sda1"
        refresh_page_files(g.files.list_current_pages)
        refresh_files_list()
        klipper.get_object_status()
        # the label "Setup Guide" is set by the screen itself (common_set: a timer, the text in the screen language)


def print_log():
    """CLL export the logs to the USB drive"""
    if detect_disk() == -1:
        page_to(ids.PRINT_LOG_F)    # CLL no USB drive: tell the user the export failed
    else:
        system("mkdir " + paths.gcode_files() + "/sda1/QD_Log")
        system("bash -c 'cp " + paths.klipper_logs() + "/klippy.log* " + paths.gcode_files() + "/sda1/QD_Log/'")
        system("bash -c 'cp " + paths.klipper_logs() + "/moonraker.log* " + paths.gcode_files() + "/sda1/QD_Log/'")
        system("bash -c 'cp " + paths.klipper_logs() + "/auto_update.log* " + paths.gcode_files() + "/sda1/QD_Log/'")
        page_to(ids.PRINT_LOG_S)


def send_file_picture(path, pixel, obj):
    """Sends the picture of ``path`` into the picture widget ``obj`` of the current page (the main page
    calls it last_file_pic; the screen answers "invalid variable name" to a widget the page lacks)."""
    g.files.meta_simage = ""
    g.files.meta_gimage = ""
    g.files.meta_parse_finished = False
    output_imgdata(path, pixel)
    data = g.pictures.tjc_data
    if data is None:
        log.error("No converted picture (/home/mks/tjc)")
        g.screen.show_preview_complete = True
        return
    g.files.meta_gimage = data
    g.port.baud(921600)
    time.sleep(0.01)
    g.port.set_baud(921600)
    g.port.cp_close(obj)
    if g.files.meta_gimage != "":
        log.debug("Sending the file picture")
        widgets.send_chunks_cp(obj, g.files.meta_gimage)
    g.port.baud(115200)
    time.sleep(0.01)
    g.port.set_baud(115200)
    g.port.vis(obj, "1")
