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
| `net_info` (113) | state of the Wi-Fi and LAN interfaces | 1 Wi-Fi radio on/off, 23 back (the wired link is never switched) |
| `wifi_kb` (56) | the keyboard, now with a mode | 0 back; the text is sent as `0x70 <kbmode> <row> <text>` |

Texts of the new pages: English and Russian (Russian when `lang==1`, English for every other language).

The host sets the globals `kbmode` (1 password of a scanned network, 2 new password of a saved one, 3 hidden SSID,
4 hidden password) and `kbmin` (shortest accepted text) before it opens `wifi_kb`.

## Names

Components, pictures, fonts and animations have readable names (the stock project used `b0`, `t1`, `pic_25`, `anim_3`).
`tools/names.json` maps the stock names to the current ones, page by page; `tools/rename_objects.py` applied it (it
rewrites the names and every reference in event code, checks the result, and verifies that the inverse renaming gives
the original project back; the compiled pages differ from the stock ones only in the names). The names the Python xindi
writes in instructions were changed with `tools/rename_host.py` (`--verify` re-checks that every name the host uses
exists on the page it addresses), the picture ids it sends as numbers are the names of `xindi/pics.py`
(`tools/pics_to_names.py`).

Conventions (names are at most 14 characters, the editor's limit):

| name | what |
|---|---|
| `back_btn`, `title` | the header: the (invisible) back button and the title text |
| `nav_main`, `nav_adjust`, `nav_files`, `nav_settings` | the navigation bar at the bottom |
| `msg`, `ok`, `cancel`, `popup_bg` | message pages and pop-ups |
| `next_btn`, `prev_btn`, `next`, `prev` | paging / wizard buttons |
| `key_0`..`key_9`, `key_a`..`key_z`, `key_ok`, `key_del`, `key_space` | keyboards |
| `nozzle_*`, `bed_*`, `chamber_*`, `fan1_*`..`fan3_*` | heaters and fans: `_btn` / `_row` / `_toggle` the buttons, `_temp` the current value, `_set` the target |
| `time_elapsed`, `time_left`, `progress`, `progress_pct`, `file_name`, `thumb` | the print status block of the printing pages |
| `row1`..`row5` (`row1_txt`) | list rows of the Wi-Fi and saved-network lists; `file1`..`file4` (`file1_name`, `file1_pic`) on the file list |
| `spin1`..`spin4`, `steps_bar`, `step1_txt`.. | the step indicator of the wizards |
| `lang_cn`, `lang_ru`, ... | language buttons (the order is the value of the screen's `lang`) |

Pictures are named after what they show or where they are used (`main_off`, `main_on_press`, `bg_settings_panel`,
`rows_lock`, `files_item_dir`, ...); `unused_N` are pictures nothing refers to (N is the number in the stock name).

