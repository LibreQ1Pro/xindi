"""Handling of the "notify_gcode_response" messages of Moonraker."""

import time
import logging
import re

from . import state as g
from . import pageids as ids
from . import ui
from .cpp import (jget, jstr, json_dump, to_string, substr, stream_float, f32)

log = logging.getLogger(__name__)


def parse_gcode_response(params):
    from . import actions, pages, settings
    log.debug("%s", json_dump(params))
    if params is not None:
        params0 = jstr(jget(params, 0))

        # 4.4.2 CLL screen sleep feature
        if g.screen.page == ids.SCREEN_SLEEP:   # SCREEN_SLEEP has no refresh function, switching pages here can't conflict
            ui.page_to(g.screen.previous_page)
            if g.screen.previous_caselight_value:
                actions.led_on_off()
                g.screen.previous_caselight_value = False

        # bltouch: z_offset: 1.000
        if params0 == "// Klipper state: Ready":
            g.klippy.idle_timeout_state = "Ready"
            log.info("Klipper restarted and is ready, sending the subscriptions")
            g.klippy.webhooks_state = "ready"
            g.klippy.webhooks_state_message = "Klipper state: Ready"
            time.sleep(5)
            actions.sub_object_status()
            time.sleep(2)
            actions.get_object_status()
            settings.get_babystep()    # 4.4.22 (was init_mks_status())
            if not g.levelling.all_level_saving:
                g.levelling.all_level_saving = True
            log.info("State after the restart: %s", g.klippy.webhooks_state)
        elif params0 == "// Klipper state: Disconnect":
            actions.sub_object_status()
        elif substr(params0, 0, 19) == "// PID parameters: ":
            log.info("// PID parameters: ")
            # std::regex_match() of a single decimal number against the whole line
            # never matches here, so only empty sub matches are printed.
            m = re.fullmatch(r"(\d+\.\d+)", params0)
            groups = [m.group(0), m.group(1), ""] if m else ["", "", ""]
            if m:
                log.debug("pid_Kp == %s", groups[0])
                log.debug("pid_Ki == %s", groups[1])
                log.debug("pid_Kd == %s", groups[2])
            log.debug("%s", groups[0])
            log.debug("%s", groups[1])
            log.debug("%s", groups[2])
            log.debug("Got the PID values")
        elif substr(params0, 0, 20) == "// probe: z_offset: ":
            log.info("Got z_offset: %s", substr(params0, 20))
            temp = stream_float(substr(params0, 20))
            temp = -temp
            temp = f32(temp - 0.15)      # subtract 0.15mm as required
            value = to_string(temp)
            babystep = substr(value, 0, value.find(".") + 4)
            settings.set_babystep(babystep)        # store the babystep in our config file
        elif substr(params0, 0, 22) == "// bltouch: z_offset: ":
            log.info("Got z_offset: %s", substr(params0, 22))
            temp = stream_float(substr(params0, 22))
            temp = -temp
            value = to_string(temp)
            babystep = substr(value, 0, value.find(".") + 4)
            settings.set_babystep(babystep)        # store the babystep in our config file
        elif params0 == "// action:cancel":
            pass
        elif substr(params0, 0, 28) == "// Klipper state: Disconnect":
            pass
        elif substr(params0, 0, 23) == "!! Must home axis first":
            pages.move_home_tips()
        elif substr(params0, 0, 29) == "!! Extrude below minimum temp":
            pages.filament_tips()
        elif substr(params0, 0, 31) == "// Recommended shaper_type_x = ":
            temp = substr(params0, 31)
            m = re.search(r"(\d+\.\d+)", temp)      # matches a decimal number
            if m:
                g.levelling.shaper_freq_x = m.group(0)
            log.debug("Got the input shaping result")
            log.info("Shaper_freq_x = %s", g.levelling.shaper_freq_x)
        elif substr(params0, 0, 31) == "// Recommended shaper_type_y = ":
            temp = substr(params0, 31)
            m = re.search(r"(\d+\.\d+)", temp)
            if m:
                g.levelling.shaper_freq_y = m.group(0)
            log.debug("Got the input shaping result")
            log.info("Shaper_freq_y = %s", g.levelling.shaper_freq_y)
        elif substr(params0, 0, 14) == "// Z position:":
            start = params0.find(">") + 1
            end = substr(params0, start).find("<") - 1
            g.levelling.str_manual_level_offset = substr(params0, start, end)
            log.debug("%s", substr(params0, start, end))
        elif substr(params0, 0, 21) == "!! Move out of range:":
            pages.move_tips()
        elif substr(params0, 0, 52) == "!! Can not update MCU 'mcu' config as it is shutdown":
            g.klippy.webhooks_state_message = "Can not update MCU 'mcu' config as it is shutdown"
        elif substr(params0, 0, 33) == "// accelerometer values (x, y, z)":
            pass
        elif substr(params0, 0, 12) == "// Lost comm":
            pass
        elif params0 == "Can not update":
            pass
        elif params0.find("Result is z=") != -1:     # 4.4.3 CLL save the z-offset only once the printer is ready again
            if g.screen.page == ids.AUTO_MOVING or g.screen.page == ids.OPEN_CALIBRATE:
                pass
        elif params0 == "!! Insufficient disk space, unable to read the file.":
            g.screen.jump_memory_warning = True
        elif params0.find("!! Printer is not ready") != -1:
            pass    # CLL nothing to do
        elif substr(params0, 0, 2) == "!!":
            g.screen.error_message = params0
            actions.detect_error()
        elif (params0.find("// Filament dia (measured mm):") != -1 or params0.find("// Filament NOT present") != -1
              or params0.find("echo: Filament run out") != -1):    # 4.4.2 CLL support mates and hall filament width sensors
            g.files.filament_message = params0
            actions.check_filament_width()
        elif substr(params0, 0, 12) == "// metadata=":     # 4.1.7 CLL web print information subscription (deprecated)
            pass
        elif params0.find("echo: Position init complete") != -1:    # CLL messages prefixed with "echo:" are custom responses
            if g.screen.page == ids.OPEN_CALIBRATE or g.screen.page == ids.AUTO_MOVING:
                g.levelling.step_1 = True
        elif params0.find("echo: Bed mesh calibrate complete") != -1:
            if g.screen.page == ids.OPEN_CALIBRATE:
                g.levelling.step_2 = True
                g.klippy.webhooks_state = "shutdown"
            if g.screen.page == ids.AUTO_MOVING:
                g.levelling.step_4 = True
        elif params0.find("echo: Input shaping complete") != -1:
            if g.screen.page == ids.OPEN_CALIBRATE:
                g.levelling.step_3 = True
            if g.screen.page == ids.SYNTONY_MOVE:
                g.levelling.step_1 = True
        elif params0.find("echo: Nozzle cleared") != -1:
            if g.screen.page == ids.AUTO_MOVING:
                g.levelling.step_2 = True
        elif params0.find("echo: Nozzle cooled") != -1:
            if g.screen.page == ids.AUTO_MOVING:
                g.levelling.step_3 = True
        elif params0.find("echo: Heat up complete") != -1:
            if (g.screen.page == ids.FILAMENT_POP_2 or g.screen.page == ids.FILAMENT_POP_3
                    or g.screen.page == ids.AUTO_UNLOAD):
                g.levelling.step_1 = True
        elif (params0.find("echo: Detected unexpected interruption during the last print.") != -1
              or params0.find("echo: Yes: RESUME_INTERRUPTED") != -1 or params0.find("echo: No: CLEAR_LAST_FILE") != -1):
            pass
        # 4.4.22: any of the load / unload messages on any of the three pages
        elif (params0.find("echo: Load finish") != -1 or params0.find("echo: Unload finish") != -1
              or params0.find("echo: Filament loaded") != -1 or params0.find("echo: Filament unloaded") != -1):
            if g.screen.page in (ids.AUTO_UNLOAD, ids.FILAMENT_POP_2, ids.FILAMENT_POP_3):
                g.levelling.step_2 = True
                log.debug("load / unload filament success, step_2=%d", 1)
