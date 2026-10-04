"""Port of src/mks_test.cpp (factory test helpers, not used by the program)."""

from .cpp import popen_read, cstr


def _first_line(command):
    out = popen_read(command) or b""
    # fgets(buffer, sizeof(buffer), fp)
    pos = out.find(b"\n")
    line = out if pos == -1 else out[:pos + 1]
    return cstr(line[:1023])


def testUSB():
    return b"QinHeng Electronics" in _first_line("lsusb | grep \"QinHeng Electronics\"")


def moko_test_func():
    return b"OpenMoko" in _first_line("lsusb | grep \"OpenMoko\"")


def network_test_func():
    return b"inet 192.168." in _first_line("ifconfig | grep \"inet 192.168.\"")
