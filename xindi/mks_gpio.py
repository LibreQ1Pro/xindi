"""Port of src/mks_gpio.cpp - sysfs GPIO helpers (not started by the program)."""

import os
import select

from .cpp import access, system, usleep
from .mks_log import MKSLOG_BLUE


def gpio_config(attr, val, gpio_path):
    file_path = "%s/%s" % (gpio_path, attr)
    try:
        fd = os.open(file_path, os.O_WRONLY)
    except OSError as e:
        print("open error: %s" % e)
        return -1
    try:
        if len(val) != os.write(fd, val.encode()):
            print("write error")
            return -1
    except OSError as e:
        print("write error: %s" % e)
        return -1
    finally:
        os.close(fd)
    return 0


def _export(number, exit_on_write_error=False):
    if access("/sys/class/gpio/gpio%d" % number):
        arg = str(number).encode()
        try:
            fd = os.open("/sys/class/gpio/export", os.O_WRONLY)
        except OSError as e:
            print("open error: %s" % e)
            return -1
        try:
            if len(arg) != os.write(fd, arg):
                raise OSError("short write")
        except OSError as e:
            print("write error: %s" % e)
            os.close(fd)
            if exit_on_write_error:
                os._exit(255)
            return -1
        os.close(fd)
    return 0


def _set_output(number, value):
    if _export(number):
        return -1
    path = "/sys/class/gpio/gpio%d" % number
    # output mode
    if gpio_config("direction", "out", path):
        print("Failed to configure the output mode")
        return -1
    # polarity
    if gpio_config("active_low", "0", path):
        print("Failed to configure the polarity")
        return -1
    # output level
    if gpio_config("value", value, path):
        print("Failed to set the output level")
        return -1
    return 0


# 32+2*8+5=53
def set_GPIO1_C5_low():
    return _set_output(53, "0")


def set_GPIO1_C5_high():
    return _set_output(53, "1")


def _init_input(number, edge):
    if _export(number, exit_on_write_error=True):
        return -1
    path = "/sys/class/gpio/gpio%d" % number
    if gpio_config("direction", "in", path):
        return -1
    if gpio_config("active_low", "0", path):
        return -1
    if gpio_config("edge", edge, path):
        return -1
    return 0


# 32+1*8+2=42
def init_GPIO1_B2():
    return _init_input(42, "falling")


def _poll_value(path):
    fd = os.open(path, os.O_RDONLY)
    os.read(fd, 1)          # read once to clear the state
    poller = select.poll()
    poller.register(fd, select.POLLPRI)
    return fd, poller


def monitor_GPIO1_B2(arg=None):
    fd, poller = _poll_value("/sys/class/gpio/gpio42/value")
    while True:
        events = poller.poll(-1)
        if not events:
            continue
        for _, revents in events:
            if revents & select.POLLPRI:
                os.lseek(fd, 0, os.SEEK_SET)
                val = os.read(fd, 1)
                if val[:1] == b"0":
                    # low level detected
                    # 4.4.1 CLL power off page disabled
                    system("echo TEST > /root/TESTGPIO; sync")
                    system("sync; shutdown -h now;")
        usleep(110000)


def init_GPIO1_C3():
    return _init_input(51, "both")


def monitor_GPIO1_C3(arg=None):
    from . import actions
    cnt = 0
    debounce_limit = 5              # debounce counter limit
    debounce_interval = 30          # debounce interval (ms)
    fd, poller = _poll_value("/sys/class/gpio/gpio51/value")
    while True:
        events = poller.poll(-1)
        if not events:
            continue
        for _, revents in events:
            if revents & select.POLLPRI:
                os.lseek(fd, 0, os.SEEK_SET)
                val = os.read(fd, 1)
                if val[:1] == b"1":
                    if cnt >= debounce_limit:
                        actions.go_to_page_power_off()
                        actions.shutdown_mcu()
                        set_GPIO1_B3_low()
                        system("sync")
                        cnt = 0
                    else:
                        cnt += 1
                        usleep(debounce_interval * 1000)
                else:
                    cnt = 0
                MKSLOG_BLUE("cnt=%d", cnt)
        usleep(110000)


def set_GPIO1_B3_low():
    return _set_output(43, "0")
