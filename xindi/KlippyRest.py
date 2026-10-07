"""Port of src/KlippyRest.cpp - Moonraker HTTP API requests."""

from .cpp import b2s
from .mks_log import MKSLOG_BLUE, cerr
from . import HTTPRequest as http


def server_files_metadata(ip, port, filename):
    return send_request(ip, port, "server/files/metadata?filename=" + filename, "GET")


def printer_objects_query(ip, port, parameter):
    return send_request(ip, port, "printer/objects/query?" + parameter, "GET")


def printer_print_start(ip, port, filename):
    return send_request(ip, port, "printer/print/start?filename=" + filename, "POST")


def printer_print_pause(ip, port):
    return send_request(ip, port, "printer/print/pause", "POST")


def printer_print_resume(ip, port):
    return send_request(ip, port, "printer/print/resume", "POST")


def printer_print_cancel(ip, port):
    return send_request(ip, port, "printer/print/cancel", "POST")


def get_server_files_list(ip, port):
    return send_request(ip, port, "server/files/list?", "GET")


def get_server_files_directory(ip, port):
    return send_request(ip, port, "server/files/directory?", "GET")


def get_server_info(ip, port):
    return send_request(ip, port, "server/info", "GET")


def get_oneshot_token(ip, port):
    return send_request(ip, port, "access/oneshot_token", "GET")


def get_printer_info(ip, port):
    return send_request(ip, port, "printer/info", "GET")


# File delete
def delete_file_delete(ip, port, filepath):
    return send_request(ip, port, "server/files/" + filepath, "DELETE")


def get_thumbnail_stream(ip, port, thumbnail):
    url = "http://" + ip + ":" + port + "/server/files/gcodes/" + thumbnail
    request = http.Request(url)
    response = request.send("GET")
    if response.status.code == 200:
        return b2s(response.body)
    else:
        return ""


def send_request(ip, port, method, request_type):
    from .pages import replace_characters
    url = "http://" + ip + ":" + port + "/" + method
    str_response = ""
    url = replace_characters(url, " ", "%20")
    MKSLOG_BLUE("Sending request to %s", url)
    try:
        request = http.Request(url)
        response = request.send(request_type)
        str_response = b2s(response.body)
    except Exception as e:
        cerr("Request failed, error", str(e), "\n")
    return str_response
