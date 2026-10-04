"""Port of src/MakerbaseParseMessage.cpp - dispatch of the messages received from Moonraker.

The responses are matched by the JSON-RPC id of the request (see
MakerbaseCommand.method2id), notifications by their method name.
"""

from . import state as g
from . import ui
from .cpp import jget, jpath, jstr, jint, jeq, json_dump, json_clear, usleep
from .mks_log import MKSLOG_BLUE, MKSLOG_RED, cout, cerr
from .MoonrakerAPI import string2json
from .mks_error import parse_error
from .mks_printer import parse_subscribe_objects_status, parse_printer_info, parse_server_history_totals
from .mks_file import parse_file_estimated_time, parse_file_estimated_time_send
from .mks_gcode import parse_gcode_response


def json_parse(arg=None):
    from . import event
    while True:
        if g.is_get_message == True:
            try:
                g.response = string2json(g.message)
                g.res = g.response
            except Exception as e:
                cerr(str(e), "\n")
            if jget(g.res, "id") is not None:
                cout(json_dump(jget(g.response, "id")))
                id_ = jint(jget(g.response, "id"))
                if id_ == 3545:
                    cout(json_dump(g.response))
                    parse_file_estimated_time(g.response)

                elif id_ == 4654:
                    cout(json_dump(g.response))
                    if jeq(jget(g.response, "result"), "ok"):
                        cout(json_dump(g.response))
                    elif jget(g.response, "result") is not None:
                        if jpath(g.response, "result", "status") is not None:
                            cout(json_dump(jpath(g.response, "result", "status")))
                            parse_subscribe_objects_status(jpath(g.response, "result", "status"))

                elif id_ == 5445:
                    cout(json_dump(g.response))
                    if jget(g.response, "result") is not None:
                        parse_printer_info(jget(g.response, "result"))

                elif id_ == 5656:       # total print time
                    cout(json_dump(g.response))
                    if jget(g.response, "result") is not None:
                        if jpath(g.response, "result", "job_totals") is not None:
                            parse_server_history_totals(jpath(g.response, "result", "job_totals"))

            if jget(g.res, "error") is not None:
                parse_error(jget(g.response, "error"))
            else:
                if jget(g.response, "method") is not None:
                    method = jstr(jget(g.response, "method"))
                    if method == "notify_proc_stat_update":
                        pass
                    elif method == "notify_gcode_response":
                        MKSLOG_RED("%s", g.message)
                        parse_gcode_response(jget(g.response, "params"))
                        MKSLOG_BLUE("Gcode response")
                    elif method == "notify_status_update":
                        parse_subscribe_objects_status(jpath(g.response, "params", 0))
                    elif method == "notify_klippy_ready":
                        cout(json_dump(g.response))
                        MKSLOG_BLUE("Klippy is ready")
                        # subscribe here
                        event.get_object_status()
                        event.sub_object_status()
                    elif method == "notify_klippy_shutdown":
                        MKSLOG_BLUE("Klippy shutdown")
                    elif method == "notify_klippy_disconnected":
                        MKSLOG_BLUE("Klippy disconnected")
                        event.get_object_status()
                        event.sub_object_status()
                    elif method == "notify_filelist_changed":
                        g.filelist_changed = True
                        MKSLOG_BLUE("File list changed")
                        if g.all_level_saving == False:
                            g.all_level_saving = True
                    elif method == "notify_update_response":
                        MKSLOG_BLUE("Update manager response")
                    elif method == "notify_update_refreshed":
                        MKSLOG_BLUE("Update manager refreshed")
                    elif method == "notify_cpu_throttled":
                        MKSLOG_BLUE("Moonraker process statistics update")
                    elif method == "notify_history_changed":
                        # 4.4.3 CLL web print information subscription
                        if g.current_page_id in (ui.TJC_PAGE_PRINTING, ui.TJC_PAGE_PRINT_ZOFFSET,
                                                 ui.TJC_PAGE_PRINT_FILAMENT, ui.TJC_PAGE_PRINTING_2):
                            pass
                        else:
                            parse_file_estimated_time_send(jpath(g.response, "params", 0, "job", "metadata"))
                            MKSLOG_BLUE("History changed")
                    elif method == "notify_user_created":
                        MKSLOG_BLUE("Authorized user created")
                    elif method == "notify_user_deleted":
                        MKSLOG_BLUE("Authorized user deleted")
                    elif method == "notify_service_state_changed":
                        pass
                    elif method == "notify_job_queue_changed":
                        MKSLOG_BLUE("Job queue changed")
                    elif method == "notify_button_event":
                        MKSLOG_BLUE("Button event")
                    elif method == "notify_announcement_update":
                        MKSLOG_BLUE("Announcement update event")
                    elif method == "notify_announcement_dismissed":
                        MKSLOG_BLUE("Announcement dismissed event")
                    elif method == "notify_announcement_wake":
                        MKSLOG_BLUE("Announcement wake event")
                    elif method == "notify_agent_event":
                        MKSLOG_BLUE("Agent event")
                    elif method == "notify_power_changed":
                        MKSLOG_BLUE("notify_power_changed")
            g.response = json_clear(g.response)
            g.is_get_message = False
        usleep(50)
