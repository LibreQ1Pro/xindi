#!/usr/bin/env python3
"""
Equivalence test of the ini parser (runs inside the xindi-e2e image): the C
iniparser/dictionary sources of the repository (compiled here into a small
driver) against xindi/iniparser.py of the port on generated ini files.

The driver loads a file, prints a few lookups, applies set / unset
operations and dumps the result with iniparser_dump_ini().
"""

import os
import random
import subprocess
import sys

sys.path.insert(0, "/opt/src_py")

from xindi import iniparser as ip  # noqa: E402

WORK = "/tmp/initest"

DRIVER = r'''
#include <stdio.h>
#include <string.h>
#include "iniparser.h"

int main(int argc, char **argv) {
    iniparser_set_error_callback(NULL);
    dictionary *d = iniparser_load(argv[1]);
    if (!d) { printf("NULL\n"); return 0; }
    FILE *ops = fopen(argv[2], "r");
    char line[4096];
    while (fgets(line, sizeof line, ops)) {
        line[strcspn(line, "\n")] = 0;
        char *arg = strchr(line, ' ');
        if (arg) *arg++ = 0;
        if (!strcmp(line, "get")) {
            const char *v = iniparser_getstring(d, arg, "<def>");
            printf("get %s=%s|int=%d|bool=%d|dbl=%.6f\n", arg, v ? v : "(null)",
                   iniparser_getint(d, arg, -77), iniparser_getboolean(d, arg, -1),
                   iniparser_getdouble(d, arg, -1.5));
        } else if (!strcmp(line, "set")) {
            char *val = strchr(arg, '=');
            *val++ = 0;
            printf("set %d\n", iniparser_set(d, arg, val));
        } else if (!strcmp(line, "unset")) {
            iniparser_unset(d, arg);
        } else if (!strcmp(line, "dump")) {
            iniparser_dump_ini(d, stdout);
            printf("--nsec=%d\n", iniparser_getnsec(d));
        }
    }
    return 0;
}
'''

SECTIONS = ["fila", "target", "babystep", "Oobe", "MKS_ethernet", "app", "led", "x y", ""]
KEYS = ["enable", "extruder", "heaterbed", "Value", "adxl_offset", "name", "token", "method", "time", "k e y"]
VALUES = ["1", "0", "220", "0x1F", "017", "-5", "0.000", "true", "No", "yes", "", "\"quoted value\"",
          "'single'", "a=b", "with ; comment", "with # hash", "  spaced  ", "\"\"", "''", "3.5e2", "abc",
          "\xd0\x9f\xd1\x80\xd0\xb8"]


def gen_file(rng, path):
    lines = []
    for _ in range(rng.randrange(1, 40)):
        r = rng.random()
        if r < 0.15:
            lines.append("[%s]" % rng.choice(SECTIONS) + rng.choice(["", " ", "", "", "", "", "  ; c"]))
        elif r < 0.25:
            lines.append(rng.choice(["# comment", "; comment", "", "   ", "\t"]))
        elif r < 0.255:
            lines.append(rng.choice(["garbage line", "=novalue", "[unterminated", "key =", "key = ;", "key = #"]))
        elif r < 0.33:
            lines.append("%s = part1 \\" % rng.choice(KEYS))
            lines.append("part2")
        else:
            lines.append("%s%s=%s%s" % (rng.choice(KEYS), rng.choice(["", " ", "   "]), rng.choice(["", " ", "  "]),
                                        rng.choice(VALUES)))
    data = "\n".join(lines) + rng.choice(["\n", "", "\n\n"])
    with open(path, "w") as f:
        f.write(data)


def gen_ops(rng, path):
    ops = []
    for _ in range(rng.randrange(1, 12)):
        sk = "%s:%s" % (rng.choice(SECTIONS), rng.choice(KEYS))
        r = rng.random()
        if r < 0.5:
            ops.append("get " + sk)
        elif r < 0.8:
            ops.append("set %s=%s" % (sk, rng.choice(["1", "abc", "", "0.150"])))
        else:
            ops.append("unset " + sk)
    ops.append("dump")
    with open(path, "w") as f:
        f.write("\n".join(ops) + "\n")


def python_driver(ini_path, ops_path):
    ip.iniparser_set_error_callback(lambda fmt, *args: 0)
    out = []
    d = ip.iniparser_load(ini_path)
    if d is None:
        return b"NULL\n"
    import io
    for line in open(ops_path, "rb").read().split(b"\n"):
        if not line:
            continue
        cmd, _, arg = line.partition(b" ")
        if cmd == b"get":
            v = ip.iniparser_getstring(d, arg, b"<def>")
            out.append(b"get %s=%s|int=%d|bool=%d|dbl=%.6f\n" % (
                arg, v if v is not None else b"(null)", ip.iniparser_getint(d, arg, -77),
                ip.iniparser_getboolean(d, arg, -1), ip.iniparser_getdouble(d, arg, -1.5)))
        elif cmd == b"set":
            key, _, val = arg.partition(b"=")
            out.append(b"set %d\n" % ip.iniparser_set(d, key, val))
        elif cmd == b"unset":
            ip.iniparser_unset(d, arg)
        elif cmd == b"dump":
            buf = io.BytesIO()
            ip.iniparser_dump_ini(d, buf)
            out.append(buf.getvalue())
            out.append(b"--nsec=%d\n" % ip.iniparser_getnsec(d))
    return b"".join(out)


def main():
    os.makedirs(WORK, exist_ok=True)
    src = "/opt/xindi_cpp/src"
    inc = "/opt/xindi_cpp/include"
    with open(os.path.join(WORK, "driver.cpp"), "w") as f:
        f.write(DRIVER)
    exe = os.path.join(WORK, "driver")
    subprocess.run(["g++", "-w", "-fpermissive", "-I" + inc, os.path.join(WORK, "driver.cpp"),
                    os.path.join(src, "iniparser.cpp"), os.path.join(src, "dictionary.cpp"), "-o", exe], check=True)
    rng = random.Random(42)
    failures = 0
    nulls = 0
    total = 1000
    for i in range(total):
        ini = os.path.join(WORK, "t.ini")
        ops = os.path.join(WORK, "t.ops")
        gen_file(rng, ini)
        gen_ops(rng, ops)
        a = subprocess.run([exe, ini, ops], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout
        b = python_driver(ini, ops)
        if a == b"NULL\n":
            nulls += 1
        if a != b:
            failures += 1
            if failures <= 5:
                print("MISMATCH case %d\n--- ini ---\n%s\n--- ops ---\n%s\n--- c ---\n%s\n--- py ---\n%s" % (
                    i, open(ini).read(), open(ops).read(), a.decode("utf-8", "replace"), b.decode("utf-8", "replace")))
    # the real config file of the printer format
    print("iniparser: %d/%d cases identical (%d files rejected by both)" % (total - failures, total, nulls))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
