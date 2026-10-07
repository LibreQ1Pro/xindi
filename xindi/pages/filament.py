"""The filament page, its pop-ups and the unload page."""

from xindi import state as g
from xindi.screen import pageids as ids, pics
from xindi.util.cpp import c_int, f32, to_string


def filament_tips():
    if g.screen.page == ids.OPEN_FILAMENTVIDEO_3:
        pass
    elif g.screen.page == ids.PRINT_FILAMENT:
        g.screen.jump_print_low_temp = True
    else:
        g.screen.jump_filament_pop_1 = True


def filament_pop():
    g.port.txt("temp_txt", "(" + to_string(g.klippy.extruder_temperature) + "/" +
                 to_string(g.klippy.extruder_target) + "℃)")
    if g.levelling.step_1:
        g.levelling.step_1 = False
        g.port.picc("steps_bar", pics.pop_steps_2)
        g.port.pco("step2_txt", "65535")
        g.port.pco("step1_txt", "38066")
        g.port.pco("temp_txt", "38066")
        g.port.vis("spin2", "0")
        g.port.vis("spin3", "1")
    if g.levelling.step_2 and g.klippy.idle_timeout_state == "Ready":
        g.levelling.step_2 = False
        g.port.picc("steps_bar", pics.pop_steps_3)
        g.port.pco("step3_txt", "65535")
        g.port.pco("step2_txt", "38066")
        g.port.vis("done_btn", "1")
        g.port.vis("alt_btn", "1")
        g.port.vis("spin3", "0")


def filament_set_fan():
    if not g.screen.move_fan_setting:     # CLL refresh only while the slider is not being dragged
        fan0 = to_string(c_int(f32(g.klippy.out_pin_fan0_value * 100)))
        fan2 = to_string(c_int(f32(g.klippy.out_pin_fan2_value * 100)))
        fan3 = to_string(c_int(f32(g.klippy.out_pin_fan3_value * 100)))
        g.port.val("fan1_slider", fan0)
        g.port.val("fan1_val", fan0)
        g.port.val("fan2_slider", fan2)
        g.port.val("fan2_val", fan2)
        g.port.val("fan3_slider", fan3)
        g.port.val("fan3_val", fan3)
        for name, value in (("fan1_toggle", g.klippy.out_pin_fan0_value), ("fan2_toggle", g.klippy.out_pin_fan2_value),
                            ("fan3_toggle", g.klippy.out_pin_fan3_value)):
            if value == 0:
                g.port.picc(name, pics.fan_row_off)
                g.port.picc2(name, pics.fan_press_off)
            else:
                g.port.picc(name, pics.fan_row_on)
                g.port.picc2(name, pics.fan_press_on)


def filament():
    g.port.txt("nozzle_temp", to_string(g.klippy.extruder_temperature))
    g.port.val("nozzle_set", to_string(g.klippy.extruder_target))
    g.port.txt("bed_temp", to_string(g.klippy.heater_bed_temperature))
    g.port.val("bed_set", to_string(g.klippy.heater_bed_target))
    g.port.txt("chamber_temp", to_string(g.klippy.hot_temperature))
    g.port.val("chamber_set", to_string(g.klippy.hot_target))
    if g.klippy.extruder_target > 0:   # CLL button state depends on the nozzle heating
        g.port.picc("nozzle_toggle", pics.filament_row_on)
        g.port.picc2("nozzle_toggle", pics.filament_press_on)
        g.port.picc("nozzle_row", pics.filament_row_on)
        g.port.picc2("nozzle_row", pics.filament_press_on)
        g.port.pco("nozzle_temp", "63488")
    else:
        g.port.picc("nozzle_toggle", pics.filament_row_off)
        g.port.picc2("nozzle_toggle", pics.filament_press_off)
        g.port.picc("nozzle_row", pics.filament_row_off)
        g.port.picc2("nozzle_row", pics.filament_press_off)
        g.port.pco("nozzle_temp", "65535")

    if g.klippy.heater_bed_target > 0:     # CLL button state depends on the bed heating
        g.port.picc("bed_toggle", pics.filament_row_on)
        g.port.picc2("bed_toggle", pics.filament_press_on)
        g.port.picc("bed_row", pics.filament_row_on)
        g.port.picc2("bed_row", pics.filament_press_on)
        g.port.pco("bed_temp", "63488")
    else:
        g.port.picc("bed_toggle", pics.filament_row_off)
        g.port.picc2("bed_toggle", pics.filament_press_off)
        g.port.picc("bed_row", pics.filament_row_off)
        g.port.picc2("bed_row", pics.filament_press_off)
        g.port.pco("bed_temp", "65535")

    if g.klippy.hot_target > 0:
        g.port.picc("chamber_toggle", pics.filament_row_on)
        g.port.picc2("chamber_toggle", pics.filament_press_on)
        g.port.picc("chamber_row", pics.filament_row_on)
        g.port.picc2("chamber_row", pics.filament_press_on)
        g.port.pco("chamber_temp", "63488")
    else:
        g.port.picc("chamber_toggle", pics.filament_row_off)
        g.port.picc2("chamber_toggle", pics.filament_press_off)
        g.port.picc("chamber_row", pics.filament_row_off)
        g.port.picc2("chamber_row", pics.filament_press_off)
        g.port.pco("chamber_temp", "65535")

    sel = {10: 0, 50: 1, 100: 2}.get(g.klippy.filament_extruder_dist)
    if sel is not None:
        for k, name in enumerate(("step_10", "step_50", "step_100")):
            if k == sel:
                g.port.picc(name, pics.filament_row_on)
                g.port.picc2(name, pics.filament_press_on)
            else:
                g.port.picc(name, pics.filament_row_off)
                g.port.picc2(name, pics.filament_press_off)


def auto_unload():
    g.port.txt("temp_txt", "(" + to_string(g.klippy.extruder_temperature) + "/" +
                 to_string(g.klippy.extruder_target) + "℃)")
    if g.levelling.step_1:
        g.levelling.step_1 = False
        g.port.vis("spin1", "0")
        g.port.vis("spin2", "1")
        g.port.picc("steps_bar", pics.unload_steps_1)
        g.port.pco("step2_txt", "65535")
        g.port.pco("step1_txt", "38066")
    if g.levelling.step_2:
        g.levelling.step_2 = False
        g.port.vis("spin2", "0")
        g.port.picc("steps_bar", pics.unload_steps_2)
        g.port.pco("step3_txt", "65535")
        g.port.pco("step2_txt", "38066")
        g.port.vis("load_btn", "1")
        g.port.vis("ok", "1")
