"""Port of src/MakerbaseNetwork.cpp"""

import sys

from .MakerbaseShell import execute_cmd


def get_wlan0_ip():
    cmd = "ifconfig wlan0 | awk 'NR==2{print $2}' | tr -d '\n\r'"
    result = execute_cmd(cmd)
    sys.stdout.write(result)
    return result


def get_eth0_ip():
    cmd = "ifconfig eth0 | awk 'NR==2{print $2}' | tr -d '\n\r'"
    result = execute_cmd(cmd)
    sys.stdout.write(result)
    return result


def get_wlan0_ip():
    """4.4.22"""
    cmd = "ifconfig wlan0 | awk 'NR==2{print $2}' | tr -d '\n\r'"
    result = execute_cmd(cmd)
    sys.stdout.write(result)
    return result
