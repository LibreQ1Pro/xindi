"""Transfer of the pictures of the file list (jpg) to the screen RAM.

The TJC screen accepts files with the ``twfile`` instruction followed by data
frames: 12 byte header + payload + 2 byte CRC.  The screen answers 0x05 for
every frame that was written successfully, 0x04 on failure and 0x24 when its
buffer overflows (those bytes are picked up by ui.parse_cmd_msg_from_tjc_screen
and stored in the get_0x?? flags).
"""

import logging
import io
import os
import time

from . import paths
from . import state as g
from . import thumbnail
from .cpp import to_string, usleep, sleep

log = logging.getLogger(__name__)

# BLOCK_SIZE 3072
BLOCK_SIZE = 3800
HEADER_SIZE = 12


def _write(fd, data):
    try:
        return os.write(fd, bytes(data))
    except (OSError, ValueError):
        return -1


def time_differ(duration, start_time):
    tmp = int(time.time())
    tmp = tmp - start_time
    if tmp > duration:
        return 1
    else:
        return 0


def time_differ_ms(duration, start_time):
    tmp = int(time.time() * 1000)
    tmp = tmp - start_time
    if tmp > duration:
        return 1
    else:
        return 0


def sent_jpg_thread_handle(arg=None):
    """Preview picture thread."""
    png_path = ""
    ram_path = ""
    jpg_path = ""

    while True:
        # refresh the small preview pictures
        if g.pictures.begin_show_64_jpg:
            g.pictures.begin_show_64_jpg = False
            # 4.4.22: refresh_page_show() waits while the pictures are sent; the
            # touch (disabled by the page buttons of the file list) is enabled
            # once at the end instead of around every picture
            g.pictures.send_jpg_status = True
            for i in range(6):
                if g.pictures.have_64_jpg[i]:
                    usleep(50500 + i * 500)
                    ram_path = "ram/" + "file" + to_string(i) + ".jpg"
                    if isinstance(g.pictures.have_64_png_path[i], thumbnail.GcodeRef):
                        # Python only: jpg made from the thumbnail inside the gcode file
                        log.debug("%s", g.pictures.have_64_png_path[i])
                        jpg_data = thumbnail.jpeg(g.pictures.have_64_png_path[i], 112)
                        if jpg_data is not None:
                            sent_jpg_to_tjc(ram_path, jpg_data)
                    else:
                        jpg_path = paths.gcode_files() + "/" + g.pictures.have_64_png_path[i]
                        log.debug("%s", jpg_path)
                        sent_jpg_to_tjc(ram_path, jpg_path)
                    g.pictures.have_64_jpg[i] = False
            g.pictures.send_jpg_status = False
            g.port.tsw("255", "1")      # enable touch
            log.debug("Touch enabled")

        usleep(60000)


def delet_pic(ram_path):
    """Delete a picture"""
    g.port.delfile(ram_path)


def getFileSize(f):
    """Size of an opened file"""
    try:
        cur = f.tell()
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(0)
        return size
    except OSError:
        return -1


def calccrc(crcbuf, crc):
    """CRC of a single byte"""
    crc = crc ^ crcbuf
    for i in range(8):
        chk = crc & 1
        crc = crc >> 1
        crc = crc & 0x7fff
        if chk == 1:
            crc = crc ^ 0xa001
        crc = crc & 0xffff
    return crc


def check_crc(buf, length):
    """CRC (Modbus) of a buffer, returned with the two bytes swapped"""
    crc = 0xFFFF
    for i in range(length):
        crc = calccrc(buf[i], crc)
    hi = crc % 256
    lo = crc // 256
    crc = (hi << 8) | lo
    return crc


def delete_small_jpg():
    """Delete all small preview pictures"""
    delet_pic("ram/file0.jpg")
    usleep(56000)
    delet_pic("ram/file1.jpg")
    usleep(56000)
    delet_pic("ram/file2.jpg")
    usleep(56000)
    delet_pic("ram/file3.jpg")
    usleep(56000)


def sent_jpg_to_tjc(ram_path, jpg_path):
    """Send a picture to the screen"""
    head_id = 0
    head_buf = bytearray([0x3A, 0xA1, 0xBB, 0x44, 0x7F, 0xFF, 0xFE, 0x01, 0x00, 0x00, 0xDC, 0x07])
    exit_buf = bytes([0x3A, 0xA1, 0xBB, 0x44, 0x7F, 0xFF, 0xFE, 0x00, 0xFF, 0xFF, 0x00, 0x00])
    read_buf_size = BLOCK_SIZE - len(head_buf)      # max 4096 - header

    try:
        # (Python only: the picture can also be passed as bytes kept in memory)
        f = io.BytesIO(jpg_path) if isinstance(jpg_path, (bytes, bytearray)) else open(jpg_path, "rb")
    except OSError:
        log.debug("Failed to open the file")
        return True

    filesize = getFileSize(f)

    # send the pass-through instruction
    g.port.twfile(ram_path, to_string(filesize))
    # wait for 0xfe + terminator
    usleep(105000)
    # send header + data frames until the end of the file
    g.pictures.sent_jpg_to_tjc_start_time = int(time.time())
    while True:
        chunk = f.read(read_buf_size - 2)           # keep two bytes for the CRC
        file_res = len(chunk)
        if file_res <= 0:
            break
        read_buf = bytearray(read_buf_size)
        read_buf[:file_res] = chunk

        # header
        head_buf[8] = head_id & 0xff
        head_buf[9] = (head_id >> 8) & 0xff
        head_buf[10] = (file_res + 2) & 0xff
        head_buf[11] = ((file_res + 2) >> 8) & 0xff
        g.port.write(head_buf)

        # CRC in the last two bytes
        crc_val = check_crc(read_buf, file_res)
        read_buf[file_res] = (crc_val >> 8) & 0xff
        read_buf[file_res + 1] = crc_val & 0xff
        # data
        g.port.write(read_buf[:file_res + 2])

        # 0x05 means the frame was written successfully
        g.pictures.sent_jpg_to_tjc_start_time = int(time.time())
        resent_time = int(time.time() * 1000)
        g.update.get_0x05 = False
        g.update.get_0xfd = False
        g.update.get_0x04 = False
        while not g.update.get_0x05 and not g.update.get_0xfd:
            usleep(2000)
            # 0x04 means the frame could not be written
            if g.update.get_0x04:
                # leave the pass-through mode
                g.port.write(exit_buf)
                print("".join("%02X" % b for b in exit_buf))
                g.port.write(exit_buf)
                log.info("Got 0x04, failed")
                f.close()
                return False
            # re-send on timeout
            if time_differ_ms(800, resent_time) and not g.update.get_0x24:
                resent_time = int(time.time() * 1000)
                # re-send the data frame
                g.port.write(head_buf)
                g.port.write(read_buf[:file_res + 2])
                log.info("Timed out waiting for the answer, re-sending the frame")

            # timeout
            if time_differ(4, g.pictures.sent_jpg_to_tjc_start_time):
                g.port.write(exit_buf)
                print("".join("%02X" % b for b in exit_buf))
                g.port.write(exit_buf)
                g.port.write(exit_buf)
                log.info("Timed out writing the data frame, failed")
                f.close()
                return False

            # CLL stop sending when the screen buffer overflows
            if g.update.get_0x24:
                sleep(4)
                g.update.get_0x24 = False
                f.close()       # (Python only: the original leaks the FILE)
                return False

        # next frame id
        head_id = (head_id + 1) & 0xffff
        # timeout
        if time_differ(6, g.pictures.sent_jpg_to_tjc_start_time):
            g.port.write(exit_buf)
            print("".join("%02X" % b for b in exit_buf))
            g.port.write(exit_buf)
            g.port.write(exit_buf)
            log.info("Timed out writing the picture, failed")
            f.close()
            break

    log.info("Picture written to the screen memory")
    f.close()
    return True


