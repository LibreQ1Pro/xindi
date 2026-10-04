"""Port of src/MakerbaseShell.cpp"""

from .cpp import popen_read, cstr, b2s

MAX_FILE_LEN = 1024 * 4


def execute_cmd(cmd):
    """Runs ``cmd`` through popen() and returns its output.

    The C++ version appends every fgets() chunk to the caller supplied buffer
    and stops once more than MAX_FILE_LEN bytes were collected; the caller's
    (zero initialised) buffer is returned here instead.
    """
    result = b""
    out = popen_read(cmd)
    if out is not None:
        pos = 0
        while pos < len(out):
            # fgets(buf_ps, MAX_FILE_LEN, ptr): up to MAX_FILE_LEN - 1 bytes or through '\n'
            end = out.find(b"\n", pos, pos + MAX_FILE_LEN - 1)
            end = (pos + MAX_FILE_LEN - 1) if end == -1 else end + 1
            chunk = out[pos:end]
            pos = end
            result += cstr(chunk)      # strcat() stops at the first NUL byte
            if len(result) > MAX_FILE_LEN:
                break
    else:
        print("popen %s error" % cmd)
    return b2s(result)
