#!/usr/bin/env python3
"""Checks the page ids that are written as numbers in the code of the pages.

The keyboards send ``prints 113,1`` (0x71, a value) followed by the id of the page the value belongs to; the host
dispatches on it (xindi/screen/events.py). The id is the position of the page in project.json, so it has to change
whenever pages are added or removed before it.
Run from display_firmware/:  python3 tools/lint_page_ids.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPECTED = {"filament_kb": "filament", "fila_set_fan": "filament", "keybdB": "printing"}


def blocks(o):
    if isinstance(o, list) and o and all(isinstance(x, str) for x in o):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from blocks(v)
    elif isinstance(o, list):
        for v in o:
            yield from blocks(v)


def main():
    project = json.load(open(os.path.join(ROOT, "project.json"), encoding="utf-8"))
    keys = [p["key"] for p in project["pages"]]
    problems = []
    for page, target in EXPECTED.items():
        want = keys.index(target)
        data = json.load(open(os.path.join(ROOT, "pages", page + ".json"), encoding="utf-8"))
        for lines in blocks(data):
            for i, line in enumerate(lines[:-1]):
                if line.strip() == "prints 113,1" and lines[i + 1].strip() != "prints %d,1" % want:
                    problems.append("%s: %s, the page '%s' is %d" % (page, lines[i + 1].strip(), target, want))
    for p in sorted(set(problems)):
        print(p)
    print("%d problems" % len(set(problems)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
