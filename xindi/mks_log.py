"""Port of include/mks_log.h - coloured printf style logging macros."""

import sys

LOG_RED = "\033[31;1m"
LOG_YELLOW = "\033[0;33m"
LOG_GREEN = "\033[0;32m"
LOG_BLUE = "\033[0;34m"
LOG_PURPLE = "\033[0;35m"
LOG_SKYBLUE = "\033[0;36m"
LOG_HIGHLIGHT = "\033[7m\033[5m"
LOG_END = "\033[0m"


def _fmt(fmt, args):
    if args:
        try:
            return fmt % args
        except (TypeError, ValueError):
            return fmt + " " + " ".join(str(a) for a in args)
    return fmt


def _out(text):
    try:
        sys.stdout.write(text)
    except Exception:
        pass


def MKSLOG(fmt, *args):
    _out(_fmt(fmt, args) + "\n")


def MKSLOG_RED(fmt, *args):
    _out(LOG_RED + _fmt(fmt, args) + "\n" + LOG_END)


def MKSLOG_YELLOW(fmt, *args):
    _out(LOG_YELLOW + _fmt(fmt, args) + "\n" + LOG_END)


def MKSLOG_BLUE(fmt, *args):
    _out(LOG_SKYBLUE + _fmt(fmt, args) + "\n" + LOG_END)


def MKSLOG_GREEN(fmt, *args):
    _out(LOG_GREEN + _fmt(fmt, args) + "\n" + LOG_END)


def MKSLOG_HIGHLIGHT(fmt, *args):
    _out(LOG_HIGHLIGHT + _fmt(fmt, args) + "\n" + LOG_END)


def cout(*parts):
    """std::cout << a << b << ... << std::endl"""
    _out("".join(str(p) for p in parts) + "\n")


def cerr(*parts):
    """std::cerr << a << b << ..."""
    try:
        sys.stderr.write("".join(str(p) for p in parts))
    except Exception:
        pass
