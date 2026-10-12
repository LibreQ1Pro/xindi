"""The saved settings (config.mksini): reading and writing them, and loading the versions."""

import logging
import os
import shutil

from xindi import state as g
from xindi.config.inifile import open_settings, reset_settings, save_setting
from xindi.moonraker import rest
from xindi.moonraker.rpc_requests import json_get_job_totals
from xindi.screen import pageids as ids
from xindi.screen.navigation import page_to
from xindi.util import paths
from xindi.util.cpp import to_string

log = logging.getLogger(__name__)


def set_led_status():
    save_setting("led", "enable", to_string(g.config.led_status))


def set_beep_status():
    save_setting("beep", "enable", to_string(g.config.beep_status))


def get_extruder_target():
    ini = open_settings()
    g.config.extruder_target = ini.get_int("target", "extruder", 200)


def set_extruder_target(target):
    if target != 0:
        save_setting("target", "extruder", to_string(target))
    

def get_heater_bed_target():
    ini = open_settings()
    g.config.heater_bed_target = ini.get_int("target", "heaterbed", 40)


def set_heater_bed_target(target):
    if target != 0:
        log.debug("######## %s", target)
        save_setting("target", "heaterbed", to_string(target))
    

def get_hot_target():
    ini = open_settings()
    g.config.hot_target = ini.get_int("target", "hot", 40)


def set_hot_target(target):
    log.debug("######## %s", target)
    save_setting("target", "hot", to_string(target))


def set_babystep(value):
    save_setting("babystep", "value", value)


def get_babystep():
    ini = open_settings()
    g.config.babystep_value = ini.get_string("babystep", "value", "0.000")
    g.config.adxl_offset = ini.get_string("babystep", "adxl_offset", "0.000")


def init():
    """4.4.22 start-up settings (the QIDI Link part is not implemented)."""
    get_babystep()
    get_ethernet()


def get_total_time():
    g.ep.send(json_get_job_totals())


def get_oobe_enabled():
    ini = open_settings()
    g.config.oobe_enabled = ini.get_bool("oobe", "enable", 0)
    return g.config.oobe_enabled


def set_oobe_enabled(enable):
    save_setting("oobe", "enable", to_string(bool(enable)))


def restore_config():
    g.screen.main_picture_refreshed = False
    rest.request("POST", "server/history/reset_totals")
    rest.request("DELETE", "server/history/job?all=true")
    reset_settings()
    variables = paths.klipper_config() + "/saved_variables.cfg"
    if os.path.exists(variables + ".bak"):      # QIDI's image keeps the factory copy
        shutil.copyfile(variables + ".bak", variables)
    g.ep.run_gcode("SAVE_VARIABLE VARIABLE=z_offset VALUE=0")
    page_to(ids.MAIN)


def get_ethernet():
    ini = open_settings()
    g.config.ethernet = int(ini.get_bool("mks_ethernet", "enable", 0))
    return g.config.ethernet
