"""Instructions for the TJC (USART HMI) screen.

Every instruction is terminated by three 0xFF bytes.  Like the original the
methods wait for the output to drain (tcdrain) and then issue a single
write(); errors are ignored.
"""

import logging
import os
import termios
import time

from xindi.screen.serial import set_option
from xindi.util.cpp import s2b, to_string

log = logging.getLogger(__name__)

END = b"\xff\xff\xff"

# Python only: XINDI_TJC_LOG=1 prints every instruction sent to the screen
# (debugging aid, off by default: the main loop sends hundreds per second)
_TJC_LOG = os.environ.get("XINDI_TJC_LOG") == "1"


class ScreenPort:
    """The serial port of the screen and the instructions it understands."""

    def __init__(self, fd=-1):
        self.fd = fd
        self._logged = {}

    def open(self, path="/dev/ttyS1", baud=115200):
        """Open the port; returns False when it cannot be opened."""
        try:
            self.fd = os.open(path, os.O_RDWR | os.O_NDELAY | os.O_NOCTTY)
        except OSError:
            self.fd = -1
            return False
        set_option(self.fd, baud, 8, 'N', 1)
        return True

    def set_baud(self, baud):
        set_option(self.fd, baud, 8, 'N', 1)

    # -- raw bytes ---------------------------------------------------------------------------------------------

    def drain(self):
        try:
            termios.tcdrain(self.fd)
        except (termios.error, OSError, ValueError):
            pass

    def write(self, data):
        try:
            return os.write(self.fd, bytes(data))
        except (OSError, ValueError):
            return -1

    def _send(self, cmd):
        if _TJC_LOG:
            # the same instruction is logged at most once a second (journald drops
            # lines when a service writes too many)
            now = time.time()
            if now - self._logged.get(cmd, 0.0) >= 1.0:
                self._logged[cmd] = now
                print("TJC> " + cmd.rstrip(b"\xff").decode("utf-8", "replace"), flush=True)
        self.drain()
        self.write(cmd)

    # -- instructions ------------------------------------------------------------------------------------------

    def page(self, pageid):
        """Switch page"""
        self._send(s2b("page " + pageid) + END)

    def vis(self, obj, state):
        """Hide / show a widget"""
        self._send(s2b("vis " + obj + "," + state) + END)

    def tsw(self, obj, state):
        """Enable / disable touch for a widget"""
        self._send(s2b("tsw " + obj + "," + state) + END)

    def twfile(self, filepath, filesize):
        """Pass-through file transfer (X3/X5 only)"""
        cmd = s2b("twfile \"" + filepath + "\"," + filesize) + END
        log.info("%s", cmd.decode("utf-8", "replace"))
        self._send(cmd)

    def delfile(self, filepath):
        """Delete a file (X3/X5 only)"""
        cmd = s2b("delfile \"" + filepath + "\"") + END
        log.info("%s", cmd.decode("utf-8", "replace"))
        self._send(cmd)

    def raw(self, instruction):
        """Any instruction of the screen, e.g. a global variable assignment ``kbmode=2``"""
        self._send(s2b(instruction) + END)

    def txt(self, obj, txt):
        """Change the text of a widget"""
        self._send(s2b(obj + ".txt=" + "\"" + txt + "\"") + END)

    def pic(self, obj, pic):
        """Change the picture of a widget"""
        self._send(s2b(obj + ".pic=" + pic) + END)

    def picc(self, obj, picc):
        self._send(s2b(obj + ".picc=" + picc) + END)

    def picc2(self, obj, picc):
        self._send(s2b(obj + ".picc2=" + picc) + END)

    def val(self, obj, val):
        """Change the value of a variable"""
        self._send(s2b(obj + ".val=" + val) + END)

    def pco(self, obj, poc):
        """Change the colour"""
        self._send(s2b(obj + ".pco=" + poc) + END)

    def cp_close(self, obj):
        self._send(s2b(obj + ".close()") + END)

    def write_begin(self, obj):
        self._send(s2b(obj + ".write(\""))

    def write_end(self):
        self._send(b"\")" + END)

    def cp_image(self, obj, image):
        self.write_begin(obj)
        self.drain()
        self.write(s2b(image))
        self.write_end()

    def txt_plus(self, obj1, obj2, obj3):
        self._send(s2b(obj1 + ".txt=" + obj2 + ".txt+" + obj3 + ".txt") + END)

    def download(self, filesize):
        self._send(s2b("whmi-wri " + to_string(filesize) + ",115200,0") + END)

    def download_data(self, data):
        """Sends the screen firmware data in 512 byte pieces (no tcdrain)."""
        data = s2b(data)
        num = 512
        length = len(data)
        end = num
        start = 0
        while start < length:
            if end > length:
                self.write(data[start:length])
                break
            self.write(data[start:start + num])
            start = end
            end = end + num
            log.debug("Sending download data")

    def baud(self, baud):
        self._send(s2b("baud=" + to_string(baud)) + END)
