---
title: Installed Page
type: feature
status: IMPLEMENTED
tags: [feature, redesign, mods, installed, check, activity]
updated: 2026-11-14
code: [deadlock_fps/pages/installed.py, deadlock_fps/pages/check.py, deadlock_fps/pages/activity.py, deadlock_fps/shell/components.py, deadlock_fps/ui.py, scripts/dev/shot_mod_pages.py]
tests: [tests/test_installed_pages.py, tests/test_store_browse.py, tests/test_shell.py]
---

# Mods › Installed, Check and Activity (rebuilt in Phase 3, step 3)

> **تحديث:** التبويبات المؤقتة (المصادر، المكتبة، الفحص القديم) انطوت داخل هذي الصفحات: [[Classic Pack and Sources]].
>
> **للمستخدم (بالعربي، ببساطة):** ثلاث صفحات انبنت من جديد على الشكل الجديد: **المركّبة** (كل مود صف فيه مفتاح تشغيل وحالة وزر «تحديث» وقائمة «المزيد»)، **الفحص** (المشاكل أول شي، كل مشكلة بعنوان بسيط وزر واحد، وتحتها جدول «هل تناسب نسخة لعبتك؟»)، و**النشاط** (سجل اللي سواه Toolbox بالترتيب من الأحدث). المحرّكات ما تغيّرت. **اللي ما انتهى:** تبويبات «Source Mods» و«Library» و«Inspection» لسا مؤقتة، ولسا ما انطوت داخل هذي الصفحات.

Engines: [[Installation Engine]], [[Installed Mods]] (what an installed mod is), [[Compatibility and Downloads]] (what the health check and the history report). Spec: [[05 Screens]]. Progress: [[Handoff - Phase 3 Build (Sonnet 5.5)]].

## Installed (`pages/installed.py`, `InstalledPage(service, classic=None)`)
* **Top:** "2 mods · 1 update · 1 off · game build 6857", *Check for updates* (busy while the sources are asked) and the primary *Update all (N)*.
* **A row per mod** (a flat List): a Switch (really moves the mod's files out of, or back into, `game/citadel/addons`), the name, a muted line "version (or 1.0 to 1.2) · author · source", a status Badge (Update, Up to date, Source unreachable, Off, Newer than the source; a Mod Store mod just says *Installed*, with the engine's note as the tooltip, because it has no source to be unreachable), *Update* when there is one, and a "more" menu: Update to X, Go back to X (only when an earlier version is kept), Show files, History, Open its page, then *Remove* in the danger look. Remove and Go back ask first (a confirm Dialog); an update shows the review Dialog (`InstallReview`, the one Browse uses); *Update all* prepares everything and shows one `BatchReview`.
* **Under the list, two folded rows:** *Classic pack (4)* with an "N on" badge; opened, it holds the whole classic pack (drop area, four switches, review and install: [[Classic Pack and Sources]]), and *Not installed by Toolbox (N)* with the file names and *Open addons folder*. A fold is hidden when it has nothing.
* **States:** empty ("No mods yet", *Browse mods*); no game (warning Banner, *Link the game*, controls off); error (danger Banner "The list of installed mods couldn't be read", *Open the folder*, goes away when the list can be read again); a failed action is a danger Banner that says nothing was changed and the switch goes back to what is true; a success is a Toast and `page.message`.
* The Trust column is gone (the design shows only author and source). *Repair* moved: it is on Check (and Home's attention list); *Open addons folder* is in the second fold.

## Check (`pages/check.py`, `CheckPage(service)`)
* "Checked just now · game build 6857" and *Check again*. Findings come problems first, each a ListRow with a plain title, one sentence and at most one action: *Your mods are switched off in the game* (*Repair*), *X was changed after it was installed*, *X has a missing file*, *X has a damaged file*, *Two mods change the same files*, *X needs another mod*, *A file could not be read*. A last green row sums up the mods that are fine. Files in `addons` that Toolbox did not install are not findings (they have their fold on Installed).
* *Do they fit your game version?*: a DataTable (mod, made for, fit Badge: Fits, Not tested on this version, Other game version, Unknown).
* **States:** all clear (EmptyState with a tick), could not finish (danger EmptyState, *Try again*), no game (warning Banner). The check is read-only; the only write is *Repair*.

## Activity (`pages/activity.py`, `ActivityPage(service)`)
* "Nothing is downloading right now." or a Card with "Downloading · 11.2 MB of 24.8 MB", a ProgressBar and *Cancel*; below, *History* newest first: "Installed Night Skyline 2.0.1", then the time and the note. A failed item has the danger look with the reason. Empty: "Nothing has happened yet". No game: warning Banner.

## Components upgraded on the way
`ListRow(lead=…)` (a Switch before the text), the separators of `ListRow` (they were invisible: the rule needed `border: none` first) with no line under the last row, `List(variant='flat')` inside a flat Card, `List.clear()` removes rows at once (a rebuild no longer shows old and new rows together), `DataTable` headers align to the leading side and `fit_height()`, `confirm()` (a confirm Dialog as a call), `plural()` ("1 mod", "5 mods"). The tab style from Browse stays.

## Checked
* `tests/test_installed_pages.py` (30): a row's content and badge, update through the review, going back (the old copy is really kept), declining, the switch really moving files, removal asked and recoverable, the menu and its order, update all with one review, the batch review's gate, the Files and History dialogs (changed files reported), the update check (busy, then a sentence), a failed action, no game, empty, an unreadable list, the folded rows, the status words; Check: all clear, real problems first with plain titles and the repair working, overlaps, the fit table, a check that cannot finish, no game, the fit words; Activity: newest first, empty, a running download, a failed item, no game; and **no sideways scrolling in the three pages at 940 px and 130 % text** (real start-up look, fonts loaded). The Mod Hub tests stay in `tests/test_mod_pages.py` (8); the store test that reads Installed moved to the new page's API.
* Looked at by eye with `scripts/dev/shot_mod_pages.py` (sample mods installed through the real engine in a throwaway game folder): English dark and Arabic light, 1200 × 820 and 940 × 680 at 130 %. Defects the tests had not caught and that were fixed that way: rows shown twice for a moment after a rebuild, invisible list separators, a scroll bar inside the fit table, a gap under the findings (a screenshot artifact of a layout not yet updated, fixed in the script), a double border in Activity.

## Not done or not verified
* The three temporary tabs are folded in now ([[Classic Pack and Sources]]); the tab bar has four tabs and no longer clips at 130 % text.
* Loading state of Installed is a busy *Check for updates* button only (no Skeleton rows); the engines answer from disk, so there is little to wait for.
* Findings use the engine's own English sentence where it has the detail (overlaps, missing files): those lines stay English in the Arabic interface.
* A check that finds a problem in a mod Toolbox did not install is shown by file name, not by mod.
* Not seen on the user's display; never run on a real game folder; no screen-reader pass.

Related: [[Browse Page]] · [[Home Page]] · [[Shell and Page Registry]] · [[Task - Installed, Compatibility and Downloads pages]]
