# Screen mockup

`index.html` — open it in a browser (one file, nothing to install). It shows the new design of all 79 screens at 1:1 (272 × 480),
with the real texts of the project in the 13 languages: pick the language on the left, or click "all languages" under a screen to
see it in all 13 side by side (long German / Russian / Arabic strings show where a text does not fit). "8 px grid" draws the grid and the
page margins, "Widget names" outlines every widget and the tooltip says `page.widget x,y w×h`: these are the names and rectangles to use in the project.

Rebuild after editing `src/*`: `python3 build_mockup.py` (texts come from `texts.json`, made by `../tools/extract_texts.py` from the pages
and `xindi/util/netstrings.py`; the icons are Lucide, ISC license, `icons/*.svg`). `shot.sh IDS out.png [lang|all] [zoom] [W H]` takes a screenshot
with google-chrome (`./shot.sh home,files /tmp/a.png 2 1 1000 540`).

## The design in short

* Dark, flat, no gradients or shadows (16-bit colour bands them). Palette: `bg #17171a`, `panel #222226`, `card #2a2a30`, `btn #35353d`, accent `#3d7bff`,
  danger `#e5484d`, heater on `#ff7a59`, text `#f4f4f7` / `#a6a6b3` / `#70707d`.
* One grid of 8 px, page margin 12, content width 248, gap 8. Buttons are 44-52 high (40 minimum), list rows 44-52, cards radius 14, buttons 10, keys 8.
* Header 48 (back arrow + title, no bar), navigation bar 56 at y 424 with an accent pill behind the icon of the open page, tabs are a segmented control.
* Primary action = blue (OK, Next, Start), destructive = dark red, disabled = dim. Lists are rows with a chevron / switch / radio / lock / check.
* Pop-ups: dim page, a card with an icon of the kind (info, warning, error, done), the message, one or two buttons at the same place on every pop-up.
* Icons: Lucide line icons (stroke 2); the three heaters (nozzle, bed, chamber) are drawn here.
* Text: units ("°C", "%", "mm") and captions are text, never part of a picture; digits use a digit font.

## Fonts the screen needs (to render in USART HMI as .zi)

* Text: 13 px (captions), 15-16 px medium (body, buttons), 19-24 px semibold (titles): Latin with accents, Cyrillic, Chinese, Japanese, Korean, Arabic, Hebrew.
* Digits: 20 / 28 px semibold, tabular: `0-9 . - / % ° ℃`.

## Not in the mockup

The animations (unboxing, filament loading) are placeholders; the thumbnails are placeholders; the debug pop-up of the main page (wrong UI version) is not drawn.
Where a state exists (heater on / off, option selected / not, button pressed) the "Components" section and the screens show one state; the others
follow the same rules (selected = blue radio and raised row; pressed = darker; disabled = dim).

## Checking the spacing

`index.html?audit=1` measures the real DOM: the gaps between neighbouring blocks (buttons, cards, rows, keys) and the margins to the screen edge, for every screen. The rule is a gap of 8 and a margin of 12; `google-chrome --headless=new --dump-dom 'file:///.../index.html?audit=1'` prints the result as JSON in `<pre id=audit>`.

## Numbers with units

A text widget draws one font, so "35 %" and "220 °C" are two widgets: the number (digit font 20/28) and the unit (13), each as wide as its text, with the baselines on one line. The host knows the widths from the font and sets `x` of the unit (`unit.x=`); `y` of the unit comes from the font metrics. `vals()` in `src/kit.js` does exactly this, and the hover titles show the real rectangle of every part.
