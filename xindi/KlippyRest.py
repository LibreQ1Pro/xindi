"""Port of src/KlippyRest.cpp - Moonraker HTTP API requests."""

from .cpp import b2s
from .mks_log import MKSLOG_BLUE, cerr
from . import HTTPRequest as http


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
