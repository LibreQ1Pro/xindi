"""Flashes the screen firmware (the ``/root/uart`` helper of the original, built in).

On the printer the C++ program runs ``/root/uart; mv /root/800_480.tft
/root/800_480.tft.bak`` at start-up when a screen firmware file is present.
This module is built in instead and called as ``screen_flash.main()``.

The port follows a copy of uart.cpp recovered from the printer's eMMC.  That
copy is a development variant: SEND_FILE_NAME is "UI/MATE_272_480.tft" and
TRANSFER_BAUD is 115200.  The binary /root/uart (aarch64, GCC 8.3) was built
from the same code with the two values below (checked against its
disassembly); /root/uart-230400 on the eMMC differs only in TRANSFER_BAUD.

Strings printed by the original (partly Chinese) are translated to English.
"""

import fcntl
import os
import termios
import time

from .cpp import substr, to_string
from .serial_port import _cfmakeraw_zeroed

SEND_FILE_NAME = "/root/800_480.tft"     # uart.cpp: "UI/MATE_272_480.tft"
UART_DEV = "/dev/ttyS1"
INIT_BAUD = 115200
TRANSFER_BAUD = 921600                   # uart.cpp: 115200

FNDELAY = os.O_NONBLOCK


def _init_globals():
    """Static initialisation of the globals of uart.cpp (a fresh process)."""
    global tftfile, tft_buff, tft_start, tft_end, tft_s, tft_data, tft_len, filesize
    global send_finish, tft_index, tft_buffer, fd
    tftfile = None
    tft_buff = 4096
    tft_start = 0
    tft_end = 0
    tft_s = b""
    tft_data = b""
    tft_len = 0
    filesize = 0

    send_finish = True

    tft_index = 0
    tft_buffer = bytearray(4096)

    fd = -1         # serial port descriptor


_init_globals()


def _open(path, flags):
    try:
        return os.open(path, flags)
    except OSError:
        return -1


def _read(fd, size):
    try:
        return os.read(fd, size)
    except OSError:
        return b""


def _write(fd, data):
    try:
        return os.write(fd, data)
    except OSError:
        return -1


def _close(fd):
    try:
        os.close(fd)
    except OSError:
        pass


# first_ack = 0

def main():
    global fd
    _init_globals()

    count = 0

    buff = b""

    fd = _open(UART_DEV, os.O_RDWR | os.O_NDELAY | os.O_NOCTTY)
    if fd < 0:
        print("OPEN TTY failed")
        return 0
    else:
        set_option(fd, INIT_BAUD, 8, 'N', 1)
        fcntl.fcntl(fd, fcntl.F_SETFL, FNDELAY)
        if os.path.exists(SEND_FILE_NAME):
            init_download_to_screen()
            # first_ack = 0
            send_cmd_download(fd, filesize)
            time.sleep(0.01)
            if TRANSFER_BAUD != INIT_BAUD:
                _close(fd)

                fd = _open(UART_DEV, os.O_RDWR | os.O_NDELAY | os.O_NOCTTY)
                if fd < 0:
                    return -1
                    print("OPEN TTY failed")     # (unreachable, as in the original)
                set_option(fd, TRANSFER_BAUD, 8, 'N', 1)

            print("open file ok")
        else:
            print("open file fail")

    while not send_finish:

        buff = _read(fd, 4096)
        count = len(buff)
        if count > 0:
            cmd = buff
            parse_cmd(cmd)
            buff = b""

        time.sleep(0.005)
    _close(fd)
    return 0


def parse_cmd(cmd):
    # std::cout << "Receive " << (int)cmd[0] << std::endl;
    c = cmd[0] if len(cmd) > 0 else 0
    if c == 0x5:
        download_to_screen()


def set_option(fd, baudrate, bits, parity, stopbit):
    if isinstance(parity, str):
        parity = ord(parity)

    try:
        termios.tcgetattr(fd)
    except (termios.error, OSError, ValueError):
        # error while reading the serial port parameters
        return -1

    iflag, oflag, cflag, lflag, cc = _cfmakeraw_zeroed()      # raw mode

    # enable the receiver
    cflag |= termios.CREAD

    # clear the data bits
    cflag &= ~termios.CSIZE

    if bits == 7:
        cflag |= termios.CS7
    elif bits == 8:
        cflag |= termios.CS8
    else:
        cflag |= termios.CS8

    if parity in (ord('O'), ord('o')):
        cflag |= (termios.PARENB | termios.PARODD)
        cflag |= termios.INPCK              # (sic) INPCK is an input flag, kept as in the original
    elif parity in (ord('E'), ord('e')):
        cflag |= termios.PARENB
        cflag &= ~termios.PARODD
        iflag |= termios.INPCK
    else:
        cflag &= ~termios.PARENB
        iflag &= ~termios.INPCK

    # baud rate
    if baudrate == 115200:
        speed = termios.B115200
    elif baudrate == 230400:
        speed = termios.B230400
        print("Baud rate is 230400")
    elif baudrate == 921600:
        speed = termios.B921600
        print("Baud rate is 921600")
    else:
        speed = termios.B115200

    # stop bits
    if stopbit == 1:
        cflag &= ~termios.CSTOPB
    elif stopbit == 2:
        cflag |= termios.CSTOPB
    else:
        cflag &= ~termios.CSTOPB

    # MIN and TIME set to 0
    cc[termios.VTIME] = 0
    cc[termios.VMIN] = 0

    # flush the buffers
    try:
        termios.tcflush(fd, termios.TCIOFLUSH)
    except (termios.error, OSError):
        return -1

    # apply the configuration
    try:
        termios.tcsetattr(fd, termios.TCSANOW, [iflag, oflag, cflag, lflag, speed, speed, cc])
    except (termios.error, OSError):
        return -1

    return 0


def init_download_to_screen():
    global tftfile, tft_data, filesize, tft_len, tft_end, send_finish
    if os.path.exists(SEND_FILE_NAME):
        tft_data = b""
        try:
            tftfile = open(SEND_FILE_NAME, "rb")
        except OSError:
            tftfile = None      # failed std::ifstream: rdbuf() yields nothing
        try:
            filesize = os.stat(SEND_FILE_NAME).st_size
        except OSError:
            pass                # (uninitialised struct stat in C++)
        print("File size: " + to_string(filesize))
        temp = b""
        if tftfile is not None:
            try:
                temp = tftfile.read()
            except OSError:
                temp = b""
        tft_data = temp
        print("Length of the read data: " + to_string(len(tft_data)))

        tft_len = len(tft_data)
        tft_end = tft_buff

        send_finish = False

        if tftfile is not None:
            tftfile.close()


def download_to_screen():
    global tft_s, tft_start, tft_end, send_finish
    # std::cout << "start of data " << tft_start << std::endl;
    if tft_start < tft_len:
        if tft_end > tft_len:
            tft_s = substr(tft_data, tft_start, tft_len - tft_start)
            # std::cout << "sending download data == " << tft_start << "/" << filesize << std::endl;
            send_cmd_download_data(fd, tft_s)
            send_finish = True
        else:
            tft_s = substr(tft_data, tft_start, tft_buff)
            tft_start = tft_end
            tft_end = tft_end + tft_buff
            send_cmd_download_data(fd, tft_s)


def send_cmd_download_data(fd, data):

    num = 2048
    length = len(data)
    end = num
    sub_data = b""
    # printf("download data: %d\n", len);

    start = 0
    while start < length:
        if end > length:
            sub_data = substr(data, start, length - start)
            _write(fd, sub_data)
            break
        sub_data = substr(data, start, num)
        _write(fd, sub_data)
        start = end
        end = end + num
        # time.sleep(1.55);
        try:
            termios.tcdrain(fd)
        except (termios.error, OSError):
            print("Transfer error")


def send_cmd_download(fd, filesize):
    cmd = "whmi-wri " + to_string(filesize) + "," + to_string(TRANSFER_BAUD) + ",0\xff\xff\xff"
    _write(fd, cmd.encode("latin-1"))
