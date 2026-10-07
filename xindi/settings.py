"""The saved settings (config.mksini): reading and writing them, and loading the versions."""

from . import paths
from . import state as g
from . import pageids as ids
from . import network
from .network import get_wlan0_status
from .ui import page_to
from .cpp import to_string, system, sleep
from .mks_log import cout
from .moonraker_api import json_run_a_gcode, json_get_job_totals
from .config_ini import (mksini_load, mksini_free, mksini_getstring, mksini_getint,
                                mksini_getboolean, mksini_set, mksini_save, mksversion_load,
                                mksversion_free, mksversion_soc, mksversion_mcu, mksversion_ui)


def set_led_status():
    mksini_load()
    mksini_set("led", "enable", to_string(g.config.led_status))
    mksini_save()
    mksini_free()


def set_beep_status():
    mksini_load()
    mksini_set("beep", "enable", to_string(g.config.beep_status))
    mksini_save()
    mksini_free()
    system("sync")


def get_language_status():
    mksini_load()
    g.config.language_status = mksini_getint("system", "language", 0)
    mksini_free()


def get_extruder_target():
    mksini_load()
    g.config.extruder_target = mksini_getint("target", "extruder", 200)
    mksini_free()


def set_extruder_target(target):
    if target != 0:
        mksini_load()
        mksini_set("target", "extruder", to_string(target))
        mksini_save()
        mksini_free()
        system("sync")


def get_heater_bed_target():
    mksini_load()
    g.config.heater_bed_target = mksini_getint("target", "heaterbed", 40)
    mksini_free()


def set_heater_bed_target(target):
    if target != 0:
        mksini_load()
        cout("######## ", target)
        mksini_set("target", "heaterbed", to_string(target))
        mksini_save()
        mksini_free()
        system("sync")


def get_hot_target():
    mksini_load()
    g.config.hot_target = mksini_getint("target", "hot", 40)
    mksini_free()


def set_hot_target(target):
    mksini_load()
    cout("######## ", target)
    mksini_set("target", "hot", to_string(target))
    mksini_save()
    mksini_free()
    system("sync")


def set_babystep(value):
    mksini_load()
    mksini_set("babystep", "value", value)
    mksini_save()
    mksini_free()
    system("sync")


def get_babystep():
    mksini_load()
    g.config.babystep_value = mksini_getstring("babystep", "value", "0.000")
    g.config.adxl_offset = mksini_getstring("babystep", "adxl_offset", "0.000")
    mksini_free()


def init():
    """4.4.22 start-up settings (the QIDI Link part is not implemented)."""
    get_babystep()
    get_ethernet()


def load_versions():
    mksversion_load()
    g.config.version_soc = mksversion_soc("V1.1.1")
    g.config.version_mcu = mksversion_mcu("V0.10.0")
    g.config.version_ui = mksversion_ui("V1.1.1")
    mksversion_free()


def wifi_save_config():
    page_to(ids.WIFI_SAVING)
    network.mks_save_config()
    sleep(2)
    get_wlan0_status()


def get_total_time():
    g.ep.Send(json_get_job_totals())


def get_oobe_enabled():
    mksini_load()
    g.config.oobe_enabled = mksini_getboolean("oobe", "enable", 0)
    mksini_free()
    return g.config.oobe_enabled


def set_oobe_enabled(enable):
    mksini_load()
    mksini_set("oobe", "enable", to_string(bool(enable)))
    mksini_save()
    mksini_free()
    system("sync")


def restore_config():
    system("rm " + paths.gcode_files() + "/.cache/*")
    g.screen.main_picture_refreshed = False
    system("curl -X POST http://127.0.0.1:7125/server/history/reset_totals")
    system("curl -X DELETE 'http://127.0.0.1:7125/server/history/job?all=true'")
    system("cp /root/config.mksini " + paths.klipper_config() + "/config.mksini")
    system("cp " + paths.klipper_config() + "/saved_variables.cfg.bak " + paths.klipper_config() + "/saved_variables.cfg")
    g.ep.Send(json_run_a_gcode("SAVE_VARIABLE VARIABLE=z_offset VALUE=0"))
    page_to(ids.MAIN)


def get_ethernet():
    mksini_load()
    g.config.ethernet = int(mksini_getboolean("mks_ethernet", "enable", 0))
    mksini_free()
    return g.config.ethernet


def set_ethernet(target):
    cout("Setting ethernet:", target)
    mksini_load()
    mksini_set("mks_ethernet", "enable", to_string(target))
    mksini_save()
    mksini_free()
    g.config.ethernet = target
