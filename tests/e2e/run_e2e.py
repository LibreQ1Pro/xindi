#!/usr/bin/env python3
"""
Runs the E2E equivalence tests: every scenario is executed once with the
original C++ program and once with the Python port (each in a fresh
xindi-e2e container) and the recorded traces are compared.

    tests/e2e/build_images.sh            # once
    tests/e2e/run_e2e.py                 # all scenarios
    tests/e2e/run_e2e.py boot_main wifi  # selected scenarios
    tests/e2e/run_e2e.py -j 6 --keep     # parallelism / keep the traces

Traces and program logs are written to tests/e2e/out/.
"""

import argparse
import concurrent.futures
import difflib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))   # repository root = the port
IMAGE = "xindi-e2e:latest"


def all_scenarios():
    names = []
    with open(os.path.join(HERE, "harness", "scenarios.py")) as f:
        for line in f:
            m = re.match(r"def scenario_(\w+)\(", line)
            if m:
                names.append(m.group(1))
    return names


def run_one(impl, scenario, out_dir, timeout):
    cmd = ["docker", "run", "--rm", "--platform", "linux/arm64",
           "-v", "%s:/opt/src_py:ro" % ROOT,
           "-v", "%s:/opt/e2e:ro" % HERE,
           "-v", "%s:/out" % out_dir,
           IMAGE, "python3", "/opt/e2e/harness/harness.py", "--impl", impl, "--scenario", scenario, "--out", "/out"]
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        output = p.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        output = "TIMEOUT"
    path = os.path.join(out_dir, "%s_%s.json" % (impl, scenario))
    try:
        with open(path) as f:
            return json.load(f), output
    except (OSError, ValueError):
        return None, output


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def dedup(seq):
    out = []
    for item in seq:
        if not out or out[-1] != item:
            out.append(item)
    return out


def normalise_shell(cmds, impl):
    out = []
    for c in cmds:
        if impl == "cpp":
            # gene4.py / libColPic and /root/uart are built into the Python port
            if c.startswith("python3 /home/mks/gene4.py "):
                continue
            if c.startswith("/root/uart; "):
                c = c[len("/root/uart; "):]
        out.append(c)
    return dedup(out)


def normalise(result):
    impl = result["impl"]
    return {
        "screen": [{"page": v["page"], "attrs": v["attrs"]} for v in result["screen_visits"]],
        "pages": result["screen_pages"],
        "ws": dedup(result["ws_received"]),
        # file downloads are made only by the Python port, which reads the
        # thumbnails from the gcode files (the C++ program uses .thumbs files)
        # and asks Moonraker for its directories (paths.py)
        "http": dedup([r for r in result["http"] if not r.startswith(("GET /server/files/gcodes/", "GET /server/files/roots"))]),
        "shell": normalise_shell(result["shell"], impl),
        "wpa": dedup(result["wpa"]),
        "files": result["files"],
        "alive": result["exit_code_before_kill"] is None,
    }


def fmt_lines(value):
    return json.dumps(value, indent=1, ensure_ascii=False, sort_keys=True).split("\n")


def compare(cpp, py):
    """Returns a list of (section, diff text)."""
    problems = []
    a = normalise(cpp)
    b = normalise(py)
    for section in ("pages", "screen", "ws", "http", "shell", "wpa", "files", "alive"):
        if a[section] != b[section]:
            diff = "\n".join(difflib.unified_diff(fmt_lines(a[section]), fmt_lines(b[section]),
                                                  "cpp/" + section, "py/" + section, n=3, lineterm=""))
            problems.append((section, diff))
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenarios", nargs="*")
    ap.add_argument("-j", "--jobs", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--keep", action="store_true", help="keep old traces in the out directory")
    ap.add_argument("--max-diff", type=int, default=120, help="max diff lines printed per section")
    args = ap.parse_args()

    scenarios = args.scenarios or all_scenarios()
    out_dir = os.path.join(HERE, "out")
    os.makedirs(out_dir, exist_ok=True)
    if not args.keep:
        for name in os.listdir(out_dir):
            if name.endswith((".json", ".log")):
                os.unlink(os.path.join(out_dir, name))

    jobs = [(impl, s) for s in scenarios for impl in ("cpp", "py")]
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as ex:
        futures = {ex.submit(run_one, impl, s, out_dir, args.timeout): (impl, s) for impl, s in jobs}
        for fut in concurrent.futures.as_completed(futures):
            impl, s = futures[fut]
            res, output = fut.result()
            results[(impl, s)] = res
            print("[done] %-4s %-20s %s" % (impl, s, (output.strip().splitlines() or [""])[-1]))
            sys.stdout.flush()

    failed = 0
    print()
    for s in scenarios:
        cpp = results.get(("cpp", s))
        py = results.get(("py", s))
        if cpp is None or py is None:
            print("FAIL  %-20s harness did not produce a result (cpp=%s py=%s)" % (s, cpp is not None, py is not None))
            failed += 1
            continue
        problems = compare(cpp, py)
        errors = ["cpp: " + e for e in cpp["errors"]] + ["py: " + e for e in py["errors"]]
        if problems or errors:
            failed += 1
            print("FAIL  %-20s %s" % (s, ", ".join(p[0] for p in problems) or "scenario errors"))
            for e in errors:
                print("      " + e.strip().replace("\n", "\n      "))
            for section, diff in problems:
                lines = diff.split("\n")
                print("\n".join("      " + l for l in lines[:args.max_diff]))
                if len(lines) > args.max_diff:
                    print("      ... (%d more lines)" % (len(lines) - args.max_diff))
        else:
            n_visits = len(cpp["screen_visits"])
            n_ws = len(dedup(cpp["ws_received"]))
            print("OK    %-20s pages=%d ws=%d shell=%d" % (s, n_visits, n_ws, len(normalise_shell(cpp["shell"], "cpp"))))
    print()
    print("%d/%d scenarios equivalent" % (len(scenarios) - failed, len(scenarios)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
