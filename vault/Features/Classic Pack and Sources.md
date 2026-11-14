---
title: Classic Pack and Sources
type: feature
status: IMPLEMENTED
tags: [feature, redesign, mods, classic, sources, inspector]
updated: 2026-11-14
code: [deadlock_fps/pages/classic.py, deadlock_fps/pages/sources.py, deadlock_fps/pages/browse_host.py, deadlock_fps/pages/check.py, deadlock_fps/pages/installed.py, deadlock_fps/ui.py]
tests: [tests/test_sources_view.py, tests/test_mod_workflow.py, tests/test_mod_inspector.py, tests/test_installed_pages.py]
---

# Classic pack, My sources and the check, folded in (Phase 3, step 3, part 2)

> **للمستخدم (بالعربي، ببساطة):** التبويبات المؤقتة الثلاثة اختفت. **مودات المصادر** صارت زر «مصادري» جنب «GameBanana» في صفحة التصفّح (يظهر بس إذا أضفت مصدر). **المكتبة والتركيب** (الحزمة الكلاسيكية: أربع مودات) صارت صف مطوي داخل «المركّبة». **الفحص** (المفتش) صار قسم «الحزمة الكلاسيكية» داخل صفحة «فحص». الآن تحت «المودات» أربع تبويبات بس: تصفّح، مركّبة، فحص، نشاط.

Pages: [[Browse Page]] (GameBanana), [[Installed Page]] (Installed, Check, Activity). Engines: [[Mod Hub]] (repository search), [[Existing Mod Library]] (the four classic mods), [[Mod Inspector]].

## My sources (`pages/sources.py`, `SourcesView(service)`; `pages/browse_host.py`, `BrowseHost`)
* `BrowseHost` holds Browse's two views and a SegmentedControl **GameBanana · My sources**; the switch is hidden until `manager.list()` has a source, and removing the last source sends you back to GameBanana. An open sheet is closed when you switch.
* `SourcesView` is the old Hub as cards: SearchField, three Selects (type, source, order: best match, name, recently updated, source, largest download), the chip *Installable only*, "N mods from M sources", the grid built 48 at a time (at most 500). A card opens the **sheet**: name, author and licence, badges for the source and its trust label (a warning Banner with the trust note unless it is official), the **Version Select and Install button first** (Install, Update to X, Reinstall X), the file facts (published, size, SHA-256 published or not, *Your game* fit badge, needs, conflicts), summary, description, changelog, *Open source page*, *Show pictures* (only when asked) and *Remove* (danger-quiet, asks first). Installing is the same journaled path as before (`ModService.prepare/commit`) with the same review Dialog (`InstallReview`), so the acknowledgement is still enforced by the engine too.
* No game linked: Install is off and a Banner offers *Link the game*. No sources: an EmptyState with *Add a source* (to Settings › Sources). The map's "open in app" for a mod calls `Window.search_sources(label)`.
* Dropped from the old page: the trust *filter* (the label is on every sheet) and the checkbox that loaded screenshots by default (pictures are now opt-in).

## Classic pack (`pages/classic.py`, `ClassicPack(window)`)
* Sits inside the folded **Classic pack (4)** row of Installed (`InstalledPage(service, classic)`; `show_classic()` opens it; Backups and the start-up flag `--mods` use it). Drop area (a dashed Card that accepts local files only, highlighting while dragging) with *Add the files* and the menu *Choose a folder* / *Find the files automatically*; four rows, each a Switch "I want it in the game" and a state Badge (Add the files, Ready, Installed, Already there); a status line, a progress bar, *Link the game* (when the game is not linked), *Details of the check* (opens Check), *Cancel*, and the primary *Check and install the choice* on its own row. Review: `ClassicReview` (a review Dialog), then the old commit. Names and numbers the rest of the window relies on did not change: `checks`, `labels`, `cards`, `status`, `busy`, `applying`, `stage`, `sequence`, `install()`, `import_paths()`, `refresh()`, `selected()`, `summary()`; the Performance page still builds its settings from `mod_checks`, Backups still calls `install_mods()`.
* The names-and-health-bar conflict rule is the same (choosing one unchecks the other).

## Check › Classic pack (`pages/check.py`)
* `CheckPage(service, scan_inputs)`: when Check is shown (and again after the choice or the game files change: `Window.check_stale()`), `inspect_mods` runs in the background and the section lists its findings first (danger for errors that stop the install, warning otherwise), then the four mods ("In the library: … · In the game: …", a *Chosen* badge). The section shows only when a classic mod is in the library, in the game, or chosen. *Save the report* writes the JSON the old page exported. Nothing is written to the game.

## Checked
* `tests/test_sources_view.py` (15): the old Hub tests ported (list, details, search and filters, install through the review, cancel, engine-enforced acknowledgement, game closed and not linked, bad download, review gate), removal with a confirm, an update offered, plain text, no sources, and the host (switch only with sources, closing a sheet on switch, signals, removing the last source). `tests/test_mod_workflow.py` (19) and `tests/test_mod_inspector.py` (8) were moved to the new widgets and gained: row states and button text, the pack being busy-proof, and Check's classic section with a real scan and a saved report. `tests/test_installed_pages.py` (30) measures Installed (with the classic pack open and no game linked), Check, Activity and My sources at 940 px and 130 % text: **no sideways scrolling**.
* Looked at by eye (`scripts/dev/shot_mod_pages.py`, sample data): English dark and Arabic light, 1200 × 820 and 940 × 680 at 130 %. Defects the tests had not caught and that were fixed that way: the classic pack's buttons side by side widened Installed past the window at 130 % (they now stack), the drop area's text squeezed by its buttons, and a missing icon name that broke the review (`icon='file'` does not exist in `assets/icons2/`).

## Not done or not verified
* Not seen on the user's display; never run on a real game folder with real classic files; no screen-reader pass. The drop itself (dragging a file onto the row) is tested only through the file filter, not with a real drag.
* The old page's JSON report and the engines' own sentences (the inspector's findings, Check's overlap lines) stay as the engines write them: English findings are not re-worded in Arabic.
* Card pictures for GameBanana and for My sources wait for the Settings switch (not built).

Related: [[Handoff - Phase 3 Build (Sonnet 5.5)]] · [[Shell and Page Registry]]
