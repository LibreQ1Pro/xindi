"""The pages of the automatic levelling, input shaping and bed calibration."""

import logging
import time

from xindi import state as g
from xindi.config import settings
from xindi.pages.widgets import cut_after_point, picc_group
from xindi.printer import heating, klipper
from xindi.screen import pageids as ids, pics
from xindi.screen.navigation import page_to
from xindi.util.cpp import f32, system, to_string

log = logging.getLogger(__name__)


def syntony_finish():
    log.debug("Printer ide_timeout state: %s", g.klippy.idle_timeout_state)
    log.debug("Printer webhooks state: %s", g.klippy.webhooks_state)
    if not g.levelling.syntony_finished:
        g.levelling.syntony_finished = True
        g.levelling.all_level_saving = False

    if g.klippy.idle_timeout_state == "Ready" and g.klippy.webhooks_state == "ready":
        log.debug("Printer webhooks state: %s", g.klippy.webhooks_state)
        time.sleep(10)
        system("sync")      # make sure the config file is saved

        g.levelling.all_level_saving = False
        settings.get_babystep()  # 4.4.22 (was init_mks_status())
        klipper.sub_object_status()
        klipper.get_object_status()
        time.sleep(10)
        page_to(ids.LEVEL_MODE)
        log.info("Left from line 739")


def auto_level():
    names = ["step_001", "step_005", "step_01", "step_05"]
    if g.levelling.auto_level_dist == f32(0.01):
        picc_group(names, 0, pics.prebed_step_on, pics.prebed_step_off, pics.prebed_press_on, pics.prebed_press_off)
    elif g.levelling.auto_level_dist == f32(0.05):
        picc_group(names, 1, pics.prebed_step_on, pics.prebed_step_off, pics.prebed_press_on, pics.prebed_press_off)
    elif g.levelling.auto_level_dist == f32(0.1):
        picc_group(names, 2, pics.prebed_step_on, pics.prebed_step_off, pics.prebed_press_on, pics.prebed_press_off)
    elif g.levelling.auto_level_dist == f32(0.5):
        picc_group(names, 3, pics.prebed_step_on, pics.prebed_step_off, pics.prebed_press_on, pics.prebed_press_off)


def syntony_move():
    if g.screen.temp_idle_state != g.klippy.idle_timeout_state:
        g.screen.temp_idle_state = g.klippy.idle_timeout_state
        log.debug("Printer ide_timeout state: %s", g.klippy.idle_timeout_state)
        log.debug("Printer webhooks state: %s", g.klippy.webhooks_state)

    if g.levelling.step_1:
        time.sleep(15)
        page_to(ids.SYNTONY_FINISH)
        g.levelling.step_1 = False


def auto_finish():
    if g.klippy.idle_timeout_state == "Idle" and g.klippy.webhooks_state == "ready":
        g.levelling.auto_level_finished = True


def auto_moving():
    g.port.txt("bed_temp", "(" + to_string(g.klippy.heater_bed_temperature) + "/" +
                 to_string(g.klippy.heater_bed_target) + ")")
    if g.levelling.step_1:
        g.port.picc("steps_bar", pics.auto_steps_1)
        g.port.pco("step2_txt", "65535")
        g.port.pco("step1_txt", "38066")
        g.port.vis("spin1", "0")
        g.port.vis("spin2", "1")
        g.levelling.step_1 = False
    if g.levelling.step_2:
        g.port.picc("steps_bar", pics.auto_steps_2)
        g.port.pco("step3_txt", "65535")
        g.port.pco("step2_txt", "38066")
        g.port.vis("spin2", "0")
        g.port.vis("spin3", "1")
        g.levelling.step_2 = False
    if g.levelling.step_3:
        g.port.picc("steps_bar", pics.auto_steps_3)
        g.port.pco("step4_txt", "65535")
        g.port.pco("step3_txt", "38066")
        g.port.vis("spin3", "0")
        g.port.vis("spin4", "1")
        g.levelling.step_3 = False
        g.klippy.idle_timeout_state = "Printing"
        settings.get_heater_bed_target()
        heating.set_heater_bed_target(g.config.heater_bed_target)
        g.ep.run_gcode("M190 S" + to_string(g.config.heater_bed_target) + "\n")
        time.sleep(1)
        g.ep.run_gcode("M4027\n")
    if g.levelling.step_4:
        time.sleep(15)
        page_to(ids.AUTO_FINISH)
        g.levelling.step_4 = False


def zoffset():
    i = 0
    while i < g.levelling.mesh_y_count:
        if i == 5:
            break
        j = 0
        while j < g.levelling.mesh_x_count:
            if j == 5:
                break
            temp = to_string(g.levelling.mesh_points[i][j])
            temp = cut_after_point(temp, 3)
            g.port.txt("cell_" + to_string(5 * i + j), temp)
            j += 1
        i += 1


def auto_heaterbed():
    g.port.txt("temp_now", to_string(g.klippy.heater_bed_temperature) + "/")
    g.port.val("temp_target", to_string(g.klippy.heater_bed_target))
    if g.klippy.heater_bed_target > 0:
        g.port.picc("heat_toggle", pics.autobed_on)
        g.port.picc2("heat_toggle", pics.autobed_press_on)
        g.port.pco("temp_now", "63488")
        g.port.pco("temp_target", "63488")
    else:
        g.port.picc("heat_toggle", pics.autobed_off)
        g.port.picc2("heat_toggle", pics.autobed_press_off)
        g.port.pco("temp_now", "65535")
        g.port.pco("temp_target", "65535")


def open_heaterbed():
    g.port.txt("t0", to_string(g.klippy.heater_bed_temperature) + "/")
    g.port.val("n0", to_string(g.klippy.heater_bed_target))
    if g.klippy.heater_bed_target > 0:
        g.port.picc("b0", pics.bedtemp_on)
        g.port.picc2("b0", pics.bedtemp_press_on)
        g.port.pco("t0", "63488")
        g.port.pco("n0", "63488")
    else:
        g.port.picc("b0", pics.bedtemp_off)
        g.port.picc2("b0", pics.bedtemp_press_off)
        g.port.pco("t0", "65535")
        g.port.pco("n0", "65535")


def bed_moving():
    if g.klippy.idle_timeout_state == "Ready":
        if g.screen.manual_count == 3:
            page_to(ids.PRE_BED_CALIBRATION)
        elif g.screen.manual_count == -2:
            page_to(ids.BED_FINISH)
        else:
            page_to(ids.BED_CALIBRATION)


def open_calibrate():
    if g.levelling.step_3:
        g.levelling.step_3 = False
        system("sync")      # CLL save the system information, then go to the filament loading page
        time.sleep(10)
        klipper.get_object_status()
        klipper.sub_object_status()
        page_to(ids.OPEN_FILAMENTVIDEO_0)
    if g.levelling.step_2 and g.klippy.webhooks_state == "ready":
        g.levelling.step_2 = False
        time.sleep(5)
        g.ep.run_gcode("M901")    # CLL input shaping after the bed levelling
    if g.levelling.step_1 and g.klippy.idle_timeout_state == "Ready":
        g.levelling.step_1 = False
        settings.get_heater_bed_target()
        heating.set_heater_bed_target(g.config.heater_bed_target)
        g.ep.run_gcode("M190 S" + to_string(g.config.heater_bed_target) + "\n")
        time.sleep(5)
        g.ep.run_gcode("M4027")   # CLL levelling after the platform / nozzle initialisation
