"""Helpers shared by the pages: widget pairs, picture transfer to the screen."""

import contextlib
import time

from xindi import state as g
from xindi.util.cpp import substr


def face_group(names, selected, on="on", off="off"):
    """Of a row of buttons the selected one looks ``on``, the others ``off``."""
    for i, name in enumerate(names):
        g.port.face(name, on if i == selected else off)


def cut_after_point(text, n):
    """``s.substr(0, s.find(".") + n)``"""
    return substr(text, 0, text.find(".") + n)


def heating_widget(temp_widget, button, target):
    """The number and the button of a heater show with their colour whether the heater is on."""
    g.port.pco(temp_widget, "65535" if target == 0 else "63488")
    g.port.face(button, "heat_off" if target == 0 else "heat_on")


def send_chunks_txt(data):
    """Sends a picture string in 2048 byte pieces through the "add" text variable."""
    num = 2048
    length = len(data)
    end = num
    start = 0
    while start < length:
        if end > length:
            s = substr(data, start, length - start)
            g.port.txt("cp_pad", s)
            g.port.drain()
            g.port.txt_plus("cp_data", "cp_data", "cp_pad")
            g.port.drain()
            break
        s = substr(data, start, num)
        start = end
        end = end + num
        g.port.txt("cp_pad", s)
        g.port.drain()
        g.port.txt_plus("cp_data", "cp_data", "cp_pad")
        g.port.drain()


def send_chunks_cp(obj, data):
    """Writes a picture string in 2048 byte pieces into a picture widget."""
    num = 2048
    length = len(data)
    end = num
    start = 0
    while start < length:
        if end > length:
            part = substr(data, start, length - start)
            g.port.drain()
            g.port.cp_image(obj, part)
            break
        part = substr(data, start, num)
        start = end
        end = end + num
        g.port.drain()
        g.port.cp_image(obj, part)


def two_state_button(button, is_on):
    g.port.face(button, "on" if is_on else "off")


@contextlib.contextmanager
def fast_screen_link():
    """The pictures go over the serial line at 921600 baud."""
    g.port.baud(921600)
    time.sleep(0.05)
    g.port.set_baud(921600)
    try:
        yield
    finally:
        g.port.baud(115200)
        time.sleep(0.05)
        g.port.set_baud(115200)
