"""Shared by the click handlers."""

from .. import pageids as ids
from ..ui import page_to
from .. import state as g


def printer_not_failed():
    return g.klippy.webhooks_state != "shutdown" and g.klippy.webhooks_state != "error"


def nav_guarded(widget_id):
    """ALL_TO_* buttons of the pages that are reachable while Klipper is in an error state."""
    from .. import actions, filelist
    if widget_id == ids.ALL_TO_MAIN:
        if printer_not_failed():
            page_to(ids.MAIN)
        return True
    if widget_id == ids.ALL_TO_FILE_LIST:
        if printer_not_failed():
            filelist.go_to_file_list()
        return True
    if widget_id == ids.ALL_TO_ADJUST:
        if printer_not_failed():
            actions.go_to_adjust()
        return True
    return False
