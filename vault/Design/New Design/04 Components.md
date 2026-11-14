---
title: 04 Components
type: design
status: PROPOSED
tags: [design, redesign, components]
updated: 2026-11-14
---

# 04 · Components

> **للمستخدم (بالعربي، ببساطة):** هذي قطع الواجهة (زر، حقل، بطاقة، جدول، حوار...) وكل حالاتها. كل صفحة تنبني من نفس القطع، وهذا اللي يخلي الواجهة متناسقة. تشوفها كلها في `docs/design-prototype/components.html`.

Part of the Phase 1 design ([[01 Principles]]); values are tokens from [[03 Visual Language]]. Live examples: `docs/design-prototype/components.html` (pictures: `shots/components.en-dark.png`, `shots/components.ar-light.png`). The **names in bold are the names Phase 2 gives the base widgets** ([[06 Handoff to Build]]).

## Rules for every component
* **States.** Interactive components have: normal, hover, pressed, focus, disabled; inputs add error; buttons add busy. Focus is always the same: a 2 px `color.border.focus` ring, 2 px outside the control, visible only for keyboard focus.
* **Disabled** is `color.bg.sunken` fill, `color.text.disabled` text, `color.border.subtle` line, and a tooltip that says why whenever the reason is not on screen.
* **Right-to-left.** Layouts use leading and trailing, never left and right: the whole component mirrors. Exceptions that stay left-to-right inside a mirrored window: paths, addresses, file and setting names, numbers with units, versions, dates, the crosshair preview, the confidence bar in Stats. A tick mark, a spinner and icons other than `chev`, `back`, `ext` are not mirrored. A slider and a progress bar do mirror (they fill from the leading side).
* **Text from outside** (mod names, descriptions, hero names) is always plain text.
* **Accessible name.** Every icon-only button has a name (also its tooltip). A badge's meaning is in its words, never only its colour.

## Actions
| Component | Looks | Variants and sizes | States and notes |
|---|---|---|---|
| **Button** | height `size.control.md`, padding `space.4`, `radius.md`, label 14/500, optional leading icon | `primary` (accent fill, white label; one per view), `secondary` (surface fill, default border; the default), `ghost` (no fill or border), `danger` (danger fill; only as the confirming button of a destructive dialog), `danger-quiet` (secondary with danger text). Sizes `sm` 28, `md` 36, `lg` 44. | hover: `color.bg.hover` or `color.accent.fill-hover`; pressed: `color.bg.pressed` or `fill-pressed`; busy: a spinner replaces the icon, the label names the action in progress, the button is disabled; disabled as above. |
| **IconButton** | a square Button with only an icon | `secondary`, `ghost`; `sm`, `md` | needs an accessible name; the "more" button (`more` icon) opens a Menu. |
| **LinkButton** | accent text, trailing `chev` | none | used for "See every setting (73)" and the action line of a Home card. |
| **Menu** | `color.bg.raised`, default border, `radius.md`, popover shadow, items 32 high | item, item with icon, separator, danger item (danger text, always last, after a separator) | opens under its button aligned to the trailing edge; arrow keys move, Enter picks, Esc closes. |

## Inputs
| Component | Looks | Variants | States and notes |
|---|---|---|---|
| **TextField** | height 36, `color.bg.sunken`, `color.border.control`, `radius.md`, optional leading icon | with label above (13, secondary), with help below (12, muted) | focus ring; error: danger border and the help line turns into the reason in danger text; disabled. |
| **SearchField** | TextField with the `search` icon and a clear button when not empty | none | filters as you type; Esc clears. |
| **PathField** | TextField in the monospace face with a `folder` icon | none | always left-to-right; followed by a "Choose" button. |
| **Select** | like TextField with a `down` arrow; its list is a Menu | none | the current choice is ticked in the list. |
| **Checkbox** | 18 px box, `radius` 5, control border; on: accent fill, white tick | with label at the trailing side | used for "I understand…" and for rows of a table. |
| **Switch** | 36 × 20 pill; off: sunken with a grey knob at the leading side; on: accent fill, white knob at the trailing side | with label or alone in a settings row | for settings that apply at once (and for a mod's on/off, which opens a review first). |
| **SegmentedControl** | sunken track, the chosen segment is a raised pill | 2 to 4 short choices | for choices that swap what is shown: period, look, text size, presets. |
| **Slider** | 4 px track, accent fill from the leading side, 18 px white knob with accent ring | with end labels and a small number field | arrow keys step, Page keys step by ten; the number field is the exact value. |
| **Chip** | pill, 28 high | off (outline), on (accent tint, tick) | a filter you can switch on and off ("Hide outdated"). |

## Containers
| Component | Looks | Variants | Notes |
|---|---|---|---|
| **Card** | `color.bg.surface`, subtle border, `radius.lg`, padding `space.5`, title 16/600 then one sentence then controls | plain; `flat` (no padding, holds a Table or a List); clickable (hover: control border and raised fill, the whole card is one button) | no shadow, no icon plate in the corner, no ornaments. |
| **DoorCard** | a clickable Card with a 40 px tinted icon, the name, one status line and an action line | only on Home | disabled look (55 % opacity) when the game is not linked. |
| **ModCard** | a clickable Card: a 16:9 picture area, then name (one line, cut with …) and "type · author" | with an "Installed" badge on the picture; selected (accent border) while its sheet is open | the picture area shows the mod's picture when pictures are loaded, otherwise a tinted placeholder with the `box` icon. Grid: columns of at least 196 px. |
| **StatTile** | a small card with one number (20/600, left-to-right) and its label (13, muted) | none | rows of four. |
| **Tabs** | text tabs with a 2 px accent underline on the current one, on a subtle bottom line | with a count badge | Ctrl+Tab moves between tabs; a tab keeps its scroll position. |
| **Sidebar** / **NavItem** | 216 wide, `color.bg.sidebar`; items 40 high with icon and label | current (accent tint and accent text), with count badge | the bottom group is pinned. |
| **TopBar** | 56 high: optional Back, page name 20/600, then at the trailing side the download pill and the **GamePill** | none | the OS window frame is kept; this bar is inside the window. |
| **ActionBar** | a bar pinned to the bottom of a page: summary text at the leading side, buttons at the trailing side, the primary one last | none | appears on pages that write to the game (Performance, Crosshair, Servers). |
| **Sheet** | a 420 px panel that slides in from the trailing edge over the page (not over the sidebar), raised fill, dialog shadow | head (title, close), body (scrolls), optional foot | used for a mod's details and a map item's details. Esc closes; the page behind stays usable. |
| **Dialog** | centred, 440 or 600 wide, raised fill, `radius.lg`, dialog shadow, over a scrim that covers the whole window | confirm (440: question as title, one or two sentences, Cancel + action), review (600: facts, the list of what will change, warnings, an acknowledgement, Cancel + action) | focus starts on Cancel for destructive dialogs, on the action otherwise; Esc is Cancel; an acknowledgement Checkbox really disables the action until ticked. |

## Data
| Component | Looks | Notes |
|---|---|---|
| **DataTable** | inside a flat Card; header 13/500 muted, rows at least 44 high with a subtle line, no vertical lines | text columns align to the leading side, number columns to the trailing side with tabular figures; hover row tint; selected row `color.bg.selected`; a second line under a name is 13, muted; header click sorts and shows an arrow; a cell never wraps a name, a version or a button. |
| **List** / **ListRow** | inside a flat Card; rows with optional leading icon or status dot, a title (500), a muted line, and one control at the trailing side | used for settings rows, findings, history, "undo one tool". |
| **KeyValue** | two columns: muted label, value | used in sheets and review dialogs. |
| **Badge** | pill, 22 high, 12/500, optional 12 px icon | neutral, success, warning, danger, info, count (accent fill, white number). States a status; it is not a button. |
| **Bar** / **ConfidenceBar** | an 8 px rounded bar | Bar fills from the leading side. ConfidenceBar (Stats) shows a range on a 0 to 100 % track with a mark at 50 %: green when the whole range is above 50, red when below, grey otherwise; always left-to-right. |

## Feedback
| Component | Looks | Notes |
|---|---|---|
| **Banner** | a tinted strip inside the page: icon, a bold line, an optional second line, optional small buttons at the trailing side | info, success, warning, danger. Stays until its cause is gone. At most one banner at the top of a page; if two apply, the more serious one wins. |
| **Toast** | a small raised card at the bottom trailing corner: icon, one line, optional Undo | confirms something that just succeeded; leaves after 6 seconds or on Esc; never used for errors. |
| **ProgressBar** | 6 px, accent fill | with a number when the total is known ("page 41 of 123"), sliding when it is not. Always next to words that say what is happening and a Stop or Cancel button when stopping is safe. |
| **Spinner** | a 16 px ring | inside a busy button or beside a short "…" sentence. |
| **Skeleton** | grey rounded blocks in the shape of the content | while a page that normally has content is loading for less than a few seconds. |
| **EmptyState** | centred: a 56 px round icon, a title 16/600, one sentence, at most one button | neutral, and a danger look (red icon) for "could not". The sentence says what will appear here or what to do next. |
| **Tooltip** | inverted small label | on icon-only buttons, cut-off names, disabled controls (the reason), and statuses that need a definition. |

## What was dropped from the old system
Panel with cut corners and corner ticks, Kicker, Rule, UtilityHeader, banner artwork, step plates, the diamond slider handle, the status chips beside the title, the "page switcher" combo. Phase 3 deletes them after the last page moves ([[06 Handoff to Build]]).

Related: [[05 Screens]] · [[Design System]]
