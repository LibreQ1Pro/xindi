"""Port of src/mks_update.cpp - updates from the USB drive."""

import os

from . import paths
from . import state as g
from .cpp import access, system, sleep, s2b, b2s, to_string
from .mks_log import cout
from .send_msg import send_cmd_download_data, send_cmd_download


def _base_path():
    """``base_path`` of the original (``/home/mks/gcode_files/sda1/QD_Update/``)"""
    return paths.gcode_files() + "/sda1/QD_Update/"


def _npos_eq(found, expected):
    """``filename.rfind(".bak") == filename.length() - 4`` with size_t arithmetic."""
    mask = (1 << 64) - 1
    return (found & mask) == (expected & mask)


def u_disk_update():
    fd = 1
    ch = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']

    for j in range(4):
        for i in range(8):
            PATH = paths.gcode_files() + "/sd%c%d/QD_Update/QD_Mates3_SOC" % (ch[i], j)
            fd = access(PATH)
            if fd == 0:
                print("Found directory %s on the USB drive, checking for update files" % PATH)
                cmd = "dpkg -i %s; rm %s -f" % (PATH, PATH)
                system(cmd)
                break
            else:
                continue
        if fd == 0:
            break

    if fd == -1:
        print("Can't open the USB drive")
    else:
        try:
            os.close(fd)        # (sic) closes descriptor 0 (stdin)
        except OSError:
            pass
    return 0


def _listdir(path):
    """opendir()/readdir() including '.' and '..' (order: as returned by the OS)."""
    try:
        names = os.listdir(path)
    except OSError:
        return None
    return [".", ".."] + names


def detect_update():
    entries = _listdir(_base_path())
    if entries is not None:
        for filename in entries:
            # skip files ending with .bak
            if _npos_eq(filename.rfind(".bak"), len(filename) - 4):
                continue

            if filename.find("QD_Q1_PATCH") == 0:
                g.detected_q1_patch_data = True
                continue
            if filename.find("QD_Q1_UI") == 0:
                g.detected_q1_ui_data = True
                continue
            if filename.find("QD_Q1_SOC") == 0:
                g.detected_q1_soc_data = True
                continue
            if filename.find("QD_Mates3_UI") == 0:
                g.detected_ui_data = True
                continue
            if filename.find("QD_Mates3_SOC") == 0:
                g.detected_soc_data = True
                continue
    else:
        print("Usb device path not found: %s" % _base_path())

    g.detected_mcu_data = access(paths.gcode_files() + "/sda1/QD_MCU/MCU") == 0
    g.detected_gcode_cfg = access(paths.gcode_files() + "/sda1/QD_Update/gcode_macro.cfg") == 0
    g.detected_printer_cfg = access(paths.gcode_files() + "/sda1/QD_Update/printer.cfg") == 0
    g.detected_MKS_THR_cfg = access(paths.gcode_files() + "/sda1/QD_Update/MKS_THR.cfg") == 0
    g.detected_gcode = access(paths.gcode_files() + "/sda1/QD_Update/QD_Gcode") == 0

    # 4.4.3 CLL updates from .deb files
    if access(paths.gcode_files() + "/sda1/QD_factory_mode.txt") == 0:
        g.detected_soc_deb = access(paths.gcode_files() + "/sda1/QD_Update/mks.deb") == 0

    return (g.detected_soc_data | g.detected_q1_soc_data | g.detected_mcu_data | g.detected_ui_data |
            g.detected_q1_ui_data | g.detected_printer_cfg | g.detected_MKS_THR_cfg | g.detected_gcode |
            g.detected_soc_deb | g.detected_gcode_cfg | g.detected_q1_patch_data)


def start_update():
    from . import event
    system("rm " + paths.gcode_files() + "/.cache/*")

    factory_mode = (
        access(paths.gcode_files() + "/sda1/QD_factory_mode.txt") != -1 or
        access(paths.gcode_files() + "/sda1/QD_Update/QD_factory_mode.txt") != -1
    )

    if g.detected_mcu_data == True:
        if access(paths.gcode_files() + "/sda1/QD_factory_mode.txt") == 0:
            system("cp " + paths.gcode_files() + "/sda1/QD_MCU/MCU /root/klipper.bin;")
            event.close_mcu_port()
            system("service klipper stop; /root/hid-flash /root/klipper.bin ttyS0; systemctl start klipper; ")
        else:
            if access(paths.gcode_files() + "/sda1/QD_Update/QD_factory_mode.txt") == 0:
                system("cp " + paths.gcode_files() + "/sda1/QD_MCU/MCU /root/klipper.bin;")
                event.close_mcu_port()
                system("service klipper stop; /root/hid-flash /root/klipper.bin ttyS0; systemctl start klipper; ")
            else:
                system("cp " + paths.gcode_files() + "/sda1/QD_MCU/MCU /root/klipper.bin;")
                event.close_mcu_port()
                system("service klipper stop; /root/hid-flash /root/klipper.bin ttyS0; systemctl start klipper; mv " + paths.gcode_files() + "/sda1/QD_MCU/MCU " + paths.gcode_files() + "/sda1/QD_MCU/MCU.bak")

    if g.detected_gcode_cfg == True:
        if access(paths.gcode_files() + "/sda1/QD_factory_mode.txt") == 0:
            system("cp " + paths.gcode_files() + "/sda1/QD_Update/gcode_macro.cfg " + paths.klipper_config() + "/gcode_macro.cfg; chmod 777 " + paths.klipper_config() + "/gcode_macro.cfg; sync")
        else:
            if access(paths.gcode_files() + "/sda1/QD_Update/QD_factory_mode.txt") == 0:
                system("cp " + paths.gcode_files() + "/sda1/QD_Update/gcode_macro.cfg " + paths.klipper_config() + "/gcode_macro.cfg; chmod 777 " + paths.klipper_config() + "/gcode_macro.cfg; sync")
            else:
                system("cp " + paths.gcode_files() + "/sda1/QD_Update/gcode_macro.cfg " + paths.klipper_config() + "/gcode_macro.cfg; chmod 777 " + paths.klipper_config() + "/gcode_macro.cfg; mv " + paths.gcode_files() + "/sda1/QD_Update/gcode_macro.cfg " + paths.gcode_files() + "/sda1/QD_Update/gcode_macro.cfg.bak; sync")

    if g.detected_printer_cfg == True:
        if access(paths.gcode_files() + "/sda1/QD_factory_mode.txt") == 0:
            system("cp " + paths.gcode_files() + "/sda1/QD_Update/printer.cfg " + paths.klipper_config() + "/printer.cfg; chmod 777 " + paths.klipper_config() + "/printer.cfg; sync")
        else:
            if access(paths.gcode_files() + "/sda1/QD_Update/QD_factory_mode.txt") == 0:
                system("cp " + paths.gcode_files() + "/sda1/QD_Update/printer.cfg " + paths.klipper_config() + "/printer.cfg; chmod 777 " + paths.klipper_config() + "/printer.cfg; sync")
            else:
                system("cp " + paths.gcode_files() + "/sda1/QD_Update/printer.cfg " + paths.klipper_config() + "/printer.cfg; chmod 777 " + paths.klipper_config() + "/printer.cfg; mv " + paths.gcode_files() + "/sda1/QD_Update/printer.cfg " + paths.gcode_files() + "/sda1/QD_Update/printer.cfg.bak; sync")

    if g.detected_MKS_THR_cfg == True:
        if access(paths.gcode_files() + "/sda1/QD_factory_mode.txt") == 0:
            system("cp " + paths.gcode_files() + "/sda1/QD_Update/MKS_THR.cfg " + paths.klipper_config() + "/MKS_THR.cfg; chmod 777 " + paths.klipper_config() + "/MKS_THR.cfg; sync")
        else:
            if access(paths.gcode_files() + "/sda1/QD_Update/QD_factory_mode.txt") == 0:
                system("cp " + paths.gcode_files() + "/sda1/QD_Update/MKS_THR.cfg " + paths.klipper_config() + "/MKS_THR.cfg; chmod 777 " + paths.klipper_config() + "/MKS_THR.cfg; sync")
            else:
                system("cp " + paths.gcode_files() + "/sda1/QD_Update/MKS_THR.cfg " + paths.klipper_config() + "/MKS_THR.cfg; chmod 777 " + paths.klipper_config() + "/MKS_THR.cfg; mv " + paths.gcode_files() + "/sda1/QD_Update/MKS_THR.cfg " + paths.gcode_files() + "/sda1/QD_Update/MKS_THR.cfg.bak; sync")

    if g.detected_gcode == True:
        # Delete everything else in gcode_files first, the sda1 directory and its
        # files are kept.  Uses rm -rf, be careful when changing the paths!!!
        system("rm " + paths.gcode_files() + "/*\n")
        system("rm " + paths.gcode_files() + "/.thumbs/*\n")
        system("systemctl stop moonraker.service\n")
        system("find " + paths.gcode_files() + " -maxdepth 1 -type d ! -name sd* -a ! -name '.*' | grep " + paths.gcode_files() + "/ | xargs rm -rf")
        system("cp " + paths.gcode_files() + "/sda1/QD_Update/QD_gcode/*.gcode " + paths.gcode_files() + "; chmod 777 " + paths.gcode_files() + "/*.gcode; sync")
        sleep(3)
        system("systemctl restart moonraker.service\n")

    # UI file found
    if g.detected_ui_data or g.detected_q1_ui_data:
        entries = _listdir(_base_path())
        if entries is not None:
            for filename in entries:
                # fuzzy match of the UI file
                if filename.find("QD_Q1_UI") == 0 or filename.find("QD_Mates3_UI") == 0:
                    filePath = _base_path() + filename
                    command = "cp " + filePath + " /root/800_480.tft; "
                    if not factory_mode:
                        command += "mv " + filePath + " " + filePath + ".bak; "
                    command += "sync"
                    system(command)
                    break   # only one UI file per update
        else:
            print("Directory not found: %s" % _base_path())

    # SOC or PATCH file found
    if g.detected_q1_patch_data or g.detected_q1_soc_data or g.detected_soc_data:
        entries = _listdir(_base_path())
        if entries is not None:
            for filename in entries:
                if filename.rfind(".bak") != -1:
                    continue
                if filename.find("QD_Q1_PATCH") == 0 or filename.find("QD_Q1_SOC") == 0 or filename.find("QD_Mates3_SOC") == 0:
                    file_path = _base_path() + filename
                    command = "mv " + file_path + " " + _base_path() + "mks.deb; dpkg -i --force-overwrite " + _base_path() + "mks.deb;"
                    system(command)

                    new_file_name = file_path
                    if not factory_mode:
                        new_file_name += ".bak"
                    command = "mv " + _base_path() + "mks.deb " + new_file_name + "; sync"
                    system(command)
        else:
            print("Directory not found: %s" % _base_path())

    if g.detected_soc_deb == True:
        # 4.4.3 CLL updates from .deb files
        if access(paths.gcode_files() + "/sda1/QD_factory_mode.txt") == 0:
            system("dpkg -i --force-overwrite " + paths.gcode_files() + "/sda1/QD_Update/mks.deb;sync")

    event.update_finished_tips()


def download_to_screen():
    cout("tft_start == ", g.tft_start)
    if g.tft_start < g.tft_len:
        if g.tft_end > g.tft_len:
            g.tft_s = g.tft_data[g.tft_start:g.tft_len]
            cout("Sending download data == ", g.tft_start, "/", g.filesize)
            send_cmd_download_data(g.tty_fd, g.tft_s)
        g.tft_s = g.tft_data[g.tft_start:g.tft_start + g.tft_buff]
        cout(len(g.tft_s), " Sending download data == ", g.tft_start, "/", g.filesize)
        g.tft_start = g.tft_end
        g.tft_end = g.tft_end + g.tft_buff
        send_cmd_download_data(g.tty_fd, g.tft_s)


def init_download_to_screen():
    if access("/root/800_480.tft") == 0:
        g.tft_data = b""
        try:
            with open("/root/800_480.tft", "rb") as tftfile:
                g.filesize = os.stat("/root/800_480.tft").st_size
                cout("File size: ", g.filesize)
                g.tft_data = tftfile.read()
        except OSError:
            pass
        cout("Length of the read data: ", len(g.tft_data))
        g.tft_len = len(g.tft_data)
        g.tft_end = g.tft_buff


def back_to_screen_old():
    if access("/root/800_480.tft.bak") == 0:
        g.tft_data = b""
        try:
            with open("/root/800_480.tft.bak", "rb") as tftfile:
                g.filesize = os.stat("/root/800_480.tft.bak").st_size
                cout("File size: ", g.filesize)
                send_cmd_download(g.tty_fd, g.filesize)
                g.tft_data = tftfile.read()
        except OSError:
            pass
        g.tft_len = len(g.tft_data)
        g.tft_end = g.tft_buff
