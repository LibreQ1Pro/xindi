"""Port of src/MakerbaseParseIni.cpp - access to /home/mks/klipper_config/config.mksini."""

from . import paths
from . import state as g
from .cpp import b2s, s2b
from .mks_log import cout
from .iniparser import (iniparser_load, iniparser_freedict, iniparser_getstring, iniparser_getint,
                        iniparser_getdouble, iniparser_getboolean, iniparser_set, iniparser_unset,
                        iniparser_dump_ini)

XINDI_PLUS = 1
XINDI_MAX = 0
XINDI_MINI = 0

# INIPATH = "/root/config.mksini"
# INIPATH = "/home/mks/klipper_config/config.mksini"


def _inipath():
    """INIPATH (the config directory is found at run time, see paths.py)"""
    return paths.klipper_config() + "/config.mksini"


VERSION_PATH = "/root/xindi/version"


def updateini_load():
    """CLL information about the online update"""
    g.mksini = iniparser_load("/root/auto_update/update_info.ini")
    if g.mksini is None:
        cout("Ini parse failure")
        return -1
    return 0


def progressini_load():
    """CLL progress of the online update"""
    g.mksini = iniparser_load("/root/auto_update/update_progress.ini")
    if g.mksini is None:
        cout("Ini parse failure")
        return -1
    return 0


def mksini_load():
    g.mksini = iniparser_load(_inipath())
    if g.mksini is None:
        cout("Ini parse failure!")
        return -1
    return 0


def mksini_free():
    iniparser_freedict(g.mksini)


def mksini_getstring(section, key, default):
    sk = section + ":" + key
    value = iniparser_getstring(g.mksini, s2b(sk), s2b(default))
    return b2s(value) if value is not None else ""


def mksini_getint(section, key, notfound):
    sk = section + ":" + key
    return iniparser_getint(g.mksini, s2b(sk), notfound)


def mksini_getdouble(section, key, notfound):
    sk = section + ":" + key
    return iniparser_getdouble(g.mksini, s2b(sk), notfound)


def mksini_getboolean(section, key, notfound):
    sk = section + ":" + key
    value = iniparser_getboolean(g.mksini, s2b(sk), notfound)
    return False if value == 0 else True


def mksini_set(section, key, value):
    sk = section + ":" + key
    return iniparser_set(g.mksini, s2b(sk), s2b(value))


def mksini_unset(section, key):
    sk = section + ":" + key
    iniparser_unset(g.mksini, s2b(sk))


def mksini_save():
    """Write the dictionary back to the config file"""
    try:
        ini = open(_inipath(), "wb")
    except OSError:
        print("[error] open mksini failed", end="")
        return
    with ini:
        iniparser_dump_ini(g.mksini, ini)


def mksversion_load():
    g.mksversion = iniparser_load(VERSION_PATH)
    if g.mksversion is None:
        cout("Mks version failure!")
        return -1
    return 0


def mksversion_free():
    iniparser_freedict(g.mksversion)


def mksversion_mcu(default):
    value = iniparser_getstring(g.mksversion, b"version:mcu", s2b(default))
    return b2s(value) if value is not None else ""


def mksversion_ui(default):
    value = iniparser_getstring(g.mksversion, b"version:ui", s2b(default))
    return b2s(value) if value is not None else ""


def mksversion_soc(default):
    value = iniparser_getstring(g.mksversion, b"version:soc", s2b(default))
    return b2s(value) if value is not None else ""
