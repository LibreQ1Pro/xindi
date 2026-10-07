"""The Wi-Fi list page, the IP address and the connection details."""

import logging

from xindi import state as g
from xindi.screen import pageids as ids, pics
from xindi.screen.navigation import page_to
from xindi.system import network
from xindi.system.network import (detected_wlan0,
                                  get_eth0_ip,
                                  get_ssid_list_pages,
                                  get_wlan0_ip,
                                  get_wlan0_status,
                                  set_page_wifi_ssid_list)
from xindi.util.cpp import b2s, to_string


log = logging.getLogger(__name__)


def refresh_wifi_keyboard():
    if g.screen.printing_wifi_keyboard_enabled:
        g.port.txt("title", g.net.get_wifi_name)


def go_to_network():
    if detected_wlan0():
        get_wlan0_status()
        g.screen.wifi_ssid_button_enabled[0] = False
        g.screen.wifi_ssid_button_enabled[1] = False
        g.screen.wifi_ssid_button_enabled[2] = False
        g.screen.wifi_ssid_button_enabled[3] = False
        g.screen.wifi_ssid_button_enabled[4] = False
        g.net.wifi_ssid_list_pages = 0
        g.net.wifi_current_pages = 0
        if g.net.status_result.wpa_state == "COMPLETED":
            g.net.current_connected_ssid_name = g.net.status_result.ssid   # name of the connected wifi
        elif g.net.status_result.wpa_state != "INACTIVE":
            g.net.current_connected_ssid_name = ""      # not connected: forget the name of the connected wifi
        page_to(ids.WIFI_LIST)
        scan_ssid_and_show()
    else:
        page_to(ids.INTERNET)


def scan_ssid_and_show():
    if detected_wlan0():
        get_wlan0_status()
        network.mks_wpa_scan_scanresults()
        get_ssid_list_pages()
        g.net.wifi_current_pages = 0
        set_page_wifi_ssid_list(g.net.wifi_current_pages)
        refresh_wifi_list()
    else:
        page_to(ids.INTERNET)


def refresh_wifi_list():
    # 4.4.22: the names come from the list, the first entry of the first page is
    # the connected network; the page buttons are set once after the list
    log.debug("pages: %d / %d", g.net.wifi_current_pages + 1, g.net.wifi_ssid_list_pages)
    for i in range(5):
        log.debug("Refreshed wifi: %s", g.net.wifi_ssid_list[i])
        g.port.txt("row" + to_string(i + 1) + "_txt", g.net.wifi_ssid_list[i])
        if g.net.status_result.wpa_state == "COMPLETED" and g.net.wifi_current_pages == 0 and i == 0:
            g.port.picc("row1", pics.rows_check)
            g.port.picc2("row" + to_string(i + 1), pics.rows_check_press)
            g.screen.wifi_ssid_button_enabled[i] = False
        elif g.net.wifi_ssid_list[i] != "":
            g.port.picc("row" + to_string(i + 1), pics.rows_lock)
            g.port.picc2("row" + to_string(i + 1), pics.bg_settings_press)
            g.screen.wifi_ssid_button_enabled[i] = True
        else:
            g.port.picc("row" + to_string(i + 1), pics.bg_settings_panel)
            g.port.picc2("row" + to_string(i + 1), pics.bg_settings_panel)
            g.screen.wifi_ssid_button_enabled[i] = False

    if g.net.wifi_ssid_list_pages == 0:
        g.port.picc("prev_btn", pics.rows_check)
        g.port.picc2("prev_btn", pics.bg_settings_press)
        g.port.picc("next_btn", pics.rows_check)
        g.port.picc2("next_btn", pics.bg_settings_press)
    else:
        if g.net.wifi_current_pages == 0:
            g.port.picc("prev_btn", pics.rows_check)
            g.port.picc2("prev_btn", pics.bg_settings_press)
        else:
            g.port.picc("prev_btn", pics.rows_lock)
            g.port.picc2("prev_btn", pics.rows_check_press)
        if g.net.wifi_ssid_list_pages - 1 == g.net.wifi_current_pages:
            g.port.picc("next_btn", pics.rows_check)
            g.port.picc2("next_btn", pics.bg_settings_press)
        else:
            g.port.picc("next_btn", pics.rows_lock)
            g.port.picc2("next_btn", pics.rows_check_press)


def get_wifi_list_ssid(index):
    g.net.get_wifi_name = ""
    g.net.get_wifi_name = g.net.wifi_ssid_list[index]


def print_ssid_psk(psk):
    """psk: bytes received from the screen keyboard"""
    log.info("SSID is %s", g.net.get_wifi_name)
    network.mks_start_connect(g.net.get_wifi_name, b2s(psk))


def refresh_ip_address():
    """4.4.22: show the network page with the address of wlan0."""
    page_to(ids.INTERNET_PAGE)
    ip_address = get_wlan0_ip()
    if ip_address != "":
        log.info("ip_address updated")
        g.port.txt("ip_txt", ip_address)


def refresh_show_ip():
    """4.4.22 refresh of the network page."""
    if g.config.ethernet == 1:
        ip_address = get_eth0_ip()
        g.port.txt("ip_txt", ip_address if ip_address.find(":") == -1 else "")
        g.port.picc("source_switch", pics.ip_switch_on)
        g.port.picc2("source_switch", pics.ip_press_on)
    else:
        g.port.txt("ip_txt", g.net.status_result.ip_address)
        g.port.picc("source_switch", pics.ip_switch_off)
        g.port.picc2("source_switch", pics.ip_press_off)
