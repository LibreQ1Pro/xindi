# Making a release

The host program is a source tree; the screen firmware needs a `.tft` that only the USART HMI editor can make.
A release is therefore: the source archive, the `.HMI` project and the `.tft` built from it.

## 1. Version

The version is `VERSION` in `xindi/screen/navigation.py` (semver as a tuple; the screen gets `major * 10000 + minor * 100 + patch`,
0.1.0 is 100). The screen firmware is built for the same number (`logo.version` of the project): after a change of `VERSION`
run `python3 display_firmware/tools/migrate_home.py` (and rebuild) so that the main page does not show the version warning.
Add the release to `CHANGELOG.md`.

## 2. Checks (everything green before a tag)

```sh
python3 tests/run_unit.py                    # in docker (xindi-port-test)
python3 tests/e2e/golden.py check            # traces of everything the host does and sends to the screen
cd display_firmware
for t in lint_program lint_frames lint_page_ids lint_faces check_host_names test_pages test_behaviour; do python3 tools/$t.py; done
```

## 3. Build the project and the `.tft`

```sh
cd display_firmware
python3 tools/build_hmi.py out/xindi_v0.1.0.HMI          # lints, validation, packing; writes out/xindi_v0.1.0.HMI.sha256
```

Open the `.HMI` in the USART HMI editor, compile it (a compile error is a defect of the project), run it in the debugger for a look
at Home, the file list, a keypad and a pop-up, then *File → Output production file* (the `.tft`). Name it `xindi_v0.1.0.tft` and write
its checksum: `sha256sum xindi_v0.1.0.tft > xindi_v0.1.0.tft.sha256`.

The host and the `.tft` belong together (the numbers of the pictures in `xindi/screen/faces.py` and of the pages in `pageids.py`
come from the project): a release never has one without the other.

## 4. Try it on a printer

1. Stop the service: `sudo systemctl stop xindi`.
2. `python3 main.py --flash-screen xindi_v0.1.0.tft` (the screen restarts when the download ends).
3. Start the service and go through: the setup guide, a print (start, pause, stop), the file list with a USB drive, Wi-Fi and LAN,
   the screen sleep, the emergency stop.

## 5. Tag and publish

```sh
git tag -s v0.1.0 -m "xindi 0.1.0"
git archive --prefix=xindi-0.1.0/ -o xindi-0.1.0.tar.gz v0.1.0
```

Attach to the release: `xindi-0.1.0.tar.gz`, `xindi_v0.1.0.HMI`, `xindi_v0.1.0.tft` and their `.sha256` files.
The sources of the generators are in the archive, so the `.HMI` can be rebuilt from it; the licenses of the parts are in `THIRD_PARTY.md`.
