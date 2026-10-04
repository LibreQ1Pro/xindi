"""Inline replacement of ``/home/mks/gene4.py`` + ``/home/mks/libColPic.so``.

The C++ program converts thumbnails for the screen by running
``python3 /home/mks/gene4.py <image> /home/mks/tjc <size>``.  The script scales
the image into a square, converts it to RGB565 and encodes it with
``ColPic_EncodeStr()`` from the aarch64 library ``libColPic.so``; the resulting
text is written to /home/mks/tjc and later streamed to the screen's
``cp0``-style picture widgets.

``libColPic.so`` was reverse engineered from its disassembly (functions
ADList0, Byte8bitEncode, ColPicEncode, ColPic_EncodeStr); the code below is a
transliteration that produces byte identical output, including the quirks of
the original (e.g. the colour "distance" uses (value >> 5) & 0xff and
value & 0xff instead of real RGB components, and three NUL bytes of padding are
added when the encoded size is already a multiple of 3).

The image handling still uses Pillow, exactly like the original script.
"""

import struct
import sys

# ---------------------------------------------------------------------------
# libColPic.so
# ---------------------------------------------------------------------------

LIST_MAX = 1024


class _ColorEntry(object):
    """U16HEAD element of the colour list (12 bytes in the C struct)."""
    __slots__ = ("colo16", "A0", "A1", "A2", "qty")

    def __init__(self, colo16=0, A0=0, A1=0, A2=0, qty=0):
        self.colo16 = colo16
        self.A0 = A0
        self.A1 = A1
        self.A2 = A2
        self.qty = qty

    def copy(self):
        return _ColorEntry(self.colo16, self.A0, self.A1, self.A2, self.qty)


def ADList0(val, color_list, listqty, maxqty):
    """Adds a colour to the list (or increments its counter); returns the new length."""
    qty = listqty
    if qty >= maxqty:
        return listqty
    for i in range(qty):
        if color_list[i].colo16 == val:
            color_list[i].qty += 1
            return listqty
    A0 = (val >> 11) & 0xFF
    A1 = ((val << 5) >> 10) & 0xFF
    A2 = ((val << 11) >> 11) & 0xFF
    color_list.append(_ColorEntry(val, A0, A1, A2, 1))
    return qty + 1


def Byte8bitEncode(fromcolor16, listu16, listqty, dotsqty, outputdata, outpos, decMaxBytesize):
    """Run length encoding of the palette indexes; returns the number of bytes written."""
    dots = 0
    srcindex = 0
    decindex = 0
    lastid = 0
    while dotsqty > 0:
        dots = 1
        for i in range(dotsqty - 1):
            if fromcolor16[srcindex + i] != fromcolor16[srcindex + i + 1]:
                break
            dots += 1
            if dots == 255:
                break
        temp = 0
        for i in range(listqty):
            if listu16[i] == fromcolor16[srcindex]:
                temp = i
                break
        tid = (temp % 32) & 0xFF
        sid = (temp // 32) & 0xFF
        if lastid != sid:
            if decindex >= decMaxBytesize:
                break
            outputdata[outpos + decindex] = ((7 << 5) + sid) & 0xFF
            decindex += 1
            lastid = sid
        if dots <= 6:
            if decindex >= decMaxBytesize:
                break
            outputdata[outpos + decindex] = ((dots << 5) + tid) & 0xFF
            decindex += 1
        else:
            if decindex >= decMaxBytesize:
                break
            outputdata[outpos + decindex] = tid
            decindex += 1
            if decindex >= decMaxBytesize:
                break
            outputdata[outpos + decindex] = dots & 0xFF
            decindex += 1
        srcindex += dots
        dotsqty -= dots
    return decindex


def ColPicEncode(fromcolor16, picw, pich, outputdata, outputmaxtsize, colorsmax):
    """Builds the ColPic header + palette + encoded pixels in ``outputdata``.

    ``fromcolor16`` is modified in place (colours outside the palette are
    replaced by their closest palette entry) like in the C library.
    """
    color_list = []
    listqty = 0
    dotsqty = picw * pich
    if colorsmax > 1024:
        colorsmax = 1024
    for i in range(dotsqty):
        listqty = ADList0(fromcolor16[i], color_list, listqty, 1024)

    # sort by number of occurrences (insertion sort, descending)
    for cindex in range(1, listqty):
        tmp = color_list[cindex].copy()
        for j in range(cindex):
            if tmp.qty >= color_list[j].qty:
                del color_list[cindex]
                color_list.insert(j, tmp)
                break

    # reduce the palette to colorsmax entries
    while listqty > colorsmax:
        tmp = color_list[listqty - 1].copy()
        minval = 255
        fid = -1
        for i in range(colorsmax):
            d0 = abs(color_list[i].A0 - tmp.A0)
            d1 = abs(color_list[i].A1 - tmp.A1)
            d2 = abs(color_list[i].A2 - tmp.A2)
            s = d0 + d1 + d2
            if s < minval:
                minval = s
                fid = i
        replacement = color_list[fid].colo16
        for i in range(dotsqty):
            if fromcolor16[i] == tmp.colo16:
                fromcolor16[i] = replacement
        listqty -= 1
        del color_list[listqty:]

    # header (32 bytes)
    for i in range(32):
        outputdata[i] = 0
    outputdata[0] = 3                                   # encodever
    struct.pack_into("<H", outputdata, 2, 0)            # oncelistqty
    struct.pack_into("<I", outputdata, 12, 0x05DDC33C)  # mark
    list_data_size = listqty * 2
    struct.pack_into("<I", outputdata, 16, list_data_size)
    listu16 = []
    for i in range(listqty):
        struct.pack_into("<H", outputdata, 32 + i * 2, color_list[i].colo16)
        listu16.append(color_list[i].colo16)
    enqty = Byte8bitEncode(fromcolor16, listu16, list_data_size >> 1, dotsqty, outputdata,
                           32 + list_data_size, outputmaxtsize - list_data_size - 32)
    struct.pack_into("<I", outputdata, 20, enqty & 0xFFFFFFFF)   # ColorDataSize
    struct.pack_into("<I", outputdata, 4, picw)
    struct.pack_into("<I", outputdata, 8, pich)
    return list_data_size + enqty + 32


def ColPic_EncodeStr(fromcolor16, picw, pich, outputdata, outputmaxtsize, colorsmax):
    """Encodes the picture and converts the binary result into printable text
    (6 bits per character, offset '0', '\\' replaced by '~').  Returns the text
    length (0 on failure); ``outputdata`` holds the NUL terminated text."""
    qty = ColPicEncode(fromcolor16, picw, pich, outputdata, outputmaxtsize, colorsmax)
    if qty == 0:
        return 0
    temp = 3 - (qty % 3)
    while temp > 0:
        outputdata[qty] = 0
        qty += 1
        temp -= 1
    if (qty * 4 // 3) >= outputmaxtsize:
        return 0
    hexindex = qty
    strindex = qty * 4 // 3
    while hexindex > 0:
        hexindex -= 3
        strindex -= 4
        b0 = outputdata[hexindex]
        b1 = outputdata[hexindex + 1]
        b2 = outputdata[hexindex + 2]
        t = [
            (b0 >> 2) & 0xFF,
            (((b0 & 3) << 4) + (b1 >> 4)) & 0xFF,
            (((b1 & 15) << 2) + (b2 >> 6)) & 0xFF,
            b2 & 63,
        ]
        for k in range(4):
            c = (t[k] + 48) & 0xFF
            if c == 0x5C:       # '\\'
                c = 0x7E        # '~'
            outputdata[strindex + k] = c
    qty = qty * 4 // 3
    outputdata[qty] = 0
    return qty


# ---------------------------------------------------------------------------
# gene4.py
# ---------------------------------------------------------------------------

def convert_to_rgb565(image_path, tjc_path, size=200):
    from PIL import Image
    image = Image.open(image_path)
    ratio_image = resize_to_square(image, size)
    ratio_image = ratio_image.convert("RGB")
    width, height = ratio_image.size

    pixels = []
    for r, g_, b in ratio_image.getdata():
        pixels.append((((r >> 3) & 0x1F) << 11) | (((g_ >> 2) & 0x3F) << 5) | ((b >> 3) & 0x1F))

    # process the RGB16 data with the (re-implemented) ColPic library
    outsize = width * height * 10
    # NOTE: for tiny pictures the C library writes its 32 byte header and the
    # palette past the end of the w*h*10 byte buffer (memory corruption without a
    # crash in the original); a larger scratch buffer is used and only the
    # w*h*10 visible bytes are taken, which gives the same file content.
    outputdata = bytearray(outsize + 32 + 2 * LIST_MAX + 16)
    ColPic_EncodeStr(pixels, width, height, outputdata, width * height * 10, 1024)

    # write the output file (text up to the first NUL, like .rstrip('\x00') on the zero filled buffer)
    text = bytes(outputdata[:outsize]).decode("utf-8").rstrip("\x00")
    with open(tjc_path, "w") as tjc:
        tjc.write(text)


def resize_to_square(image, size):
    from PIL import Image, ImageOps
    width, height = image.size
    if width > height:
        ratio = size / width
    else:
        ratio = size / height

    if ratio > 1:
        ratio = 1

    new_width = int(width * ratio)
    new_height = int(height * ratio)

    resized_image = image.resize((new_width, new_height))

    square_image = Image.new('RGB', (size, size), (0, 0, 0))

    square_image = ImageOps.pad(resized_image, (size, size))
    return square_image


def main(argv):
    """Command line of gene4.py: <image path> <output path> <size>"""
    if len(argv) < 3:
        print("Please pass the image path and the output path as command line arguments")
        return 1
    image_path = argv[0]
    tjc_path = argv[1]
    try:
        size = int(argv[2])
    except ValueError:
        size = 200
    try:
        convert_to_rgb565(image_path, tjc_path, size)
    except Exception as e:
        # the original script dies with a traceback (the output file stays unchanged)
        sys.stderr.write("gene4: %s: %s\n" % (type(e).__name__, e))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
