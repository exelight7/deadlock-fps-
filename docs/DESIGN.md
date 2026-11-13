# Deadlock Toolbox — design brief

**Mood:** a brass-and-ink switchboard in a haunted Manhattan tower, a little after midnight, 1931.

Everything in the interface is original, code-generated artwork in a noir, art-deco, industrial-gothic style. Nothing is copied or traced from Valve; the Deadlock wordmark, logos, heroes and icons are not used. Deadlock Toolbox is an independent community utility and is not affiliated with Valve.

The values below live in `deadlock_fps/theme.py`. The stylesheet and widgets (`design.py`, `motion.py`) and the asset generator (`scripts/make_assets.py`) all read that one file.

## 1. Palette

| Role | Token | Hex | Used for |
|---|---|---|---|
| Void | `INK` | `#07090b` | intro curtain, deepest shadow |
| Window | `BASE` | `#0b1114` | window background |
| Rail | `SIDEBAR` | `#0a0f12` | directory rail |
| Panel | `SURFACE` | `#0f1b1e` | panels, dialogs |
| Raised | `RAISED` | `#14262a` | hover, table header |
| Well | `SUNKEN` | `#091013` | inputs, tracks, code |
| Pressed | `ACTIVE` | `#1b3539` | pressed, strongest teal |
| Hairline | `LINE` | `#213739` | panel and input borders |
| Hairline strong | `LINE_STRONG` | `#35585a` | hover borders, dividers |
| Brass | `BRASS` | `#c9a45c` | the single accent |
| Brass bright | `BRASS_BRIGHT` | `#e7c08a` | selected fills, key text |
| Brass deep | `BRASS_DEEP` | `#8a6f3b` | brass borders on dark |
| On brass | `ON_BRASS` | `#17120a` | text on a brass fill |
| Text | `TEXT` | `#ede6d6` | primary text (parchment) |
| Text soft | `TEXT_SOFT` | `#b9b4a3` | descriptions |
| Text muted | `TEXT_MUTED` | `#8e948c` | captions, placeholders |
| Crimson | `CRIMSON` / `CRIMSON_TEXT` | `#b3262e` / `#ec7f86` | destructive and error only |
| Verdigris | `VERDIGRIS` | `#74c7ad` | success, connected |
| Amber | `AMBER` | `#d9a45c` | waiting, not connected |

Rules:

- One accent. Brass marks the thing to do next and the thing that is selected; nothing else is brass.
- Crimson is restrained: destructive buttons, blocking errors, a saved block. Never decoration.
- Flat fills and line work. No glossy gradients; the only gradients are scrims that keep text readable over artwork.
- Contrast: body text is at least WCAG AA (4.5:1) on every surface it sits on. Measured on `SURFACE`: `TEXT` 14.1:1, `TEXT_SOFT` 8.5:1, `TEXT_MUTED` 5.7:1, `BRASS` 7.5:1, `CRIMSON_TEXT` 6.7:1, `VERDIGRIS` 8.8:1; `ON_BRASS` on `BRASS` 7.9:1; the lowest pair in use is `TEXT_MUTED` on `RAISED` at 5.1:1. `scripts/make_assets.py --contrast` prints the table.

## 2. Type

| Face | Role | License |
|---|---|---|
| Reem Kufi (variable, 400–700) | display: page titles, panel titles, numerals, buttons that lead | SIL OFL 1.1 |
| Noto Sans Arabic + Noto Sans (variable) | body: everything you read or type | SIL OFL 1.1 |

Reem Kufi is a geometric Kufic design whose Latin is Josefin Sans, so one display face carries the 1920s geometry in both scripts. The fonts and their licenses are bundled in `assets/fonts/`.

Scale (px): hero 26 · title 24 · heading 17 · subheading 14 · body 13 · label 12 · caption 11 · kicker 10.

- Kickers are small capitals with 3px tracking, **Latin only**. Arabic is a joined script: tracking is switched off automatically whenever a label contains Arabic (`theme.has_arabic`).
- Numbers that matter (level, ping, version) are set in the display face.
- Paths, diffs and codes use the system monospace and are always left-to-right.

## 3. Space and shape

- 4px grid: 4, 8, 12, 16, 24, 32. Page gutter 28, panel padding 20, gap between panels 16, gap inside a panel 12.
- Control height 36 (compact 30). Minimum hit target 30×30.
- **One corner style: the cut corner.** Panels are chamfered by 10px with a brass tick in two opposite corners. Controls are square with a 2px radius. Nothing is pill-shaped except status pills.
- Icons: one 24px grid, one 1.5px stroke, square caps, mitred joins. Icons are SVG and are tinted at run time.
- Directory rail 232px. Form pages cap their column at 1080px so sliders stay a sensible length on wide screens; tables use the full width.

## 4. Components

- **Panel** — `SURFACE` fill, `LINE` hairline, cut corners, brass corner ticks. Optional step plate (a brass numeral) or icon in the leading corner. Title in the display face, one line of description in `TEXT_SOFT`.
- **Buttons** — four ranks, at most one primary per view.
  - Primary: brass fill, `ON_BRASS` text, double brass border.
  - Default: `SURFACE` fill, hairline; brass hairline on hover.
  - Quiet: transparent, hairline.
  - Danger: crimson hairline and text; crimson fill only on hover.
  - Positive: verdigris hairline and text.
  - States: hover lifts the border to brass, pressed drops to `ACTIVE`, focus draws a brass border, disabled drops to `TEXT_OFF` on `SUNKEN` with no border colour. Busy buttons are disabled and the page shows a brass progress line.
- **Segmented choice** (presets, tabs) — joined squares; the active one takes `BRASS_WASH` with a brass underline.
- **Slider** — 4px well, brass fill, a diamond handle.
- **Toggle / checkbox** — a square that fills brass with an ink check.
- **Table** — no grid, 1px row rules, header in kicker style on `RAISED`. Selected rows take `BRASS_SHADE` with a brass bar on the leading edge.
- **Status pill** — small, squared, tone by state: muted, ready (brass), success (verdigris), danger (crimson).
- **Dialogs** — the panel surface with a display-face title, a short summary, details behind a disclosure, and the confirming action last.
- **Empty states** — a line illustration, one sentence saying what is missing, and the action that fixes it.
- **Motion** — short and event-driven: 150ms hover, 260ms selection, 300ms page hand-over. Nothing animates while idle. Hidden widgets skip straight to their final state.

## 5. Layout

- The rail (leading side) holds the emblem, the eight destinations and the footer. The selected destination is a brass-washed plate with a brass bar.
- Each page starts with the same header: breadcrumb, title in the display face, status chips, then one line of guidance over a deco rule.
- Pages that end in an action keep that action in a bar pinned to the bottom of the window.
- Right-to-left is the default. Layouts use leading/trailing, never left/right; artwork mirrors with the layout direction; anything that is inherently left-to-right (paths, sliders with numeric ends, the English crosshair workspace) says so explicitly.

## 6. Assets

All artwork is generated by `python scripts/make_assets.py` (PySide6 only), which also writes `docs/contact-sheet.png`.

| Path | What |
|---|---|
| `assets/app.svg`, `assets/app.png`, `assets/app.ico`, `assets/brand/icon-*.png` | app icon, 16–512px and a multi-size Windows icon |
| `assets/brand/emblem.svg` | the keyhole-and-sunburst mark on its own |
| `assets/art/banner-*.svg` | header artwork: a deco skyline under a sunburst, one per banner page |
| `assets/icons/*.svg` | the line icon set |
| `assets/patterns/*.svg` | fan, lattice and chevron tiles |
| `assets/illustrations/empty-*.svg` | empty-state illustrations |

The emblem is a keyhole standing on a stepped plinth under a sunburst, inside a cut-corner frame: the lock in the name, drawn as a deco tower.
