"""Access to config.mksini (the settings of the screen backend) and the version file."""

import os

from . import paths
from . import state as g
from .cpp import b2s, s2b
from .mks_log import cout
from .iniparser import (iniparser_load, iniparser_freedict, iniparser_getstring, iniparser_getint,
                        iniparser_getboolean, iniparser_set, iniparser_dump_ini)

XINDI_PLUS = 1
XINDI_MAX = 0
XINDI_MINI = 0

# INIPATH = "/root/config.mksini"
# INIPATH = "/home/mks/klipper_config/config.mksini"


def _inipath():
    """INIPATH (the config directory is found at run time, see paths.py)"""
    return paths.klipper_config() + "/config.mksini"


VERSION_PATH = "/root/xindi/version"


# Python only: written when the file does not exist (QIDI's system image comes
# with one, other systems do not, and the settings could not be saved).  The
# values are the defaults the program uses when a key is missing.
DEFAULT_MKSINI = """[led]
enable = 0

[beep]
enable = 0

[system]
language = 0

[target]
extruder = 200
heaterbed = 40
hot = 40

[babystep]
value = 0.000
adxl_offset = 0.000

[fila]
enable = 0

[total]
time = 0

[oobe]
enable = 0

[mks_ethernet]
enable = 0

[app_connection]
method = 0

[app_server]
name =

[app]
device_code =
subdomain =
token =
username =
avatar =
bind_status =
"""


def _create_default_mksini(path):
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
    except OSError:
        return          # exists already (or the directory is missing)
    with os.fdopen(fd, "w") as ini:
        ini.write(DEFAULT_MKSINI)
    try:
        # owned like the directory, so that it can be edited in the web UI
        st = os.stat(os.path.dirname(path))
        os.chown(path, st.st_uid, st.st_gid)
        os.chmod(path, 0o666)
    except OSError:
        pass
    cout("Created " + path + " with the default settings")


def mksini_load():
    if not os.path.exists(_inipath()):
        _create_default_mksini(_inipath())
    g.config.mksini = iniparser_load(_inipath())
    if g.config.mksini is None:
        cout("Ini parse failure!")
        return -1
    return 0


def mksini_free():
    iniparser_freedict(g.config.mksini)


def mksini_getstring(section, key, default):
    sk = section + ":" + key
    value = iniparser_getstring(g.config.mksini, s2b(sk), s2b(default))
    return b2s(value) if value is not None else ""


def mksini_getint(section, key, notfound):
    sk = section + ":" + key
    return iniparser_getint(g.config.mksini, s2b(sk), notfound)


def mksini_getboolean(section, key, notfound):
    sk = section + ":" + key
    value = iniparser_getboolean(g.config.mksini, s2b(sk), notfound)
    return False if value == 0 else True


def mksini_set(section, key, value):
    sk = section + ":" + key
    return iniparser_set(g.config.mksini, s2b(sk), s2b(value))


def mksini_save():
    """Write the dictionary back to the config file"""
    try:
        ini = open(_inipath(), "wb")
    except OSError:
        print("[error] open mksini failed", end="")
        return
    with ini:
        iniparser_dump_ini(g.config.mksini, ini)


def mksversion_load():
    g.config.mksversion = iniparser_load(VERSION_PATH)
    if g.config.mksversion is None:
        cout("Mks version failure!")
        return -1
    return 0


def mksversion_free():
    iniparser_freedict(g.config.mksversion)


def mksversion_mcu(default):
    value = iniparser_getstring(g.config.mksversion, b"version:mcu", s2b(default))
    return b2s(value) if value is not None else ""


def mksversion_ui(default):
    value = iniparser_getstring(g.config.mksversion, b"version:ui", s2b(default))
    return b2s(value) if value is not None else ""


def mksversion_soc(default):
    value = iniparser_getstring(g.config.mksversion, b"version:soc", s2b(default))
    return b2s(value) if value is not None else ""
