---
title: 06 Handoff to Build
type: design
status: PROPOSED
tags: [design, redesign, handoff]
updated: 2026-11-14
---

# 06 · Handoff to build (for Phase 2 and Phase 3)

> **للمستخدم (بالعربي، ببساطة):** هذي الورقة للنموذجين اللي بعدي. فيها بالضبط: أسماء الألوان والمقاسات، أسماء قطع الواجهة، أسماء الصفحات، وبأي ترتيب تتحوّل الصفحات القديمة للشكل الجديد.

The design is in [[01 Principles]], [[02 Information Architecture]], [[03 Visual Language]], [[04 Components]], [[05 Screens]]. This note is the build contract. Nothing in `deadlock_fps/` was changed in Phase 1.

## Files Phase 1 produced
| Path | What |
|---|---|
| `docs/design-prototype/tokens.json` | **the token source**: `themes.dark`, `themes.light`, `accents.{violet,orange}.{dark,light}`, `scale` |
| `docs/design-prototype/tokens.css` | the same tokens for the mock-up (generated) |
| `docs/design-prototype/index.html`, `app.css`, `app.js`, `pages-main.js`, `pages-more.js` | the clickable mock-up of every screen and state |
| `docs/design-prototype/components.html` | every component and state |
| `docs/design-prototype/shots/*.png` | 48 reference pictures |
| `scripts/dev/design_tokens.py` | checks contrast; `--write` regenerates the JSON, the CSS and the tables of note 03 |
| `scripts/dev/design_shots.py` | photographs the mock-up with Qt WebEngine |

## 1. Tokens (final list)
39 colour tokens × 2 themes and 51 scale tokens. Names and values: the two tables in [[03 Visual Language]]; load them from `tokens.json`, never retype them.
* Groups: `color.bg.*` (app, sidebar, surface, raised, sunken, hover, pressed, selected, scrim), `color.border.*` (subtle, default, control, focus), `color.text.*` (primary, secondary, muted, disabled, on-accent, link), `color.accent.*` (fill, fill-hover, fill-pressed, text, tint), `color.{success,warning,danger,info}.{text,tint,border}`, `color.danger.fill`, `color.danger.fill-hover`, `color.shadow`; `space.*`, `radius.*`, `size.*`, `border.*`, `font.*`, `motion.*`, `shadow.*`, `scale.options`.
* **For Phase 2:** copy `tokens.json` into the package (for example `deadlock_fps/ui/tokens.json`; add it to the PyInstaller data files) and keep the copy in `docs/` identical (a test can compare them). A `Theme` object resolves `name → value` for (theme, accent, text scale). The stylesheet is a template with `{color.bg.surface}` style placeholders filled from it; switching theme, accent or text size re-applies the stylesheet without a restart. Painted widgets (the map canvas, sliders, the crosshair frame) read the same object.
* Colours with alpha are `#RRGGBBAA` in the JSON; Qt wants `rgba(r, g, b, a)` in a stylesheet and `QColor` takes `#AARRGGBB`: convert in one place.
* Text scale multiplies `font.size.*`, `size.control.*`, `size.icon.*`, `space.*`. "System" look follows `QStyleHints.colorScheme()`.
* Fonts: use `font.family.ui` as an ordered fallback list. IBM Plex is **not bundled** until the user agrees ([[Handoff - Phase 1 Design (Fable 5.2)]], decisions); the bundled Noto fonts are the working fallback, so nothing blocks Phase 2.

## 2. Components (final list)
Names, variants and states: [[04 Components]]. Build them as base widgets with exactly these names:

`Button` (variant: primary, secondary, ghost, danger, danger-quiet; size: sm, md, lg; busy) · `IconButton` · `LinkButton` · `Menu` · `TextField` · `SearchField` · `PathField` · `Select` · `Checkbox` · `Switch` · `SegmentedControl` · `Slider` · `Chip` · `Card` (plain, flat, clickable) · `DoorCard` · `ModCard` · `StatTile` · `Tabs` · `Sidebar` · `NavItem` · `TopBar` · `GamePill` · `ActionBar` · `Sheet` · `Dialog` (confirm, review) · `DataTable` · `List` · `ListRow` · `KeyValue` · `Badge` (neutral, success, warning, danger, info, count) · `Bar` · `ConfidenceBar` · `Banner` (info, success, warning, danger) · `Toast` · `ProgressBar` · `Spinner` · `Skeleton` · `EmptyState` (neutral, danger) · `Tooltip`.

Qt notes that shaped the design (so nothing here needs a trick):
* No shadows except on `Dialog`, `Sheet`, `Menu`, `Toast` (`QGraphicsDropShadowEffect`); cards are a fill and a 1 px border.
* Variants and states are dynamic properties (`variant="primary"`, `state="error"`) matched in the stylesheet; `Switch`, `Slider`, `ConfidenceBar`, `Bar`, `Spinner`, `Skeleton` are painted widgets.
* Keep the native window frame. On Windows set the title bar to dark or light to match the theme (DWM immersive dark mode attribute); do not build a frameless window.
* The focus ring is drawn by the widget (stylesheets cannot draw an outline outside a widget): reserve 4 px around focusable controls or paint it in the parent.
* Right-to-left: `setLayoutDirection` on the application; use `ui_common.ltr` for the left-to-right islands listed in [[04 Components]]; known trap: `QTableWidget.selectRow` in right-to-left ([[Environment and Pitfalls]]).
* Icons: the 31 paths in `docs/design-prototype/app.js` (`ICONS`, 20 × 20 view box, stroke 1.5, round caps and joins, no fill) are original to this project. Write them out as SVG files (a new folder, for example `assets/icons2/`) and tint them at run time as today; mirror `chev`, `back`, `ext` in right-to-left.

## 3. Page registry (ids for Phase 2)
From [[02 Information Architecture]]. A page is registered with: `id`, `title` (a `tr()` string), `icon`, `group` (`main`, `bottom`, `hidden`), `tabs` (list of `id`, `title`), and a builder.

| Id | Group | Icon | Tabs |
|---|---|---|---|
| `home` | main | `home` | |
| `mods` | main | `box` | `browse`, `installed`, `health`, `activity` |
| `performance` | main | `gauge` | `level`, `all` |
| `stats` | main | `chart` | `heroes`, `ranks`, `me` |
| `crosshair` | main | `crosshair` | |
| `servers` | main | `globe` | |
| `backups` | bottom | `history` | |
| `settings` | bottom | `settings` | `general`, `game`, `protect`, `update`, `sources`, `advanced`, `about` |
| `map` | hidden | `map` | |

Navigation is `navigate('mods.health')`. The start-up flags map to ids: `--mods` → `mods.installed`, `--inspector` → `mods.health`, `--updates` → `settings.update`, `--crosshair` → `crosshair`, `--install` → `settings.update` (check what it does today before mapping it).

**During Phase 2 the 17 old pages keep working inside the new shell**, each under its future home, so the app is usable at every step:

| Old page (stack number) | Temporary place in the new shell |
|---|---|
| Home 0 | `home` |
| Performance 1 | `performance.level` (the details window stays a window until Phase 3) |
| Mod Store 15 | `mods.browse` |
| Source Mods 10 | `mods.browse`, reached by a temporary second tab "My sources" |
| Installed 11 | `mods.installed` |
| Mods library 2, Inspector 7 | temporary tabs of `mods` ("Classic pack", "Inspector") |
| Compatibility 12 | `mods.health` |
| Downloads 13 | `mods.activity` |
| Stats 16 | `stats` (the old page keeps its own inner tabs until Phase 3) |
| Crosshair 5, Servers 4, Recovery 3 | `crosshair`, `servers`, `backups` |
| Settings 8 | `settings.general` |
| Updates 6 | `settings.update` |
| Sources 9 | `settings.sources` |
| Graph 14 | `map` |

## 4. Order of work for Phase 3 (one page at a time)
Each step: code, English and Arabic strings, tests, and pictures looked at in English and Arabic, dark and light, at 940 × 680. Compare with the picture of the same name in `docs/design-prototype/shots/`.

1. **Home**: small, exercises DoorCard, List, Banner, the first-run card.
2. **Mods › Browse** with the Sheet and the review Dialog: the most important path; exercises ModCard, Sheet, Dialog, EmptyState, ProgressBar.
3. **Mods › Installed**, then **Check**, then **Activity**: fold in the classic pack, the inspector and the "My sources" switch; remove the temporary tabs.
4. **Performance › Level**, then **Every setting** (the window becomes a tab): exercises Slider, SegmentedControl, ActionBar, the review Dialog, Toast.
5. **Stats** (three tabs): exercises DataTable, ConfidenceBar, StatTile.
6. **Settings** (all seven sections, including App update and Extra mod sources).
7. **Servers**, **Crosshair**, **Backups**.
8. **Project map** (recolour from tokens, Sheet for details).
9. Delete the old system (`design.py` widgets, `theme.py`, `motion.py` leftovers, unused assets and strings) and update the notes.

## 5. Checks before a page is called done
* The four states exist and can be reached in a test (filled, empty, loading, error), plus "no game" where the page needs the game.
* Words match [[05 Screens]] and [[02 Information Architecture]]; no jargon on screen; no arrow characters.
* Keyboard: every control reachable by Tab in reading order, a visible focus ring, Esc closes the top overlay, Enter activates the default button.
* Both themes, both directions, the minimum window, and text size 130 % looked at with one's own eyes.
* The usual gates: the test suite, `scripts/i18n_tool.py check`, `scripts/check_vault.py`, LF line endings ([[Verification Cookbook]]).

## 6. What Phase 1 did not verify (carry forward honestly)
* The design was rendered as HTML in Chromium (Qt WebEngine), **not in Qt widgets**: spacing and text metrics will differ a little; the tokens are the truth, the pictures are the target.
* Not seen on the user's real display; no screen reader; text sizes other than 100 % were specified, not drawn.
* The mock-up fonts are system fallbacks unless IBM Plex is installed on the viewing PC.
* Whether GameBanana thumbnails load fast enough for a card grid is unknown (pictures are off by default in the design).

Related: [[Redesign Plan]] · [[Handoff - Phase 2 Infrastructure (Opus 5.5)]] · [[Handoff - Phase 3 Build (Sonnet 5.5)]] · [[How The Code Works]]
