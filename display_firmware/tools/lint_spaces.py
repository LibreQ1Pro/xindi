#!/usr/bin/env python3
"""Checks that no instruction of the pages has more than 60 spaces (the compiler of the editor refuses it: "extra space after the instruction").

    python3 tools/lint_spaces.py

Measured with v22: 60 spaces compile, 61 do not (the padded lines of a centred text add many).  migrate_pages.py splits such a text into several
``txt=`` / ``txt+=`` instructions (MAX_SPACES, 56 for a margin).
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIMIT = 60


def strings(node):
    if isinstance(node, dict):
        for value in node.values():
            yield from strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from strings(value)
    elif isinstance(node, str):
        yield node


def main():
    problems = []
    for path in sorted(glob.glob(os.path.join(ROOT, "pages", "*.json"))):
        for line in strings(json.load(open(path, encoding="utf-8"))):
            if ".txt" in line and line.strip().count(" ") > LIMIT:
                problems.append("%s: %d spaces: %s" % (os.path.basename(path), line.strip().count(" "), line.strip()[:60]))
    print("\n".join(problems))
    print("%d problems" % len(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
