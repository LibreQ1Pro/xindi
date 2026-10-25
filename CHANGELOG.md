# Changelog

## Unreleased

- Runs outside QIDI's image: ini configuration (`contrib/xindi.ini.example`), no `/root` and `/home/mks`, no shell
  commands, `--flash-screen FILE.tft`, USB drives through udev + systemd (`contrib/usb-automount`), systemd unit.
- New screen design (`display_firmware/`), file list with 112 px thumbnails, names without `.gcode`.
- Removed: QIDI cloud, updates (online and from USB), factory mode, c_helper.so repair.
- Calibrations call the named macros of the LibreQ1Pro Klipper config (`AUTO_CALIBRATE BED=`, `BED_SCREWS_PREPARE`,
  `UNBOXING_PREPARE`, `INPUT_SHAPER_CALIBRATE`) instead of QIDI's M4027/M4029/M4030/M4031/M901; the setup guide makes no blind
  moves; cancelling a print sends only `CANCEL_PRINT` (no `breakmacro`/`breakheater`, which mainline Klipper does not have).
