"""The system settings page."""

from xindi import state as g
from xindi.config import settings


def common_setting():
    g.shown.oobe_enabled = settings.get_oobe_enabled()
    state = "oobe_on" if g.shown.oobe_enabled else "oobe_off"
    if g.shown.changed("reset_btn", state):
        g.port.face("reset_btn", state)
