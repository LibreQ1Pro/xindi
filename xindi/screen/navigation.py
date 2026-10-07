"""Switching the page of the screen and the version the screen compares."""

from xindi import state as g
from xindi.screen import pageids as ids
from xindi.util.cpp import to_string


# The version of the port as semver. The screen cannot compare semver, so it gets major * 10000 + minor * 100 + patch
# (1.7.10 -> 10710, 0.1.0 -> 100); the main page of the screen firmware shows a warning when it differs from the number
# it was built for (display_firmware/pages/main.json). The screen forgets it on every power-up, so it is sent again
# whenever the main page is opened and when the screen reports a start.
VERSION = (0, 1, 0)


def version_number(version):
    """The number the screen compares: major (0-99), minor (0-99), patch (0-99)."""
    major, minor, patch = version
    if not (0 <= major <= 99 and 0 <= minor <= 99 and 0 <= patch <= 99):
        raise ValueError("version %r does not fit the screen: every part must be 0..99" % (version,))
    return major * 10000 + minor * 100 + patch


UI_VERSION = str(version_number(VERSION))


def send_ui_version():
    g.port.val("logo.version", UI_VERSION)


def page_to(page_id):
    if page_id == ids.MAIN:
        send_ui_version()
    g.screen.previous_page = g.screen.page
    g.screen.page = page_id
    g.port.page(to_string(page_id))
