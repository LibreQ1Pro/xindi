# Changelog

## Unreleased

- Runs outside QIDI's image: ini configuration (`contrib/xindi.ini.example`), no `/root` and `/home/mks`, no shell
  commands, `--flash-screen FILE.tft`, USB drives through udev + systemd (`contrib/usb-automount`), systemd unit.
- New screen design (`display_firmware/`), file list with 112 px thumbnails, names without `.gcode`.
- Removed: QIDI cloud, updates (online and from USB), factory mode, c_helper.so repair.
