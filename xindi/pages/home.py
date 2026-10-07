"""The main page."""

import logging

from xindi import state as g
from xindi.pages import file_list
from xindi.pages.widgets import two_state_button
from xindi.printer import job
from xindi.screen import pics, thumbnail
from xindi.util.cpp import substr, to_string

log = logging.getLogger(__name__)


def main_heater(temp_widget, button, target):
    """CLL heating state on the main page: the colour of the number and the button of a heater."""
    g.port.pco(temp_widget, "65535" if target == 0 else "63488")
    two_state_button(button, target != 0, pics.main_on, pics.main_off, pics.main_on_press, pics.nav_btn_press)


def main_last_file_picture():
    """CLL the picture and the name of the last printed file (the first entry of the file list)."""
    g.files.list_pages = 0
    g.files.list_current_pages = 0
    g.files.list_folder_layers = 0
    g.files.list_previous_path = ""
    g.files.list_root_path = file_list.DEFAULT_DIR
    g.files.list_path = ""
    file_list.refresh_page_files(g.files.list_current_pages)
    if g.files.list_list_show_type[0] != "[c]":
        g.port.pic("b[0]", pics.main_bg_noimg)
        g.port.picc("last_file_btn", pics.main_bg_noimg)
        g.port.picc2("last_file_btn", pics.main_on_press)
        g.port.txt("last_file_name", "")
        g.port.vis("last_file_pic", "0")
        return

    g.port.txt("last_file_name", g.files.list_list_show_name[0])
    name0 = g.files.list_list_show_name[0]
    # NOTE: thumbnail from the gcode file instead of .cache/.thumbs/<name>-160x160.png / .jpg
    picture_path = thumbnail.GcodeRef(substr(g.files.list_path + "/.cache/" + name0, 1))
    log.info("Picture path:%s", picture_path)
    thumb = thumbnail.find(picture_path, 160, "PNG")
    if thumb is None:
        g.port.pic("b[0]", pics.main_bg_noimg)
        g.port.picc("last_file_btn", pics.main_bg_noimg)
        g.port.picc2("last_file_btn", pics.main_on_press)
        g.port.vis("last_file_pic", "0")
        return

    log.info("Found png picture" if thumb.fmt == "PNG" else "Found jpg picture")
    g.port.pic("b[0]", pics.main_bg_photo)
    g.port.picc("last_file_btn", pics.main_bg_photo)
    g.port.picc2("last_file_btn", pics.nav_btn_press)
    if thumb.fmt == "PNG":
        g.port.vis("last_file_pic", "1")
    file_list.send_file_picture(picture_path, 160, "last_file_pic")
    g.screen.main_picture_detected = True


def main():
    g.port.val("nozzle_temp", to_string(g.klippy.extruder_temperature))
    g.port.val("bed_temp", to_string(g.klippy.heater_bed_temperature))
    g.port.val("chamber_temp", to_string(g.klippy.hot_temperature))

    g.port.picc("usb_icon", pics.main_off if file_list.detect_disk() == 0 else pics.main_on)    # CLL USB drive inserted?
    g.port.picc("wifi_icon", pics.main_off if g.net.status_result.wpa_state == "COMPLETED" else pics.main_on)

    # LED logo, beeper
    two_state_button("light_btn", g.klippy.caselight_value != 0,
                      pics.main_on, pics.main_off, pics.main_on_press, pics.nav_btn_press)
    two_state_button("beep_btn", g.klippy.out_pin_beep_value != 0,
                      pics.main_on, pics.main_off, pics.main_on_press, pics.nav_btn_press)

    main_heater("nozzle_temp", "nozzle_btn", g.klippy.extruder_target)
    main_heater("bed_temp", "bed_btn", g.klippy.heater_bed_target)
    main_heater("chamber_temp", "chamber_btn", g.klippy.hot_target)

    # CLL refresh the picture after every boot or print
    if not g.screen.main_picture_refreshed:
        main_last_file_picture()
        g.screen.main_picture_refreshed = True

    # CLL ask for the power loss recovery once after boot
    if not g.screen.open_reprint_asked:
        job.check_print_interrupted()
        g.screen.open_reprint_asked = True
