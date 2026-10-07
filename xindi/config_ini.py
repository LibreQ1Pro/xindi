"""Access to config.mksini (the settings of the screen backend) and the version file."""

import os

from . import paths
from .cpp import b2s, s2b
from .mks_log import cout
from .iniparser import (iniparser_load, iniparser_getstring, iniparser_getint,
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


class IniFile:
    """One ini file: reads come from the dictionary loaded at open time, ``save()`` writes it back."""

    def __init__(self, path):
        self.path = path
        self._dict = iniparser_load(path)
        if self._dict is None:
            cout("Ini parse failure!")

    def get_string(self, section, key, default):
        if self._dict is None:
            return default
        value = iniparser_getstring(self._dict, s2b(section + ":" + key), s2b(default))
        return b2s(value) if value is not None else ""

    def get_int(self, section, key, default):
        if self._dict is None:
            return default
        return iniparser_getint(self._dict, s2b(section + ":" + key), default)

    def get_bool(self, section, key, default):
        if self._dict is None:
            return bool(default)
        return iniparser_getboolean(self._dict, s2b(section + ":" + key), default) != 0

    def set(self, section, key, value):
        if self._dict is not None:
            iniparser_set(self._dict, s2b(section + ":" + key), s2b(value))

    def save(self):
        """Write the dictionary back to the file"""
        if self._dict is None:
            return
        try:
            ini = open(self.path, "wb")
        except OSError:
            print("[error] open mksini failed", end="")
            return
        with ini:
            iniparser_dump_ini(self._dict, ini)


def open_settings():
    """config.mksini, created with the defaults when it does not exist."""
    if not os.path.exists(_inipath()):
        _create_default_mksini(_inipath())
    return IniFile(_inipath())


def save_setting(section, key, value):
    """Change one value of config.mksini and write the file."""
    ini = open_settings()
    ini.set(section, key, value)
    ini.save()


def open_version_file():
    return IniFile(VERSION_PATH)
