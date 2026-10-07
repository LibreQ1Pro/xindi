# Screen firmware (TJC / USART HMI, 272x480)

The unpacked stock V4.4.24 project in the portable format (see `PORTABLE_FORMAT.md` of
[QSART_Linux_EN](../../../QSART_Linux_EN)), plus the network management pages made for the Python xindi
(`xindi/netui.py`, `xindi/network.py`). Compatibility with QIDI's xindi is not kept.

## Build

```bash
cd QSART_Linux_EN
python3 hmi_project.py pack /path/to/display_firmware out.HMI --config project.json
python3 hmi_parse.py out.HMI --check
```

`out.HMI` is a project, not the firmware: open it in USART HMI and use *File -> Output production file* to get the
`.tft` (the printer flashes `/root/800_480.tft` into the screen at start-up).

`tools/add_network_pages.py` is the script that made the network changes from the stock sources (it refuses to run
twice). `tools/preview_page.py OUT.png page...` draws a rough preview of pages (Noto Sans instead of the screen fonts).

## Network pages

| page (id) | what | actions sent as `65 <page id> <action> ff ff ff` |
|---|---|---|
| `internet_page` (81) | rows "Network info", "Saved networks", "Hidden network" | 5, 6, 7 (2 LAN/Wi-Fi switch, 3 Wi-Fi list, 1 back) |
| `wifi_list` (51) | scan list; buttons "Saved" / "Hidden" next to refresh | rows 0-4, 5 prev, 6 next, 7 refresh, 8 saved, 9 hidden |
| `net_saved` (110) | saved Wi-Fi connections, 5 rows with paging | rows 0-4, 5 prev, 6 next, 23 back |
| `net_detail` (111) | one connection | 1 connect / disconnect, 2 new password, 3 autoconnect, 4 forget, 23 back |
| `net_confirm` (112) | forget the connection? | 1 forget, 0 cancel, 23 back |
| `net_info` (113) | state of the Wi-Fi and LAN interfaces | 1 Wi-Fi on/off, 2 LAN on/off, 23 back |
| `wifi_kb` (56) | the keyboard, now with a mode | 0 back; the text is sent as `0x70 <kbmode> <row> <text>` |

Texts of the new pages: English and Russian (Russian when `lang==1`, English for every other language).

The host sets the globals `kbmode` (1 password of a scanned network, 2 new password of a saved one, 3 hidden SSID,
4 hidden password) and `kbmin` (shortest accepted text) before it opens `wifi_kb`.
