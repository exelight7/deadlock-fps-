---
title: Rebuilt Pages - Performance to Map
type: feature
status: IMPLEMENTED
tags: [feature, redesign, phase-3, ui]
updated: 2026-11-14
code: [deadlock_fps/pages/performance.py, deadlock_fps/pages/stats.py, deadlock_fps/pages/settings.py, deadlock_fps/pages/update.py, deadlock_fps/pages/source_list.py, deadlock_fps/pages/backups.py, deadlock_fps/pages/servers.py, deadlock_fps/pages/crosshair.py, deadlock_fps/pages/map.py, deadlock_fps/shell/base.py, deadlock_fps/shell/motion.py, deadlock_fps/ui.py, deadlock_fps/shell/registry.py]
tests: [tests/test_perf.py, tests/test_stats_ui.py, tests/test_settings_page.py, tests/test_repos_ui.py, tests/test_updates.py, tests/test_backups_page.py, tests/test_server_selection.py, tests/test_crosshair.py, tests/test_graph_ui.py, tests/test_motion.py, tests/test_shell.py]
---

# Rebuilt pages: Performance, Stats, Settings, Backups, Servers, Crosshair, Map

> **للمستخدم (بالعربي، ببساطة):** هذي آخر دفعة من إعادة التصميم. كل الصفحات الباقية انبنت على القطع الجديدة: **الأداء** (تبويبان: المستوى، وكل إعداد)، **الإحصائيات** (أبطال، رتب، إحصائياتي)، **الإعدادات** (سبعة أقسام بقائمة على الجنب، فيها زر المظهر الفاتح وحجم الخط)، **النسخ والاسترجاع**، **السيرفرات**، **الكروس هير**، و**الخريطة** (تُفتح من الإعدادات ← متقدم). والنظام القديم (design.py وtheme.py وmotion.py ومجلد legacy) انحذف.

Part of [[Redesign Plan]], phase 3. The earlier pages are in [[Home Page]], [[Browse Page]], [[Installed Page]] and [[Classic Pack and Sources]]. Parts: [[Shell and Page Registry]].

## What each page is now
| Page (address) | File | Notes |
|---|---|---|
| Performance › Level (`performance.level`) | `pages/performance.py` `LevelPage` | presets as a SegmentedControl (none selected between presets), one Slider for the level 0–200, view width (1.78–3.50) and frame limit; the review Dialog (`ApplyReview`) shows files and "what changes", every line on request; applying is a Toast with Undo (restores the originals). `PerformanceMixin` keeps `settings()`, `load_settings()`, `load_preset()`, `preview()` for the window. |
| Performance › Every setting (`performance.all`) | `AllSettingsPage` | the old "What does this level change?" window as a tab: four StatTiles, group filter, "only what the game ignores", Checkbox per row (protected rows disabled), Badge status from Valve's data ([[Performance Details]]). Moving the level clears a leave-out list made for another level. |
| Stats (`stats.heroes`, `.ranks`, `.me`) | `pages/stats.py` `StatsPage` (holds the logic) + three views | one shared filter kept in step on Heroes and Ranks; the "How sure" cell is painted by a delegate (cell widgets do not follow a sort); My stats has its own filter and says plainly that a Steam number is sent ([[Stats]]). |
| Settings (`settings.general` … `.about`) | `pages/settings.py` | one slot, a list of seven sections (`Page.section_list` hides the tab bar). General: language, look (system/dark/light), text size, less motion. Game, Protection (the guard Switch), App update (`pages/update.py`), Extra mod sources (`pages/source_list.py`), Advanced (mod pictures, project map, app data folder), About. |
| Backups (`backups`) | `pages/backups.py` | restore the originals (confirm Dialog, "keep changes made outside Toolbox"), undo one tool, save/load the graphics settings file, saved copies (what was saved before each restore). |
| Servers (`servers`) | `pages/servers.py` | rows are rebuilt in the wanted order (name or lowest ping), so a checkbox never separates from its row; ping colour tokens; every firewall action goes through a review Dialog. |
| Crosshair (`crosshair`) | `pages/crosshair.py` | preview and design cards side by side; "PRO Crosshairs" is a Dialog gallery; colours have a code field; Review and apply shows the exact lines first. |
| Map (`map`) | `pages/map.py` | the same QPainter canvas, recoloured from tokens; the top bar has a Back button to Settings › Advanced ([[Knowledge Graph]]). |

## What changed under them
* `ui.py` no longer has a hero banner, a hint line, a status line or an action bar: every page owns its own (`ActionBar` inside the page). `Window.notify()` is a passing toast.
* `shell/base.py` (fonts, palette, emblem) and `shell/motion.py` (page hand-over, launch reveal) are the only things kept from the old `design.py` / `motion.py`. The old `theme.py` colours live only in `scripts/legacy_tokens.py` for `scripts/make_assets.py`.
* `ui_common.Job` is the shared background job. `scripts/dev/add_arabic.py` merges new Arabic (and English) strings into the catalogues.
* New components used: `SegmentedControl.set_value(None)`, `EmptyState.set_text()`; style rules for scroll bars, `QPlainTextEdit`, spin boxes, status text and card-title tones were added to `shell/style.qss`.

## Rules learned in this chapter
* A test that creates many `Window`s must delete them (`close()` then `deleteLater()` and process the delete events): a later theme switch restyles every widget still alive and took minutes.
* `QTest.mouseClick(widget)` clicks the centre; a checkbox indicator sits at the leading edge, so click `QPoint(8, h // 2)`.
* A `QTableWidget` does not move cell widgets when it sorts; rebuild the rows in the wanted order instead, or paint the cell with a delegate.
* Never hold two copies of a page's state: the Performance page owns the level, the window reads it (`window.level` is the page's slider).

## Not done / not verified
* Mod pictures on **cards** (Settings › Advanced only makes the detail Sheet show pictures without pressing the button).
* Nothing was seen on the user's real display and nothing was run on a real game folder; every check used throwaway folders, scripted servers and offscreen pictures.
* `scripts/dev/mutation_perf.py` and `mutation_stats.py` were re-pointed at the new files but not re-run in this chapter.

Related: [[Handoff - Phase 3 Build (Sonnet 5.5)]] · [[Known Issues]] · [[Testing]]
