# USB drive automount

QIDI's system image mounts USB drives with `makerbase-automount@.service` at
`/home/mks/gcode_files/sda1`, where xindi looks for updates, recovery files
and writes the logs, and where Moonraker lists the files of the drive.
Other systems (Armbian, KIAUH installs) do not have it. These files provide
a replacement that mounts the drive in the gcode directory that Moonraker
uses (`~/printer_data/gcodes/sda1`).

```sh
sudo install -m 755 xindi-usb-mount /usr/local/sbin/
sudo install -m 644 makerbase-automount@.service /etc/systemd/system/
sudo install -m 644 99-xindi-usb.rules /etc/udev/rules.d/
sudo systemctl daemon-reload
sudo udevadm control --reload
```

FAT, exFAT and NTFS drives are mounted for the `mks` user (`XINDI_USER` in
the environment of the service changes it).
