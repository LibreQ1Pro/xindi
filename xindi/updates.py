"""Updates: from a USB drive and online, and the progress page."""

from . import paths
from . import state as g
from . import pics
from . import ui
from .ui import page_to
from .cpp import to_string, substr, b2s, cstr, access, system, sleep, popen_read, read_file, pthread_create
from .mks_log import cout, cerr
from .send_msg import (send_cmd_txt, send_cmd_val, send_cmd_pco, send_cmd_picc, send_cmd_vis,
                       send_cmd_tsw, send_cmd_pco2)
from .MoonrakerAPI import json_run_a_gcode, json_get_klippy_host_information
from .MakerbaseParseIni import mksini_free, mksini_getstring, mksini_getint, updateini_load, progressini_load
from .mks_update import detect_update


def finish_tjc_update():
    if access("/root/800_480.tft") == 0:
        system("mv /root/800_480.tft /root/800_480.tft.bak; sync")


def update_finished_tips():
    sleep(5)
    system("sync")
    system("systemctl restart makerbase-client.service")


def go_to_update():
    page_to(ui.TJC_PAGE_UPDATE_MODE)
    send_cmd_txt(g.tty_fd, "ver_cur", g.config.version_soc)
    # 4.4.22: the online update needs QIDI Link, which the port does not
    # implement: the button is disabled (LAN only)
    send_cmd_tsw(g.tty_fd, "online_btn", "0")
    send_cmd_picc(g.tty_fd, "online_btn", pics.update_mode_press)
    send_cmd_pco(g.tty_fd, "online_btn", "38066")
    send_cmd_pco2(g.tty_fd, "online_btn", "38066")


def local_update():
    g.ep.Send(json_get_klippy_host_information())
    if detect_update():
        page_to(ui.TJC_PAGE_UPDATE_FOUND)
    else:
        page_to(ui.TJC_PAGE_UPDATE_NOT_FOUND)


def run_python_code(cmd):
    """CLL runs a command and returns its output"""
    out = popen_read(cmd)
    if out is None:
        raise RuntimeError("popen() failed!")
    result = b""
    pos = 0
    while pos < len(out):
        # fgets(buffer.data(), 128, pipe) + result += buffer.data()
        end = out.find(b"\n", pos, pos + 127)
        end = (pos + 127) if end == -1 else end + 1
        result += cstr(out[pos:end])
        pos = end
    return b2s(result)


def check_online_version():
    page_to(ui.TJC_PAGE_SEARCH_SERVER)
    if g.net.connection_method == 0:
        return
    g.update.target_soc_version = run_python_code("python3 /root/auto_update/version_check.py")
    cout("Server version:", g.update.target_soc_version)
    if g.update.target_soc_version.find("0") == 0:
        page_to(ui.TJC_PAGE_UPDATE_MODE)
        send_cmd_vis(g.tty_fd, "msg_latest", "1")
        send_cmd_vis(g.tty_fd, "msg_failed", "0")
    elif g.update.target_soc_version.find("-1") == 0:
        page_to(ui.TJC_PAGE_UPDATE_MODE)
        send_cmd_vis(g.tty_fd, "msg_failed", "1")
        send_cmd_vis(g.tty_fd, "msg_latest", "0")
    else:
        page_to(ui.TJC_PAGE_ONLINE_UPDATE)
        send_cmd_txt(g.tty_fd, "ver_cur", g.config.version_soc)
        send_cmd_txt(g.tty_fd, "ver_new", g.update.target_soc_version)
        updateini_load()
        # CLL update notes in Chinese, Russian, English, Japanese, French, German,
        # Italian, Spanish, Korean, Portuguese, Arabic, Turkish and Hebrew
        langs = ["cn", "ru", "en", "jp", "fr", "gr", "it", "sp", "kr", "pr", "ar", "tr", "hb"]
        infos = [mksini_getstring(lang, "content", "NULL") for lang in langs]
        for lang, info in zip(langs, infos):
            send_cmd_txt(g.tty_fd, "notes_" + lang, info)
        mksini_free()


def online_update():
    page_to(ui.TJC_PAGE_UPDATING)
    send_cmd_vis(g.tty_fd, "progress", "1")
    send_cmd_vis(g.tty_fd, "pct_txt", "1")
    pthread_create(receive_progress, None)
    system("rm " + paths.gcode_files() + "/.cache/*\n")
    system("python3 /root/auto_update/download_update.py\n")
    system("sync\n")
    system("systemctl restart makerbase-client\n")


def receive_progress(arg=None):
    """CLL thread that shows the progress of the online update"""
    import time
    while True:
        if g.screen.page == ui.TJC_PAGE_UPDATING:
            progressini_load()
            update_progress = mksini_getint("progress", "value", 0)        # (uninitialised default in C++)
            progress_name = mksini_getstring("filename", "name", "")
            mksini_free()
            if progress_name.find("Installing") == -1:
                send_cmd_txt(g.tty_fd, "info_txt", progress_name)
                send_cmd_val(g.tty_fd, "progress", to_string(update_progress))
                send_cmd_txt(g.tty_fd, "pct_txt", to_string(update_progress) + "%")
            else:
                page_to(ui.TJC_PAGE_INSTALLING)
                break
        time.sleep(0)   # the C++ thread spins without sleeping; yield the GIL here
    return None


def check_print_interrupted():
    printer_variables = read_file(paths.klipper_config() + "/saved_variables.cfg")
    if printer_variables is None:
        cerr("Can't open the file ", paths.klipper_config() + "/saved_variables.cfg", "\n")
        return
    print_interrupted_status = substr(printer_variables, printer_variables.find("was_interrupted =") + 18, 5)
    if print_interrupted_status != "False":
        g.ep.Send(json_run_a_gcode("DETECT_INTERRUPTION\n"))
        g.screen.jump_resume_print = True
