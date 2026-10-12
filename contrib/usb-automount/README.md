# USB drive for xindi (udev + systemd)

xindi shows the files of a USB drive when the drive is mounted in the gcode
directory, in the folder `sda1` (the first partition; Moonraker lists the
folder like any other one, and the logs are exported to `sda1/QD_Log`).
xindi itself mounts nothing: it only looks whether `<gcodes>/sda1` is a mount
point.  Mounting is the job of udev and systemd, set up as follows.

Why not udisks: it mounts under `/media/<user>/<label>`, outside Moonraker's
gcode root, and the name is not fixed, so the drive would be neither listed by
Moonraker nor found by xindi.  If you prefer udisks, bind-mount its mount point
to `<gcodes>/sda1` yourself.

```sh
sudo install -m 755 xindi-usb-mount /usr/local/sbin/
sudo install -m 644 xindi-usb-mount@.service /etc/systemd/system/
sudo install -m 644 99-xindi-usb.rules /etc/udev/rules.d/
sudo install -m 644 xindi-usb.default /etc/default/xindi-usb
sudoedit /etc/default/xindi-usb          # XINDI_USER (and GCODES if it is not ~/printer_data/gcodes)
sudo systemctl daemon-reload
sudo udevadm control --reload
```

Plug the drive in (or `sudo udevadm trigger --action=add /dev/sda1`) and
check: `findmnt ~/printer_data/gcodes/sda1`.  FAT, exFAT and NTFS drives are
mounted for `XINDI_USER`; other file systems with their own permissions.
Needs `curl` and `python3` only when `GCODES` is not set.
