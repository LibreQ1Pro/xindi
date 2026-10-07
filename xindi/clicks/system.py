"""Clicks on the network, settings, error and pop-up pages. Each function gets the page id and the widget id the screen sent; HANDLERS maps pages to them."""

from .. import state as g
from .. import actions, filelist, netui, settings, wifi_ui
from .. import pageids as ids
from ..cpp import sleep
from ..mks_log import cout
from ..ui import page_to
from ..network import set_page_wifi_ssid_list
from .common import nav_guarded


def internet(page_id, widget_id):
    if nav_guarded(widget_id):
        pass
    elif widget_id == ids.ALL_TO_SETTING:
        pass
    elif widget_id == ids.INTERNET_REFRESH:
        cout("################## refresh button pressed")
        wifi_ui.scan_ssid_and_show()
        cout("Waiting 3s...")
        sleep(3)
        wifi_ui.scan_ssid_and_show()
    elif widget_id == ids.INTERNET_TO_WIFI:
        pass
    elif widget_id == ids.INTERNET_TO_SETTING:
        page_to(ids.COMMON_SETTING)


def wifi_list(page_id, widget_id):
    if nav_guarded(widget_id):
        pass
    elif widget_id == ids.ALL_TO_SETTING:
        pass
    elif widget_id in (ids.WIFI_LIST_SSID_1, ids.WIFI_LIST_SSID_2, ids.WIFI_LIST_SSID_3,
                       ids.WIFI_LIST_SSID_4, ids.WIFI_LIST_SSID_5):
        index = widget_id - ids.WIFI_LIST_SSID_1
        if g.screen.wifi_ssid_button_enabled[index] == True:
            wifi_ui.get_wifi_list_ssid(index)
            netui.open_keyboard(netui.KB_PSK_SCANNED, 8, g.net.get_wifi_name)
    elif widget_id == ids.WIFI_LIST_SAVED:
        netui.open_saved()
    elif widget_id == ids.WIFI_LIST_HIDDEN:
        netui.open_hidden()
    elif widget_id == ids.WIFI_LIST_REFRESH:
        cout("################## refresh button pressed")
        wifi_ui.scan_ssid_and_show()
        # 4.4.1 CLL wifi refresh fix
    elif widget_id == ids.WIFI_LIST_PREVIOUS:
        if g.net.wifi_current_pages > 0:
            cout("page_wifi_current_pages = ", g.net.wifi_current_pages)
            cout("page_wifi_ssid_list_pages = ", g.net.wifi_ssid_list_pages)
            g.net.wifi_current_pages -= 1
            set_page_wifi_ssid_list(g.net.wifi_current_pages)
            wifi_ui.refresh_wifi_list()
    elif widget_id == ids.WIFI_LIST_NEXT:
        if g.net.wifi_current_pages < g.net.wifi_ssid_list_pages - 1:
            cout("page_wifi_current_pages = ", g.net.wifi_current_pages)
            cout("page_wifi_ssid_list_pages = ", g.net.wifi_ssid_list_pages)
            g.net.wifi_current_pages += 1
            set_page_wifi_ssid_list(g.net.wifi_current_pages)
            wifi_ui.refresh_wifi_list()
    elif widget_id == ids.WIFI_LIST_TO_WIFI:
        pass
    elif widget_id == ids.WIFI_LIST_TO_SETTING:
        wifi_ui.refresh_ip_address()             # 4.4.22: the network page (was the QR code page)


# 4.4.24: the timer of the page reports a connection that takes too long
def wifi_connect(page_id, widget_id):
    if widget_id == ids.WIFI_CONNECT_TIMEOUT:
        page_to(ids.WIFI_FAILED)


def wifi_success(page_id, widget_id):
    if widget_id == ids.WIFI_SUCCESS_YES:
        settings.wifi_save_config()


def wifi_failed(page_id, widget_id):
    if widget_id == ids.WIFI_FAILED_YES:
        wifi_ui.go_to_network()                  # 4.4.22 (was page_to(ids.WIFI_LIST))


def wifi_kb(page_id, widget_id):
    if widget_id == ids.WIFI_KB_BACK:
        netui.keyboard_back()


def net_saved_or_net_info(page_id, widget_id):
    if nav_guarded(widget_id):
        pass
    elif page_id == ids.NET_SAVED:
        netui.saved_clicked(widget_id)
    elif page_id == ids.NET_DETAIL:
        netui.detail_clicked(widget_id)
    elif page_id == ids.NET_CONFIRM:
        netui.confirm_clicked(widget_id)
    else:
        netui.info_clicked(widget_id)


def common_setting(page_id, widget_id):
    if nav_guarded(widget_id):
        pass
    elif widget_id == ids.ALL_TO_SETTING:
        pass
    elif widget_id == ids.COMMON_SETTING_LANGUAGE:
        page_to(ids.LANGUAGE)
    elif widget_id == ids.COMMON_SETTING_WIFI:
        wifi_ui.refresh_ip_address()             # 4.4.22: the network page (was the QR code page)
    elif widget_id == ids.COMMON_SETTING_SYSTEM:
        actions.go_to_reset()
    elif widget_id == ids.COMMON_SETTING_SERVICE:
        page_to(ids.SERVICE)
    elif widget_id == ids.COMMON_SETTING_SCREEN_SLEEP:
        page_to(ids.SLEEP_MODE)
    elif widget_id == ids.COMMON_SETTING_RESTORE:
        page_to(ids.RESTORE_CONFIG)
    elif widget_id == ids.COMMON_SETTING_OOBE_OFF:
        settings.set_oobe_enabled(False)
        page_to(ids.COMMON_SETTING)
    elif widget_id == ids.COMMON_SETTING_OOBE_ON:
        settings.set_oobe_enabled(True)
    elif widget_id == ids.COMMON_SETTING_TO_LEVEL_MODE:
        page_to(ids.LEVEL_MODE)
        g.screen.set_mode = "Level_mode"


def language_or_sleep_mode(page_id, widget_id):
    if nav_guarded(widget_id):
        pass
    elif widget_id == ids.ALL_TO_SETTING:
        pass
    elif widget_id == ids.BACK_TO_COMMON_SETTING:
        page_to(ids.COMMON_SETTING)
    elif widget_id == ids.RESET_PRINT_LOG:
        filelist.print_log()
    elif widget_id == ids.RESET_RESTART_KLIPPER:
        actions.reset_klipper()
    elif widget_id == ids.RESET_RESTART_FIRMWARE:
        actions.reset_firmware()


def update_success(page_id, widget_id):
    if widget_id == ids.UPDATE_SUCCESS_YES:
        actions.finish_screen_update()
        page_to(ids.MAIN)


def detect_error(page_id, widget_id):
    if widget_id == ids.DETECT_ERROR_YES:
        if g.screen.previous_page == ids.AUTO_MOVING or g.screen.previous_page == ids.OPEN_CALIBRATE:
            actions.reset_klipper()
        page_to(ids.MAIN)
        actions.clear_previous_data()


def gcode_error(page_id, widget_id):
    if widget_id == ids.GCODE_ERROR_YES:
        page_to(ids.MAIN)


# 4.4.2 CLL screen sleep feature
def screen_sleep(page_id, widget_id):
    if widget_id == ids.SCREEN_SLEEP_ENTER:
        page_to(ids.SCREEN_SLEEP)
    elif widget_id == ids.SCREEN_SLEEP_EXIT:
        if g.screen.previous_page == ids.FILE_LIST:
            filelist.go_to_file_list()
        else:
            page_to(g.screen.previous_page)
            actions.get_object_status()


def restore_config(page_id, widget_id):
    if widget_id == ids.RESTORE_CONFIG_YES:
        settings.restore_config()
    elif widget_id == ids.RESTORE_CONFIG_NO:
        page_to(ids.COMMON_SETTING)


def memory_warning(page_id, widget_id):
    if widget_id == ids.MEMORY_WARNING_YES:
        page_to(ids.MAIN)


# 4.4.24 network page (4.4.22 binary); the QIDI Link buttons are not implemented
def internet_page(page_id, widget_id):
    if nav_guarded(widget_id):
        pass
    elif widget_id == ids.INTERNET_PAGE_BACK:
        page_to(ids.COMMON_SETTING)
    elif widget_id == ids.INTERNET_PAGE_ETHERNET:
        # 1: ethernet, 0: wifi (the page shows the address on the next refresh)
        settings.set_ethernet(0 if g.config.ethernet == 1 else 1)
    elif widget_id == ids.INTERNET_PAGE_WIFI:
        wifi_ui.go_to_network()
    elif widget_id == ids.INTERNET_PAGE_INFO:
        netui.open_info()
    elif widget_id == ids.INTERNET_PAGE_SAVED:
        netui.open_saved()
    elif widget_id == ids.INTERNET_PAGE_HIDDEN:
        netui.open_hidden()


HANDLERS = {
    ids.INTERNET: internet,
    ids.WIFI_LIST: wifi_list,
    ids.WIFI_CONNECT: wifi_connect,
    ids.WIFI_SUCCESS: wifi_success,
    ids.WIFI_FAILED: wifi_failed,
    ids.WIFI_KB: wifi_kb,
    ids.NET_SAVED: net_saved_or_net_info,
    ids.NET_DETAIL: net_saved_or_net_info,
    ids.NET_CONFIRM: net_saved_or_net_info,
    ids.NET_INFO: net_saved_or_net_info,
    ids.COMMON_SETTING: common_setting,
    ids.LANGUAGE: language_or_sleep_mode,
    ids.SERVICE: language_or_sleep_mode,
    ids.SYS_OK: language_or_sleep_mode,
    ids.RESET: language_or_sleep_mode,
    ids.SLEEP_MODE: language_or_sleep_mode,
    ids.UPDATE_SUCCESS: update_success,
    ids.DETECT_ERROR: detect_error,
    ids.GCODE_ERROR: gcode_error,
    ids.SCREEN_SLEEP: screen_sleep,
    ids.RESTORE_CONFIG: restore_config,
    ids.MEMORY_WARNING: memory_warning,
    ids.INTERNET_PAGE: internet_page,
}
