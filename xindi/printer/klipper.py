"""Subscriptions, restarts and plain gcode: talking to Klipper itself."""

from xindi import state as g
from xindi.moonraker.printer_status import subscribe_objects_status
from xindi.moonraker.rpc_requests import json_query_printer_object_status, json_subscribe_to_printer_object_status
from xindi.screen import pageids as ids
from xindi.screen.navigation import page_to


def sub_object_status():
    g.ep.send(json_subscribe_to_printer_object_status(subscribe_objects_status()))


def get_object_status():
    g.ep.send(json_query_printer_object_status(subscribe_objects_status()))


def reset_klipper():
    g.ep.run_gcode("RESTART\n")


def reset_firmware():
    g.ep.run_gcode("FIRMWARE_RESTART\n")


def go_to_reset():
    if g.klippy.webhooks_state == "shutdown":
        page_to(ids.RESET)
    else:
        # 4.4.22: fixed name (was read from /dev_info.txt)
        page_to(ids.SYS_OK)
        g.port.txt("info_txt", "Q1 Pro")


def send_gcode(command):
    g.ep.run_gcode(command)
