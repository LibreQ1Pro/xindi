"""The saved settings (config.mksini): reading and writing them, and loading the versions."""

import time
import logging

from . import paths
from . import state as g
from . import pageids as ids
from . import network
from .network import get_wlan0_status
from .ui import page_to
from .cpp import to_string, system
from .moonraker_api import json_get_job_totals
from .config_ini import open_settings, save_setting, open_version_file

log = logging.getLogger(__name__)


def set_led_status():
    save_setting("led", "enable", to_string(g.config.led_status))


def set_beep_status():
    save_setting("beep", "enable", to_string(g.config.beep_status))
    system("sync")


def get_language_status():
    ini = open_settings()
    g.config.language_status = ini.get_int("system", "language", 0)


def get_extruder_target():
    ini = open_settings()
    g.config.extruder_target = ini.get_int("target", "extruder", 200)


def set_extruder_target(target):
    if target != 0:
        save_setting("target", "extruder", to_string(target))
        system("sync")


def get_heater_bed_target():
    ini = open_settings()
    g.config.heater_bed_target = ini.get_int("target", "heaterbed", 40)


def set_heater_bed_target(target):
    if target != 0:
        log.debug("######## %s", target)
        save_setting("target", "heaterbed", to_string(target))
        system("sync")


def get_hot_target():
    ini = open_settings()
    g.config.hot_target = ini.get_int("target", "hot", 40)


def set_hot_target(target):
    log.debug("######## %s", target)
    save_setting("target", "hot", to_string(target))
    system("sync")


def set_babystep(value):
    save_setting("babystep", "value", value)
    system("sync")


def get_babystep():
    ini = open_settings()
    g.config.babystep_value = ini.get_string("babystep", "value", "0.000")
    g.config.adxl_offset = ini.get_string("babystep", "adxl_offset", "0.000")


def init():
    """4.4.22 start-up settings (the QIDI Link part is not implemented)."""
    get_babystep()
    get_ethernet()


def load_versions():
    ini = open_version_file()
    g.config.version_soc = ini.get_string("version", "soc", "V1.1.1")
    g.config.version_mcu = ini.get_string("version", "mcu", "V0.10.0")
    g.config.version_ui = ini.get_string("version", "ui", "V1.1.1")


def wifi_save_config():
    page_to(ids.WIFI_SAVING)
    network.mks_save_config()
    time.sleep(2)
    get_wlan0_status()


def get_total_time():
    g.ep.send(json_get_job_totals())


def get_oobe_enabled():
    ini = open_settings()
    g.config.oobe_enabled = ini.get_bool("oobe", "enable", 0)
    return g.config.oobe_enabled


def set_oobe_enabled(enable):
    save_setting("oobe", "enable", to_string(bool(enable)))
    system("sync")


def restore_config():
    system("rm " + paths.gcode_files() + "/.cache/*")
    g.screen.main_picture_refreshed = False
    system("curl -X POST http://127.0.0.1:7125/server/history/reset_totals")
    system("curl -X DELETE 'http://127.0.0.1:7125/server/history/job?all=true'")
    system("cp /root/config.mksini " + paths.klipper_config() + "/config.mksini")
    system("cp " + paths.klipper_config() + "/saved_variables.cfg.bak " + paths.klipper_config() + "/saved_variables.cfg")
    g.ep.run_gcode("SAVE_VARIABLE VARIABLE=z_offset VALUE=0")
    page_to(ids.MAIN)


def get_ethernet():
    ini = open_settings()
    g.config.ethernet = int(ini.get_bool("mks_ethernet", "enable", 0))
    return g.config.ethernet


def set_ethernet(target):
    log.debug("Setting ethernet:%s", target)
    save_setting("mks_ethernet", "enable", to_string(target))
    g.config.ethernet = target
