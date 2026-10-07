"""Start-up sequence and main loop of the screen backend ("xindi")."""

import fcntl
import os
import queue
import sys
import time

from . import paths
from . import state as g
from . import ui
from . import pageids as ids
from .cpp import access, system, sleep, pthread_create, terminate
from .mks_log import MKSLOG, MKSLOG_BLUE, cout, cerr
from .moonraker_ws import MoonrakerClient
from .moonraker_messages import json_parse
from .network import mks_wifi_hdlevent_thread, mks_wpa_scan_scanresults, get_wlan0_status, get_ssid_list_pages
from .picture_transfer import sent_jpg_thread_handle
from . import actions, pages, settings
from . import screen_rx
from . import screen_flash

REFRESH_INTERVAL = 0.05     # s between two redraws of the page


def mount_usb_drive():
    """Ask the automounter for the USB drive when it is plugged in but not mounted yet."""
    try:
        entries = os.listdir("/dev")
    except OSError as e:
        print("Can't open the directory /dev: %s" % e, file=sys.stderr)
        entries = []

    for name in entries:
        # NOTE: d_name never starts with "/dev/sd", so this never matches (as in the original)
        if name.startswith("/dev/sd"):
            if len(name) >= 8:
                partition_suffix = name[7:]
                if partition_suffix[1:2] == "1":
                    system("/usr/bin/systemctl --no-block restart makerbase-automount@%s.service" % partition_suffix)

    # 4.4.22: mount the USB drive if it is not mounted yet
    if (((access("/dev/sda") == 0 and access("/dev/sda1") == 0) or
         (access("/dev/sda1") == 0 and access("/dev/sdb1") == 0)) and
            access(paths.gcode_files() + "/sda1") != 0):
        system("/usr/bin/systemctl --no-block restart makerbase-automount@sda1.service")


def apply_usb_recovery_files():
    usb = paths.gcode_files() + "/sda1"
    if access(usb + "/mksscreen.recovery") == 0:
        system("cp " + usb + "/mksscreen.recovery /root/800_480.tft; sync")

    if access(usb + "/mksclient.recovery") == 0:
        system("dpkg -i --force-overwrite " + usb + "/mksclient.recovery; sync")


def update_screen_firmware():
    """Flash /root/800_480.tft into the screen when there is one."""
    g.update.find_screen_tft_file = access("/root/800_480.tft") == 0
    if not g.update.find_screen_tft_file:
        MKSLOG_BLUE("No tft update file found")
        return
    MKSLOG_BLUE("Found the tft update file")
    MKSLOG("Running the screen update")
    # The original runs "/root/uart; mv /root/800_480.tft /root/800_480.tft.bak";
    # the uart helper is built in (see screen_flash.py).
    screen_flash.main()
    system("mv /root/800_480.tft /root/800_480.tft.bak")


def run_factory_mode_script():
    usb = paths.gcode_files() + "/sda1"
    if access(usb + "/QD_factory_mode.txt") == 0:
        system("dmesg > " + usb + "/mks-dmesg.log; sync; ")
        if access(usb + "/mks-super.sh") == 0:
            system("bash " + usb + "/mks-super.sh")


def restore_c_helper():
    """4.4.15 CCW: put the backup back when klippy's c_helper.so is missing or truncated."""
    source_file = "/home/mks/klipper/klippy/chelper/c_helper.so"
    backup_file = "/root/etc/c_helper.so"

    try:
        size = os.stat(source_file).st_size
        with open(source_file, "rb"):
            pass
    except OSError:
        print("File does not exist or could not open file: %s" % source_file)
        size = -1

    if size >= 10240:
        print("File %s exists and is not less than 10KB, no action taken" % source_file)
        return
    print("File %s does not exist or is less than 10KB" % source_file)
    try:
        with open(backup_file, "rb") as src, open(source_file, "wb") as dst:
            dst.write(src.read())      # copy the file content
        print("File %s has been replaced with %s" % (source_file, backup_file))
    except OSError:
        print("Failed to open source or destination file")


def connect_moonraker(argv):
    host = "localhost"
    url = "ws://localhost:7125/websocket?"
    MKSLOG("%s", url)

    if len(argv) == 2:
        host = argv[1]
        url = "ws://" + host + ":7125/websocket?"

    g.ep = MoonrakerClient(host, "7125")
    cout(g.ep.url())
    cout(g.ep.poll_status())
    cout(int(g.ep.connected()))

    connected_count = 0
    while not g.ep.connected():
        cout(connected_count, "Not connected: ", int(g.ep.connected()))
        g.ep.close()
        g.ep.connect(url)
        connected_count += 1
        sleep(1)
        g.ep.poll_status()
        sleep(1)


def open_screen_port():
    """Open the screen's serial port; returns its file descriptor or -1."""
    if not g.port.open():
        print("Open tty failed")
        return -1
    MKSLOG_BLUE("%d", g.port.fd)
    print("Open tty success")
    return g.port.fd


def start_screen(fd, frames):
    """Start reading the screen, load the printer state and show the first page."""
    try:
        fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NDELAY)

        # the port is read by a thread of its own, the frames wait in a queue (see screen_rx.py): the main loop
        # spends its time on writing to the screen and may be busy for a while without losing what the screen
        # sent meanwhile
        parser = screen_rx.FrameParser()
        pthread_create(lambda _: screen_rx.reader_thread(fd, parser, frames), None)

        settings.get_total_time()
        sleep(2)
        actions.sub_object_status()       # subscribe to the printer objects

        sleep(2)

        actions.get_object_status()       # query the required values
        sleep(2)
        settings.init()     # 4.4.22 (was init_mks_status())
        get_wlan0_status()
        mks_wpa_scan_scanresults()
        get_ssid_list_pages()
        settings.load_versions()
        sleep(3)

        # CLL UI / SOC version check of the main page (the screen may start later: see ui.send_ui_version)
        ui.send_ui_version()
        if g.update.find_screen_tft_file:
            g.screen.page = ids.UPDATE_SUCCESS
        else:
            g.screen.previous_page = ids.LOGO
            g.screen.page = ids.OPEN_LANGUAGE if settings.get_oobe_enabled() else ids.MAIN
        ui.page_to(g.screen.page)
    except Exception as e:
        cerr("Page main error, ", str(e), "\n")


def main_loop(frames):
    next_refresh = 0.0
    while True:
        frame = screen_rx.next_frame(frames, max(0.0, next_refresh - time.monotonic()))
        if frame is not None:
            ui.parse_cmd_msg_from_tjc_screen(frame.ljust(4096, b"\0"))
        if time.monotonic() >= next_refresh:
            pages.show()
            next_refresh = time.monotonic() + REFRESH_INTERVAL


def main(argv):
    mount_usb_drive()
    apply_usb_recovery_files()
    update_screen_firmware()
    run_factory_mode_script()
    restore_c_helper()

    pthread_create(mks_wifi_hdlevent_thread, None)
    connect_moonraker(argv)
    pthread_create(json_parse, None)
    pthread_create(sent_jpg_thread_handle, None)        # preview picture thread

    frames = queue.Queue()
    fd = open_screen_port()
    if fd >= 0:
        start_screen(fd, frames)
    main_loop(frames)


def run():
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass
    try:
        return main(sys.argv)
    except KeyboardInterrupt:
        return 130
    except SystemExit:
        raise
    except BaseException as e:      # uncaught exception -> std::terminate()
        terminate(e)
