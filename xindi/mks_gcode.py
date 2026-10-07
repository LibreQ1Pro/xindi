"""Port of src/mks_gcode.cpp - handling of the "notify_gcode_response" messages."""

import re

from . import state as g
from . import ui
from .cpp import (jget, jstr, json_dump, to_string, substr, stream_float, f32, sleep)
from .mks_log import MKSLOG, MKSLOG_BLUE, MKSLOG_RED, MKSLOG_YELLOW, cout


def parse_gcode_response(params):
    from . import event
    cout(json_dump(params))
    if params is not None:
        params0 = jstr(jget(params, 0))

        # 4.4.2 CLL screen sleep feature
        if g.current_page_id == ui.TJC_PAGE_SCREEN_SLEEP:   # SCREEN_SLEEP has no refresh function, switching pages here can't conflict
            ui.page_to(g.previous_page_id)
            if g.previous_caselight_value == True:
                event.led_on_off()
                g.previous_caselight_value = False

        # bltouch: z_offset: 1.000
        if params0 == "// Klipper state: Ready":
            g.printer_idle_timeout_state = "Ready"
            MKSLOG("Klipper restarted and is ready, sending the subscriptions")
            g.printer_webhooks_state = "ready"
            g.printer_webhooks_state_message = "Klipper state: Ready"
            sleep(5)
            event.sub_object_status()
            sleep(2)
            event.get_object_status()
            event.get_mks_babystep()    # 4.4.22 (was init_mks_status())
            if g.all_level_saving == False:
                g.all_level_saving = True
            MKSLOG_YELLOW("State after the restart: %s", g.printer_webhooks_state)
        elif params0 == "// Klipper state: Disconnect":
            event.sub_object_status()
        elif substr(params0, 0, 19) == "// PID parameters: ":
            MKSLOG_RED("// PID parameters: ")
            # std::regex_match() of a single decimal number against the whole line
            # never matches here, so only empty sub matches are printed.
            m = re.fullmatch(r"(\d+\.\d+)", params0)
            groups = [m.group(0), m.group(1), ""] if m else ["", "", ""]
            if m:
                cout("pid_Kp == ", groups[0])
                cout("pid_Ki == ", groups[1])
                cout("pid_Kd == ", groups[2])
            cout(groups[0])
            cout(groups[1])
            cout(groups[2])
            cout("Got the PID values")
        elif substr(params0, 0, 20) == "// probe: z_offset: ":
            MKSLOG_RED("Got z_offset: %s", substr(params0, 20))
            temp = stream_float(substr(params0, 20))
            temp = -temp
            temp = f32(temp - 0.15)      # subtract 0.15mm as required
            value = to_string(temp)
            babystep = substr(value, 0, value.find(".") + 4)
            event.set_mks_babystep(babystep)        # store the babystep in our config file
        elif substr(params0, 0, 22) == "// bltouch: z_offset: ":
            MKSLOG_RED("Got z_offset: %s", substr(params0, 22))
            temp = stream_float(substr(params0, 22))
            temp = -temp
            value = to_string(temp)
            babystep = substr(value, 0, value.find(".") + 4)
            event.set_mks_babystep(babystep)        # store the babystep in our config file
        elif params0 == "// action:cancel":
            pass
        elif substr(params0, 0, 28) == "// Klipper state: Disconnect":
            pass
        elif substr(params0, 0, 23) == "!! Must home axis first":
            event.move_home_tips()
        elif substr(params0, 0, 29) == "!! Extrude below minimum temp":
            event.filament_tips()
        elif substr(params0, 0, 31) == "// Recommended shaper_type_x = ":
            temp = substr(params0, 31)
            m = re.search(r"(\d+\.\d+)", temp)      # matches a decimal number
            if m:
                g.page_syntony_shaper_freq_x = m.group(0)
            cout("Got the input shaping result")
            MKSLOG_YELLOW("Shaper_freq_x = %s", g.page_syntony_shaper_freq_x)
        elif substr(params0, 0, 31) == "// Recommended shaper_type_y = ":
            temp = substr(params0, 31)
            m = re.search(r"(\d+\.\d+)", temp)
            if m:
                g.page_syntony_shaper_freq_y = m.group(0)
            cout("Got the input shaping result")
            MKSLOG_YELLOW("Shaper_freq_y = %s", g.page_syntony_shaper_freq_y)
        elif substr(params0, 0, 14) == "// Z position:":
            start = params0.find(">") + 1
            end = substr(params0, start).find("<") - 1
            g.str_manual_level_offset = substr(params0, start, end)
            cout(substr(params0, start, end))
        elif substr(params0, 0, 21) == "!! Move out of range:":
            event.move_tips()
        elif substr(params0, 0, 52) == "!! Can not update MCU 'mcu' config as it is shutdown":
            g.printer_webhooks_state_message = "Can not update MCU 'mcu' config as it is shutdown"
        elif substr(params0, 0, 33) == "// accelerometer values (x, y, z)":
            pass
        elif substr(params0, 0, 12) == "// Lost comm":
            pass
        elif params0 == "Can not update":
            pass
        elif params0.find("Result is z=") != -1:     # 4.4.3 CLL save the z-offset only once the printer is ready again
            if g.current_page_id == ui.TJC_PAGE_AUTO_MOVING or g.current_page_id == ui.TJC_PAGE_OPEN_CALIBRATE:
                pass
        elif params0 == "!! Insufficient disk space, unable to read the file.":
            g.jump_to_memory_warning = True
        elif params0.find("!! Printer is not ready") != -1:
            pass    # CLL nothing to do
        elif substr(params0, 0, 2) == "!!":
            g.error_message = params0
            event.detect_error()
        elif (params0.find("// Filament dia (measured mm):") != -1 or params0.find("// Filament NOT present") != -1
              or params0.find("echo: Filament run out") != -1):    # 4.4.2 CLL support mates and hall filament width sensors
            g.filament_message = params0
            event.check_filament_width()
        elif substr(params0, 0, 12) == "// metadata=":     # 4.1.7 CLL web print information subscription (deprecated)
            pass
        elif params0.find("echo: Position init complete") != -1:    # CLL messages prefixed with "echo:" are custom responses
            if g.current_page_id == ui.TJC_PAGE_OPEN_CALIBRATE or g.current_page_id == ui.TJC_PAGE_AUTO_MOVING:
                g.step_1 = True
        elif params0.find("echo: Bed mesh calibrate complete") != -1:
            if g.current_page_id == ui.TJC_PAGE_OPEN_CALIBRATE:
                g.step_2 = True
                g.printer_webhooks_state = "shutdown"
            if g.current_page_id == ui.TJC_PAGE_AUTO_MOVING:
                g.step_4 = True
        elif params0.find("echo: Input shaping complete") != -1:
            if g.current_page_id == ui.TJC_PAGE_OPEN_CALIBRATE:
                g.step_3 = True
            if g.current_page_id == ui.TJC_PAGE_SYNTONY_MOVE:
                g.step_1 = True
        elif params0.find("echo: Nozzle cleared") != -1:
            if g.current_page_id == ui.TJC_PAGE_AUTO_MOVING:
                g.step_2 = True
        elif params0.find("echo: Nozzle cooled") != -1:
            if g.current_page_id == ui.TJC_PAGE_AUTO_MOVING:
                g.step_3 = True
        elif params0.find("echo: Heat up complete") != -1:
            if (g.current_page_id == ui.TJC_PAGE_FILAMENT_POP_2 or g.current_page_id == ui.TJC_PAGE_FILAMENT_POP_3
                    or g.current_page_id == ui.TJC_PAGE_AUTO_UNLOAD):
                g.step_1 = True
        elif (params0.find("echo: Detected unexpected interruption during the last print.") != -1
              or params0.find("echo: Yes: RESUME_INTERRUPTED") != -1 or params0.find("echo: No: CLEAR_LAST_FILE") != -1):
            pass
        # 4.4.22: any of the load / unload messages on any of the three pages
        elif (params0.find("echo: Load finish") != -1 or params0.find("echo: Unload finish") != -1
              or params0.find("echo: Filament loaded") != -1 or params0.find("echo: Filament unloaded") != -1):
            if g.current_page_id in (ui.TJC_PAGE_AUTO_UNLOAD, ui.TJC_PAGE_FILAMENT_POP_2, ui.TJC_PAGE_FILAMENT_POP_3):
                g.step_2 = True
                MKSLOG_BLUE("load / unload filament success, step_2=%d", 1)
