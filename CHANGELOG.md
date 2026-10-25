# Changelog

## Unreleased

- Runs outside QIDI's image: ini configuration (`contrib/xindi.ini.example`), no `/root` and `/home/mks`, no shell
  commands, `--flash-screen FILE.tft`, USB drives through udev + systemd (`contrib/usb-automount`), systemd unit.
- New screen design (`display_firmware/`), file list with 112 px thumbnails, names without `.gcode`.
- Removed: QIDI cloud, updates (online and from USB), factory mode, c_helper.so repair.
- Calibrations call the named macros of the LibreQ1Pro Klipper config (`AUTO_CALIBRATE BED=`, `BED_SCREWS_PREPARE`,
  `UNBOXING_PREPARE`, `INPUT_SHAPER_CALIBRATE`) instead of QIDI's M4027/M4029/M4030/M4031/M901; the setup guide makes no blind
  moves; cancelling a print sends only `CANCEL_PRINT` (no `breakmacro`/`breakheater`, which mainline Klipper does not have).
- The macro steps are the `// action:xindi <event>` messages of the LibreQ1Pro Klipper config instead of the plain `M118`
  texts; the end of a print no longer sends `PRINT_END` (the slicer end G-code is `PRINT_END`), no `PRINT_END_POWEROFF`.
- The display-only macros are hidden from Mainsail / Fluidd: `_XINDI_MESH_ADAPTIVE` / `_XINDI_MESH_SAVED` instead of
  `G31` / `G32`, `_XINDI_DETECT_INTERRUPTION`, `_XINDI_RESUME_INTERRUPTED`, `_XINDI_CLEAR_LAST_FILE`; the sound button
  state is the `enabled` variable of `gcode_macro _SOUND` instead of `output_pin sound`.
