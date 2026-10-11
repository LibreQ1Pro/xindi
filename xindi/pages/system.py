"""The system settings page."""

from xindi import state as g
from xindi.config import settings
from xindi.screen import pics


def common_setting():
    g.shown.oobe_enabled = settings.get_oobe_enabled()
    if g.shown.oobe_enabled:
        pictures = (pics.reset_row_on, pics.settings_press_on)
    else:
        pictures = (pics.reset_row, pics.settings_press)
    if g.shown.changed("reset_btn", pictures):
        g.port.picc("reset_btn", pictures[0])
        g.port.picc2("reset_btn", pictures[1])
