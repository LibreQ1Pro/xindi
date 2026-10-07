# E2E tests of the Python port

The port runs in a simulated printer inside docker, and everything it does to the outside world is
recorded and compared with the golden traces of `golden/`. They exist so that a refactoring can be
checked: a trace must not change unless the behaviour was changed on purpose.

## How it works

`build_image.sh` builds the image `xindi-port-test` (Debian with Python, Pillow and aiohttp; native
architecture, one minute). It holds only the test support: a `/bin/sh` wrapper that logs every
`system()` / `popen()` command, no-op stubs for system tools (`systemctl`, `dpkg`, `curl`, ...), and an
`LD_PRELOAD` shim (`timescale.c`) that shortens sleeps of 1.5 s and more to a quarter.

`harness/harness.py` runs inside the container and starts the port with

* a **virtual TJC screen** on a pty linked to `/dev/ttyS1`: it records every instruction (`page n`,
  `obj.attr=value`, `vis ...`, `cp0.write("...")`), injects touch (`0x65`), value (`0x71`) and keyboard
  (`0x70`) events and implements the firmware download (`whmi-wri`) and file transfer (`twfile`) protocols;
* a **fake Moonraker** (aiohttp): websocket JSON-RPC plus the HTTP API, backed by a fixture file tree;
  the scenarios push status updates, gcode responses and notifications through it;
* deterministic **fixtures** (`harness/fixtures.py`): `config.mksini`, gcode files with thumbnails, a USB
  drive, update packages, a screen firmware file.

Each scenario of `harness/scenarios.py` drives the port like a user would. The trace has every page visit
with the distinct values of every widget attribute, every websocket message and HTTP request, every shell
command, the touched files, and whether the port was still alive. Repetitions caused by the refresh loops
are collapsed, so timing does not matter, but order and content do.

## Running

```sh
tests/e2e/build_image.sh           # once
tests/e2e/golden.py check -j 22    # all scenarios at once; compare with golden/ (under a minute)
tests/e2e/golden.py check wifi     # selected scenarios
tests/e2e/golden.py record -j 22   # accept a deliberate change of behaviour
```

`XINDI_SRC=<checkout>` runs the port of another checkout (to record the traces of an older commit).

A full run takes under a minute: the harness waits for the port to go quiet (nothing new on the screen for half a
second) instead of fixed pauses, and the time-outs are a few seconds.

## Scenarios

| Scenario | Covers |
|---|---|
| boot_main | start-up sequence, subscriptions, main page refresh, cached file picture (ColPic), LED / beeper / emergency stop |
| boot_oobe | out-of-box guide pages, filament steps, `switch` fall-through 72 → 11 → 12 |
| oobe_calibrate | guide heater bed page, automatic calibration steps (gcode `echo:` responses) |
| boot_tft_update | screen firmware flashing with the built-in uart (whmi-wri protocol), c_helper.so recovery |
| boot_interrupted | power loss recovery question |
| no_cache | start without a cached file |
| file_list | file list pages, folders, USB / local, 112×112 thumbnails via `twfile`, preview pictures, back navigation |
| print_flow | starting a print, filament pop-ups, printing pages, keyboard values, z-offset, pause / resume, stop, completion |
| print_events | print started from the web UI, filament runout (switch and hall sensor), filament page while paused, print error |
| temperatures | filament page keyboards / limits, heaters, fans page, distances, printing page value events |
| move_page | moves and distances, homing / out-of-range / cold extrusion pop-ups |
| levelling | mesh table, auto levelling sequence, input shaping, probe / bltouch z-offset results |
| bed_calibration | manual bed screw calibration loop |
| settings | system info, log export to USB, restarts, guide switch, factory reset |
| errors | Klipper shutdown / error / ready, gcode errors, Klipper state messages, levelling error |
| notifications | all Moonraker notifications, error responses, and a malformed message that makes the port abort |
| screen_sleep | screen sleep with the LED and wake-up |
| filament | filament load / unload, automatic and manual |
