"""Port of src/send_msg.cpp - instructions for the TJC (USART HMI) screen.

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


def _send(fd, cmd):
    _tcdrain(fd)
    _write(fd, cmd)


def send_cmd_page(fd, pageid):
    """Switch page"""
    cmd = s2b("page " + pageid) + END
    _send(fd, cmd)


def send_cmd_ref(fd, obj):
    """Redraw a widget"""
    cmd = s2b("ref " + obj) + END
    _send(fd, cmd)


def send_cmd_get(fd, att):
    """Get a formatted variable/constant value"""
    cmd = s2b("get " + att) + END
    _send(fd, cmd)


def send_cmd_vis(fd, obj, state):
    """Hide / show a widget"""
    cmd = s2b("vis " + obj + "," + state) + END
    _send(fd, cmd)


def send_cmd_tsw(fd, obj, state):
    """Enable / disable touch for a widget"""
    cmd = s2b("tsw " + obj + "," + state) + END
    _send(fd, cmd)


def send_cmd_randset(fd, minval, maxval):
    """Set the random number range"""
    cmd = s2b("randset " + minval + "," + maxval) + END
    _send(fd, cmd)


def send_cmd_add(fd, objid, ch, val):
    """Add data to a curve widget"""
    cmd = s2b("add " + objid + "," + ch + "," + val) + END
    _send(fd, cmd)


def send_cmd_cle(fd, objid, ch):
    """Clear the data of a curve widget"""
    cmd = s2b("cle " + objid + "," + ch) + END
    _send(fd, cmd)


def send_cmd_addt(fd, objid, ch, qyt):
    """Curve data pass-through"""
    cmd = s2b("addt " + objid + "," + ch + "," + qyt) + END
    _send(fd, cmd)


def send_cmd_doevents(fd):
    """Give control to the screen refresh"""
    cmd = s2b("doevents") + END
    _send(fd, cmd)


def send_cmd_sendme(fd):
    """Send the current page id to the serial port"""
    cmd = s2b("sendme") + END
    _send(fd, cmd)


def send_cmd_covx(fd, att1, att2, lenth):
    """Variable type conversion"""
    cmd = s2b("covx " + att1 + "," + att2 + "," + lenth) + END
    _send(fd, cmd)


def send_cmd_strlen(fd, att0, att1):
    """String length in characters"""
    cmd = s2b("strlen " + att0 + "," + att1) + END
    _send(fd, cmd)


def send_cmd_btlen(fd, att0, att1):
    """String length in bytes"""
    cmd = s2b("btlen " + att0 + "," + att1) + END
    _send(fd, cmd)


def send_cmd_substr(fd, att0, att1, star, lenth):
    """Substring"""
    cmd = s2b("substr " + att0 + "," + att1 + "," + star + "," + lenth) + END
    _send(fd, cmd)


def send_cmd_spstr(fd, src, dec, key, indec):
    """Split a string"""
    cmd = s2b("spstr " + src + "," + dec + "," + key + "," + indec) + END
    _send(fd, cmd)


def send_cmd_touch_j(fd):
    """Touch calibration"""
    cmd = s2b("touch_j") + END
    _send(fd, cmd)


def send_cmd_ref_stop(fd):
    """Pause screen refresh"""
    cmd = s2b("ref_stop") + END
    _send(fd, cmd)


def send_cmd_ref_star(fd):
    """Resume screen refresh"""
    cmd = s2b("ref_star") + END
    _send(fd, cmd)


def send_cmd_com_stop(fd):
    """Pause serial command execution"""
    cmd = s2b("com_stop") + END
    _send(fd, cmd)


def send_cmd_com_star(fd):
    """Resume serial command execution"""
    cmd = s2b("com_star") + END
    _send(fd, cmd)


def send_cmd_code_c(fd):
    """Clear the serial command buffer"""
    cmd = s2b("code_c") + END
    _send(fd, cmd)


def send_cmd_rest(fd):
    """Reset"""
    cmd = s2b("rest") + END
    _send(fd, cmd)


def send_cmd_wepo(fd, att, add):
    """Write a variable to the user storage"""
    cmd = s2b("wepo " + att + "," + add) + END
    _send(fd, cmd)


def send_cmd_repo(fd, att, add):
    """Read the user storage into a variable"""
    cmd = s2b("repo " + att + "," + add) + END
    _send(fd, cmd)


def send_cmd_wept(fd, add, lenth):
    """Pass-through write to the user storage"""
    cmd = s2b("wept " + add + "," + lenth) + END
    _send(fd, cmd)


def send_cmd_rept(fd, add, lenth):
    """Pass-through read of the user storage"""
    cmd = s2b("rept " + add + "," + lenth) + END
    _send(fd, cmd)


def send_cmd_cfgpio(fd, id, state, obj):
    """Extended IO configuration"""
    cmd = s2b("cfgpio " + id + "," + state + "," + obj) + END
    _send(fd, cmd)


def send_cmd_crcrest(fd, crctype, initval):
    """Reset the CRC initial value"""
    cmd = s2b("crcrest " + crctype + "," + initval) + END
    _send(fd, cmd)


def send_cmd_crcputs(fd, att, length):
    """CRC of a variable / constant"""
    cmd = s2b("crcputs " + att + "," + length) + END
    _send(fd, cmd)


def send_cmd_crcputh(fd, hex):
    """CRC of a group of hex values"""
    cmd = s2b("crcputh " + hex) + END
    _send(fd, cmd)


def send_cmd_crcputu(fd, star, length):
    """CRC of a part of the serial buffer (recmod=1 only)"""
    cmd = s2b("crcputu " + star + "," + length) + END
    _send(fd, cmd)


def send_cmd_setlayer(fd, obj0, obj1):
    """Change the widget layer order at runtime (X3/X5 only)"""
    cmd = s2b("setplayer " + obj0 + "," + obj1) + END
    _send(fd, cmd)


def send_cmd_move(fd, obj, startx, starty, endx, endy, first, time):
    """Move a widget (X3/X5 only)"""
    cmd = s2b("move " + obj + "," + startx + "," + starty + "," + endx + "," + endy + "," + first + "," + time) + END
    _send(fd, cmd)


def send_cmd_play(fd, ch, audio, loop):
    """Play audio (X3/X5 only)"""
    cmd = s2b("play " + ch + "," + audio + "," + loop) + END
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


def send_cmd_refile(fd, srcfilepath, decfilepath):
    """Rename a file (X3/X5 only)"""
    cmd = s2b("refile " + srcfilepath + "," + decfilepath) + END
    _send(fd, cmd)


def send_cmd_findfile(fd, filepath, att):
    """Find a file (X3/X5 only)"""
    cmd = s2b("findfile " + filepath + "," + att) + END
    _send(fd, cmd)


def send_cmd_rdfile(fd, filepath, addr, size, crc):
    """Pass-through file read (X3/X5 only)"""
    cmd = s2b("rdfile " + filepath + "," + addr + "," + size + "," + crc) + END
    _send(fd, cmd)


def send_cmd_newfile(fd, filepath, size):
    """Create a file (X3/X5 only)"""
    cmd = s2b("newfile " + filepath + "," + size) + END
    _send(fd, cmd)


def send_cmd_newdir(fd, dir):
    """Create a directory (X3/X5 only)"""
    cmd = s2b("newdir " + dir) + END
    _send(fd, cmd)


def send_cmd_deldir(fd, dir):
    """Delete a directory (X3/X5 only)"""
    cmd = s2b("deldir " + dir) + END
    _send(fd, cmd)


def send_cmd_redir(fd, srcdir, decdir):
    """Rename a directory (X3/X5 only)"""
    cmd = s2b("redir " + srcdir + "," + decdir) + END
    _send(fd, cmd)


def send_cmd_finddir(fd, dir, att):
    """Find a directory (X3/X5 only)"""
    cmd = s2b("finddir " + dir + "," + att) + END
    _send(fd, cmd)


def send_cmd_beep(fd, time):
    """Buzzer (X2 only)"""
    cmd = s2b("beep " + time) + END
    _send(fd, cmd)


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


def send_cmd_pco2(fd, obj, poc2):
    cmd = s2b(obj + ".pco2=" + poc2) + END
    _send(fd, cmd)


def send_cmd_bpic(fd, obj, bpic):
    """Change the background picture"""
    cmd = s2b(obj + ".bpic=" + bpic) + END
    _send(fd, cmd)


def send_cmd_click(fd, obj, event):
    """Trigger the press / release event of a widget.

    NOTE: the original writes ``sizeof(cmd)`` bytes (the size of the std::string
    object, 32 on aarch64) instead of ``cmd.length()``, i.e. garbage.  The
    function is never used; here the command is truncated / padded to 32 bytes.
    """
    cmd = s2b("click " + obj + "," + event) + END
    cmd = (cmd + b"\0" * 32)[:32]
    _send(fd, cmd)


def send_cmd_prints(fd, att, lenth=0):
    """Print a variable / constant to the serial port"""
    cmd = s2b("prints " + att + "," + to_string(lenth)) + END
    _send(fd, cmd)


def send_cmd_cp(fd, obj):
    cp0 = s2b(obj + ".write(\"")
    _send(fd, cp0)


def send_cmd_vid(fd, obj, vid):
    cmd = s2b(obj + ".vid=" + vid) + END
    _send(fd, cmd)


def send_cmd_cp_write(fd, obj, data):
    _send(fd, s2b(data))


def send_cmd_cp_end(fd):
    end = b"\")" + END
    _send(fd, end)


def send_cmd_cp_close(fd, obj):
    cmd = s2b(obj + ".close()") + END
    _send(fd, cmd)


def send_cmd_byte_data(fd, data):
    if isinstance(data, int):
        data = bytes([data & 0xFF])
    _send(fd, data[:1])


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


def send_cmd_txt_start(fd, obj):
    cmd = s2b(obj + ".txt=\"")
    _send(fd, cmd)


def send_cmd_txt_data(fd, txt):
    _send(fd, s2b(txt))


def send_cmd_txt_end(fd):
    cmd = b"\"" + END
    _send(fd, cmd)


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


def send_cmd_vid_en(fd, obj, value):
    cmd = s2b(obj + ".en=" + to_string(value)) + END
    _send(fd, cmd)


def send_cmd_bauds(fd, bauds):
    cmd = s2b("bauds=" + to_string(bauds)) + END
    _send(fd, cmd)


def send_cmd_baud(fd, baud):
    cmd = s2b("baud=" + to_string(baud)) + END
    _send(fd, cmd)


def send_var_value(fd, var, value):
    cmd = s2b(var + "=" + to_string(value)) + END
    _send(fd, cmd)
