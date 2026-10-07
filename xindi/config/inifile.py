"""Access to config.mksini (the settings of the screen backend) and the version file."""

import logging
import os
import re

from xindi.util import paths
from xindi.util.cpp import i32, strtol

log = logging.getLogger(__name__)

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
    log.debug("%s", "Created " + path + " with the default settings")


class IniFile:
    """An ini file: ``[section]`` lines and ``key = value`` lines, keys and sections in lower case.

    ``values`` is None when the file does not exist or has a syntax error; the getters then give the default.
    """

    def __init__(self, path):
        self.path = path
        self.values = self._parse(path)
        if self.values is None:
            log.debug("Ini parse failure!")

    @staticmethod
    def _parse(path):
        try:
            with open(path, "rb") as f:
                text = f.read().decode("utf-8", "replace")
        except OSError:
            return None
        values = {}
        section = ""
        pending = ""
        for number, raw in enumerate(text.split("\n"), 1):
            line = pending + raw.rstrip()
            if line.endswith("\\"):          # the line continues
                pending = line[:-1]
                continue
            pending = ""
            line = line.strip()
            if not line or line[0] in "#;":
                continue
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1].strip().lower()
                values.setdefault(section, {})
                continue
            m = _KEY_VALUE.match(line)
            if not m:
                log.error("iniparser: syntax error in %s (%d):\n-> %s", path, number, line)
                return None
            key, quoted, plain = m.group(1).strip().lower(), m.group(2) or m.group(3), m.group(4)
            if quoted is None:
                quoted = (plain or "").split(";")[0].split("#")[0].strip()
            values.setdefault(section, {})[key] = quoted
        return values

    def _find(self, section, key):
        if self.values is None:
            return None
        return self.values.get(section.lower(), {}).get(key.lower())

    def get_string(self, section, key, default):
        value = self._find(section, key)
        return default if value is None else value

    def get_int(self, section, key, default):
        value = self._find(section, key)
        return default if value is None else i32(strtol(value, 0))

    def get_bool(self, section, key, default):
        first = (self._find(section, key) or "")[:1]
        if first in ("y", "Y", "1", "t", "T"):
            return True
        if first in ("n", "N", "0", "f", "F"):
            return False
        return bool(default)

    def set(self, section, key, value):
        if self.values is not None:
            self.values.setdefault(section.lower(), {})[key.lower()] = value

    def save(self):
        """Write the file back, in the layout the original program wrote."""
        if self.values is None:
            return
        try:
            ini = open(self.path, "wb")
        except OSError:
            print("[error] open mksini failed", end="")
            return
        with ini:
            for section, entries in self.values.items():
                if not section:
                    continue
                ini.write(("\n[%s]\n" % section).encode())
                for key, value in entries.items():
                    ini.write(("%-30s = %s\n" % (key, value)).encode())
                ini.write(b"\n")
            ini.write(b"\n")


# key = "value" | key = 'value' | key = value ; comment | key = (empty)
_KEY_VALUE = re.compile(r"([^=]+?)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\"']*?))\s*$")


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
