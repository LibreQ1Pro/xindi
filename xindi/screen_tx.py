"""Instructions for the TJC (USART HMI) screen.

Every instruction is terminated by three 0xFF bytes.  Like the original the
functions wait for the output to drain (tcdrain) and then issue a single
write(); errors are ignored.
"""

import os
import termios

from .cpp import s2b, to_string
from .mks_log import MKSLOG_YELLOW, MKSLOG_BLUE

END = b"\xff\xff\xff"


def _tcdrain(fd):
    try:
        termios.tcdrain(fd)
    except (termios.error, OSError, ValueError):
        pass


def _write(fd, data):
    try:
        return os.write(fd, data)
    except (OSError, ValueError):
        return -1


# Python only: XINDI_TJC_LOG=1 prints every instruction sent to the screen
# (debugging aid, off by default: the main loop sends hundreds per second)
_TJC_LOG = os.environ.get("XINDI_TJC_LOG") == "1"


_tjc_logged = {}


def _send(fd, cmd):
    if _TJC_LOG:
        # the same instruction is logged at most once a second (journald drops
        # lines when a service writes too many)
        import time
        now = time.time()
        if now - _tjc_logged.get(cmd, 0.0) >= 1.0:
            _tjc_logged[cmd] = now
            print("TJC> " + cmd.rstrip(b"\xff").decode("utf-8", "replace"), flush=True)
    _tcdrain(fd)
    _write(fd, cmd)


def send_cmd_page(fd, pageid):
    """Switch page"""
    cmd = s2b("page " + pageid) + END
    _send(fd, cmd)


def send_cmd_vis(fd, obj, state):
    """Hide / show a widget"""
    cmd = s2b("vis " + obj + "," + state) + END
    _send(fd, cmd)


def send_cmd_tsw(fd, obj, state):
    """Enable / disable touch for a widget"""
    cmd = s2b("tsw " + obj + "," + state) + END
    _send(fd, cmd)


def send_cmd_twfile(fd, filepath, filesize):
    """Pass-through file transfer (X3/X5 only)"""
    cmd = s2b("twfile \"" + filepath + "\"," + filesize) + END
    MKSLOG_YELLOW("%s", cmd.decode("utf-8", "replace"))
    _send(fd, cmd)


def send_cmd_delfile(fd, filepath):
    """Delete a file (X3/X5 only)"""
    cmd = s2b("delfile \"" + filepath + "\"") + END
    MKSLOG_YELLOW("%s", cmd.decode("utf-8", "replace"))
    _send(fd, cmd)


def send_cmd_raw(fd, instruction):
    """Any instruction of the screen, e.g. a global variable assignment ``kbmode=2``"""
    _send(fd, s2b(instruction) + END)


def send_cmd_txt(fd, obj, txt):
    """Change the text of a widget"""
    cmd = s2b(obj + ".txt=" + "\"" + txt + "\"") + END
    _send(fd, cmd)


def send_cmd_pic(fd, obj, pic):
    """Change the picture of a widget"""
    cmd = s2b(obj + ".pic=" + pic) + END
    _send(fd, cmd)


def send_cmd_picc(fd, obj, picc):
    cmd = s2b(obj + ".picc=" + picc) + END
    _send(fd, cmd)


def send_cmd_picc2(fd, obj, picc):
    cmd = s2b(obj + ".picc2=" + picc) + END
    _send(fd, cmd)


def send_cmd_val(fd, obj, val):
    """Change the value of a variable"""
    cmd = s2b(obj + ".val=" + val) + END
    _send(fd, cmd)


def send_cmd_pco(fd, obj, poc):
    """Change the colour"""
    cmd = s2b(obj + ".pco=" + poc) + END
    _send(fd, cmd)


def send_cmd_cp_close(fd, obj):
    cmd = s2b(obj + ".close()") + END
    _send(fd, cmd)


def send_cmd_write(fd, obj):
    cmd = s2b(obj + ".write(\"")
    _send(fd, cmd)


def send_cmd_write_end(fd):
    cmd = b"\")" + END
    _send(fd, cmd)


def send_cmd_cp_image(fd, obj, image):
    send_cmd_write(fd, obj)
    _tcdrain(fd)
    _write(fd, s2b(image))
    send_cmd_write_end(fd)


def send_cmd_txt_plus(fd, obj1, obj2, obj3):
    cmd = s2b(obj1 + ".txt=" + obj2 + ".txt+" + obj3 + ".txt") + END
    _send(fd, cmd)


def send_cmd_download(fd, filesize):
    cmd = s2b("whmi-wri " + to_string(filesize) + ",115200,0") + END
    _send(fd, cmd)


def send_cmd_download_data(fd, data):
    """Sends the screen firmware data in 512 byte pieces (no tcdrain)."""
    data = s2b(data)
    num = 512
    length = len(data)
    end = num
    start = 0
    while start < length:
        if end > length:
            sub_data = data[start:length]
            _write(fd, sub_data)
            break
        sub_data = data[start:start + num]
        _write(fd, sub_data)
        start = end
        end = end + num
        MKSLOG_BLUE("Sending download data")


def send_cmd_baud(fd, baud):
    cmd = s2b("baud=" + to_string(baud)) + END
    _send(fd, cmd)


