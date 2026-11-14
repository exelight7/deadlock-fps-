---
title: Handoff - Phase 3 Build (Sonnet 5.5)
type: guide
tags: [handoff, redesign, build]
updated: 2026-11-14
---

# Handoff · Phase 3 · Build (Sonnet 5.5)

> **للمستخدم:** بعد **`✅ المرحلة 2 انتهت (Opus 5.5)`** افتح دردشة جديدة مع **Sonnet 5.5** والصق البرومت. هذي المرحلة طويلة: ممكن تحتاج أكثر من دردشة، وكل دردشة تحدّث «التقدّم» في آخر هذي الملاحظة. لما يخلص كل شي يختم بـ **`✅ المرحلة 3 انتهت (Sonnet 5.5)`**.

Plan: [[Redesign Plan]]. Needs the Results of [[Handoff - Phase 1 Design (Fable 5.2)]] and [[Handoff - Phase 2 Infrastructure (Opus 5.5)]].

## The prompt to paste

```text
أنت Sonnet 5.5 في المرحلة 3 (البناء) من إعادة تصميم واجهة Deadlock Toolbox.

اقرأ: CLAUDE.md، vault/AI Memory/00 Start Here.md، vault/Roadmap/Redesign Plan.md، vault/Design/New Design/ كاملة، والقسم Result في ملاحظتي Handoff للمرحلتين 1 و2، ثم "التقدّم" في vault/AI Memory/Handoff - Phase 3 Build (Sonnet 5.5).md لتعرف أين وصل من قبلك.
إذا المرحلتان 1 و2 ما انتهتا (لا يوجد Result فيهما)، لا تبدأ وقل للمستخدم.
رد عليّ بالعربي، قصير وبسيط، سطر لكل فكرة. ممنوع commit/push إلا إذا طلبت. ما تلمس vaults أوبسيديان الثانية.

مهمتك: كل الباقي، بالترتيب الذي في 06 Handoff to Build:
1. أعد بناء كل صفحة على المكوّنات الجديدة وبمواصفات التصميم (واحدة واحدة، كل صفحة: كود + ترجمة عربي/إنجليزي + اختبارات + لقطات شاشة تفحصها بعينك بالعربي والإنجليزي والفاتح والداكن).
2. احذف الكود والستايل القديم اللي صار ما يُستخدم (design.py/theme القديم) بعد ما تنتقل كل الصفحات.
3. الميزات الباقية بعد الواجهة (من vault/Roadmap/Redesign Plan.md "What is left from the reference app"): ابدأ بالأسهل نفعًا، واسأل المستخدم قبل أي تنزيل حقيقي أو إرسال رقم حساب Steam أو تشغيل على مجلد اللعبة الحقيقي.
4. حدّث الـvault مع كل خطوة (Implementation Log، ملاحظات الميزات، Known Issues، Testing) وحدّث "التقدّم" في هذي الملاحظة: ما انتهى، ما هو جارٍ، ما هو التالي.
5. قبل ما تقول إن شي انتهى: الاختبارات (QT_QPA_PLATFORM=offscreen .venv/Scripts/python.exe -m unittest discover -s tests)، scripts/i18n_tool.py check، scripts/check_vault.py، وفحص LF. اذكر بصدق ما لم يُفحص.

قواعد: كلمات بسيطة في الواجهة (لا repository)، ملفات LF، لا تنسخ من التطبيق المرجعي (GPL)، المحرّكات Qt-free ما تتغير إلا لسبب مكتوب.

لما تخلص كل شي فعلًا: اختم رسالتك الأخيرة بهذا السطر بالضبط:
✅ المرحلة 3 انتهت (Sonnet 5.5)
إذا خلصت جزءًا فقط (قبل ما يمتلئ السياق)، اكتب في التقدّم أين وقفت واختم بـ:
⏸ المرحلة 3 مستمرة: افتح دردشة جديدة مع Sonnet 5.5 والصق نفس البرومت
```

## Progress
*(Each Sonnet chat updates this: done, in progress, next.)*

### Chat 1 (2026-11-14)
**Done:** step 1 of 06 Handoff to Build, **Home** ([[Home Page]]): new page, game link moved to `game_link.py`, game pill, attention list, Arabic strings, 17 tests, pictures checked (English dark, Arabic light, 940 × 680, 130 %).

**Rules the next chat must keep (learned here):**
* Write the page in `deadlock_fps/pages/<name>.py` (English-first strings through `tr()`, Arabic in `lang_ar.py` via a JSON file and a small script; `i18n_tool.py check` reads `pages/`). Tables of words must call `tr('literal')` inside a function, otherwise the check cannot see them and Arabic stays English.
* In `ui.py` add the slot name to `REBUILT_SLOTS` (hides the old hint and status line), build it in `build_slots()`, point the registry at it.
* Look at it with `scripts/dev/shot_page.py OUT.png ADDRESS --lang ar --look light --size 940x680 --scale 130 --state linked` before saying it is done. Screens are the proof; the first Home pictures showed four defects the tests did not.
* Rename registry titles to the design words when you rebuild a page (Recovery → Backups, Browse / Installed / Check / Activity). The sidebar still says "Recovery".

**Not done / known gaps:** `ListRow` separators are invisible; card icons do not follow a theme switch; the sidebar footer (version, GitHub button) is still old style; the old scroll bar style still comes from `design.STYLE` (the new stylesheet has no scroll bar rules yet: add them before deleting `design.py`); the `sqlite3 unable to open database file` lines printed at the end of some test runs come from store timers firing after their temporary folder is gone (not checked whether they were there before this work).

**Next (after chat 1):** step 2, Mods › Browse. See chat 2 below. Then Installed, Check, Activity; Performance; Stats; Settings; Servers, Crosshair, Backups; map; delete the old system. Light-theme switch in Settings only after the last page is rebuilt.

### Chat 2 (2026-11-14)
**Done:** step 2, **Mods › Browse** ([[Browse Page]]): `deadlock_fps/pages/browse.py` (`BrowsePage`, `InstallReview`), card grid, the Sheet, the review Dialog, every state; `store_ui.py` and its test file are deleted; 58 Arabic strings; `tests/test_store_browse.py` (51, named so the mutation script still finds it); `scripts/dev/shot_browse.py` (sample data, no network, every state). Components upgraded on the way: `ElidedLabel`, `ModCard` (icon, badge, picture hook), `Sheet.reposition`, `Dialog` height, `KeyValue` (widgets, alignment, `clear`), `EmptyState` text height, `breakable()`; the tab style no longer leaks the old checked-button look. Registry: tab "Browse", page "Backups" (the sidebar no longer says "Recovery").

**Rules learned (add to chat 1's):**
* A sentence that **starts** with `ltr()` (a direction mark) is laid out left to right even in Arabic: never start a translated sentence with a wrapped number.
* A wrapped label cannot be narrower than its longest word, and a dialog or empty state is only as tall as the one-line hints unless told otherwise: look at the picture, and use `breakable()` for addresses and `Dialog`'s height rule.
* A test that checks widths must start the real look (`ui.start_look`, fonts loaded); `theme.apply` alone leaves the old base style out and passes when the app would not.

**Not done / known gaps:** card pictures (wait for the Settings switch), the "GameBanana · My sources" switch (step 3 folds the Hub tab in), the tab bar is still the seven temporary tabs and clips at 130 % in the smallest window, scroll bars and sidebar footer still old style, `ListRow` separators,  not seen on the user's display, never run on a real game folder.

**Next:** step 3, **Mods › Installed**, then Check, then Activity; fold in the classic pack, the inspector and "My sources"; remove the temporary tabs (this also fixes the clipped tab bar). Rebuild order after that is unchanged.

### Chat 3 (2026-11-14)
**Done:** step 3 in part: **Mods › Installed, Check and Activity** rebuilt ([[Installed Page]]): `pages/installed.py`, `pages/check.py`, `pages/activity.py`; `installed_ui.py` is deleted; the registry tabs are "Browse, Installed, Check, Activity" and the three temporary tabs (Source Mods, Library, Inspection) now come after them. 71 Arabic strings; `tests/test_installed_pages.py` (30); `tests/look_fixture.py`. Components: `ListRow(lead=)`, **visible `ListRow` separators** (fixed), `List(variant='flat')`, `List.clear()` removes at once, `DataTable.fit_height()` and leading-aligned headers, `confirm()`, `plural()`.

**Rules learned (add to the earlier ones):**
* A test that switches the real look (`ui.start_look`, a text size) must put the application stylesheet and the theme state back (`tests/look_fixture.keep_look`): tests that run later (alphabetically) fail otherwise, and only in the full run.
* `QSS` `border-bottom` alone draws nothing on a `QFrame`: write `border: none; border-bottom: …`.
* `deleteLater()` does not take a widget out of a layout: remove and hide it first, or a rebuild shows old and new together (and a picture taken right after `reload()` needs `processEvents()`).

**Not done (then):** folding the temporary tabs in: done in chat 4 below.

### Chat 4 (2026-11-14)
**Done:** step 3 finished ([[Classic Pack and Sources]]): the three temporary tabs are gone. **Source Mods** → Browse's *GameBanana · My sources* (`pages/sources.py`, `pages/browse_host.py`); **Library / classic pack** → the *Classic pack* row on Installed (`pages/classic.py`, `ClassicPack`, same names for the window); **Inspection** → the *Classic pack* section of Check (scan, findings, *Save the report*). Deleted: `mod_ui.py`, `inspector_ui.py`, the Hub page (`hub_ui.py` keeps only `failure_text`), `tests/test_mod_pages.py` (ported to `tests/test_sources_view.py`). The registry has four Mods tabs (Browse, Installed, Check, Activity); `--inspector` now opens `mods.health`, `--mods` opens `mods.installed`. 73 Arabic strings.

**Rules learned:** a row of buttons that fits at 100 % will not fit at 130 % in the smallest window: stack buttons (small ones, then the primary on a row of its own) and measure with the real window, a game *not* linked (the "Link the game" button adds width) and `Fusion`; an icon name that is not in `assets/icons2/` raises at build time and can leave a stage stuck (check names with `ls assets/icons2`).

**Not done:** card pictures (Settings switch), Skeleton loading on Installed, Arabic for the engines' own sentences. Everything below in the old list stays.

**Next:** step 4, **Performance** (Level, then Every setting: the window becomes a tab; read `legacy/performance.py`, `perf_ui.py`, `vault/Features/Performance Tuning.md`, `Performance Details.md`). Then Stats, Settings (including the light-theme switch and "Show mod pictures"), Servers, Crosshair, Backups, the map, and delete the old system.

### Chat 5 (2026-11-14): the rest, in one go
**Done:** Performance (Level, Every setting), Stats (Heroes, Ranks, My stats), Settings (seven sections; the light theme and text size switch is on; "Show mod pictures" and "Less motion" are remembered), Backups, Servers, Crosshair and the Map, all on the new components ([[Rebuilt Pages - Performance to Map]]). Deleted: `design.py`, `theme.py`, `motion.py`, `legacy/`, `perf_ui.py`, `stats_ui.py`, `server_ui.py`, `server_delegate.py`, `crosshair_ui.py`, `crosshair_style.py`, `update_ui.py`, `repo_ui.py`, `graph_ui.py`. Kept: `shell/base.py` (fonts, palette, emblem) and `shell/motion.py` (page hand-over, launch reveal).

**Rules learned:** see "Rules learned in this chapter" in [[Rebuilt Pages - Performance to Map]].

**Not done:** card pictures (Settings only makes the detail Sheet show them without a click); never seen on the user's real display; never run on a real game folder; the two mutation scripts were re-pointed but not re-run; `assets/icons`, `patterns`, `art`, `illustrations` (old artwork) are still in the repository because `scripts/make_assets.py` and `scripts/smoke_desktop.py` name them.

Previous: [[Handoff - Phase 2 Infrastructure (Opus 5.5)]]
