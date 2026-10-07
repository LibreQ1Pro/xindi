"""Port of src/mks_file.cpp - gcode file list and metadata handling."""

import sys

from . import paths
from . import state as g
from . import ui
from .cpp import (jget, jpath, jstr, jfloat, jint, jsize, jeq, c_int, f32, to_string, substr,
                  find_last_of, access, system, json_parse, json_dump)
from .mks_log import MKSLOG, MKSLOG_RED, cout
from .KlippyRest import send_request


def _event():
    from . import event
    return event


def parse_file_estimated_time(response):
    result = jget(response, "result")
    if jget(result, "estimated_time") is not None:
        g.file_metadata_estimated_time = c_int(jfloat(jget(result, "estimated_time")))
    if jget(result, "filename") is not None:
        g.file_metadata_filename = jstr(jget(result, "filename"))
    if jget(result, "filament_total") is not None:
        g.file_metadata_filament_total = f32(jint(jget(result, "filament_total")))
        MKSLOG_RED("Filament length %f", g.file_metadata_filament_total)
    if jget(result, "object_height") is not None:
        g.file_metadata_object_height = jint(jget(result, "object_height"))
    if jget(result, "filament_name") is not None:
        g.file_metadata_filament_name = jstr(jget(result, "filament_name"))
    if jget(result, "filament_type") is not None:
        g.file_metadata_filament_type = jstr(jget(result, "filament_type"))
    if jget(result, "filament_weight_total") is not None:
        g.file_metadata_filament_weight_total = jfloat(jget(result, "filament_weight_total"))
    if jget(result, "gimage") is not None:
        g.file_metadata_gimage = jstr(jget(result, "gimage"))
    if jget(result, "simage") is not None:
        g.file_metadata_simage = jstr(jget(result, "simage"))
    thumbnails = jget(result, "thumbnails")
    if thumbnails is not None:
        i = 0
        while jget(thumbnails, i) is not None:
            thumb = jget(thumbnails, i)
            width = jget(thumb, "width")
            if jeq(width, 168) or jeq(width, 300):
                g.thumbnail_relative_path = jstr(jget(thumb, "relative_path"))
                if getParentDirectory(g.file_metadata_filename) == "":
                    g.thumbnail_path = g.thumbnail_relative_path
                else:
                    g.thumbnail_path = getParentDirectory(g.file_metadata_filename) + "/" + g.thumbnail_relative_path
                MKSLOG_RED("Picture path %s", g.thumbnail_path)
                break
            if jget(thumbnails, i) is None:
                g.thumbnail_relative_path = ""
                g.thumbnail_path = ""
            i += 1
    g.mks_file_parse_finished = True


def parse_server_files_list(result):
    g.server_files_list.clear()
    path_temp = ""
    for i in range(jsize(result)):
        path_temp = jstr(jpath(result, i, "path"))
        g.server_files_list.add(path_temp)


def parse_server_files_get_directory(result):
    g.server_files_get_directroy.clear()
    g.server_files_list.clear()

    dirname_temp = ""
    filename_temp = ""

    for i in range(jsize(jget(result, "dirs"))):
        cout(json_dump(jpath(result, "dirs", i, "dirname")))
        dirname_temp = jstr(jpath(result, "dirs", i, "dirname"))
        g.server_files_list.add(filename_temp)
    for j in range(jsize(jget(result, "files"))):
        cout(json_dump(jpath(result, "files", j, "filename")))
        filename_temp = jstr(jpath(result, "files", j, "filename"))
        g.server_files_list.add(filename_temp)


def parse_server_files_metadata(result):
    pass


def parse_create_directory(result):
    cout("path: ", json_dump(jpath(result, "item", "path")))
    cout("root: ", json_dump(jpath(result, "item", "root")))
    cout("action: ", json_dump(jget(result, "action")))


def parse_delete_directory(result):
    cout("path: ", json_dump(jpath(result, "item", "path")))
    cout("root: ", json_dump(jpath(result, "item", "root")))


def parse_move_a_file_or_directory(result):
    cout("item: ", json_dump(jget(result, "item")))
    cout("source_item", json_dump(jget(result, "source_item")))
    cout("action: ", json_dump(jget(result, "action")))


def parse_copy_a_file_or_directory(result):
    cout("root: ", json_dump(jpath(result, "item", "root")))
    cout("path: ", json_dump(jpath(result, "item", "path")))
    cout("action: ", json_dump(jget(result, "action")))


def parse_file_delete(result):
    cout("path: ", json_dump(jpath(result, "item", "path")))
    cout("root: ", json_dump(jpath(result, "item", "root")))
    cout("action: ", json_dump(jget(result, "action")))


def get_page_files_filelist(current_dir):
    """Fetch the file list information"""
    if g.page_files_last_printing_files_dir == current_dir:
        g.page_files_is_last_print_files_dir = True
    else:
        g.page_files_is_last_print_files_dir = False
    g.page_files_dirname_list.clear()
    g.page_files_filename_list.clear()
    g.page_files_dirname_filename_list.clear()
    json_temp = None
    result = None
    # 4.4.2 CLL show the last printed file as the first entry of the first page
    temp_dirname = ""
    temp_filename = ""
    json_files_directory = send_request("localhost", "7125", "server/files/directory?path=gcodes//.cache", "GET")
    if json_files_directory != "" and g.page_files_folder_layers == 0:
        json_temp = json_parse(json_files_directory)
        result = jget(json_temp, "result")
        if 0 < jsize(jget(result, "files")):
            cout(json_dump(jpath(result, "files", 0, "filename")))
            temp_filename = jstr(jpath(result, "files", 0, "filename"))
            if temp_filename.find(".gcode") != -1:
                if temp_filename.find(".") != 0:
                    g.page_files_filename_list.add(temp_filename)
                    first = min(g.page_files_filename_list)
                    g.page_files_dirname_filename_list.add("[c] " + first)
                    g.page_files_filename_list.clear()
    json_files_directory = send_request("localhost", "7125", "server/files/directory?path=" + current_dir, "GET")
    if json_files_directory != "":
        json_temp = json_parse(json_files_directory)
        result = jget(json_temp, "result")

    for i in range(jsize(jget(result, "dirs"))):
        temp_dirname = jstr(jpath(result, "dirs", i, "dirname"))
        if temp_dirname != "System Volume Information" and temp_dirname.find(".") != 0 and temp_dirname != "sda1":
            g.page_files_dirname_list.add(temp_dirname)

    for j in range(jsize(jget(result, "files"))):
        cout(json_dump(jpath(result, "files", j, "filename")))
        temp_filename = jstr(jpath(result, "files", j, "filename"))
        if temp_filename.find(".gcode") != -1:
            if temp_filename.find(".") != 0:
                g.page_files_filename_list.add(temp_filename)

    for name in sorted_std(g.page_files_dirname_list):
        g.page_files_dirname_filename_list.add("[d] " + name)

    for name in sorted_std(g.page_files_filename_list):
        g.page_files_dirname_filename_list.add("[f] " + name)

    count = len(g.page_files_dirname_filename_list)
    if 0 == count % 4:      # CLL the divisor is the number of files on one page
        g.page_files_pages = count // 4 - 1
        if g.page_files_pages <= 0:
            g.page_files_pages = 0
    else:
        g.page_files_pages = count // 4


def sorted_std(strings):
    """Iteration order of std::set<std::string> (byte-wise lexicographic)."""
    from .cpp import s2b
    return sorted(strings, key=s2b)


def set_page_files_show_list(pages):
    g.page_files_list_name[0] = ""
    g.page_files_list_name[1] = ""
    g.page_files_list_name[2] = ""
    g.page_files_list_name[3] = ""

    entries = sorted_std(g.page_files_dirname_filename_list)
    it = 0

    for i in range(pages * 4):
        it += 1
        # NOTE: the original dereferences the iterator even past the end (UB)
        if it < len(entries):
            cout(entries[it])
    for i in range(4):
        if it < len(entries):
            g.page_files_list_name[i] = entries[it]
            it += 1

    # test output
    for j in range(4):
        if g.page_files_list_name[j] != "":
            g.page_files_list_show_type[j] = substr(g.page_files_list_name[j], 0, 3)
            g.page_files_list_show_name[j] = substr(g.page_files_list_name[j], 4)
        else:
            g.page_files_list_show_type[j] = "[n]"
            g.page_files_list_show_name[j] = ""


def get_sub_dir_files_list(button):
    event = _event()
    # 4.4.2 CLL show the printed file on the first page of the file list
    if "[c]" == g.page_files_list_show_type[button]:
        g.jump_to_print = False
        g.show_preview_complete = False
        g.cache_clicked = True
        g.page_files_path_stack.append(g.page_files_path)
        g.page_files_print_files_path = g.page_files_path + "/.cache/" + g.page_files_list_show_name[button]
        g.page_files_folder_layers += 1
        event.get_file_estimated_time(substr(g.page_files_print_files_path, 1))
        ui.page_to(ui.TJC_PAGE_PREVIEW)
    elif "[d]" == g.page_files_list_show_type[button]:
        g.page_files_path_stack.append(g.page_files_path)
        g.page_files_path = g.page_files_path + "/" + g.page_files_list_show_name[button]
        g.page_files_folder_layers += 1
        ui.page_to(ui.TJC_PAGE_FILE_LIST)
        g.page_files_current_pages = 0
        g.file_list_refreshed = False       # 4.4.22
        event.refresh_page_files(g.page_files_current_pages)
        event.refresh_page_files_list()
    elif "[f]" == g.page_files_list_show_type[button]:
        g.jump_to_print = False
        g.show_preview_complete = False
        g.cache_clicked = False
        g.page_files_path_stack.append(g.page_files_path)
        g.page_files_print_files_path = g.page_files_path + "/" + g.page_files_list_show_name[button]
        g.page_files_folder_layers += 1
        MKSLOG("%s", substr(g.page_files_print_files_path, 1))
        event.get_file_estimated_time(substr(g.page_files_print_files_path, 1))
        event.check_timelapse_state()       # 4.4.22 timelapse switch of the preview page
        ui.page_to(ui.TJC_PAGE_PREVIEW)


def get_parenet_dir_files_list():
    event = _event()
    # NOTE: std::stack::top() on an empty stack is undefined behaviour in C++
    g.page_files_previous_path = g.page_files_path_stack[-1] if g.page_files_path_stack else ""
    g.page_files_path = g.page_files_previous_path
    if g.current_page_id != ui.TJC_PAGE_PREVIEW:
        g.file_list_refreshed = False       # 4.4.22 (back from the preview: keep the list)
        g.page_files_current_pages = 0
    # 4.4.2 CLL local / USB buttons on the file list page
    if event.detect_disk() == -1 and g.file_mode == "USB":
        ui.page_to(ui.TJC_PAGE_FILE_LIST)
        g.page_files_pages = 0
        g.page_files_current_pages = 0
        g.page_files_folder_layers = 1
        g.page_files_previous_path = ""
        g.page_files_root_path = "gcodes/"
        g.page_files_path = "/sda1"
        event.refresh_page_files(g.page_files_current_pages)
        event.refresh_page_files_list()
        event.get_object_status()
    elif g.page_files_folder_layers > 0:
        ui.page_to(ui.TJC_PAGE_FILE_LIST)
        g.page_files_folder_layers -= 1
        if g.page_files_folder_layers == 0:
            event.refresh_page_files(g.page_files_current_pages)
            event.refresh_page_files_list()
            g.page_files_previous_path = ""
            g.page_files_path = ""
        else:
            event.refresh_page_files(g.page_files_current_pages)
            event.refresh_page_files_list()
            if g.page_files_path_stack:
                g.page_files_path_stack.pop()


def parse_file_estimated_time_send(response):
    if jget(response, "estimated_time") is not None:
        g.file_metadata_estimated_time = c_int(jfloat(jget(response, "estimated_time")))
    if jget(response, "filename") is not None:
        g.file_metadata_filename = jstr(jget(response, "filename"))
    if jget(response, "filament_total") is not None:
        g.file_metadata_filament_total = f32(jint(jget(response, "filament_total")))
        MKSLOG_RED("Filament length %f", g.file_metadata_filament_total)
    if jget(response, "object_height") is not None:
        g.file_metadata_object_height = jint(jget(response, "object_height"))
    if jget(response, "filament_name") is not None:
        g.file_metadata_filament_name = jstr(jget(response, "filament_name"))
    if jget(response, "filament_type") is not None:
        g.file_metadata_filament_type = jstr(jget(response, "filament_type"))

    if jget(response, "filament_weight_total") is not None:
        g.file_metadata_filament_weight_total = jfloat(jget(response, "filament_weight_total"))
    if jget(response, "gimage") is not None:
        g.file_metadata_gimage = jstr(jget(response, "gimage"))
        MKSLOG_RED("gimage")
    if jget(response, "simage") is not None:
        g.file_metadata_simage = jstr(jget(response, "simage"))
        MKSLOG_RED("simage")
    thumbnails = jpath(response, "result", "thumbnails")
    if thumbnails is not None:
        last = _json_back(thumbnails)
        if last is not None:
            g.thumbnail_relative_path = jstr(jget(last, "relative_path"))
            if getParentDirectory(g.file_metadata_filename) == "":
                g.thumbnail_path = g.thumbnail_relative_path
            else:
                g.thumbnail_path = getParentDirectory(g.file_metadata_filename) + "/" + g.thumbnail_relative_path
            MKSLOG_RED("Picture path %s", g.thumbnail_path)
    else:
        g.thumbnail_relative_path = ""
        g.thumbnail_path = ""
    g.mks_file_parse_finished = True


def _json_back(value):
    """json::back(): last element of an array / object, the value itself otherwise."""
    if isinstance(value, list):
        return value[-1] if value else None
    if isinstance(value, dict):
        if not value:
            return None
        return value[sorted(value)[-1]]
    return value


def getParentDirectory(path):
    found = find_last_of(path, "/\\")
    if found != -1:
        return substr(path, 0, found)
    else:
        return ""   # no separator: root directory


def output_imgdata(thumbpath, size):
    """Converts a thumbnail into the screen's ColPic text format.

    The original runs ``python3 /home/mks/gene4.py "<path>" /home/mks/tjc <size>``
    which uses /home/mks/libColPic.so; both are re-implemented in gene4.py of
    this package and called directly.  The result is kept in memory
    (``g.tjc_data``) instead of the file /home/mks/tjc.  A failed conversion
    leaves None there (the original keeps the previous file and shows the
    picture of another file).
    """
    from . import gene4, thumbnail
    g.tjc_data = None
    if isinstance(thumbpath, thumbnail.GcodeRef):
        # Python only: picture from the thumbnails inside the gcode file
        cout("Converting the thumbnail of " + thumbpath + " (" + to_string(size) + ")")
        try:
            g.tjc_data = thumbnail.colpic(thumbpath, size)
        except Exception as e:
            sys.stderr.write("gene4: %s: %s\n" % (type(e).__name__, e))
        return 0
    if size != 176:
        path = paths.gcode_files() + "/" + thumbpath
    else:
        path = thumbpath
    temp = "python3 /home/mks/gene4.py \"" + path + "\" /home/mks/tjc " + to_string(size)
    cout(temp)
    try:
        g.tjc_data = gene4.encode_picture(path, size)
    except Exception as e:
        # the original script dies with a traceback (the old output stays)
        sys.stderr.write("gene4: %s: %s\n" % (type(e).__name__, e))
    return 0


def output_jpg(thumbpath, size):
    """Unused in the program - /home/mks/gene5.py does not exist on the printer."""
    path = paths.gcode_files() + "/" + thumbpath
    path2 = path + ".jpg"
    temp = "python3 /home/mks/gene5.py \"" + path + "\" \"" + path2 + "\" " + to_string(size)
    cout(temp)
    if access(path2) == -1:
        system(temp)
    return 0


def extractFileName(filePath):
    """Extract the file name from a path"""
    lastSlash = find_last_of(filePath, "/\\")
    if lastSlash != -1:
        return substr(filePath, lastSlash + 1)
    return filePath
