# xindi – Python port of the QIDI Q1 Pro screen backend

This is a line-by-line port of the C++ screen backend (`main.cpp` + `src/` +
`include/`, the program that runs as `/root/xindi/build/xindi` on the printer)
to Python 3. It talks to the TJC (USART HMI) display on `/dev/ttyS1`, to
Moonraker on `ws://<host>:7125/websocket` and its HTTP API, and to
wpa_supplicant's control socket. It also runs the same shell commands as the
original.

## Original source

The C++ original is QIDI's [QIDI_Q1_Pro](https://github.com/QIDITECH/QIDI_Q1_Pro)
repository at commit
[`8aaa970c1a7175d0ffc0ca5a29cac92617d5733c`](https://github.com/QIDITECH/QIDI_Q1_Pro/tree/8aaa970c1a7175d0ffc0ca5a29cac92617d5733c).
The port is based on exactly this commit: the following commits of the upstream
repository removed the source code.

The port is not refactored. Every C++ file has a Python module with the same
name, and every function keeps its name, order of statements and quirks, so the
C++ sources can be used side by side with the port. Strings that are only
written to the log, and all comments, are in English. Text that is sent to the
screen is byte-identical to the original, because the screen's behaviour
depends on it.

## Running

```sh
python3 main.py localhost        # same arguments as the C++ binary
# or
python3 -m xindi localhost
```

Requirements: Python ≥ 3.7 (the printer ships Debian buster's 3.7) and Pillow
(already installed on the printer; it was used by the original `gene4.py`). No
other third-party packages are needed. The websocket client, the HTTP client
and wpa_ctrl are implemented inline.

To use it on the printer instead of the C++ binary, change the last line of
`/root/xindi/build/start.sh` from `/root/xindi/build/xindi localhost` to
`python3 /path/to/main.py localhost`.

## Helper binaries that are now built in

| Original | Replacement | Notes |
|---|---|---|
| `/root/uart` (aarch64 ELF, built from `uart.cpp`) | `xindi/uart.py` | Reverse engineered from the disassembly and checked against a development copy of `uart.cpp` (which differs only in the file name and baud rate). Flashes `/root/800_480.tft` into the screen with `whmi-wri <size>,921600,0`, sending a 4096 byte block for every `0x05` the screen returns, written in 2048 byte pieces. `main.py` calls it instead of `system("/root/uart; mv …")`. The `mv` is still a shell command. |
| `/home/mks/gene4.py` | `xindi/gene4.py` | The same Pillow code (resize, `ImageOps.pad`, RGB565). It is called directly instead of through `python3 …`, and the result stays in memory instead of `/home/mks/tjc`. |
| `/home/mks/libColPic.so` (aarch64) | `xindi/gene4.py` (`ColPic_EncodeStr` …) | Reverse engineered (`ADList0`, `Byte8bitEncode`, `ColPicEncode`, `ColPic_EncodeStr`). Output is byte-identical to the original library, including its quirks. |
| libwpa_client (`wpa_ctrl.c`) | `xindi/wpa_ctrl.py` | UNIX datagram socket client of wpa_supplicant. |
| websocketpp | `xindi/MakerbaseClient.py` | Minimal RFC 6455 client with the same connection-state semantics. |
| HTTPRequest.hpp | `xindi/HTTPRequest.py` | Includes the library's quirk of returning an empty body when the first `recv()` does not contain the whole header. |
| iniparser / dictionary | `xindi/iniparser.py`, `xindi/dictionary.py` | Byte-exact parsing and `iniparser_dump_ini()` output, including slot order. |

Scripts that are not part of this repository and are not present on the printer
image (`/home/mks/qrcode/qrcode_QD.py`, `/root/auto_update/*.py`) and real
system tools (`cp`, `mv`, `systemctl`, `dpkg`, `wpa_cli`, `curl`, `hid-flash`, …)
are still run through the shell exactly like before.

## Structure

* `xindi/state.py` holds **all global variables** of the C++ program, grouped by
  the file that defines them, with their original names and initial values.
  The code uses them as `g.<name>`.
* `xindi/cpp.py` reproduces the C/C++ semantics the code depends on:
  * 32-bit `float` rounding (`f32`) and `std::to_string`
  * `std::string::substr` / `npos` arithmetic and integer division / `%` truncating toward zero
  * C `round()`, `strtol` / `atof` / `std::stof` / stream parsing
  * nlohmann::json style access and type errors (`jget`, `jstr`, `jint`, …)
  * `pthread_create` that aborts the process on an uncaught exception, like `std::terminate`
* Every other module is the port of the C++ file with the same name. The page and
  widget constants of `ui.h` are at the top of `xindi/ui.py`. Fall-through
  `switch` cases (missing `break`) are reproduced and marked with a `NOTE`.

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
  written to `/home/mks/tjc` and read back. A failed conversion keeps the
  previous picture, as the unchanged file did.
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
  itself.
* `json_parse()` does not poll `is_get_message` every 50 µs (about 10% CPU in
  Python). It sleeps on a `threading.Event` that the websocket thread sets
  together with the flag, so messages are handled the same way, only without
  the busy loop.
* For tiny thumbnails `libColPic.so` writes past the end of its output buffer.
  The port uses a larger scratch buffer and produces the same file content.

## Tests

`tests/e2e/` contains the E2E equivalence tests. Every scenario runs once with
the original C++ program and once with this port in docker, and the complete
external behaviour is compared. The C++ sources are downloaded at the pinned
commit; the original helper binaries of the printer (`uart`, `gene4.py`,
`libColPic.so`) are not stored here and have to be provided from the printer's
eMMC. See `tests/e2e/README.md`.

## License

Copyright (C) 2024 QIDI Technology — original C++ program
([QIDI_Q1_Pro](https://github.com/QIDITECH/QIDI_Q1_Pro/tree/8aaa970c1a7175d0ffc0ca5a29cac92617d5733c);
`MoonrakerAPI` by Kenneth Lin, 2022).

The original program is licensed under the GNU Affero General Public License
v3.0, so this port, as a derived work, is distributed under the same license.
See [LICENSE](LICENSE).

Ported third-party code keeps its own copyright and license:

* `xindi/iniparser.py`, `xindi/dictionary.py`: port of iniparser,
  Copyright (c) 2000-2011 Nicolas Devillard, MIT License.
* `xindi/wpa_ctrl.py`: port of `wpa_ctrl.c` from hostap,
  Copyright (c) 2004-2007 Jouni Malinen, BSD license.
* `xindi/HTTPRequest.py`: port of HTTPRequest by Elviss Strazdins, public domain (Unlicense).
