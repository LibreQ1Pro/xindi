# E2E equivalence tests: C++ `xindi` vs. Python port

These tests run the original C++ program and the Python port (this repository)
in the same simulated printer and check that both behave the same towards the outside
world.

## How it works

`build_images.sh` builds the `xindi-e2e` docker image for **linux/arm64**. On
an x86 host it runs through qemu binfmt. The image contains:

* the C++ program built from the original sources
  ([QIDI_Q1_Pro@8aaa970](https://github.com/QIDITECH/QIDI_Q1_Pro/tree/8aaa970c1a7175d0ffc0ca5a29cac92617d5733c):
  `main.cpp`, `src/`, `include/`, the bundled nlohmann json 3.11.3), websocketpp,
  boost, and libwpa_client from hostap 2.10;
* the **original helper binaries from the printer's eMMC**: `/root/uart`,
  `/home/mks/gene4.py` and `/home/mks/libColPic.so`. Only the C++ program
  uses them; the Python port has them built in. Running the originals is why the
  image is arm64;
* the support files: a `/bin/sh` wrapper that logs every `system()` / `popen()`
  command, no-op stubs for system tools (`systemctl`, `dpkg`, `wpa_cli`, `curl`,
  `ifconfig`, …) and an `LD_PRELOAD` shim (`timescale.c`). The shim shortens
  sleeps of ≥ 1.5 s to a quarter for both implementations. It also makes
  `write()` to the pty complete instead of returning EAGAIN, because on the real
  UART `tcdrain()` guarantees the buffer is empty before every write and on a
  pty it doesn't.

`harness/harness.py` runs inside the container and starts one implementation
with:

* a **virtual TJC screen** on a pty linked to `/dev/ttyS1`. It records every
  instruction (`page n`, `obj.attr=value`, `vis …`, `cp0.write("…")`, …),
  injects touch (`0x65`), value (`0x71`) and keyboard (`0x70`) events, and
  implements the firmware download (`whmi-wri`) and file transfer (`twfile`)
  protocols. The event byte formats were checked against the event code in
  `UI/MATE_272_480.HMI`.
* a **fake Moonraker** (aiohttp): websocket JSON-RPC (`printer.objects.*`,
  `server.files.metadata`, history totals, gcode scripts, …) plus HTTP
  `server/files/directory` backed by the fixture file tree. The scenarios push
  status updates, gcode responses and notifications through it.
* a **fake wpa_supplicant** control socket (`STATUS`, `SCAN`, `SCAN_RESULTS`,
  `SET_NETWORK`, …, events).
* deterministic **fixtures** (`harness/fixtures.py`): `config.mksini`, version
  file, saved variables, gcode files with PNG / JPEG thumbnails, a USB drive,
  update packages, a screen firmware file, server list, QR code.

Each scenario in `harness/scenarios.py` drives the program like a user would.
At the end the harness writes a JSON trace containing:

* every screen page visit with the sequence of distinct values of every widget
  attribute;
* every websocket message and HTTP request sent to Moonraker;
* every shell command;
* every wpa_supplicant command;
* the content / hash of all files the program may touch (`config.mksini`,
  `/home/mks/tjc`, `frpc.toml`, update targets, …);
* whether the program was still alive (crashes must match too).

`run_e2e.py` runs every scenario for both implementations in fresh containers
and compares the traces. Repetitions caused by the refresh loops are collapsed
(consecutive duplicates only), so timing doesn't matter but order and content
do. For the C++ run, `python3 /home/mks/gene4.py …` is dropped from the shell
log and the `/root/uart; ` prefix is removed, because the port runs both
in-process.

## Inputs of the reference image

Nothing of the original program is stored in this repository. `build_images.sh`
assembles it from three inputs, each checked against a sha256 manifest in
`manifests/`, so the reference is always exactly the same:

| Input | Where it comes from | Manifest |
|---|---|---|
| C++ sources (`main.cpp`, `CMakeLists.txt`, `src/`, `include/`) | downloaded from GitHub at the pinned commit, or `XINDI_CPP_SRC=<local checkout>` | `cpp-sources.sha256` |
| printer helper files: `/root/uart`, `/home/mks/gene4.py`, `/home/mks/libColPic.so` | `XINDI_PRINTER_FILES` (required, see below) | `printer-files.sha256` |
| hostap 2.10 (for libwpa_client) | downloaded from deb.debian.org | `hostap.sha256` |

The C++ program is always built from source, no prebuilt `xindi` binary is
needed. The printer helper files are QIDI's binaries from the printer's eMMC
(firmware V4.4.24) without a published source or license, so they are kept
outside this repository. `XINDI_PRINTER_FILES` can be:

* a directory with `uart`, `gene4.py`, `libColPic.so`;
* the printer's root file system (a mounted eMMC image or a copy of it); the
  files are taken from `root/uart`, `home/mks/gene4.py`, `home/mks/libColPic.so`;
* a `.tar.gz` with the three files at its top level, as a local path or an
  `http(s)://` URL (e.g. a release asset of a private repository).

Downloads are cached in `docker/.cache/`.

## Running

```sh
XINDI_PRINTER_FILES=/path/to/printer-files tests/e2e/build_images.sh   # once (C++ build under qemu takes a few minutes)
tests/e2e/run_e2e.py -j 8          # all scenarios, 8 containers in parallel
tests/e2e/run_e2e.py wifi print_flow
```

Requirements: docker with linux/arm64 support (on x86: qemu-user-static /
binfmt), curl, Python 3 on the host.

Traces (`out/<impl>_<scenario>.json`) and the program logs
(`out/<impl>_<scenario>.log`) are kept in `tests/e2e/out/`.

Additional library-level tests (run inside the image):

```sh
docker run --rm --platform linux/arm64 -v $PWD:/opt/src_py:ro -v $PWD/tests/e2e:/opt/e2e:ro \
    xindi-e2e python3 /opt/e2e/harness/unit_colpic.py   # original gene4.py + libColPic.so vs. port
docker run --rm --platform linux/arm64 -v $PWD:/opt/src_py:ro -v $PWD/tests/e2e:/opt/e2e:ro \
    xindi-e2e python3 /opt/e2e/harness/unit_ini.py      # original iniparser (C) vs. port, 1000 fuzzed files
```

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
| wifi | scan list paging, keyboard, connect success / failure, WPS event, save |
| wifi_connected | connected non-ASCII SSID (`\xNN` decoding), QR code, ethernet switch, server list / selection, `frpc.toml` + `config.mksini` rewrite |
| settings | system info, log export to USB, restarts, guide switch, factory reset |
| local_update | USB update detection and installation |
| online_update | version check, release notes, progress thread |
| errors | Klipper shutdown / error / ready, gcode errors, Klipper state messages, levelling error |
| notifications | all Moonraker notifications, error responses, and a malformed message that makes both implementations abort the same way |
| screen_sleep | screen sleep with the LED and wake-up |
| filament | filament load / unload, automatic and manual |
