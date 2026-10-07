"""Helpers shared by the pages: widget pairs, picture transfer to the screen."""

import contextlib
import time

from xindi import state as g
from xindi.screen import pics
from xindi.util.cpp import substr


def picc_group(names, selected, on_picc, off_picc, on_picc2, off_picc2):
    for i, name in enumerate(names):
        g.port.picc(name, on_picc if i == selected else off_picc)
    for i, name in enumerate(names):
        g.port.picc2(name, on_picc2 if i == selected else off_picc2)


def cut_after_point(text, n):
    """``s.substr(0, s.find(".") + n)``"""
    return substr(text, 0, text.find(".") + n)


def heating_widget(temp_widget, button, target):
    """The number and the button of a heater show with their colour whether the heater is on."""
    if target == 0:
        g.port.pco(temp_widget, "65535")
        g.port.picc(button, pics.printing_row_off)
        g.port.picc2(button, pics.printing_press_off)
    else:
        g.port.pco(temp_widget, "63488")
        g.port.picc(button, pics.printing_row_on)
        g.port.picc2(button, pics.printing_press_on)


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


def two_state_button(button, is_on, on_pic, off_pic, on_press, off_press):
    g.port.picc(button, on_pic if is_on else off_pic)
    g.port.picc2(button, on_press if is_on else off_press)


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
