#!/usr/bin/env python3
"""
Interactive printer for screen development - runs INSIDE the xindi-port-test image (start it with
``tests/e2e/emulator.py``). Instead of the harness' recording screen it runs the HMI emulator of hmi-builder
(docs/EMULATOR.md) on /dev/ttyS1, next to the fake Moonraker of the E2E tests and the port itself:

    browser (touch screen)  <->  hmi_emulator.py  <-- /dev/ttyS1 -->  xindi (main.py)  <->  fake Moonraker

The fake Moonraker takes commands over HTTP so that the printer can be played from a shell or the browser:

    POST /emu/status   {"extruder": {"temperature": 31.6}}        status update (notify_status_update)
    POST /emu/gcode    plain text                                  gcode response (notify_gcode_response)
    POST /emu/notify   {"method": "notify_klippy_shutdown"}       any notification ("params" optional)
    POST /emu/preset/<name>                                        a ready-made situation, see PRESETS
    GET  /emu/state                                                status objects, requests of the port
"""

import argparse
import json
import os
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import fixtures                     # noqa: E402
import harness                      # noqa: E402

PRESETS = {
    "idle": {"print_stats": {"state": "standby", "filename": "", "print_duration": 0.0},
             "display_status": {"progress": 0.0}, "pause_resume": {"is_paused": False},
             "idle_timeout": {"state": "Idle"}},
    "heating": {"extruder": {"temperature": 120.0, "target": 220.0}, "heater_bed": {"temperature": 45.0, "target": 60.0}},
    "printing": {"print_stats": {"state": "printing", "filename": "cube.gcode", "print_duration": 600.0,
                                 "filament_used": 1500.0},
                 "display_status": {"progress": 0.35}, "idle_timeout": {"state": "Printing"},
                 "extruder": {"temperature": 220.0, "target": 220.0}, "heater_bed": {"temperature": 60.0, "target": 60.0}},
    "paused": {"print_stats": {"state": "paused"}, "pause_resume": {"is_paused": True}},
    "complete": {"print_stats": {"state": "complete"}, "display_status": {"progress": 1.0},
                 "idle_timeout": {"state": "Ready"}},
    "cancelled": {"print_stats": {"state": "cancelled", "filename": ""}, "idle_timeout": {"state": "Ready"}},
    "runout": {"filament_switch_sensor fila": {"filament_detected": False}},
    "shutdown": {"webhooks": {"state": "shutdown", "state_message": "MCU shutdown (emulated)"}},
}


class Moonraker(harness.Moonraker):
    """The fake Moonraker of the tests plus the /emu/ control interface."""

    async def _http(self, request):
        from aiohttp import web
        path = request.path
        if not path.startswith("/emu/"):
            return await super()._http(request)
        try:
            if path == "/emu/state":
                with self.lock:
                    return web.json_response({"state": self.state, "ws_received": self.received[-50:],
                                              "http": self.http[-50:]})
            body = await request.text()
            if path == "/emu/status":
                self.push_status(json.loads(body))
            elif path == "/emu/gcode":
                self.push_gcode(body)
            elif path == "/emu/notify":
                msg = json.loads(body)
                self.notify(msg["method"], msg.get("params"))
            elif path.startswith("/emu/preset/"):
                name = path[len("/emu/preset/"):]
                if name not in PRESETS:
                    return web.json_response({"error": "presets: " + ", ".join(sorted(PRESETS))}, status=404)
                self.push_status(json.loads(json.dumps(PRESETS[name])))
            else:
                return web.json_response({"error": "unknown /emu/ command"}, status=404)
        except (ValueError, KeyError) as e:
            return web.json_response({"error": str(e)}, status=400)
        return web.json_response({"ok": True})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="boot_main", help="fixture options (see fixtures.OPTIONS)")
    ap.add_argument("--project", default="/opt/display_firmware")
    ap.add_argument("--builder", default="/opt/hmi-builder")
    ap.add_argument("--http", default="0.0.0.0:8765", help="web UI of the emulator")
    args = ap.parse_args()

    fixture = fixtures.Fixture(args.scenario)
    fixture.install()
    if os.path.lexists("/dev/ttyS1"):
        os.unlink("/dev/ttyS1")
    os.makedirs("/tmp/eeprom", exist_ok=True)
    emu = subprocess.Popen(
        [sys.executable, os.path.join(args.builder, "tools", "hmi_emulator.py"), args.project,
         "--pty", "/dev/ttyS1", "--http", args.http, "--watch", "--state-dir", "/tmp/eeprom"])
    for _ in range(100):
        if os.path.lexists("/dev/ttyS1"):
            break
        time.sleep(0.1)
    else:
        sys.exit("the emulator did not create /dev/ttyS1")

    mr = Moonraker(fixture)
    mr.host = "0.0.0.0"
    mr.start()
    wifi = fixture.wifi()
    if wifi is not None:
        wpa = harness.FakeWpa(wifi["status"], wifi["scan_results"])
        wpa.start()

    env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONDONTWRITEBYTECODE="1", XINDI_SHELL_LOG="/tmp/xindi_shell.log")
    sut = subprocess.Popen(["python3", "/opt/src_py/main.py", "localhost"], env=env, cwd="/root")
    print("xindi started; web UI of the screen on port %s, control on 7125 (/emu/...)" % args.http.rsplit(":", 1)[-1],
          flush=True)

    def commands():
        # shell commands of the port (systemctl, reboot, ...) go to stubs; show them
        seen = 0
        while True:
            time.sleep(1)
            try:
                with open("/tmp/xindi_shell.log", "rb") as f:
                    data = f.read()
            except OSError:
                continue
            cmds = [c for c in data.split(b"\x1e") if c]
            for c in cmds[seen:]:
                print("shell: " + c.decode("utf-8", "replace"), flush=True)
            seen = len(cmds)
    threading.Thread(target=commands, daemon=True).start()

    try:
        while sut.poll() is None and emu.poll() is None:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    for p in (sut, emu):
        if p.poll() is None:
            p.terminate()
    print("xindi exit code %r, emulator exit code %r" % (sut.poll(), emu.poll()), flush=True)


if __name__ == "__main__":
    main()
