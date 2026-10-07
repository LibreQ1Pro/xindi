"""Dispatch of the messages received from Moonraker.

The responses are matched by the JSON-RPC id of the request (see
rpc_methods.method2id), notifications by their method name.
"""

from . import state as g
from . import pageids as ids
from .cpp import jget, jpath, jstr, jint, jeq, json_dump, json_clear
from .mks_log import MKSLOG_BLUE, MKSLOG_RED, cout, cerr
from .moonraker_api import string2json
from .printer_status import parse_subscribe_objects_status, parse_printer_info, parse_server_history_totals
from .file_browser import parse_file_estimated_time, parse_file_estimated_time_send
from .gcode_responses import parse_gcode_response


def json_parse(arg=None):
    from . import actions
    while True:
        # NOTE: the original polls is_get_message every 50 us and parses the
        # last message stored by the websocket thread; the port waits for the
        # next queued message, so that none is lost (see state.message_queue)
        g.rpc.message = g.rpc.message_queue.get()
        g.rpc.is_get_message = True
        if g.rpc.is_get_message:
            try:
                g.rpc.response = string2json(g.rpc.message)
                g.rpc.res = g.rpc.response
            except Exception as e:
                cerr(str(e), "\n")
            if jget(g.rpc.res, "id") is not None:
                cout(json_dump(jget(g.rpc.response, "id")))
                id_ = jint(jget(g.rpc.response, "id"))
                if id_ == 3545:
                    cout(json_dump(g.rpc.response))
                    parse_file_estimated_time(g.rpc.response)

                elif id_ == 4654:
                    cout(json_dump(g.rpc.response))
                    if jeq(jget(g.rpc.response, "result"), "ok"):
                        cout(json_dump(g.rpc.response))
                    elif jget(g.rpc.response, "result") is not None:
                        if jpath(g.rpc.response, "result", "status") is not None:
                            cout(json_dump(jpath(g.rpc.response, "result", "status")))
                            parse_subscribe_objects_status(jpath(g.rpc.response, "result", "status"))

                elif id_ == 5445:
                    cout(json_dump(g.rpc.response))
                    if jget(g.rpc.response, "result") is not None:
                        parse_printer_info(jget(g.rpc.response, "result"))

                elif id_ == 5656:       # total print time
                    cout(json_dump(g.rpc.response))
                    if jget(g.rpc.response, "result") is not None:
                        if jpath(g.rpc.response, "result", "job_totals") is not None:
                            parse_server_history_totals(jpath(g.rpc.response, "result", "job_totals"))

            if jget(g.rpc.res, "error") is not None:
                parse_error(jget(g.rpc.response, "error"))
            else:
                if jget(g.rpc.response, "method") is not None:
                    method = jstr(jget(g.rpc.response, "method"))
                    if method == "notify_proc_stat_update":
                        pass
                    elif method == "notify_gcode_response":
                        MKSLOG_RED("%s", g.rpc.message)
                        parse_gcode_response(jget(g.rpc.response, "params"))
                        MKSLOG_BLUE("Gcode response")
                    elif method == "notify_status_update":
                        parse_subscribe_objects_status(jpath(g.rpc.response, "params", 0))
                    elif method == "notify_klippy_ready":
                        cout(json_dump(g.rpc.response))
                        MKSLOG_BLUE("Klippy is ready")
                        # subscribe here
                        actions.get_object_status()
                        actions.sub_object_status()
                    elif method == "notify_klippy_shutdown":
                        MKSLOG_BLUE("Klippy shutdown")
                    elif method == "notify_klippy_disconnected":
                        MKSLOG_BLUE("Klippy disconnected")
                        actions.get_object_status()
                        actions.sub_object_status()
                    elif method == "notify_filelist_changed":
                        g.files.filelist_changed = True
                        MKSLOG_BLUE("File list changed")
                        g.screen.file_list_refreshed = False      # 4.4.22
                        if not g.levelling.all_level_saving:
                            g.levelling.all_level_saving = True
                    elif method == "notify_update_response":
                        MKSLOG_BLUE("Update manager response")
                    elif method == "notify_update_refreshed":
                        MKSLOG_BLUE("Update manager refreshed")
                    elif method == "notify_cpu_throttled":
                        MKSLOG_BLUE("Moonraker process statistics update")
                    elif method == "notify_history_changed":
                        # 4.4.3 CLL web print information subscription
                        if g.screen.page in (ids.PRINTING, ids.PRINT_ZOFFSET,
                                                 ids.PRINT_FILAMENT, ids.PRINTING_2):
                            pass
                        else:
                            parse_file_estimated_time_send(jpath(g.rpc.response, "params", 0, "job", "metadata"))
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
            g.rpc.response = json_clear(g.rpc.response)
            g.rpc.is_get_message = False


def parse_error(error):
    cout(json_dump(error))
