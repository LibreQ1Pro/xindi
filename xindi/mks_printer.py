"""Port of src/mks_printer.cpp - parsing of the Klipper printer object status."""

from . import state as g
from .cpp import jget, jpath, jstr, jfloat, jdouble, jbool, f32, c_int, c_round, json_dump
from .mks_log import MKSLOG_BLUE, MKSLOG_RED, cout


def _cout_float(v):
    """std::cout << float (6 significant digits)"""
    return "%g" % v


def parse_server_history_totals(totals):
    if jget(totals, "total_print_time") is not None:
        g.klippy.total_print_time = jdouble(jget(totals, "total_print_time"))
    cout("total_print_time = ", c_int(g.klippy.total_print_time))


def parse_printer_probe(probe):
    if jget(probe, "x_offset") is not None:
        g.klippy.probe_x_zoffset = jfloat(jget(probe, "x_offset"))
    if jget(probe, "y_offset") is not None:
        g.klippy.probe_y_zoffset = jfloat(jget(probe, "y_offset"))
    if jget(probe, "z_offset") is not None:
        g.klippy.probe_z_zoffset = jfloat(jget(probe, "z_offset"))


def parse_printer_beep(beep):
    if jget(beep, "value") is not None:
        g.klippy.out_pin_beep_value = jfloat(jget(beep, "value"))
        MKSLOG_BLUE("printer_out_pin_beep_value = %f", g.klippy.out_pin_beep_value)


def parse_printer_caselight(caselight):
    if jget(caselight, "value") is not None:
        g.klippy.caselight_value = jfloat(jget(caselight, "value"))
        MKSLOG_BLUE("printer_caselight_value = %f", g.klippy.caselight_value)


def parse_printer_heater_fan_my_nozzle_fan1(heater_fan_my_nozzle_fan1):
    if jget(heater_fan_my_nozzle_fan1, "speed") is not None:
        g.klippy.heater_fan_my_nozzle_fan1_speed = jfloat(jget(heater_fan_my_nozzle_fan1, "speed"))


def parse_printer_out_pin_fan0(out_pin_fan0):
    if jget(out_pin_fan0, "speed") is not None:
        g.klippy.out_pin_fan0_value = jfloat(jget(out_pin_fan0, "speed"))
    cout("printer_out_pin_fan0_value ", _cout_float(g.klippy.out_pin_fan0_value))


def parse_printer_out_pin_fan2(out_pin_fan2):
    if jget(out_pin_fan2, "speed") is not None:
        g.klippy.out_pin_fan2_value = jfloat(jget(out_pin_fan2, "speed"))
    cout("printer_out_pin_fan2_value ", _cout_float(g.klippy.out_pin_fan2_value))


def parse_printer_out_pin_fan3(out_pin_fan3):
    if jget(out_pin_fan3, "speed") is not None:
        g.klippy.out_pin_fan3_value = jfloat(jget(out_pin_fan3, "speed"))
    cout("printer_out_pin_fan3_value ", _cout_float(g.klippy.out_pin_fan3_value))


def parse_filament_switch_sensor_fila(filament_switch_sensor):
    if jget(filament_switch_sensor, "filament_detected") is not None:
        g.klippy.fila_sensor_detected = jbool(jget(filament_switch_sensor, "filament_detected"))
        cout("!!!! filament_detected: ", int(g.klippy.fila_sensor_detected))
    if jget(filament_switch_sensor, "enabled") is not None:
        g.klippy.fila_sensor_enabled = jbool(jget(filament_switch_sensor, "enabled"))
        cout("!!!! enabled: ", int(g.klippy.fila_sensor_enabled))


def parse_idle_timeout(idle_timeout):
    if jget(idle_timeout, "state") is not None:
        g.klippy.idle_timeout_state = jstr(jget(idle_timeout, "state"))
        cout("idle_timeout: ", g.klippy.idle_timeout_state)
        MKSLOG_RED("idle_timeout changed: %s", g.klippy.idle_timeout_state)


def parse_bed_mesh(bed_mesh):
    if jget(bed_mesh, "mesh_min") is not None:
        g.levelling.mesh_min[0] = jfloat(jpath(bed_mesh, "mesh_min", 0))
        g.levelling.mesh_min[1] = jfloat(jpath(bed_mesh, "mesh_min", 1))
    if jget(bed_mesh, "mesh_max") is not None:
        g.levelling.mesh_max[0] = jfloat(jpath(bed_mesh, "mesh_max", 0))
        g.levelling.mesh_max[1] = jfloat(jpath(bed_mesh, "mesh_max", 1))
    if jget(bed_mesh, "profiles") is not None:
        if jpath(bed_mesh, "profiles", "default") is not None:
            mesh_params = jpath(bed_mesh, "profiles", "default", "mesh_params")
            if mesh_params is not None:
                if jget(mesh_params, "tension") is not None:
                    g.levelling.mesh_tension = jfloat(jget(mesh_params, "tension"))
                if jget(mesh_params, "mesh_x_pps") is not None:
                    g.levelling.mesh_mesh_x_pps = jfloat(jget(mesh_params, "mesh_x_pps"))
                if jget(mesh_params, "algo") is not None:
                    g.levelling.mesh_algo = jstr(jget(mesh_params, "algo"))
                if jget(mesh_params, "min_x") is not None:
                    g.levelling.mesh_min_x = jfloat(jget(mesh_params, "min_x"))
                    cout("printer_bed_mesh_profiles_mks_mesh_params_min_x = ", _cout_float(g.levelling.mesh_min_x))
                if jget(mesh_params, "min_y") is not None:
                    g.levelling.mesh_min_y = jfloat(jget(mesh_params, "min_y"))
                if jget(mesh_params, "y_count") is not None:
                    g.levelling.mesh_y_count = jfloat(jget(mesh_params, "y_count"))
                if jget(mesh_params, "mesh_y_pps") is not None:
                    g.levelling.mesh_mesh_y_pps = jfloat(jget(mesh_params, "mesh_y_pps"))
                if jget(mesh_params, "x_count") is not None:
                    g.levelling.mesh_x_count = jfloat(jget(mesh_params, "x_count"))
                if jget(mesh_params, "max_x") is not None:
                    g.levelling.mesh_max_x = jfloat(jget(mesh_params, "max_x"))
                if jget(mesh_params, "max_y") is not None:
                    g.levelling.mesh_max_y = jfloat(jget(mesh_params, "max_y"))

            points = jpath(bed_mesh, "profiles", "default", "points")
            if points is not None:
                i = 0
                while i < g.levelling.mesh_y_count:
                    if i == 5:
                        break
                    j = 0
                    while j < g.levelling.mesh_x_count:
                        if j == 5:
                            break
                        g.levelling.mesh_points[i][j] = jfloat(jpath(points, i, j))
                        j += 1
                    i += 1


def parse_webhooks(webhooks):
    if jget(webhooks, "state") is not None:
        g.klippy.webhooks_state = jstr(jget(webhooks, "state"))
    if jget(webhooks, "state_message") is not None:
        g.klippy.webhooks_state_message = jstr(jget(webhooks, "state_message"))
    MKSLOG_RED("State message: %s", g.klippy.webhooks_state_message)


def parse_gcode_move(gcode_move):
    if jget(gcode_move, "speed_factor") is not None:
        g.klippy.gcode_move_speed_factor = jfloat(jget(gcode_move, "speed_factor"))
    if jget(gcode_move, "speed") is not None:
        g.klippy.gcode_move_speed = jfloat(jget(gcode_move, "speed"))
    if jget(gcode_move, "extrude_factor") is not None:
        g.klippy.gcode_move_extrude_factor = jfloat(jget(gcode_move, "extrude_factor"))
    if jget(gcode_move, "homing_origin") is not None:
        g.klippy.gcode_move_homing_origin[0] = jfloat(jpath(gcode_move, "homing_origin", 0))
        g.klippy.gcode_move_homing_origin[1] = jfloat(jpath(gcode_move, "homing_origin", 1))
        g.klippy.gcode_move_homing_origin[2] = jfloat(jpath(gcode_move, "homing_origin", 2))
        g.klippy.gcode_move_homing_origin[3] = jfloat(jpath(gcode_move, "homing_origin", 3))
    if jget(gcode_move, "gcode_position") is not None:
        g.klippy.gcode_move_gcode_position[2] = jfloat(jpath(gcode_move, "gcode_position", 2))
        # round(float * 1000) / 1000 - float arithmetic (std::round(float) overload)
        g.klippy.gcode_z_position = f32(f32(c_round(f32(g.klippy.gcode_move_gcode_position[2] * 1000))) / 1000)


def parse_toolhead(toolhead):
    if jget(toolhead, "position") is not None:
        g.klippy.toolhead_position[0] = jdouble(jpath(toolhead, "position", 0))
        g.klippy.x_position = c_round(g.klippy.toolhead_position[0] * 10) / 10
        g.klippy.toolhead_position[1] = jdouble(jpath(toolhead, "position", 1))
        g.klippy.y_position = c_round(g.klippy.toolhead_position[1] * 10) / 10
        g.klippy.toolhead_position[2] = jdouble(jpath(toolhead, "position", 2))
        g.klippy.z_position = c_round(g.klippy.toolhead_position[2] * 10) / 10
        g.klippy.toolhead_position[3] = jdouble(jpath(toolhead, "position", 3))

    if jget(toolhead, "axis_minimum") is not None:
        for i in range(4):
            g.klippy.toolhead_axis_minimum[i] = jdouble(jpath(toolhead, "axis_minimum", i))

    if jget(toolhead, "axis_maximum") is not None:
        for i in range(4):
            g.klippy.toolhead_axis_maximum[i] = jdouble(jpath(toolhead, "axis_maximum", i))


def parse_extruder(extruder):
    if jget(extruder, "temperature") is not None:
        temp = jfloat(jget(extruder, "temperature"))
        g.klippy.extruder_temperature = c_int(temp + 0.5)
    if jget(extruder, "target") is not None:
        temp = jfloat(jget(extruder, "target"))
        g.klippy.extruder_target = c_int(temp + 0.5)


def parse_heater_bed(heater_bed):
    if jget(heater_bed, "temperature") is not None:
        temp = jfloat(jget(heater_bed, "temperature"))
        g.klippy.heater_bed_temperature = c_int(temp + 0.5)
    if jget(heater_bed, "target") is not None:
        temp = jfloat(jget(heater_bed, "target"))
        g.klippy.heater_bed_target = c_int(temp + 0.5)


def parse_heater_generic_hot(heater_generic_hot):
    if jget(heater_generic_hot, "temperature") is not None:
        temp = jfloat(jget(heater_generic_hot, "temperature"))
        g.klippy.hot_temperature = c_int(temp + 0.5)
    if jget(heater_generic_hot, "target") is not None:
        temp = jfloat(jget(heater_generic_hot, "target"))
        g.klippy.hot_target = c_int(temp + 0.5)


def parse_fan(fan):
    if jget(fan, "speed") is not None:
        g.klippy.fan_speed = jfloat(jget(fan, "speed"))


def parse_heater_fan(heater_fan):
    if jget(heater_fan, "speed") is not None:
        g.klippy.heater_fan_speed = jfloat(jget(heater_fan, "speed"))


def parse_print_stats(print_stats):
    if jget(print_stats, "state") is not None:
        g.klippy.print_stats_state = jstr(jget(print_stats, "state"))
        cout("\033[31;1m", "printer_print_stats_state = ", g.klippy.print_stats_state, "\033[0m")
    if jget(print_stats, "filename") is not None:
        g.klippy.print_stats_filename = jstr(jget(print_stats, "filename"))
        cout("\033[31;1m", "printer_print_stats_filename = ", g.klippy.print_stats_filename, "\033[0m")
    if jget(print_stats, "print_duration") is not None:
        g.klippy.print_stats_print_duration = jfloat(jget(print_stats, "print_duration"))
    if jget(print_stats, "total_duration") is not None:
        g.klippy.print_stats_total_duration = jfloat(jget(print_stats, "total_duration"))


def parse_display_status(display_status):
    temp = 0.0
    if jget(display_status, "progress") is not None:
        temp = jdouble(jget(display_status, "progress"))
        g.klippy.display_status_progress = c_int(temp * 100)


def parse_pause_resume(pause_resume):
    cout(json_dump(pause_resume))
    if jget(pause_resume, "is_paused") is not None:
        g.klippy.pause_resume_is_paused = jbool(jget(pause_resume, "is_paused"))


def parse_subscribe_objects_status(status):
    """Parse the status of the subscribed objects"""
    if jget(status, "idle_timeout") is not None:
        parse_idle_timeout(jget(status, "idle_timeout"))
    if jget(status, "bed_mesh") is not None:
        cout(json_dump(jget(status, "bed_mesh")))
        parse_bed_mesh(jget(status, "bed_mesh"))
        for i in range(5):
            for j in range(5):
                cout("############# Points :", i, ", ", j, " ", _cout_float(g.levelling.mesh_points[i][j]))
    if jget(status, "webhooks") is not None:
        parse_webhooks(jget(status, "webhooks"))
    if jget(status, "gcode_move") is not None:
        parse_gcode_move(jget(status, "gcode_move"))
    if jget(status, "toolhead") is not None:
        parse_toolhead(jget(status, "toolhead"))
    if jget(status, "extruder") is not None:
        parse_extruder(jget(status, "extruder"))
    if jget(status, "heater_bed") is not None:
        parse_heater_bed(jget(status, "heater_bed"))
    if jget(status, "heater_generic chamber") is not None:
        parse_heater_generic_hot(jget(status, "heater_generic chamber"))
    if jget(status, "fan") is not None:
        parse_fan(jget(status, "fan"))
    if jget(status, "heater_fan fan1") is not None:
        parse_heater_fan(jget(status, "heater_fan fan1"))
    if jget(status, "pause_resume") is not None:
        parse_pause_resume(jget(status, "pause_resume"))
    if jget(status, "print_stats") is not None:
        parse_print_stats(jget(status, "print_stats"))
    if jget(status, "display_status") is not None:
        parse_display_status(jget(status, "display_status"))
    if jget(status, "heater_fan my_nozzle_fan1") is not None:
        parse_printer_heater_fan_my_nozzle_fan1(jget(status, "heater_fan my_nozzle_fan1"))
    if jget(status, "fan_generic cooling_fan") is not None:
        parse_printer_out_pin_fan0(jget(status, "fan_generic cooling_fan"))
    if jget(status, "fan_generic auxiliary_cooling_fan") is not None:
        parse_printer_out_pin_fan2(jget(status, "fan_generic auxiliary_cooling_fan"))
    if jget(status, "fan_generic chamber_circulation_fan") is not None:
        parse_printer_out_pin_fan3(jget(status, "fan_generic chamber_circulation_fan"))
    if jget(status, "filament_switch_sensor fila") is not None:
        parse_filament_switch_sensor_fila(jget(status, "filament_switch_sensor fila"))
    if jget(status, "output_pin caselight") is not None:
        parse_printer_caselight(jget(status, "output_pin caselight"))
    if jget(status, "output_pin sound") is not None:
        parse_printer_beep(jget(status, "output_pin sound"))
    if jget(status, "probe") is not None:
        parse_printer_probe(jget(status, "probe"))


def subscribe_objects_status():
    objects = {}
    objects["extruder"] = None
    objects["heater_generic chamber"] = None
    objects["heater_bed"] = None
    objects["gcode_move"] = None
    objects["fan"] = ["speed"]
    objects["heater_fan fan1"] = ["speed"]
    objects["toolhead"] = None
    objects["print_stats"] = ["print_duration", "total_duration", "filament_used", "filename", "state", "message"]
    objects["display_status"] = ["progress", "message"]
    objects["idle_timeout"] = ["state"]
    objects["pause_resume"] = ["is_paused"]
    objects["webhooks"] = ["state", "state_message"]
    objects["firmware_retraction"] = ["retract_length", "retract_speed", "unretract_extra_length",
                                      "unretract_speed"]
    objects["bed_mesh"] = None
    objects["heater_fan my_nozzle_fan1"] = None
    objects["filament_switch_sensor fila"] = ["filament_detected", "enabled"]
    objects["fan_generic cooling_fan"] = ["speed", "rpm"]
    objects["fan_generic auxiliary_cooling_fan"] = ["speed", "rpm"]
    objects["fan_generic chamber_circulation_fan"] = ["speed", "rpm"]
    objects["output_pin caselight"] = None
    objects["output_pin sound"] = None
    objects["probe"] = None
    return objects


def get_cal_printing_time(print_time, estimated_time, progress):
    left_time = 0
    total_time = 0
    if progress <= 10:
        total_time = estimated_time
        left_time = total_time - print_time
    elif progress > 10:
        from .cpp import cdiv, i32
        total_time = cdiv(i32(print_time * 100), progress)
        left_time = total_time - print_time
    return left_time


def parse_printer_info(result):
    if jget(result, "software_version") is not None:
        g.klippy.info_software_version = jstr(jget(result, "software_version"))
        MKSLOG_RED("Version: %s", g.klippy.info_software_version)
