"""Switching to the main pages from the printer logic."""

from xindi import state as g
from xindi.screen import pageids as ids
from xindi.screen.navigation import page_to


def go_to_adjust():
    """CLL remember the last choice of the adjust page"""
    if g.screen.adjust_mode == "Filament":
        page_to(ids.FILAMENT)
    else:
        page_to(ids.MOVE)


def go_to_setting():
    if g.screen.set_mode == "Level_mode":
        page_to(ids.LEVEL_MODE)
    else:
        page_to(ids.COMMON_SETTING)
