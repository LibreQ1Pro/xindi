"""What a click on the screen does: ``handle`` looks the page up in the tables of the modules of this package."""

from ..mks_log import cout
from . import guide, printing, move_filament, levelling, system

HANDLERS = {}
for _module in (guide, printing, move_filament, levelling, system):
    for _page, _handler in _module.HANDLERS.items():
        assert _page not in HANDLERS, _page
        HANDLERS[_page] = _handler


def handle(page_id, widget_id, type_id):
    cout("+++++++++++++++++++", page_id)
    cout("+++++++++++++++++++", widget_id)
    cout("+++++++++++++++++++", type_id)
    handler = HANDLERS.get(page_id)
    if handler is not None:
        handler(page_id, widget_id)
