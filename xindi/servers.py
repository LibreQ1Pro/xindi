"""QIDI server selection page (the cloud itself is not implemented)."""

from . import paths
from . import state as g
from . import pics
from . import ui
from .ui import page_to
from .cpp import to_string, stoi, s2b, system, read_file, getline_all, json_parse, jget, jstr
from .mks_log import cout, cerr
from .send_msg import send_cmd_txt, send_cmd_picc, send_cmd_picc2, send_cmd_vis
from .MakerbaseParseIni import (mksini_load, mksini_free, mksini_getstring, mksini_getint,
                                mksini_set, mksini_save)


class Server_config(object):
    def __init__(self, address="", name=""):
        self.address = address
        self.name = name


def get_connection_method():
    mksini_load()
    g.net.connection_method = mksini_getint("app_connection", "method", 0)
    mksini_free()


def set_connection_method(target):
    g.screen.qr_refreshed = False
    mksini_load()
    cout("######## ", target)
    mksini_set("app_connection", "method", to_string(target))
    mksini_save()
    mksini_free()
    system("sync")


def get_selected_server():
    mksini_load()
    g.net.selected_server = mksini_getstring("app_server", "name", "")
    mksini_free()
    cout(g.net.selected_server)


def go_to_page(n):
    g.net.server_page = n
    g.net.total_server_count = 0
    g.net.server_configs.clear()
    if g.net.connection_method == 1 and g.net.status_result.wpa_state == "COMPLETED":
        page_to(ui.TJC_PAGE_SEARCH_SERVER)
        update(0)
        get_selected_server()
        get_connection_method()
    page_to(ui.TJC_PAGE_SERVER_SET)


def update_server_config(lines, config):
    for i in range(len(lines)):
        if lines[i] == "[app_server]":
            # make sure we are not at the end of the file
            if i + 1 < len(lines):
                # simply replace the next line
                lines[i + 1] = "name = " + config.name
                return

    # no [app_server] section: append it at the end of the file
    lines.append("[app_server]")
    lines.append("name = " + config.name)


def _config(id_):
    """std::map<int, Server_config>::operator[]"""
    if id_ not in g.net.server_configs:
        g.net.server_configs[id_] = Server_config()
    return g.net.server_configs[id_]


def update(choice):
    # CLL download the server list (json)
    if choice == 0:
        get_selected_server()
        server_for_command = "aws" if g.net.selected_server == "" else g.net.selected_server
        command = ("curl -s -S -L -o /root/frp/server_list.json http://www." + server_for_command +
                   ".qidi3dprinter.com:5050/downloads/server_list.json")
        cout("Executing command: ", command)
        system(command)
    else:
        g.screen.qr_refreshed = False      # CLL switching the server requires a new QR code

    g.net.total_server_count = 0
    FRPC_CONFIG_PATH = "/root/frp/frpc.toml"
    MKSCONFIG_PATH = paths.klipper_config() + "/config.mksini"
    SERVER_LIST_PATH = "/root/frp/server_list.json"     # path of the JSON file

    try:
        # read the JSON file and parse the server configurations
        data = read_file(SERVER_LIST_PATH)
        serverList = json_parse(data if data is not None else "")
        if isinstance(serverList, dict):
            items = [(k, serverList[k]) for k in sorted(serverList, key=s2b)]
        elif isinstance(serverList, list):
            items = [(str(k), v) for k, v in enumerate(serverList)]
        else:
            items = [("", serverList)] if serverList is not None else []
        for key, value in items:
            id_ = stoi(key)
            config = Server_config(jstr(jget(value, "address")), jstr(jget(value, "name")))
            cout(id_, ":", config.name)
            g.net.server_configs[id_] = config
            g.net.total_server_count += 1
    except Exception as e:
        cerr("fail_to_read:", str(e), "\n")

    if choice != 0:
        if choice not in g.net.server_configs:
            cout("Invalid choice. Please enter a valid option.")
            return

        config = g.net.server_configs[choice]

        # stop frpc.service
        cout("Stopping frpc.service...")
        system("sudo systemctl stop frpc.service")

        # update frpc.toml
        content = read_file(FRPC_CONFIG_PATH)
        if content is None:
            content = ""

        pos = content.find("serverAddr = ")
        if pos != -1:
            endPos = content.find("\n", pos)
            new = "serverAddr = \"" + config.address + "\""
            if endPos == -1:
                content = content[:pos] + new
            else:
                content = content[:pos] + new + content[endPos:]

        try:
            with open(FRPC_CONFIG_PATH, "wb") as frpcOut:
                frpcOut.write(s2b(content))
        except OSError:
            pass

        # read config.mksini into a list
        lines = getline_all(MKSCONFIG_PATH)

        # update the app_server configuration
        update_server_config(lines, config)

        # write the updated content back to config.mksini
        try:
            with open(MKSCONFIG_PATH, "wb") as mksOut:
                for outputLine in lines:
                    mksOut.write(s2b(outputLine) + b"\n")
        except OSError:
            pass

        # restart frpc.service
        cout("Starting frpc.service...")
        system("sudo systemctl start frpc.service")

        cout("Configuration updated to ", config.name, " successfully.")
        get_selected_server()


def refresh_page():
    if g.net.connection_method == 0 or g.net.status_result.wpa_state != "COMPLETED":
        send_cmd_picc(g.tty_fd, "b2", pics.server_row_off)
        send_cmd_picc2(g.tty_fd, "b2", pics.server_press_off)
        send_cmd_vis(g.tty_fd, "msg", "1")
        send_cmd_vis(g.tty_fd, "t0", "0")
        send_cmd_vis(g.tty_fd, "prev_btn", "0")
        send_cmd_vis(g.tty_fd, "next_btn", "0")
        send_cmd_vis(g.tty_fd, "refresh_btn", "0")
    else:
        send_cmd_picc(g.tty_fd, "b2", pics.server_row_on)
        send_cmd_picc2(g.tty_fd, "b2", pics.server_press_on)
        send_cmd_vis(g.tty_fd, "msg", "0")
        send_cmd_vis(g.tty_fd, "t0", "1")
        send_cmd_vis(g.tty_fd, "prev_btn", "1")
        send_cmd_vis(g.tty_fd, "next_btn", "1")
        send_cmd_vis(g.tty_fd, "refresh_btn", "1")

    if g.net.server_page == 0:
        send_cmd_picc(g.tty_fd, "prev_btn", pics.server_row_on)
        send_cmd_picc2(g.tty_fd, "prev_btn", pics.server_press_on)
    else:
        send_cmd_picc(g.tty_fd, "prev_btn", pics.server_row_off)
        send_cmd_picc2(g.tty_fd, "prev_btn", pics.server_press_off)

    if (g.net.server_page + 1) * 4 >= g.net.total_server_count:
        send_cmd_picc(g.tty_fd, "next_btn", pics.server_row_on)
        send_cmd_picc2(g.tty_fd, "next_btn", pics.server_press_on)
    else:
        send_cmd_picc(g.tty_fd, "next_btn", pics.server_row_off)
        send_cmd_picc2(g.tty_fd, "next_btn", pics.server_press_off)
    for i in range(4):
        if i + g.net.server_page * 4 + 1 > g.net.total_server_count:
            break
        send_cmd_txt(g.tty_fd, "srv" + to_string(i + 1) + "_txt", _config(1 + i + g.net.server_page * 4).name)
        if g.net.selected_server == _config(1 + i + g.net.server_page * 4).name:
            cout("selected_server:", _config(i + 1 + g.net.server_page * 4).name)
            send_cmd_picc(g.tty_fd, "srv" + to_string(i + 1), pics.server_row_off)
            send_cmd_picc2(g.tty_fd, "srv" + to_string(i + 1), pics.server_press_on)
        else:
            cout("unselected_server:", _config(i + 1 + g.net.server_page * 4).name)
            send_cmd_picc(g.tty_fd, "srv" + to_string(i + 1), pics.server_row_on)
            send_cmd_picc2(g.tty_fd, "srv" + to_string(i + 1), pics.server_press_off)
