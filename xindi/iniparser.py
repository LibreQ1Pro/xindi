"""Port of src/iniparser.cpp (N. Devillard's ini file parser).

Works on byte strings like the C library.  ``sscanf`` patterns used by the
line parser are reproduced with equivalent regular expressions.
"""

import re
import sys

from .dictionary import (dictionary_new, dictionary_del, dictionary_get, dictionary_set,
                         dictionary_unset)

ASCIILINESZ = 1024
INI_INVALID_KEY = object()

LINE_UNPROCESSED = 0
LINE_ERROR = 1
LINE_EMPTY = 2
LINE_COMMENT = 3
LINE_SECTION = 4
LINE_VALUE = 5

_SPACE = b" \t\n\v\f\r"


def _isspace(c):
    return c in (0x20, 0x09, 0x0A, 0x0B, 0x0C, 0x0D)


def strlwc(s, length):
    """Lowercase (ASCII, "C" locale) at most length - 1 characters of ``s``."""
    if s is None or length == 0:
        return None
    s = s[:length - 1]
    return bytes(c + 32 if 0x41 <= c <= 0x5A else c for c in s)


def strstrip(s):
    """Remove blanks at the beginning and the end of a string."""
    if s is None:
        return b""
    start = 0
    end = len(s)
    while start < end and _isspace(s[start]):
        start += 1
    while end > start and _isspace(s[end - 1]):
        end -= 1
    return s[start:end]


def default_error_callback(fmt, *args):
    try:
        sys.stderr.write(fmt % args)
    except Exception:
        pass
    return 0


iniparser_error_callback = default_error_callback


def iniparser_set_error_callback(errback):
    global iniparser_error_callback
    iniparser_error_callback = errback if errback else default_error_callback


def iniparser_getnsec(d):
    """Number of sections in a dictionary"""
    if d is None:
        return -1
    nsec = 0
    for i in range(d.size):
        if d.key[i] is None:
            continue
        if b":" not in d.key[i]:
            nsec += 1
    return nsec


def iniparser_getsecname(d, n):
    """Name of the n-th section"""
    if d is None or n < 0:
        return None
    foundsec = 0
    i = 0
    while i < d.size:
        if d.key[i] is not None and b":" not in d.key[i]:
            foundsec += 1
            if foundsec > n:
                break
        i += 1
    if foundsec <= n:
        return None
    return d.key[i]


def iniparser_dump(d, f):
    if d is None or f is None:
        return
    for i in range(d.size):
        if d.key[i] is None:
            continue
        if d.val[i] is not None:
            f.write(b"[%s]=[%s]\n" % (d.key[i], d.val[i]))
        else:
            f.write(b"[%s]=UNDEF\n" % d.key[i])


def iniparser_dump_ini(d, f):
    """Save a dictionary to a loadable ini file (binary file object)."""
    if d is None or f is None:
        return

    nsec = iniparser_getnsec(d)
    if nsec < 1:
        # No section in file: dump all keys as they are
        for i in range(d.size):
            if d.key[i] is None:
                continue
            f.write(b"%s = %s\n" % (d.key[i], d.val[i] if d.val[i] is not None else b"(null)"))
        return
    for i in range(nsec):
        secname = iniparser_getsecname(d, i)
        iniparser_dumpsection_ini(d, secname, f)
    f.write(b"\n")


def iniparser_dumpsection_ini(d, s, f):
    """Save a dictionary section to a loadable ini file"""
    if d is None or f is None:
        return
    if not iniparser_find_entry(d, s):
        return

    seclen = len(s)
    f.write(b"\n[%s]\n" % s)
    keym = s + b":"
    for j in range(d.size):
        if d.key[j] is None:
            continue
        if d.key[j][:seclen + 1] == keym:
            f.write(b"%-30s = %s\n" % (d.key[j][seclen + 1:], d.val[j] if d.val[j] is not None else b""))
    f.write(b"\n")


def iniparser_getsecnkeys(d, s):
    nkeys = 0
    if d is None:
        return nkeys
    if not iniparser_find_entry(d, s):
        return nkeys
    seclen = len(s)
    keym = strlwc(s, ASCIILINESZ + 1) + b":"
    for j in range(d.size):
        if d.key[j] is None:
            continue
        if d.key[j][:seclen + 1] == keym:
            nkeys += 1
    return nkeys


def iniparser_getseckeys(d, s):
    if d is None:
        return None
    if not iniparser_find_entry(d, s):
        return None
    seclen = len(s)
    keym = strlwc(s, ASCIILINESZ + 1) + b":"
    keys = []
    for j in range(d.size):
        if d.key[j] is None:
            continue
        if d.key[j][:seclen + 1] == keym:
            keys.append(d.key[j])
    return keys


def iniparser_getstring(d, key, default):
    """Value of ``section:key`` or ``default``."""
    if d is None or key is None:
        return default
    lc_key = strlwc(key, ASCIILINESZ + 1)
    return dictionary_get(d, lc_key, default)


def iniparser_getlongint(d, key, notfound):
    from .cpp import strtol, b2s
    s = iniparser_getstring(d, key, INI_INVALID_KEY)
    if s is INI_INVALID_KEY or s is None:
        # NOTE: a NULL value (section entry) would crash strtol() in C
        return notfound
    return strtol(b2s(s), 0)


def iniparser_getint(d, key, notfound):
    from .cpp import i32
    return i32(iniparser_getlongint(d, key, notfound))


def iniparser_getdouble(d, key, notfound):
    from .cpp import atof, b2s
    s = iniparser_getstring(d, key, INI_INVALID_KEY)
    if s is INI_INVALID_KEY or s is None:
        return notfound
    return atof(b2s(s))


def iniparser_getboolean(d, key, notfound):
    c = iniparser_getstring(d, key, INI_INVALID_KEY)
    if c is INI_INVALID_KEY or c is None:
        return notfound
    c0 = c[0:1]
    if c0 in (b"y", b"Y", b"1", b"t", b"T"):
        ret = 1
    elif c0 in (b"n", b"N", b"0", b"f", b"F"):
        ret = 0
    else:
        ret = notfound
    return ret


def iniparser_find_entry(ini, entry):
    found = 0
    if iniparser_getstring(ini, entry, INI_INVALID_KEY) is not INI_INVALID_KEY:
        found = 1
    return found


def iniparser_set(ini, entry, val):
    return dictionary_set(ini, strlwc(entry, ASCIILINESZ + 1), val)


def iniparser_unset(ini, entry):
    dictionary_unset(ini, strlwc(entry, ASCIILINESZ + 1))


# sscanf() patterns of iniparser_line()
_RE_SECTION = re.compile(rb"\[([^\]]+)", re.S)                         # "[%[^]]"
_RE_VALUE_DQ = re.compile(rb"([^=]+)[ \t\n\v\f\r]*=[ \t\n\v\f\r]*\"([^\"]+)", re.S)   # "%[^=] = \"%[^\"]\""
_RE_VALUE_SQ = re.compile(rb"([^=]+)[ \t\n\v\f\r]*=[ \t\n\v\f\r]*'([^']+)", re.S)     # "%[^=] = '%[^\']'"
# NOTE: sscanf's whitespace directive never gives characters back, hence the
# atomic (lookahead + backreference) whitespace match before the value.
_RE_VALUE = re.compile(rb"([^=]+)[ \t\n\v\f\r]*=(?=([ \t\n\v\f\r]*))\2([^;#]+)", re.S)   # "%[^=] = %[^;#]"
_RE_VALUE_CMT = re.compile(rb"([^=]+)[ \t\n\v\f\r]*=[ \t\n\v\f\r]*([;#]+)", re.S)    # "%[^=] = %[;#]"
_RE_VALUE_EMPTY = re.compile(rb"([^=]+)[ \t\n\v\f\r]*(=+)", re.S)                     # "%[^=] %[=]"


def iniparser_line(input_line, ctx):
    """Load a single line from an INI file.

    ``ctx`` holds the ``section`` / ``key`` / ``value`` buffers which keep their
    content between calls like the C char arrays do.
    """
    line = strstrip(input_line)
    length = len(line)

    sta = LINE_UNPROCESSED
    if length < 1:
        sta = LINE_EMPTY
    elif line[0:1] in (b"#", b";"):
        sta = LINE_COMMENT
    elif line[0:1] == b"[" and line[length - 1:length] == b"]":
        m = _RE_SECTION.match(line)
        if m:
            ctx["section"] = m.group(1)
        ctx["section"] = strstrip(ctx["section"])
        ctx["section"] = strlwc(ctx["section"], length)
        sta = LINE_SECTION
    else:
        m = _RE_VALUE_DQ.match(line) or _RE_VALUE_SQ.match(line)
        if m:
            ctx["key"] = strlwc(strstrip(m.group(1)), length)
            ctx["value"] = m.group(2)
            # Don't strip spaces from values surrounded with quotes
            sta = LINE_VALUE
        else:
            m = _RE_VALUE.match(line)
            if m:
                ctx["key"] = strlwc(strstrip(m.group(1)), length)
                value = strstrip(m.group(3))
                # sscanf cannot handle '' or "" as empty values
                if value == b'""' or value == b"''":
                    value = b""
                ctx["value"] = value
                sta = LINE_VALUE
            else:
                m = _RE_VALUE_CMT.match(line) or _RE_VALUE_EMPTY.match(line)
                if m:
                    # Special cases: key=  key=;  key=#
                    ctx["key"] = strlwc(strstrip(m.group(1)), length)
                    ctx["value"] = b""
                    sta = LINE_VALUE
                else:
                    sta = LINE_ERROR
    return sta


def iniparser_load(ininame):
    """Parse an ini file and return an allocated dictionary object (or None)."""
    try:
        f = open(ininame, "rb")
    except OSError:
        iniparser_error_callback("iniparser: cannot open %s\n", ininame)
        return None

    with f:
        data = f.read()

    d = dictionary_new(0)
    ctx = {"section": b"", "key": b"", "value": b""}
    line = b""
    last = 0
    lineno = 0
    errs = 0
    mem_err = 0
    pos = 0

    while True:
        # fgets(line+last, ASCIILINESZ-last, in)
        if pos >= len(data):
            break
        maxlen = ASCIILINESZ - last - 1
        if maxlen <= 0:
            # fgets() with size 1 reads nothing; avoid an endless loop
            break
        end = data.find(b"\n", pos, pos + maxlen)
        end = (pos + maxlen) if end == -1 else end + 1
        end = min(end, len(data))
        chunk = data[pos:end]
        pos = end
        nul = chunk.find(b"\0")
        line = line[:last] + (chunk if nul == -1 else chunk[:nul])
        at_eof = pos >= len(data)

        lineno += 1
        length = len(line) - 1
        if length <= 0:
            line = b""
            last = 0
            continue
        # Safety check against buffer overflows
        if line[length:length + 1] != b"\n" and not at_eof:
            iniparser_error_callback("iniparser: input line too long in %s (%d)\n", ininame, lineno)
            dictionary_del(d)
            return None
        # Get rid of \n and spaces at end of line
        while length >= 0 and (line[length:length + 1] == b"\n" or _isspace(line[length])):
            line = line[:length]
            length -= 1
        if length < 0:
            length = 0
        # Detect multi-line
        if line[length:length + 1] == b"\\":
            last = length
            continue
        else:
            last = 0

        sta = iniparser_line(line, ctx)
        if sta in (LINE_EMPTY, LINE_COMMENT):
            pass
        elif sta == LINE_SECTION:
            mem_err = dictionary_set(d, ctx["section"], None)
        elif sta == LINE_VALUE:
            tmp = ctx["section"] + b":" + ctx["key"]
            mem_err = dictionary_set(d, tmp, ctx["value"])
        elif sta == LINE_ERROR:
            iniparser_error_callback("iniparser: syntax error in %s (%d):\n-> %s\n", ininame, lineno,
                                     line.decode("utf-8", "replace"))
            errs += 1
        line = b""
        last = 0
        if mem_err < 0:
            iniparser_error_callback("iniparser: memory allocation failure\n")
            break
    if errs:
        dictionary_del(d)
        d = None
    return d


def iniparser_freedict(d):
    dictionary_del(d)
