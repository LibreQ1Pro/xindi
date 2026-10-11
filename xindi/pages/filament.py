"""The filament page, its pop-ups and the unload page."""

from xindi import state as g
from xindi.pages.widgets import face_group
from xindi.screen import pageids as ids
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
        g.port.face("steps_bar", "load_2")
        g.port.pco("step2_txt", "65535")
        g.port.pco("step1_txt", "38066")
        g.port.pco("temp_txt", "38066")
        g.port.vis("spin2", "0")
        g.port.vis("spin3", "1")
    if g.levelling.step_2 and g.klippy.idle_timeout_state == "Ready":
        g.levelling.step_2 = False
        g.port.face("steps_bar", "load_3")
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
            g.port.face(name, "off" if value == 0 else "on")


def filament():
    g.port.txt("nozzle_temp", to_string(g.klippy.extruder_temperature))
    g.port.val("nozzle_set", to_string(g.klippy.extruder_target))
    g.port.txt("bed_temp", to_string(g.klippy.heater_bed_temperature))
    g.port.val("bed_set", to_string(g.klippy.heater_bed_target))
    g.port.txt("chamber_temp", to_string(g.klippy.hot_temperature))
    g.port.val("chamber_set", to_string(g.klippy.hot_target))
    # CLL the buttons of a heater and its number show whether the heater is on
    for heater, target in (("nozzle", g.klippy.extruder_target), ("bed", g.klippy.heater_bed_target),
                           ("chamber", g.klippy.hot_target)):
        state = "on" if target > 0 else "off"
        g.port.face(heater + "_toggle", state)
        g.port.face(heater + "_row", state)
        g.port.pco(heater + "_temp", "63488" if target > 0 else "65535")

    sel = {10: 0, 50: 1, 100: 2}.get(g.klippy.filament_extruder_dist)
    if sel is not None:
        face_group(("step_10", "step_50", "step_100"), sel)


def auto_unload():
    g.port.txt("temp_txt", "(" + to_string(g.klippy.extruder_temperature) + "/" +
                 to_string(g.klippy.extruder_target) + "℃)")
    if g.levelling.step_1:
        g.levelling.step_1 = False
        g.port.vis("spin1", "0")
        g.port.vis("spin2", "1")
        g.port.face("steps_bar", "unload_1")
        g.port.pco("step2_txt", "65535")
        g.port.pco("step1_txt", "38066")
    if g.levelling.step_2:
        g.levelling.step_2 = False
        g.port.vis("spin2", "0")
        g.port.face("steps_bar", "unload_2")
        g.port.pco("step3_txt", "65535")
        g.port.pco("step2_txt", "38066")
        g.port.vis("load_btn", "1")
        g.port.vis("ok", "1")
