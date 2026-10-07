"""Start-up sequence and main loop of the screen backend ("xindi")."""

import fcntl
import logging
import os
import queue
import sys
import time

from xindi import state as g
from xindi.config import settings
from xindi.moonraker.rpc_messages import json_parse
from xindi.moonraker.ws_client import MoonrakerClient
from xindi.pages import refresh
from xindi.printer import klipper
from xindi.screen import events, flash, navigation, pageids as ids, rx
from xindi.screen.transfer import sent_jpg_thread_handle
from xindi.system.network import (get_ssid_list_pages,
                                  get_wlan0_status,
                                  mks_wifi_hdlevent_thread,
                                  mks_wpa_scan_scanresults)
from xindi.util import paths
from xindi.util.cpp import pthread_create, system, terminate


log = logging.getLogger(__name__)


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
    if (((os.path.exists("/dev/sda") and os.path.exists("/dev/sda1")) or
         (os.path.exists("/dev/sda1") and os.path.exists("/dev/sdb1"))) and
            not os.path.exists(paths.gcode_files() + "/sda1")):
        system("/usr/bin/systemctl --no-block restart makerbase-automount@sda1.service")


def apply_usb_recovery_files():
    usb = paths.gcode_files() + "/sda1"
    if os.path.exists(usb + "/mksscreen.recovery"):
        system("cp " + usb + "/mksscreen.recovery /root/800_480.tft; sync")

    if os.path.exists(usb + "/mksclient.recovery"):
        system("dpkg -i --force-overwrite " + usb + "/mksclient.recovery; sync")


def update_screen_firmware():
    """Flash /root/800_480.tft into the screen when there is one."""
    g.update.find_screen_tft_file = os.path.exists("/root/800_480.tft")
    if not g.update.find_screen_tft_file:
        log.debug("No tft update file found")
        return
    log.debug("Found the tft update file")
    log.info("Running the screen update")
    # The original runs "/root/uart; mv /root/800_480.tft /root/800_480.tft.bak";
    # the uart helper is built in (see screen_flash.py).
    flash.main()
    system("mv /root/800_480.tft /root/800_480.tft.bak")


def run_factory_mode_script():
    usb = paths.gcode_files() + "/sda1"
    if os.path.exists(usb + "/QD_factory_mode.txt"):
        system("dmesg > " + usb + "/mks-dmesg.log; sync; ")
        if os.path.exists(usb + "/mks-super.sh"):
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
    log.info("%s", url)

    if len(argv) == 2:
        host = argv[1]
        url = "ws://" + host + ":7125/websocket?"

    g.ep = MoonrakerClient(host, "7125")
    log.debug("%s", g.ep.url())
    log.debug("%s", g.ep.poll_status())
    log.debug("%s", int(g.ep.connected()))

    connected_count = 0
    while not g.ep.connected():
        log.debug("%sNot connected: %s", connected_count, int(g.ep.connected()))
        g.ep.close()
        g.ep.connect(url)
        connected_count += 1
        time.sleep(1)
        g.ep.poll_status()
        time.sleep(1)


def open_screen_port():
    """Open the screen's serial port; returns its file descriptor or -1."""
    if not g.port.open():
        print("Open tty failed")
        return -1
    log.debug("%d", g.port.fd)
    print("Open tty success")
    return g.port.fd


def start_screen(fd, frames):
    """Start reading the screen, load the printer state and show the first page."""
    try:
        fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NDELAY)

        # the port is read by a thread of its own, the frames wait in a queue (see screen_rx.py): the main loop
        # spends its time on writing to the screen and may be busy for a while without losing what the screen
        # sent meanwhile
        parser = rx.FrameParser()
        pthread_create(lambda _: rx.reader_thread(fd, parser, frames), None)

        settings.get_total_time()
        time.sleep(2)
        klipper.sub_object_status()       # subscribe to the printer objects

        time.sleep(2)

        klipper.get_object_status()       # query the required values
        time.sleep(2)
        settings.init()     # 4.4.22 (was init_mks_status())
        get_wlan0_status()
        mks_wpa_scan_scanresults()
        get_ssid_list_pages()
        settings.load_versions()
        time.sleep(3)

        # CLL UI / SOC version check of the main page (the screen may start later: see ui.send_ui_version)
        navigation.send_ui_version()
        if g.update.find_screen_tft_file:
            g.screen.page = ids.UPDATE_SUCCESS
        else:
            g.screen.previous_page = ids.LOGO
            g.screen.page = ids.OPEN_LANGUAGE if settings.get_oobe_enabled() else ids.MAIN
        navigation.page_to(g.screen.page)
    except Exception as e:
        log.error("Page main error, %s", str(e))


def main_loop(frames):
    next_refresh = 0.0
    while True:
        frame = rx.next_frame(frames, max(0.0, next_refresh - time.monotonic()))
        if frame is not None:
            events.parse_cmd_msg_from_tjc_screen(frame.ljust(4096, b"\0"))
        if time.monotonic() >= next_refresh:
            refresh.show()
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


def setup_logging():
    """Log to stdout (the journal of the service); XINDI_LOG=debug shows the chatty messages too."""
    level = os.environ.get("XINDI_LOG", "info").upper()
    logging.basicConfig(stream=sys.stdout, level=getattr(logging, level, logging.INFO),
                        format="%(levelname).1s %(name)s: %(message)s")


def run():
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass
    setup_logging()
    try:
        return main(sys.argv)
    except KeyboardInterrupt:
        return 130
    except SystemExit:
        raise
    except BaseException as e:      # uncaught exception -> std::terminate()
        terminate(e)
