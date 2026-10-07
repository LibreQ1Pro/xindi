"""Port of main.cpp - start-up sequence and main loop of the screen backend ("xindi")."""

import fcntl
import os
import queue
import sys
import time

from . import paths
from . import state as g
from . import ui
from .cpp import access, system, sleep, pthread_create, terminate
from .mks_log import MKSLOG, MKSLOG_BLUE, cout, cerr
from .MakerbaseClient import MakerbaseClient
from .MakerbaseSerial import set_option
from .MakerbaseParseMessage import json_parse
from .network import mks_wifi_hdlevent_thread, mks_wpa_scan_scanresults
from .MakerbaseWiFi import get_wlan0_status, get_ssid_list_pages
from .send_jpg import sent_jpg_thread_handle
from . import event
from . import screen_rx
from . import uart

REFRESH_INTERVAL = 0.05     # s between two redraws of the page


def main(argv):
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
                    command = "/usr/bin/systemctl --no-block restart makerbase-automount@%s.service" % partition_suffix
                    system(command)

    # 4.4.22: mount the USB drive if it is not mounted yet
    if (((access("/dev/sda") == 0 and access("/dev/sda1") == 0) or
         (access("/dev/sda1") == 0 and access("/dev/sdb1") == 0)) and
            access(paths.gcode_files() + "/sda1") != 0):
        system("/usr/bin/systemctl --no-block restart makerbase-automount@sda1.service")

    if access(paths.gcode_files() + "/sda1/mksscreen.recovery") == 0:
        system("cp " + paths.gcode_files() + "/sda1/mksscreen.recovery /root/800_480.tft; sync")

    if access(paths.gcode_files() + "/sda1/mksclient.recovery") == 0:
        system("dpkg -i --force-overwrite " + paths.gcode_files() + "/sda1/mksclient.recovery; sync")

    if access("/root/800_480.tft") == 0:
        g.update.find_screen_tft_file = True
        MKSLOG_BLUE("Found the tft update file")
    else:
        g.update.find_screen_tft_file = False
        MKSLOG_BLUE("No tft update file found")

    if g.update.find_screen_tft_file == True:
        MKSLOG("Running the screen update")
        # The original runs "/root/uart; mv /root/800_480.tft /root/800_480.tft.bak";
        # the uart helper is built in (see uart.py).
        uart.main()
        system("mv /root/800_480.tft /root/800_480.tft.bak")

    if access(paths.gcode_files() + "/sda1/QD_factory_mode.txt") == 0:
        system("dmesg > " + paths.gcode_files() + "/sda1/mks-dmesg.log; sync; ")
        if access(paths.gcode_files() + "/sda1/mks-super.sh") == 0:
            system("bash " + paths.gcode_files() + "/sda1/mks-super.sh")

    # 4.4.15 CCW check c_helper.so at start-up
    sourceFile = "/home/mks/klipper/klippy/chelper/c_helper.so"
    destFile = "/root/etc/c_helper.so"

    try:
        size = os.stat(sourceFile).st_size
        with open(sourceFile, "rb"):
            pass
    except OSError:
        print("File does not exist or could not open file: %s" % sourceFile)
        size = -1

    # check that c_helper.so looks valid
    if size < 10240:
        print("File %s does not exist or is less than 10KB" % sourceFile)
        src = None
        dst = None
        try:
            src = open(destFile, "rb")
        except OSError:
            src = None
        try:
            dst = open(sourceFile, "wb")
        except OSError:
            dst = None
        if src is None or dst is None:
            print("Failed to open source or destination file")
        else:
            dst.write(src.read())      # copy the file content
            print("File %s has been replaced with %s" % (sourceFile, destFile))
        if src is not None:
            src.close()
        if dst is not None:
            dst.close()
    else:
        print("File %s exists and is not less than 10KB, no action taken" % sourceFile)

    pthread_create(mks_wifi_hdlevent_thread, None)

    host = "localhost"
    url = "ws://localhost:7125/websocket?"
    MKSLOG("%s", url)

    if len(argv) == 2:
        host = argv[1]
        url = "ws://" + host + ":7125/websocket?"

    g.ep = MakerbaseClient(host, "7125")
    cout(g.ep.GetURL())
    cout(g.ep.GetStatus())
    cout(int(g.ep.GetIsConnected()))

    connected_count = 0

    while not g.ep.GetIsConnected():
        cout(connected_count, "Not connected: ", int(g.ep.GetIsConnected()))
        g.ep.Close()
        g.ep.Connect(url)
        connected_count += 1
        sleep(1)
        g.ep.GetStatus()
        sleep(1)

    pthread_create(json_parse, None)
    pthread_create(sent_jpg_thread_handle, None)        # preview picture thread

    frames = queue.Queue()
    try:
        fd = os.open("/dev/ttyS1", os.O_RDWR | os.O_NDELAY | os.O_NOCTTY)
    except OSError:
        fd = -1
    if fd < 0:
        print("Open tty failed")
    else:
        MKSLOG_BLUE("%d", g.tty_fd)
        g.tty_fd = fd
        print("Open tty success")
        set_option(fd, 115200, 8, 'N', 1)
        try:
            fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NDELAY)

            # the port is read by a thread of its own, the frames wait in a queue (see screen_rx.py): the main loop
            # spends its time on writing to the screen and may be busy for a while without losing what the screen
            # sent meanwhile
            parser = screen_rx.FrameParser()
            pthread_create(lambda _: screen_rx.reader_thread(fd, parser, frames), None)

            event.get_total_time()
            sleep(2)
            event.sub_object_status()       # subscribe to the printer objects

            sleep(2)

            event.get_object_status()       # query the required values
            sleep(2)
            event.system_setting_init()     # 4.4.22 (was init_mks_status())
            get_wlan0_status()
            mks_wpa_scan_scanresults()
            get_ssid_list_pages()
            event.mks_get_version()
            sleep(3)

            # CLL UI / SOC version check of the main page (the screen may start later: see ui.send_ui_version)
            ui.send_ui_version()
            if g.update.find_screen_tft_file == False:
                g.screen.previous_page = ui.TJC_PAGE_LOGO
                if event.get_mks_oobe_enabled() == True:
                    g.screen.page = ui.TJC_PAGE_OPEN_LANGUAGE
                else:
                    g.screen.page = ui.TJC_PAGE_MAIN
            else:
                g.screen.page = ui.TJC_PAGE_UPDATE_SUCCESS
            ui.page_to(g.screen.page)
        except Exception as e:
            cerr("Page main error, ", str(e), "\n")

    next_refresh = 0.0
    while True:
        frame = screen_rx.next_frame(frames, max(0.0, next_refresh - time.monotonic()))
        if frame is not None:
            ui.parse_cmd_msg_from_tjc_screen(frame.ljust(4096, b"\0"))
        if time.monotonic() >= next_refresh:
            event.refresh_page_show()
            next_refresh = time.monotonic() + REFRESH_INTERVAL


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
