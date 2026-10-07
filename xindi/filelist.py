"""The file list pages and their pictures, the USB drive."""

import os

from . import paths
from . import state as g
from . import pics
from . import ui
from . import mks_file
from . import thumbnail
from .ui import page_to
from .cpp import to_string, substr, access, system, sleep, usleep
from .mks_log import MKSLOG, MKSLOG_RED, cout, cerr
from .send_msg import (send_cmd_txt, send_cmd_picc, send_cmd_picc2, send_cmd_vis, send_cmd_cp_close,
                       send_cmd_baud, send_cmd_tsw)
from .MakerbaseSerial import set_option
from .MoonrakerAPI import json_get_gcode_metadata, json_file_delete
from .mks_file import output_imgdata
from .send_jpg import delete_small_jpg
from . import actions, pages


DEFAULT_DIR = "gcodes/"


def _file_name_only(path):
    return substr(path, path.rfind("/") + 1)


def _name_of(path):
    """File name without the directories"""
    return substr(path, path.rfind("/") + 1)


def _stem_of(path):
    """``path.substr(rfind("/") + 1, rfind(".") - (rfind("/") + 1))``"""
    start = path.rfind("/") + 1
    return substr(path, start, path.rfind(".") - start)


def refresh_files_list():
    # 4.4.22: the pictures are only sent again when the list changed
    # (file_list_refreshed), the folder and page are kept meanwhile
    if g.screen.file_list_refreshed == False:
        delete_small_jpg()
    if detect_disk_2() == 1 and g.screen.file_mode == "USB":
        send_cmd_txt(g.tty_fd, "empty_msg", "")
    elif detect_disk_2() == 0 and g.screen.file_mode == "USB":
        send_cmd_txt(g.tty_fd, "empty_msg", "\u7a7a")     # "empty"
    send_cmd_vis(g.tty_fd, "file1_mark", "0")
    for i in range(4):
        send_cmd_txt(g.tty_fd, "file" + to_string(i + 1) + "_name", g.files.list_list_show_name[i])
        send_cmd_vis(g.tty_fd, "cp" + to_string(i), "0")
        t = g.files.list_list_show_type[i]
        if t == "[c]":
            send_cmd_picc(g.tty_fd, "file" + to_string(i + 1), pics.files_item_img)
            send_cmd_picc2(g.tty_fd, "file" + to_string(i + 1), pics.files_tab_local_press)
            send_cmd_vis(g.tty_fd, "file1_mark", "1")
        elif t == "[d]":
            send_cmd_picc(g.tty_fd, "file" + to_string(i + 1), pics.files_item_dir)
            send_cmd_picc2(g.tty_fd, "file" + to_string(i + 1), pics.files_dir_press)
        elif t == "[f]":
            send_cmd_picc(g.tty_fd, "file" + to_string(i + 1), pics.files_item_img)
            send_cmd_picc2(g.tty_fd, "file" + to_string(i + 1), pics.files_tab_local_press)
        elif t == "[n]":
            send_cmd_picc(g.tty_fd, "file" + to_string(i + 1), pics.files_tab_usb)
            send_cmd_picc2(g.tty_fd, "file" + to_string(i + 1), pics.files_tab_usb)

    # 4.4.2 CLL local / USB buttons on the file list page
    if g.screen.file_mode == "Local":
        send_cmd_picc(g.tty_fd, "local_tab", pics.files_tab_local)
        send_cmd_picc2(g.tty_fd, "local_tab", pics.files_tab_local_press)
        send_cmd_picc(g.tty_fd, "usb_tab", pics.files_tab_local)
        send_cmd_picc2(g.tty_fd, "usb_tab", pics.files_tab_local_press)
    elif g.screen.file_mode == "USB":
        send_cmd_picc(g.tty_fd, "local_tab", pics.files_tab_usb)
        send_cmd_picc2(g.tty_fd, "local_tab", pics.files_tab_usb_press)
        send_cmd_picc(g.tty_fd, "usb_tab", pics.files_tab_usb)
        send_cmd_picc2(g.tty_fd, "usb_tab", pics.files_tab_usb_press)
        if detect_disk() == -1:
            send_cmd_vis(g.tty_fd, "empty_msg", "1")
    if g.files.list_current_pages == 0:
        send_cmd_picc(g.tty_fd, "prev", pics.files_item_img)
        send_cmd_picc2(g.tty_fd, "prev", pics.files_dir_press)
    else:
        send_cmd_picc(g.tty_fd, "prev", pics.files_item_dir)
        send_cmd_picc2(g.tty_fd, "prev", pics.files_tab_local_press)
    if g.files.list_current_pages == g.files.list_pages:
        send_cmd_picc(g.tty_fd, "next", pics.files_item_img)
        send_cmd_picc2(g.tty_fd, "next", pics.files_dir_press)
    else:
        send_cmd_picc(g.tty_fd, "next", pics.files_item_dir)
        send_cmd_picc2(g.tty_fd, "next", pics.files_tab_local_press)
    if g.files.list_folder_layers == 0 or (g.files.list_folder_layers == 1 and g.screen.file_mode != "Local"):
        send_cmd_picc(g.tty_fd, "up_dir", pics.files_item_img)
        send_cmd_picc2(g.tty_fd, "up_dir", pics.files_dir_press)
    else:
        send_cmd_picc(g.tty_fd, "up_dir", pics.files_item_dir)
        send_cmd_picc2(g.tty_fd, "up_dir", pics.files_tab_local_press)
    if g.screen.file_list_refreshed == True:
        send_cmd_tsw(g.tty_fd, "255", "1")      # pictures still in the screen memory: enable touch
    else:
        for i in range(4):      # CLL refresh the pictures after all the other widgets
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
                MKSLOG_RED("Picture path:%s", picture_path)
                if thumbnail.find(picture_path, 112, "JPEG") is not None:
                    g.pictures.have_64_jpg[i] = True
                    g.pictures.have_64_png_path[i] = picture_path
            # the picture thread also enables the touch again when there is no picture
            g.pictures.begin_show_64_jpg = True
        g.screen.file_list_refreshed = True


def refresh_page_files(pages):
    mks_file.get_page_files_filelist(g.files.list_root_path + g.files.list_path)
    mks_file.set_page_files_show_list(pages)


def get_file_estimated_time(filename):
    g.ep.Send(json_get_gcode_metadata(filename))


def delete_file(filepath):
    import time
    g.files.filelist_changed = False
    g.ep.Send(json_file_delete(filepath))
    while not g.files.filelist_changed:
        time.sleep(0)


def clear_cp0_image():
    send_cmd_cp_close(g.tty_fd, "preview.preview_pic")
    send_cmd_txt(g.tty_fd, "preview.cp_data", "")
    send_cmd_txt(g.tty_fd, "preview.cp_pad", "")
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
        cerr("is_mounted ", path, ": ", str(e), "\n")
        return -1


def detect_disk_2():
    """4.4.22: is the USB drive mounted (1), not mounted (0), or missing (-1)?"""
    result = is_mounted(paths.gcode_files() + "/sda1")
    if result == 1:
        MKSLOG("%s is mounted", paths.gcode_files() + "/sda1")
    elif result == 0:
        MKSLOG("%s is not mounted", paths.gcode_files() + "/sda1")
    return result


def detect_disk():
    if access("/dev/sda") == 0:
        if access("/dev/sda1") == 0:
            if access(paths.gcode_files() + "/sda1") != 0:
                system("/usr/bin/systemctl --no-block restart makerbase-automount@sda1.service")
                sleep(1)
        return 0
    else:
        return -1


def refresh_files_list_2():
    """4.4.2 CLL refresh of the file list page"""
    if g.screen.file_mode == "USB":
        if detect_disk() == -1:
            g.screen.file_mode = "NULL"
            page_to(ui.TJC_PAGE_FILE_LIST)
            g.files.list_pages = 0
            g.files.list_current_pages = 0
            g.files.list_folder_layers = 1
            g.files.list_previous_path = ""
            g.files.list_root_path = "gcodes/"
            g.files.list_path = "/sda1"
            refresh_page_files(g.files.list_current_pages)
            refresh_files_list()
            actions.get_object_status()
    elif g.screen.file_mode == "NULL":
        if detect_disk() == 0:
            sleep(1)
            g.screen.file_mode = "USB"
            page_to(ui.TJC_PAGE_FILE_LIST)
            g.files.list_pages = 0
            g.files.list_current_pages = 0
            g.files.list_folder_layers = 1
            g.files.list_previous_path = ""
            g.files.list_root_path = "gcodes/"
            g.files.list_path = "/sda1"
            refresh_page_files(g.files.list_current_pages)
            refresh_files_list()
            actions.get_object_status()


def go_to_file_list():
    # 4.4.22: the folder and page are kept while the list is up to date
    if g.screen.file_mode == "Local":
        page_to(ui.TJC_PAGE_FILE_LIST)
        if g.screen.file_list_refreshed == False:
            g.files.list_pages = 0
            g.files.list_current_pages = 0
            g.files.list_folder_layers = 0
            g.files.list_previous_path = ""
            g.files.list_root_path = DEFAULT_DIR
            g.files.list_path = ""
        refresh_page_files(g.files.list_current_pages)
        refresh_files_list()
        actions.get_object_status()
    else:
        page_to(ui.TJC_PAGE_FILE_LIST)
        if g.screen.file_list_refreshed == False:
            g.files.list_pages = 0
            g.files.list_current_pages = 0
            g.files.list_folder_layers = 1
            g.files.list_previous_path = ""
            g.files.list_root_path = DEFAULT_DIR
            g.files.list_path = "/sda1"
        refresh_page_files(g.files.list_current_pages)
        refresh_files_list()
        actions.get_object_status()
        # the label "Setup Guide" is set by the screen itself (common_set: a timer, the text in the screen language)


def print_log():
    """CLL export the logs to the USB drive"""
    if detect_disk() == -1:
        page_to(ui.TJC_PAGE_PRINT_LOG_F)    # CLL no USB drive: tell the user the export failed
    else:
        system("mkdir " + paths.gcode_files() + "/sda1/QD_Log")
        system("bash -c 'cp " + paths.klipper_logs() + "/klippy.log* " + paths.gcode_files() + "/sda1/QD_Log/'")
        system("bash -c 'cp " + paths.klipper_logs() + "/moonraker.log* " + paths.gcode_files() + "/sda1/QD_Log/'")
        system("bash -c 'cp " + paths.klipper_logs() + "/auto_update.log* " + paths.gcode_files() + "/sda1/QD_Log/'")
        page_to(ui.TJC_PAGE_PRINT_LOG_S)


def send_file_picture(path, pixel, obj):
    """Sends the picture of ``path`` into the picture widget ``obj`` of the current page (the main page
    calls it last_file_pic; the screen answers "invalid variable name" to a widget the page lacks)."""
    g.files.meta_simage = ""
    g.files.meta_gimage = ""
    g.files.meta_parse_finished = False
    output_imgdata(path, pixel)
    data = g.pictures.tjc_data
    if data is None:
        cerr("No converted picture (/home/mks/tjc)", "\n")
        g.screen.show_preview_complete = True
        return
    g.files.meta_gimage = data
    send_cmd_baud(g.tty_fd, 921600)
    usleep(10000)
    set_option(g.tty_fd, 921600, 8, 'N', 1)
    send_cmd_cp_close(g.tty_fd, obj)
    if g.files.meta_gimage != "":
        cout("Sending the file picture")
        pages._send_chunks_cp(obj, g.files.meta_gimage)
    send_cmd_baud(g.tty_fd, 115200)
    usleep(10000)
    set_option(g.tty_fd, 115200, 8, 'N', 1)
    send_cmd_vis(g.tty_fd, obj, "1")


def send_file_picture_2(path, size, i):
    g.pictures.input_path = path
    g.pictures.input_size = size
    g.pictures.begin_show_64_jpg = True


def send_file_picture_3(inputPath, size, i):
    return 0
