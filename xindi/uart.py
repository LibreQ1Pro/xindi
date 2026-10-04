"""Inline replacement of the ``/root/uart`` helper binary.

On the printer the C++ program runs ``/root/uart; mv /root/800_480.tft
/root/800_480.tft.bak`` at start-up when a screen firmware file is present.
``/root/uart`` is a small aarch64 program (built from ``uart.cpp``, GCC 8.3) that
flashes the TJC screen.  It was reverse engineered from the binary found on the
printer's eMMC; this module is a transliteration of its disassembly:

* open /dev/ttyS1 (O_RDWR | O_NOCTTY | O_NDELAY), 115200 8N1, O_NONBLOCK
* if /root/800_480.tft exists: read the whole file, send
  ``whmi-wri <filesize>,921600,0\\xff\\xff\\xff``, wait 10 ms, reopen the port at
  921600 baud
* loop (5 ms period) reading the port; every time the screen answers with a
  0x05 byte the next 4096 byte block of the file is sent (written in 2048 byte
  pieces, each followed by tcdrain)
* stop after the last (short) block has been sent.  Like the original, a file
  whose size is an exact multiple of 4096 bytes never sets the "finished" flag
  and the loop keeps running.

Strings printed by the original (partly Chinese) are translated to English.
"""

import os
import termios
import time

from .MakerbaseSerial import _cfmakeraw_zeroed

TTY_PATH = "/dev/ttyS1"
TFT_PATH = "/root/800_480.tft"


class _State(object):
    """Global variables of uart.cpp"""

    def __init__(self):
        self.fd = -1
        self.tft_data = b""
        self.tft_s = b""
        self.tft_buff = 4096        # initialised data
        self.send_finish = True     # initialised data
        self.tft_start = 0
        self.tft_end = 0
        self.tft_len = 0
        self.filesize = 0
        self.tft_index = 0


def set_option(fd, baudrate, bits, parity, stopbit):
    """set_option() of uart.cpp (identical to MakerbaseSerial's except for the
    supported baud rates: 230400, 921600 and 115200 / default)."""
    if isinstance(parity, str):
        parity = ord(parity)
    try:
        termios.tcgetattr(fd)
    except (termios.error, OSError):
        return -1

    iflag, oflag, cflag, lflag, cc = _cfmakeraw_zeroed()
    cflag |= termios.CREAD
    cflag &= ~termios.CSIZE
    if bits == 7:
        cflag |= termios.CS7
    else:
        cflag |= termios.CS8

    if parity in (ord('O'), ord('o')):
        cflag |= termios.PARENB | termios.PARODD
        cflag |= termios.INPCK
    elif parity in (ord('E'), ord('e')):
        cflag |= termios.PARENB
        cflag &= ~termios.PARODD
        iflag |= termios.INPCK
    else:
        cflag &= ~termios.PARENB
        iflag &= ~termios.INPCK

    if baudrate == 230400:
        speed = termios.B230400
        print("Baud rate is 230400")
    elif baudrate == 921600:
        speed = termios.B921600
        print("Baud rate is 921600")
    else:
        speed = termios.B115200

    if stopbit == 2:
        cflag |= termios.CSTOPB
    else:
        cflag &= ~termios.CSTOPB

    cc[termios.VTIME] = 0
    cc[termios.VMIN] = 0

    try:
        termios.tcflush(fd, termios.TCIOFLUSH)
    except (termios.error, OSError):
        return -1
    try:
        termios.tcsetattr(fd, termios.TCSANOW, [iflag, oflag, cflag, lflag, speed, speed, cc])
    except (termios.error, OSError):
        return -1
    return 0


def _write(fd, data):
    try:
        return os.write(fd, data)
    except OSError:
        return -1


def send_cmd_download(st, fd, filesize):
    cmd = b"whmi-wri " + str(filesize).encode() + b"," + str(921600).encode() + b",0\xff\xff\xff"
    _write(fd, cmd)


def send_cmd_download_data(st, fd, data):
    num = 2048
    length = len(data)
    end = num
    start = 0
    while start < length:
        if end > length:
            _write(fd, data[start:length])
            break
        _write(fd, data[start:start + num])
        start = end
        end = end + num
        try:
            termios.tcdrain(fd)
        except (termios.error, OSError):
            print("Transfer error")


def init_download_to_screen(st):
    if os.access(TFT_PATH, os.F_OK):
        st.tft_data = b""
        try:
            with open(TFT_PATH, "rb") as f:
                st.filesize = os.stat(TFT_PATH).st_size
                print("File size: %d" % st.filesize)
                st.tft_data = f.read()
        except OSError:
            st.tft_data = b""
        print("Length of the read data: %d" % len(st.tft_data))
        st.tft_len = len(st.tft_data)
        st.tft_end = st.tft_buff
        st.send_finish = False


def download_to_screen(st):
    if st.tft_start < st.tft_len:
        if st.tft_end > st.tft_len:
            st.tft_s = st.tft_data[st.tft_start:st.tft_len]
            send_cmd_download_data(st, st.fd, st.tft_s)
            st.send_finish = True
        else:
            st.tft_s = st.tft_data[st.tft_start:st.tft_start + st.tft_buff]
            st.tft_start = st.tft_end
            st.tft_end = st.tft_end + st.tft_buff
            send_cmd_download_data(st, st.fd, st.tft_s)


def parse_cmd(st, cmd):
    if cmd[0:1] == b"\x05":
        download_to_screen(st)


def _open_tty():
    try:
        return os.open(TTY_PATH, os.O_RDWR | os.O_NOCTTY | os.O_NDELAY)
    except OSError:
        return -1


def main():
    """Runs the screen firmware upload; returns the exit code of the original."""
    st = _State()
    st.fd = _open_tty()
    if st.fd < 0:
        print("OPEN TTY failed")
        return 0
    set_option(st.fd, 115200, 8, 'N', 1)
    try:
        import fcntl
        fcntl.fcntl(st.fd, fcntl.F_SETFL, os.O_NONBLOCK)
    except OSError:
        pass

    if os.access(TFT_PATH, os.F_OK):
        init_download_to_screen(st)
        send_cmd_download(st, st.fd, st.filesize)
        time.sleep(0.01)
        os.close(st.fd)
        st.fd = _open_tty()
        if st.fd < 0:
            return -1
        set_option(st.fd, 921600, 8, 'N', 1)
        print("open file ok")
    else:
        print("open file fail")

    while not st.send_finish:
        try:
            buff = os.read(st.fd, 4096)
        except OSError:
            buff = b""
        if len(buff) > 0:
            parse_cmd(st, buff)
        time.sleep(0.005)

    try:
        os.close(st.fd)
    except OSError:
        pass
    return 0
