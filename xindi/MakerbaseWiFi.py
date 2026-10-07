"""Port of src/MakerbaseWiFi.cpp - pages of the wifi list."""

from . import state as g
from .mks_log import cout
from .network import mks_wifi_run_cmd_status


def set_page_wifi_ssid_list(pages):
    g.net.wifi_ssid_list[0] = ""
    g.net.wifi_ssid_list[1] = ""
    g.net.wifi_ssid_list[2] = ""
    g.net.wifi_ssid_list[3] = ""
    g.net.wifi_ssid_list[4] = ""

    it = 0
    for i in range(pages * 5):
        it += 1

    for k in range(5):
        if it < len(g.net.ssid_list):
            g.net.wifi_ssid_list[k] = g.net.ssid_list[it]
            it += 1

    for j in range(5):
        cout(g.net.wifi_ssid_list[j])


def get_ssid_list_pages():
    """4.4.1 CLL wifi refresh fix"""
    if len(g.net.ssid_list) % 5 == 0:
        g.net.wifi_ssid_list_pages = len(g.net.ssid_list) // 5
    else:
        g.net.wifi_ssid_list_pages = len(g.net.ssid_list) // 5 + 1

    if g.net.wifi_ssid_list_pages > 5:
        g.net.wifi_ssid_list_pages = 5


def get_wlan0_status():
    mks_wifi_run_cmd_status(g.net.status_result)
