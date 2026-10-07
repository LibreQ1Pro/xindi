# xindi – Python port of the QIDI Q1 Pro screen backend

This is a line-by-line port of the C++ screen backend (`main.cpp` + `src/` +
`include/`, the program that runs as `/root/xindi/build/xindi` on the printer)
to Python 3. It talks to the TJC (USART HMI) display on `/dev/ttyS1`, to
Moonraker on `ws://<host>:7125/websocket` and its HTTP API, and to
NetworkManager (`nmcli`) for Wi-Fi and LAN. It also runs the same shell commands as the
original.

## Original source

The C++ original is QIDI's [QIDI_Q1_Pro](https://github.com/QIDITECH/QIDI_Q1_Pro)
repository at commit
[`8aaa970c1a7175d0ffc0ca5a29cac92617d5733c`](https://github.com/QIDITECH/QIDI_Q1_Pro/tree/8aaa970c1a7175d0ffc0ca5a29cac92617d5733c).
The port is based on exactly this commit: the following commits of the upstream
repository removed the source code.

## Screen firmware 4.4.24

The port works with the screen firmware (TJC project) **V4.4.24**. The sources
above belong to the firmware V4.4.19; the changes for V4.4.24 follow QIDI's
xindi **V4.4.22** binary, for which there are no sources (it was decompiled;
functions changed in it are marked "4.4.22" in the code). The main changes:

* the screen checks the version as `major * 10000 + minor * 100 + patch` (`logo.version`; 0.1.0 is 100, see `ui.VERSION`),
* page 81 (QR code) became the network page: IP address, ethernet / Wi-Fi,
* new pages: 94 (the bed is moving, start-up guide), 95 (emergency stop
  confirmation from the printing page); the case light moved to the second
  printing page, the printing keyboard has a silent mode (50 % speed), the
  preview page a timelapse switch (Moonraker's timelapse plugin),
* the main page opens the filament page with three buttons, Wi-Fi connection
  timeout, shorter start-up guide (pages 8..10 are no longer used),
* the file list keeps its folder and page and only sends the pictures again
  when the list changed; the picture transfer pauses the page refresh,
* the screen sleep no longer switches the case light, the total print time is
  no longer counted in `config.mksini`.

**QIDI's cloud and the updates are not part of the port** (LAN only): QIDI Link (accounts, QR code login, device
binding, the frpc tunnel, server selection) and the updates from a USB drive and online are gone from the host and
from the screen firmware (their pages are removed, so the page numbers of the screen firmware differ from QIDI's).
The screen firmware itself is still flashed from `/root/800_480.tft` at start-up (`xindi/screen_flash.py`). The start-up cleanup
of the binary (`clear_deprecated_services()`, which deletes `/root/auto_update` and QIDI's frpc service) is not done.

The port began as a line-by-line translation of the C++ program and has been refactored since: the
global state is split by area (`xindi/state.py`), the page logic by what it does (`pages`, `actions`,
`settings`, `filelist`, `wifi_ui`), the clicks of the screen are a table of handlers per page
(`xindi/clicks/`), and the dead code and the modules named after the C++ files are gone. The settings file has a small parser of its own (`xindi/config_ini.py`), the log goes through the `logging` module (`XINDI_LOG=debug` shows the chatty messages), and the Moonraker messages, the gcode responses and the status objects are handled through tables. The names of
the modules and functions no longer follow the C++ sources. What the screen is sent is unchanged
and checked by the golden traces of `tests/e2e`.

## Running

```sh
python3 main.py localhost        # same arguments as the C++ binary
# or
python3 -m xindi localhost
```

Requirements: Python ≥ 3.7 (the printer ships Debian buster's 3.7) and Pillow
(already installed on the printer; it was used by the original `gene4.py`). No
other third-party packages are needed. The websocket client, the HTTP client
are implemented inline. Wi-Fi and LAN need NetworkManager (`nmcli`).

To use it on the printer instead of the C++ binary, change the last line of
`/root/xindi/build/start.sh` from `/root/xindi/build/xindi localhost` to
`python3 /path/to/main.py localhost`.

## Helper binaries that are now built in

| Original | Replacement | Notes |
|---|---|---|
| `/root/uart` (aarch64 ELF, built from `uart.cpp`) | `xindi/screen_flash.py` | Reverse engineered from the disassembly and checked against a development copy of `uart.cpp` (which differs only in the file name and baud rate). Flashes `/root/800_480.tft` into the screen with `whmi-wri <size>,921600,0`, sending a 4096 byte block for every `0x05` the screen returns, written in 2048 byte pieces. `main.py` calls it instead of `system("/root/uart; mv …")`. The `mv` is still a shell command. |
| `/home/mks/gene4.py` | `xindi/colpic.py` | The same Pillow code (resize, `ImageOps.pad`, RGB565). It is called directly instead of through `python3 …`, and the result stays in memory instead of `/home/mks/tjc`. |
| `/home/mks/libColPic.so` (aarch64) | `xindi/colpic.py` (`col_pic_encode_str` …) | Reverse engineered (`ad_list0`, `byte8bit_encode`, `col_pic_encode`, `col_pic_encode_str`). Output is byte-identical to the original library, including its quirks. |
| wpa_supplicant control socket (`mks_wpa_cli.cpp`, libwpa_client) | `xindi/network.py` | Not ported: Wi-Fi scan / connect / status and the addresses of the Wi-Fi and LAN interfaces go through NetworkManager (`nmcli`), so the screen, KlipperScreen and `nmcli` share one state. The interfaces are looked up, not assumed to be `wlan0` / `eth0`. The status keeps the wpa_supplicant words the screen code uses (`wpa_state` is `COMPLETED` when connected). |
| websocketpp | `xindi/moonraker_ws.py` | Minimal RFC 6455 client with the same connection-state semantics. |
| HTTPRequest.hpp | `xindi/http_client.py` | Includes the library's quirk of returning an empty body when the first `recv()` does not contain the whole header. |

Scripts that are not part of this repository and are not present on the printer
image and real
system tools (`cp`, `mv`, `systemctl`, `dpkg`, `curl`, `hid-flash`, …)
are still run through the shell exactly like before.

## Structure

* `xindi/state.py` holds the shared state, one object per area: `g.screen` (what the screen
  shows, page flags), `g.klippy` (the printer as Klipper reports it), `g.shown` (values last sent
  to the screen), `g.levelling`, `g.files`, `g.net`, `g.config`, `g.update`, `g.pictures` and
  `g.rpc` (the Moonraker message being handled). The two connections are `g.port` (the screen's serial port: `g.port.page(...)`, `g.port.txt(...)`, …, in `xindi/screen_tx.py`) and `g.ep` (Moonraker).
* `xindi/cpp.py` reproduces the C/C++ semantics the code depends on:
  * 32-bit `float` rounding (`f32`) and `std::to_string`
  * `std::string::substr` / `npos` arithmetic and integer division / `%` truncating toward zero
  * C `round()`, `strtol` / `atof` / `std::stof` / stream parsing
  * nlohmann::json style access and type errors (`jget`, `jstr`, `jint`, …)
  * `pthread_create` that aborts the process on an uncaught exception, like `std::terminate`
* The other modules are named after what they do (see the list in the refactoring paragraph above). The page
  ids are in `xindi/pageids.py`. Fall-through `switch` cases (missing `break`) of the C++ code are
  reproduced and marked with a `NOTE`.

## Deliberate deviations

The port follows the original including its bugs. It only differs where the C++
code has undefined behaviour that cannot be reproduced in a meaningful way:

* `page_wifi_list_ssid_button_enabled` is `bool[3]` in C++ but indexed 0..4. The
  port uses five entries.
* `std::stack::top()` on an empty stack and iterating past `std::set::end()` in
  the file list are guarded and yield an empty string / no entry.
* `send_cmd_click()` writes `sizeof(std::string)` bytes of object memory in C++.
  It is unused; the port writes the command padded to 32 bytes.
* `mks_set_psk()` uses `sprintf` into a 64 byte buffer. The port does not
  reproduce the overflow for long passwords. SSIDs are truncated at 62 bytes
  like the `snprintf` in `mks_set_ssid()`.
* The uninitialised default of `recevice_progress_handle()` is 0 / "".
* The busy loop of `recevice_progress_handle()` yields the GIL (`time.sleep(0)`)
  so that the other threads keep running.
* Converted thumbnails are kept in memory (`g.tjc_data`) instead of being
  written to `/home/mks/tjc` and read back. A failed conversion leaves no
  picture; the original keeps the unchanged file and shows the picture of the
  previous file.
* Thumbnails are read from the gcode files themselves (`xindi/thumbnail.py`):
  the start of the file is downloaded from Moonraker
  (`/server/files/gcodes/<path>` with a Range header) and the embedded
  `; thumbnail[_JPG|_QOI] begin WxH` blocks are decoded in memory. The original
  only works with QIDI's own slicer and Moonraker: it reads
  `/home/mks/gcode_files/<dir>/.thumbs/<name>-160x160.png` for the preview and
  sends `<name>-112x112_QD.jpg` to the screen for the file list. The port picks
  the best embedded size instead, and makes a 112×112 baseline JPEG for the list. The screen
  is mounted rotated, so the pictures are turned 90° counterclockwise first
  (QIDI's `.thumbs` pictures are stored turned already). When a print is started from the web UI the original
  only looks at the `.cache` copy of the file; the port falls back to the file
  itself. Transparent parts of the thumbnails are shown black (gene4.py drops
  the alpha channel and shows the colour the slicer left under it). Only the
  header of the file is read: the search stops at the first gcode command. The
  list JPEG is made before the touch is disabled for the transfer.
* `json_parse()` does not poll `is_get_message` every 50 µs (about 10% CPU in
  Python). The websocket thread puts the messages into a queue and
  `json_parse()` waits for the next one. In the original a message that
  arrives while the previous one is parsed overwrites it or is dropped when the
  flag is reset; the port handles every message.
* The directories of the gcode files, the Klipper configuration and the logs
  are not fixed to QIDI's `/home/mks/gcode_files`, `/home/mks/klipper_config`
  and `/home/mks/klipper_logs` (`xindi/paths.py`). They are asked from
  Moonraker (`/server/files/roots`); while it does not answer,
  `/home/mks/printer_data/{gcodes,config,logs}` are used when they exist, QIDI's
  otherwise. USB drives are still expected at `<gcodes>/sda1`; systems
  without QIDI's `makerbase-automount@.service` can install the one in
  `contrib/usb-automount`.
* When `config.mksini` does not exist it is created with the defaults of the
  program (QIDI's system image ships one, other systems do not, and the
  settings of the screen could not be saved).
* `sent_jpg_to_tjc()` closes the file when the screen reports a full buffer
  (0x24); the original leaks it.
* For tiny thumbnails `libColPic.so` writes past the end of its output buffer.
  The port uses a larger scratch buffer and produces the same file content.

## Tests

`tests/unit/` has the tests of the pure logic (no printer, no network): `PYTHONPATH=. python3 -I -m unittest discover -s tests/unit -t .`
(the splitting of the screen's byte stream into frames, `xindi/screen_rx.py`).

`tests/e2e/` runs the port in a simulated printer in docker and compares everything it does with golden traces,
to check refactorings (`tests/e2e/golden.py check`). See `tests/e2e/README.md`.

## License

Copyright (C) 2024 QIDI Technology — original C++ program
([QIDI_Q1_Pro](https://github.com/QIDITECH/QIDI_Q1_Pro/tree/8aaa970c1a7175d0ffc0ca5a29cac92617d5733c);
`MoonrakerAPI` by Kenneth Lin, 2022).

The original program is licensed under the GNU Affero General Public License
v3.0, so this port, as a derived work, is distributed under the same license.
See [LICENSE](LICENSE).

Ported third-party code keeps its own copyright and license:

* `xindi/http_client.py`: port of HTTPRequest by Elviss Strazdins, public domain (Unlicense).
