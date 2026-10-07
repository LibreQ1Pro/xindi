"""Clicks on the main page, the file list, the preview and the pages of a print. Each function gets the page id and the widget id the screen sent; HANDLERS maps pages to them."""

import logging

from .. import state as g
from .. import actions, filelist, file_browser, pages
from .. import pageids as ids
from ..cpp import sleep
from ..ui import page_to

log = logging.getLogger(__name__)


def main(page_id, widget_id):
    if widget_id == ids.ALL_TO_MAIN:
        pass
    elif widget_id == ids.ALL_TO_FILE_LIST:
        filelist.go_to_file_list()
    elif widget_id == ids.ALL_TO_ADJUST:
        actions.go_to_adjust()
    elif widget_id == ids.ALL_TO_SETTING:
        actions.go_to_setting()
    elif widget_id == ids.MAIN_CASELIGHT:
        actions.led_on_off()
    elif widget_id == ids.MAIN_BEEP:
        actions.beep_on_off()
    elif widget_id == ids.MAIN_STOP:
        actions.motors_off()
    elif widget_id in (ids.MAIN_SET_TEMP, ids.MAIN_SET_TEMP_2, ids.MAIN_SET_TEMP_3):
        g.screen.adjust_mode = "Filament"
        page_to(ids.FILAMENT)
    elif widget_id == ids.MAIN_CACHE:
        g.files.list_pages = 0
        g.files.list_current_pages = 0
        g.files.list_folder_layers = 0
        g.files.list_previous_path = ""
        g.files.list_root_path = filelist.DEFAULT_DIR
        g.files.list_path = ""
        filelist.refresh_page_files(g.files.list_current_pages)
        if g.files.list_list_show_type[0] == "[c]":
            filelist.clear_cp0_image()
            file_browser.get_sub_dir_files_list(0)
            g.screen.file_mode = "Local"


def file_list(page_id, widget_id):
    if widget_id == ids.ALL_TO_MAIN:
        page_to(ids.MAIN)
    elif widget_id == ids.ALL_TO_FILE_LIST:
        pass
    elif widget_id == ids.ALL_TO_ADJUST:
        actions.go_to_adjust()
    elif widget_id == ids.ALL_TO_SETTING:
        actions.go_to_setting()
    elif widget_id == ids.FILE_LIST_BACK:
        if g.files.list_folder_layers == 0 or (g.files.list_folder_layers == 1 and g.screen.file_mode != "Local"):
            pass
        else:
            file_browser.get_parenet_dir_files_list()
    elif widget_id in (ids.FILE_LIST_BTN_1, ids.FILE_LIST_BTN_2, ids.FILE_LIST_BTN_3,
                       ids.FILE_LIST_BTN_4):
        filelist.clear_cp0_image()
        file_browser.get_sub_dir_files_list(widget_id - ids.FILE_LIST_BTN_1)
        g.screen.bed_leveling = True
    # 4.4.22: the list is marked as changed and the touch is disabled
    # until the pictures of the new page are sent
    elif widget_id == ids.FILE_LIST_PREVIOUS:
        if filelist.detect_disk() == -1 and g.screen.file_mode == "USB":
            g.screen.file_list_refreshed = False
            filelist.go_to_file_list()
        elif g.files.list_current_pages > 0:
            g.screen.file_list_refreshed = False
            g.files.list_current_pages -= 1
            page_to(ids.FILE_LIST)
            g.port.tsw("255", "0")
            filelist.refresh_page_files(g.files.list_current_pages)
            filelist.refresh_files_list()
        log.debug("%d", g.files.list_folder_layers)
    elif widget_id == ids.FILE_LIST_NEXT:
        if filelist.detect_disk() == -1 and g.screen.file_mode == "USB":
            g.screen.file_list_refreshed = False
            filelist.go_to_file_list()
        elif g.files.list_current_pages < g.files.list_pages:
            g.screen.file_list_refreshed = False
            g.files.list_current_pages += 1
            page_to(ids.FILE_LIST)
            g.port.tsw("255", "0")
            filelist.refresh_page_files(g.files.list_current_pages)
            filelist.refresh_files_list()
        log.debug("%d", g.files.list_folder_layers)
    # 4.4.2 CLL local / USB buttons on the file list page
    elif widget_id == ids.FILE_LIST_LOCAL:
        if g.screen.file_mode != "Local":
            g.screen.file_mode = "Local"
            g.screen.file_list_refreshed = False
            filelist.go_to_file_list()
    elif widget_id == ids.FILE_LIST_USB:
        if g.screen.file_mode != "USB":
            g.screen.file_mode = "USB"
            g.screen.file_list_refreshed = False
            filelist.go_to_file_list()


def preview(page_id, widget_id):
    if g.screen.page == ids.PREVIEW:
        printing_or_paused = (g.klippy.print_stats_state == "printing" or g.klippy.print_stats_state == "paused")
        if widget_id == ids.ALL_TO_MAIN:
            if printing_or_paused:
                page_to(ids.PRINTING)
                g.screen.jump_print = False
            else:
                page_to(ids.MAIN)
        elif widget_id == ids.ALL_TO_FILE_LIST:
            pass
        elif widget_id == ids.ALL_TO_ADJUST:
            if printing_or_paused:
                page_to(ids.PRINTING)
                g.screen.jump_print = False
            else:
                actions.go_to_adjust()
        elif widget_id == ids.ALL_TO_SETTING:
            if printing_or_paused:
                page_to(ids.PRINTING)
                g.screen.jump_print = False
            else:
                actions.go_to_setting()
        elif widget_id == ids.PREVIEW_BACK:
            # 4.4.3 CLL keep the preview page from getting stuck
            if printing_or_paused:
                page_to(ids.PRINTING)
                g.screen.jump_print = False
            elif not g.files.meta_parse_finished:
                file_browser.get_parenet_dir_files_list()
                pages.clear_preview()
                g.screen.show_preview_complete = False
                filelist.clear_cp0_image()
            else:
                if g.screen.show_preview_complete:     # the button only works once the preview is loaded
                    file_browser.get_parenet_dir_files_list()
                    pages.clear_preview()             # clear the data when going back
                    g.screen.show_preview_complete = False
                    filelist.clear_cp0_image()
        elif widget_id == ids.PREVIEW_START:
            if printing_or_paused:
                page_to(ids.PRINTING)
                g.screen.jump_print = False
            elif g.screen.show_preview_complete:
                g.screen.muted = False             # 4.4.22 silent mode is per print
                actions.print_start()
                sleep(1)
                if g.klippy.filament_detected:
                    log.info("No filament runout detected")
                    g.klippy.print_stats_state = "printing"
                    actions.check_filament_type()
                    actions.start_printing(g.files.list_print_files_path)
                    g.screen.show_preview_complete = False
                else:
                    log.info("Filament runout detected")
                    page_to(ids.PRINT_NO_FILAMENT)
            g.screen.main_picture_detected = False
            g.screen.main_picture_refreshed = False
        elif widget_id == ids.PREVIEW_BED_LEVELING:
            if printing_or_paused:
                page_to(ids.PRINTING)
                g.screen.jump_print = False
            else:
                if g.screen.bed_leveling:
                    g.screen.bed_leveling = False
                else:
                    g.screen.bed_leveling = True
        elif widget_id == ids.PREVIEW_TIMELAPSE:
            actions.switch_timelapse_state()


def preview_pop(page_id, widget_id):
    if widget_id == ids.PREVIEW_POP_YES:
        page_to(ids.PRINTING)
    elif widget_id == ids.PREVIEW_POP_NO_POP:
        if g.screen.page == ids.PREVIEW_POP_1:
            g.screen.preview_pop_1_on = False
        elif g.screen.page == ids.PREVIEW_POP_2:
            g.screen.preview_pop_2_on = False
        page_to(ids.PRINTING)


def printing(page_id, widget_id):
    if widget_id in (ids.PRINTING_EXTRUDER, ids.PRINTING_HEATER_BED, ids.PRINTING_FAN_1,
                     ids.PRINTING_FAN_2, ids.PRINTING_FAN_3, ids.PRINTING_HOT):
        g.screen.printing_keyboard_enabled = True
        pages.clear_printing_arg()
    elif widget_id == ids.PRINTING_NEXT:
        page_to(ids.PRINTING_2)
    elif widget_id == ids.PRINTING_EMERGENCY_STOP:
        page_to(ids.STOP_CONFIRM)
    elif widget_id == ids.PRINTING_PAUSE_RESUME:
        g.klippy.ready = False
        actions.set_print_pause()
        page_to(ids.PRINT_FILAMENT)
        pages.clear_printing_arg()
    elif widget_id == ids.PRINTING_STOP:
        page_to(ids.PRINT_STOP)
        pages.clear_printing_arg()


def printing_kb(page_id, widget_id):
    if widget_id == ids.PRINTING_KB_BACK:
        g.screen.printing_keyboard_enabled = False
        log.debug("Restored")
    elif widget_id == ids.PRINTING_KB_MUTE:
        log.debug("Silent mode switched")
        if not g.screen.muted:
            g.screen.muted = True
            actions.set_printer_speed(50)
        else:
            g.screen.muted = False
            actions.set_printer_speed(100)
    elif widget_id == ids.PRINTING_KB_PAUSE_RESUME:
        g.screen.printing_keyboard_enabled = False
        actions.set_print_pause()
        page_to(ids.PRINT_FILAMENT)
        pages.clear_printing_arg()
    elif widget_id == ids.PRINTING_KB_STOP:
        g.screen.printing_keyboard_enabled = False
        page_to(ids.PRINT_STOP)
        pages.clear_printing_arg()


def print_zoffset(page_id, widget_id):
    if widget_id == ids.PRINT_ZOFFSET_BACK:
        g.screen.printing_keyboard_enabled = False
        page_to(ids.PRINTING_2)
    elif widget_id == ids.PRINT_ZOFFSET_SET_001:
        actions.set_intern_zoffset(0.01)
    elif widget_id == ids.PRINT_ZOFFSET_SET_005:
        actions.set_intern_zoffset(0.05)
    elif widget_id == ids.PRINT_ZOFFSET_SET_01:
        actions.set_intern_zoffset(0.1)
    elif widget_id == ids.PRINT_ZOFFSET_SET_05:
        actions.set_intern_zoffset(0.5)
    elif widget_id == ids.PRINT_ZOFFSET_UP:
        actions.set_zoffset(False)
    elif widget_id == ids.PRINT_ZOFFSET_DOWN:
        actions.set_zoffset(True)
    elif widget_id == ids.PRINT_ZOFFSET_PAUSE_RESUME:
        g.klippy.ready = False
        actions.set_print_pause()
        page_to(ids.PRINT_FILAMENT)
        pages.clear_printing_arg()
    elif widget_id == ids.PRINT_ZOFFSET_STOP:
        page_to(ids.PRINT_STOP)


def print_filament(page_id, widget_id):
    if widget_id == ids.PRINT_FILAMENT_ON_OFF:
        actions.set_print_filament_target()
    elif widget_id == ids.PRINT_FILAMENT_T_UP:
        actions.set_filament_extruder_target(True)
    elif widget_id == ids.PRINT_FILAMENT_T_DOWN:
        actions.set_filament_extruder_target(False)
    elif widget_id == ids.PRINT_FILAMENT_LOAD:
        g.screen.load_mode = True
        page_to(ids.PRE_HEAT)
    elif widget_id == ids.PRINT_FILAMENT_UNLOAD:
        g.screen.load_mode = False
        page_to(ids.PRE_HEAT)
    elif widget_id == ids.PRINT_FILAMENT_PAUSE_RESUME:
        log.debug("get_filament_detected_enable: %d", int(actions.get_filament_detected_enable()))
        log.debug("get_filament_detected: %d", int(actions.get_filament_detected()))
        g.klippy.ready = False
        page_to(ids.PRINTING)
        actions.set_print_resume()
    elif widget_id == ids.PRINT_FILAMENT_STOP:
        page_to(ids.PRINT_STOP)
        pages.clear_printing_arg()
    elif widget_id == ids.PRINT_FILAMENT_RETRACT:
        actions.send_gcode("M603\n")
    elif widget_id == ids.PRINT_FILAMENT_EXTRUDE:
        actions.set_print_filament_dist(50)
        actions.start_extrude()


def printing_2(page_id, widget_id):
    if widget_id == ids.PRINTING_2_BACK:
        page_to(ids.PRINTING)
    elif widget_id in (ids.PRINTING_2_SPEED, ids.PRINTING_2_FLOW):
        g.screen.printing_keyboard_enabled = True
        pages.clear_printing_arg()
    elif widget_id == ids.PRINTING_2_ZOFFSET:
        page_to(ids.PRINT_ZOFFSET)
    elif widget_id == ids.PRINTING_2_PAUSE_RESUME:
        g.klippy.ready = False
        actions.set_print_pause()
        page_to(ids.PRINT_FILAMENT)
        pages.clear_printing_arg()
    elif widget_id == ids.PRINTING_2_STOP:
        page_to(ids.PRINT_STOP)
    elif widget_id == ids.PRINTING_2_CASE_LIGHT:
        actions.led_on_off()


def print_finish(page_id, widget_id):
    if widget_id == ids.PRINT_FINISH_YES:
        actions.finish_print()


def print_stop(page_id, widget_id):
    if widget_id == ids.PRINT_STOP_YES:
        g.klippy.idle_timeout_state = "Printing"
        page_to(ids.PRINT_STOPPING)
        actions.cancel_print()
    elif widget_id == ids.PRINT_STOP_NO:
        page_to(g.screen.previous_page)


# 4.4.22 emergency stop from the printing page
def stop_confirm(page_id, widget_id):
    if widget_id == ids.STOP_CONFIRM_YES:
        page_to(ids.PRINT_STOPPING)
        g.klippy.print_stats_state = "paused"
        actions.motors_off()
    elif widget_id == ids.STOP_CONFIRM_NO:
        page_to(ids.PRINTING)


def print_no_filament(page_id, widget_id):
    if widget_id == ids.PRINT_NO_FILAMENT_YES:
        g.klippy.filament_detected = True
        if g.screen.previous_page == ids.PREVIEW:
            actions.get_object_status()
            page_to(ids.MOVE)
        else:
            actions.get_object_status()
            page_to(ids.PRINT_FILAMENT)


def print(page_id, widget_id):
    if page_id == ids.PRINT_NO_FILAMENT_2:
        if widget_id == ids.PRINT_NO_FILAMENT_2_YES:
            actions.get_object_status()
            page_to(ids.PRINT_FILAMENT)
        # NOTE: no "break" in the original - falls through into the next case
    if widget_id == ids.PRINT_LOW_TEMP_YES:
        g.klippy.idle_timeout_state = "Ready"
        page_to(ids.PRINT_FILAMENT)


def print_log(page_id, widget_id):
    if widget_id == ids.PRINT_LOG_YES:
        actions.go_to_reset()


def resume_print(page_id, widget_id):
    if widget_id == ids.RESUME_PRINT_YES:
        page_to(ids.RE_PRINTING)
        actions.send_gcode("RESUME_INTERRUPTED\n")
    elif widget_id == ids.RESUME_PRINT_NO:
        page_to(ids.MAIN)
        actions.send_gcode("CLEAR_LAST_FILE")
    elif widget_id == ids.RESUME_PRINT_LOADED:
        g.screen.jump_resume_print = False      # 4.4.24: the page reports that it is shown


HANDLERS = {
    ids.MAIN: main,
    ids.FILE_LIST: file_list,
    ids.PREVIEW: preview,
    ids.PREVIEW_POP_1: preview_pop,
    ids.PREVIEW_POP_2: preview_pop,
    ids.PRINTING: printing,
    ids.PRINTING_KB: printing_kb,
    ids.PRINT_ZOFFSET: print_zoffset,
    ids.PRINT_FILAMENT: print_filament,
    ids.PRINTING_2: printing_2,
    ids.PRINT_FINISH: print_finish,
    ids.PRINT_STOP: print_stop,
    ids.STOP_CONFIRM: stop_confirm,
    ids.PRINT_NO_FILAMENT: print_no_filament,
    ids.PRINT_NO_FILAMENT_2: print,
    ids.PRINT_LOW_TEMP: print,
    ids.PRINT_LOG_F: print_log,
    ids.PRINT_LOG_S: print_log,
    ids.RESUME_PRINT: resume_print,
}
