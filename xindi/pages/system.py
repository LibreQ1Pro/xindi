"""The system settings page."""

from xindi import state as g
from xindi.config import settings
from xindi.screen import pics


def common_setting():
    g.shown.oobe_enabled = settings.get_oobe_enabled()
    g.port.txt("version_txt", g.config.version_soc)
    if not g.shown.oobe_enabled:
        g.port.picc("reset_btn", pics.reset_row)
        g.port.picc2("reset_btn", pics.settings_press)
    else:
        g.port.picc("reset_btn", pics.reset_row_on)
        g.port.picc2("reset_btn", pics.settings_press_on)
