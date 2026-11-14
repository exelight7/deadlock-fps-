---
title: Home Page
type: feature
status: IMPLEMENTED
tags: [feature, redesign, home, game-link]
updated: 2026-11-14
code: [deadlock_fps/pages/home.py, deadlock_fps/game_link.py, deadlock_fps/ui.py, scripts/dev/shot_page.py]
tests: [tests/test_home.py, tests/test_workspace.py]
---

# Home page (rebuilt in Phase 3, step 1)

> **للمستخدم (بالعربي، ببساطة):** الصفحة الرئيسية انبنت من جديد على الشكل الجديد. فيها ثلاث بطاقات كبيرة (المودات، الأداء، الإحصائيات)، وقائمة «تحتاج انتباهك»، وثلاث بطاقات صغيرة (الكروس هير، السيرفرات، النسخ). إذا اللعبة غير مربوطة تطلع بطاقة «أول شي، اربط لعبتك». الشارة فوق تقول: اللعبة مرتبطة / غير مرتبطة / تعمل.

Spec: [[05 Screens]] (Home), build order: [[06 Handoff to Build]], progress: [[Handoff - Phase 3 Build (Sonnet 5.5)]].

## Parts
| Part | File | Role |
|---|---|---|
| `HomePage` | `deadlock_fps/pages/home.py` | Draws only: link card (PathField, Steam-account Select, *Find it automatically*, *Choose the folder*, *Install Deadlock from Steam*), one Banner for the game state, three DoorCards, the "Needs your attention" card (ListRows with one small button), three small clickable Cards. Fed through `set_*` methods; emits `openRequested(address)` and `gameRequired`. |
| `GameLinkMixin` | `deadlock_fps/game_link.py` | What `legacy/home.py` did (moved, readable): the folder and account, saved workspace, detection, `refresh_home()` (reads the installer for counts, updates, "mods switched off"), `repair_mods()` (the same `repair` operation as the Installed page, then a Toast). `game_linked` is the single truth; `set_game_linked` updates the `GamePill` and the page. |
| `Window.build_home` | `deadlock_fps/ui.py` | Creates the page and exposes its fields under the old names (`window.path`, `window.accounts`, `window.connection_note`) so the engines and old pages keep working. |

## Behaviour
* **Not linked:** the link card shows; Mods and Performance doors are dimmed and a press takes you to the card (they need the game); Stats works. The banner says why the game is missing (not found, Steam still downloading, no Steam). While searching: a sliding ProgressBar and a busy button.
* **Linked:** the card is hidden; every door opens its page. The **game pill** in the top bar (or `focus_game()`) brings the card back to change the folder; Phase 3's Settings > Game will take over that job. "Game is running" turns the pill amber and shows a warning Banner.
* **Needs your attention** (cheap reads only, no file hashing): mods switched off in `gameinfo.gi` (button **Repair**), installed mods with updates (**See updates** → `mods.installed`), an app update (**Update** → `settings.update`). Hidden when empty.
* Words are English-first (`tr()`), Arabic in `lang_ar.py`; no jargon on screen.

## Checked
* `tests/test_home.py` (17): the page on its own (first run, linked, doors, every game state, install button, searching, texts, attention list) and in the real window (link, pill, running, door to card, attention list from a fake installer, repair, no sideways scrolling at 940 px and 130 % text, which fails if the install button goes back into the first button row).
* Looked at by eye: English dark, Arabic light, 940 × 680, 130 % text, with and without a game, with sample attention rows (`scripts/dev/shot_page.py`).

## Not done or not verified
* The list separators of `ListRow` are not visible in the pictures (a defect in the component's style, see [[Known Issues]]).
* The icons inside cards are tinted at build time and do not follow a theme switch until the page is rebuilt.
* Light mode was only looked at on this page and the frame; the other pages stay dark until they are rebuilt.
* IBM Plex is not bundled; the pictures use the bundled Noto faces.
* Not seen on the user's own display; no screen-reader pass.

Related: [[Shell and Page Registry]] · [[Redesign Plan]] · [[Recovery]]
