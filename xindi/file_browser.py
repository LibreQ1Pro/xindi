"""The gcode file list of the file pages and the metadata of the chosen file."""

import sys

from . import paths
from . import state as g
from . import pageids as ids
from . import ui
from .cpp import (jget, jpath, jstr, jfloat, jint, jsize, jeq, c_int, f32, to_string, substr, find_last_of,
                  json_parse, json_dump)
from .jsonfields import read_fields
from .mks_log import MKSLOG, MKSLOG_RED, cout
from .http_client import send_request


def parse_file_estimated_time(response):
    result = jget(response, "result")
    read_fields(g.files, result, [("meta_estimated_time", "estimated_time", lambda v: c_int(jfloat(v))),
                                  ("meta_filename", "filename", jstr),
                                  ("meta_filament_total", "filament_total", lambda v: f32(jint(v))),
                                  ("meta_object_height", "object_height", jint),
                                  ("meta_filament_name", "filament_name", jstr),
                                  ("meta_filament_type", "filament_type", jstr),
                                  ("meta_filament_weight_total", "filament_weight_total", jfloat),
                                  ("meta_gimage", "gimage", jstr),
                                  ("meta_simage", "simage", jstr)])
    thumbnails = jget(result, "thumbnails")
    for i in range(jsize(thumbnails)):
        thumb = jget(thumbnails, i)
        if jeq(jget(thumb, "width"), 168) or jeq(jget(thumb, "width"), 300):
            g.files.thumbnail_relative_path = jstr(jget(thumb, "relative_path"))
            directory = parent_directory(g.files.meta_filename)
            if directory == "":
                g.files.thumbnail_path = g.files.thumbnail_relative_path
            else:
                g.files.thumbnail_path = directory + "/" + g.files.thumbnail_relative_path
            MKSLOG_RED("Picture path %s", g.files.thumbnail_path)
            break
    g.files.meta_parse_finished = True


def get_page_files_filelist(current_dir):
    """Fetch the file list information"""
    if g.files.list_last_printing_files_dir == current_dir:
        g.files.list_is_last_print_files_dir = True
    else:
        g.files.list_is_last_print_files_dir = False
    g.files.list_dirname_list.clear()
    g.files.list_filename_list.clear()
    g.files.list_dirname_filename_list.clear()
    json_temp = None
    result = None
    # 4.4.2 CLL show the last printed file as the first entry of the first page
    temp_dirname = ""
    temp_filename = ""
    json_files_directory = send_request("localhost", "7125", "server/files/directory?path=gcodes//.cache", "GET")
    if json_files_directory != "" and g.files.list_folder_layers == 0:
        json_temp = json_parse(json_files_directory)
        result = jget(json_temp, "result")
        if 0 < jsize(jget(result, "files")):
            cout(json_dump(jpath(result, "files", 0, "filename")))
            temp_filename = jstr(jpath(result, "files", 0, "filename"))
            if temp_filename.find(".gcode") != -1:
                if temp_filename.find(".") != 0:
                    g.files.list_filename_list.add(temp_filename)
                    first = min(g.files.list_filename_list)
                    g.files.list_dirname_filename_list.add("[c] " + first)
                    g.files.list_filename_list.clear()
    json_files_directory = send_request("localhost", "7125", "server/files/directory?path=" + current_dir, "GET")
    if json_files_directory != "":
        json_temp = json_parse(json_files_directory)
        result = jget(json_temp, "result")

    for i in range(jsize(jget(result, "dirs"))):
        temp_dirname = jstr(jpath(result, "dirs", i, "dirname"))
        if temp_dirname != "System Volume Information" and temp_dirname.find(".") != 0 and temp_dirname != "sda1":
            g.files.list_dirname_list.add(temp_dirname)

    for j in range(jsize(jget(result, "files"))):
        cout(json_dump(jpath(result, "files", j, "filename")))
        temp_filename = jstr(jpath(result, "files", j, "filename"))
        if temp_filename.find(".gcode") != -1:
            if temp_filename.find(".") != 0:
                g.files.list_filename_list.add(temp_filename)

    for name in sorted_std(g.files.list_dirname_list):
        g.files.list_dirname_filename_list.add("[d] " + name)

    for name in sorted_std(g.files.list_filename_list):
        g.files.list_dirname_filename_list.add("[f] " + name)

    count = len(g.files.list_dirname_filename_list)
    if 0 == count % 4:      # CLL the divisor is the number of files on one page
        g.files.list_pages = count // 4 - 1
        if g.files.list_pages <= 0:
            g.files.list_pages = 0
    else:
        g.files.list_pages = count // 4


def sorted_std(strings):
    """Iteration order of std::set<std::string> (byte-wise lexicographic)."""
    from .cpp import s2b
    return sorted(strings, key=s2b)


def set_page_files_show_list(pages):
    g.files.list_list_name[0] = ""
    g.files.list_list_name[1] = ""
    g.files.list_list_name[2] = ""
    g.files.list_list_name[3] = ""

    entries = sorted_std(g.files.list_dirname_filename_list)
    it = 0

    for i in range(pages * 4):
        it += 1
        # NOTE: the original dereferences the iterator even past the end (UB)
        if it < len(entries):
            cout(entries[it])
    for i in range(4):
        if it < len(entries):
            g.files.list_list_name[i] = entries[it]
            it += 1

    # test output
    for j in range(4):
        if g.files.list_list_name[j] != "":
            g.files.list_list_show_type[j] = substr(g.files.list_list_name[j], 0, 3)
            g.files.list_list_show_name[j] = substr(g.files.list_list_name[j], 4)
        else:
            g.files.list_list_show_type[j] = "[n]"
            g.files.list_list_show_name[j] = ""


def get_sub_dir_files_list(button):
    from . import actions, filelist
    # 4.4.2 CLL show the printed file on the first page of the file list
    if "[c]" == g.files.list_list_show_type[button]:
        g.screen.jump_print = False
        g.screen.show_preview_complete = False
        g.screen.cache_clicked = True
        g.files.list_path_stack.append(g.files.list_path)
        g.files.list_print_files_path = g.files.list_path + "/.cache/" + g.files.list_list_show_name[button]
        g.files.list_folder_layers += 1
        filelist.get_file_estimated_time(substr(g.files.list_print_files_path, 1))
        ui.page_to(ids.PREVIEW)
    elif "[d]" == g.files.list_list_show_type[button]:
        g.files.list_path_stack.append(g.files.list_path)
        g.files.list_path = g.files.list_path + "/" + g.files.list_list_show_name[button]
        g.files.list_folder_layers += 1
        ui.page_to(ids.FILE_LIST)
        g.files.list_current_pages = 0
        g.screen.file_list_refreshed = False       # 4.4.22
        filelist.refresh_page_files(g.files.list_current_pages)
        filelist.refresh_files_list()
    elif "[f]" == g.files.list_list_show_type[button]:
        g.screen.jump_print = False
        g.screen.show_preview_complete = False
        g.screen.cache_clicked = False
        g.files.list_path_stack.append(g.files.list_path)
        g.files.list_print_files_path = g.files.list_path + "/" + g.files.list_list_show_name[button]
        g.files.list_folder_layers += 1
        MKSLOG("%s", substr(g.files.list_print_files_path, 1))
        filelist.get_file_estimated_time(substr(g.files.list_print_files_path, 1))
        actions.check_timelapse_state()       # 4.4.22 timelapse switch of the preview page
        ui.page_to(ids.PREVIEW)


def get_parenet_dir_files_list():
    from . import actions, filelist
    # NOTE: std::stack::top() on an empty stack is undefined behaviour in C++
    g.files.list_previous_path = g.files.list_path_stack[-1] if g.files.list_path_stack else ""
    g.files.list_path = g.files.list_previous_path
    if g.screen.page != ids.PREVIEW:
        g.screen.file_list_refreshed = False       # 4.4.22 (back from the preview: keep the list)
        g.files.list_current_pages = 0
    # 4.4.2 CLL local / USB buttons on the file list page
    if filelist.detect_disk() == -1 and g.screen.file_mode == "USB":
        ui.page_to(ids.FILE_LIST)
        g.files.list_pages = 0
        g.files.list_current_pages = 0
        g.files.list_folder_layers = 1
        g.files.list_previous_path = ""
        g.files.list_root_path = "gcodes/"
        g.files.list_path = "/sda1"
        filelist.refresh_page_files(g.files.list_current_pages)
        filelist.refresh_files_list()
        actions.get_object_status()
    elif g.files.list_folder_layers > 0:
        ui.page_to(ids.FILE_LIST)
        g.files.list_folder_layers -= 1
        if g.files.list_folder_layers == 0:
            filelist.refresh_page_files(g.files.list_current_pages)
            filelist.refresh_files_list()
            g.files.list_previous_path = ""
            g.files.list_path = ""
        else:
            filelist.refresh_page_files(g.files.list_current_pages)
            filelist.refresh_files_list()
            if g.files.list_path_stack:
                g.files.list_path_stack.pop()


def parse_file_estimated_time_send(response):
    if jget(response, "estimated_time") is not None:
        g.files.meta_estimated_time = c_int(jfloat(jget(response, "estimated_time")))
    if jget(response, "filename") is not None:
        g.files.meta_filename = jstr(jget(response, "filename"))
    if jget(response, "filament_total") is not None:
        g.files.meta_filament_total = f32(jint(jget(response, "filament_total")))
        MKSLOG_RED("Filament length %f", g.files.meta_filament_total)
    if jget(response, "object_height") is not None:
        g.files.meta_object_height = jint(jget(response, "object_height"))
    if jget(response, "filament_name") is not None:
        g.files.meta_filament_name = jstr(jget(response, "filament_name"))
    if jget(response, "filament_type") is not None:
        g.files.meta_filament_type = jstr(jget(response, "filament_type"))

    if jget(response, "filament_weight_total") is not None:
        g.files.meta_filament_weight_total = jfloat(jget(response, "filament_weight_total"))
    if jget(response, "gimage") is not None:
        g.files.meta_gimage = jstr(jget(response, "gimage"))
        MKSLOG_RED("gimage")
    if jget(response, "simage") is not None:
        g.files.meta_simage = jstr(jget(response, "simage"))
        MKSLOG_RED("simage")
    thumbnails = jpath(response, "result", "thumbnails")
    if thumbnails is not None:
        last = _json_back(thumbnails)
        if last is not None:
            g.files.thumbnail_relative_path = jstr(jget(last, "relative_path"))
            if parent_directory(g.files.meta_filename) == "":
                g.files.thumbnail_path = g.files.thumbnail_relative_path
            else:
                g.files.thumbnail_path = parent_directory(g.files.meta_filename) + "/" + g.files.thumbnail_relative_path
            MKSLOG_RED("Picture path %s", g.files.thumbnail_path)
    else:
        g.files.thumbnail_relative_path = ""
        g.files.thumbnail_path = ""
    g.files.meta_parse_finished = True


def _json_back(value):
    """json::back(): last element of an array / object, the value itself otherwise."""
    if isinstance(value, list):
        return value[-1] if value else None
    if isinstance(value, dict):
        if not value:
            return None
        return value[sorted(value)[-1]]
    return value


def parent_directory(path):
    found = find_last_of(path, "/\\")
    if found != -1:
        return substr(path, 0, found)
    else:
        return ""   # no separator: root directory


def output_imgdata(thumbpath, size):
    """Converts a thumbnail into the screen's ColPic text format.

    The original runs ``python3 /home/mks/colpic.py "<path>" /home/mks/tjc <size>``
    which uses /home/mks/libColPic.so; both are re-implemented in colpic.py of
    this package and called directly.  The result is kept in memory
    (``g.pictures.tjc_data``) instead of the file /home/mks/tjc.  A failed conversion
    leaves None there (the original keeps the previous file and shows the
    picture of another file).
    """
    from . import colpic, thumbnail
    g.pictures.tjc_data = None
    if isinstance(thumbpath, thumbnail.GcodeRef):
        # Python only: picture from the thumbnails inside the gcode file
        cout("Converting the thumbnail of " + thumbpath + " (" + to_string(size) + ")")
        try:
            g.pictures.tjc_data = thumbnail.colpic(thumbpath, size)
        except Exception as e:
            sys.stderr.write("gene4: %s: %s\n" % (type(e).__name__, e))
        return 0
    if size != 176:
        path = paths.gcode_files() + "/" + thumbpath
    else:
        path = thumbpath
    temp = "python3 /home/mks/colpic.py \"" + path + "\" /home/mks/tjc " + to_string(size)
    cout(temp)
    try:
        g.pictures.tjc_data = colpic.encode_picture(path, size)
    except Exception as e:
        # the original script dies with a traceback (the old output stays)
        sys.stderr.write("gene4: %s: %s\n" % (type(e).__name__, e))
    return 0


