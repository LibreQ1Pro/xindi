#!/usr/bin/env python3
"""
Golden traces of the Python port alone (the C++ reference is obsolete since the port follows firmware 4.4.24).
Every scenario of harness/scenarios.py runs in the xindi-e2e container; the normalised trace (screen
instructions, Moonraker traffic, shell commands, touched files) is stored in golden/ or compared with it.
A refactoring must leave the traces unchanged; a change of behaviour shows up as a diff and is recorded on purpose.

    tests/e2e/golden.py record [-j 4] [scenario ...]    # (re)write golden/<scenario>.json
    tests/e2e/golden.py check  [-j 4] [scenario ...]    # compare; exit 1 on a difference
"""
import argparse
import concurrent.futures
import difflib
import json
import os
import sys
import tempfile

import run_e2e

HERE = os.path.dirname(os.path.abspath(__file__))
GOLDEN = os.path.join(HERE, "golden")
SECTIONS = ("pages", "screen", "ws", "http", "shell", "wpa", "files", "alive")


def trace(scenario, out_dir, timeout):
    result, output = run_e2e.run_one("py", scenario, out_dir, timeout)
    if result is None:
        return None, output
    return run_e2e.normalise(result), output


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("record", "check"))
    ap.add_argument("scenarios", nargs="*")
    ap.add_argument("-j", "--jobs", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=600)
    args = ap.parse_args()
    scenarios = args.scenarios or run_e2e.all_scenarios()
    os.makedirs(GOLDEN, exist_ok=True)
    failed = 0
    with tempfile.TemporaryDirectory() as out_dir, concurrent.futures.ThreadPoolExecutor(args.jobs) as ex:
        futures = {ex.submit(trace, s, out_dir, args.timeout): s for s in scenarios}
        results = {}
        for fut in concurrent.futures.as_completed(futures):
            results[futures[fut]] = fut.result()
    for s in scenarios:
        now, output = results[s]
        path = os.path.join(GOLDEN, s + ".json")
        if now is None:
            print("FAIL  %-20s no trace\n%s" % (s, output[-500:]))
            failed += 1
        elif args.mode == "record":
            with open(path, "w", encoding="utf-8") as f:
                json.dump(now, f, indent=1, ensure_ascii=False, sort_keys=True)
                f.write("\n")
            print("wrote %s" % s)
        else:
            try:
                with open(path, encoding="utf-8") as f:
                    old = json.load(f)
            except OSError:
                print("FAIL  %-20s no golden trace" % s)
                failed += 1
                continue
            bad = [k for k in SECTIONS if old[k] != now[k]]
            if bad:
                failed += 1
                print("FAIL  %-20s %s" % (s, ", ".join(bad)))
                for k in bad:
                    diff = difflib.unified_diff(run_e2e.fmt_lines(old[k]), run_e2e.fmt_lines(now[k]),
                                                "golden/" + k, "now/" + k, n=2, lineterm="")
                    print("\n".join("      " + l for l in list(diff)[:60]))
            else:
                print("OK    %s" % s)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
