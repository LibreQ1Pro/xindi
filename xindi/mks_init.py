"""Port of src/mks_init.cpp"""

import os

from . import paths
from . import state as g
from .cpp import substr, getline_all
from .mks_log import cout
from .MakerbaseShell import execute_cmd


def get_by_id():
    if not os.path.isdir("/dev/serial/by-id"):
        print("Failed to read the serial ports!!!!!!!!!!!!!!!!")
        return False
    else:
        g.serial_by_id = generate_by_id()
        g.serial_by_id = substr(g.serial_by_id, 0, 58)
        cout(len(g.serial_by_id), " Got the ID  " + g.serial_by_id)
        return True


def generate_by_id():
    cmd = "ls /dev/serial/by-id/*"
    result = execute_cmd(cmd)
    print(result, end="")
    return result


def FileStringReplace(instream, outstream):
    """instream / outstream: text file objects"""
    for line in instream:
        s = line.rstrip("\n")
        pos = s.find("serial:")      # look for "serial:" in every line
        if pos != -1:
            s = s[:pos] + "Jerry"    # replace it (left-over example code)
            outstream.write(s + "\n")
            continue
        outstream.write(s + "\n")
    return True


def get_cfg_by_id():
    path = paths.klipper_config() + "/MKS_THR.cfg"
    ret = ""
    for strline in getline_all(path):
        exists = strline.find("serial: ") == -1
        if not exists:
            cout(len(strline), " serial value in the CFG file " + substr(strline, 8, 62))
            ret = substr(strline, 8, 63)
            break
    return ret
