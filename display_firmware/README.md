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
twice); `tools/draw_source_switch.py` redraws the LAN / Wi-Fi switch of the network page as a two-segment control with Lucide icons (`icons/`, ISC license);
`tools/draw_network_pictures.py` draws the backgrounds of the network pages (antialiased rounded corners, run it
again after changing a layout). Helpers: `tools/page_dump.py` (a page as text), `tools/pic_sheet.py` (pictures by id on one
image), `tools/name_pictures.py` (how the picture names were proposed); on the printer, `tests/printer/check_network.py`
checks the NetworkManager part of xindi. `tools/preview_page.py OUT.png page...` draws a rough preview of pages (Noto Sans instead of the screen fonts).

## Languages

The screen has 13 languages (the global `lang`: 0 zh, 1 ru, 2 en, 3 ja, 4 fr, 5 de, 6 it, 7 es, 8 ko, 9 pt, 10 ar, 11 tr,
12 he); every page sets its texts in `codesload` with an `if(lang==N)` chain. The text stored in the component itself
(what the editor shows) is English, and so are the pictures the editor shows by default (the per-language pictures
`*_cn`, `*_en`, `*_ru` ... are chosen by `codesload`). Rules for new texts:

- put the English text into the `txt` attribute, translations into `codesload`; a component whose text comes from the host at run time (the network pages: names, addresses, states) is left
  empty, so nothing wrong flashes while the page loads (`tools/preview_page.py` has its own sample data to draw them);
- `txt_maxl` is in bytes: a Chinese character takes 3, an Arabic one 2; check the longest language;
- the network pages take their texts from `xindi/netstrings.py` (the host uses the same table for the texts that depend on
  the state): edit the table, then run `python3 tools/net_i18n.py` from this directory;
- the copy of every language lives in tools: English and Russian in `tools/english_copy.py`, the other ten languages as
  translations of the English text in `tools/translations.py` (keyed by the English text; `SHORT` in `english_copy.py`
  holds the shorter texts where a translation does not fit its component). Run `python3 tools/english_copy.py` after
  changing either; it also reports a text that is wider or taller than its component (glyph widths of the screen font);
  Japanese, Arabic and Hebrew are not broken into lines by hand, the screen wraps them;
- `tools/lint_program.py` checks `Program.s`: every global is used by a page or the host and none is declared twice;
- `tools/page_context.py` prints every page next to the buttons it really has (to check that "tap Next" refers to a button that exists; buttons named in a text are put in quotes, an icon button is written as the icon: “>”, “+”, “↓”);

## Frames to the host

Everything the screen sends is a frame that ends with `ff ff ff`. The editor adds it by itself to the keys of
"send key" components and to `get` / `sendme`, but `prints` and `printh` send exactly what they are told: every handler
that prints a frame has to print the terminator itself (three `prints 0xff,1`, or `printh ... ff ff ff`). The host
(`xindi/screen_rx.py`) cuts the stream at the terminators, so a frame without one is glued to the next frame and both are
lost. `python3 tools/lint_frames.py` finds such handlers (`--fix` adds the terminators); run it after every change of
an event. Frames the host knows: `65 page widget [event]` (click), `70 mode row text` (keyboard), `71 page widget low high`
(a number, 2 bytes, may be `ff ff`), `1a` (invalid variable name), `91` (the screen was updated). The only thing without
a terminator is the single byte `05` the screen answers to every data packet of a picture transfer.

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

