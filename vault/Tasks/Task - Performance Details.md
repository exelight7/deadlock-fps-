---
title: Task - Performance Details
type: task
status: IMPLEMENTED
tags: [task, performance]
updated: 2026-11-14
implements: [Performance Details, Performance Tuning]
code: [deadlock_fps/perf/facts.py, deadlock_fps/perf/knowledge.py, deadlock_fps/perf/explain.py, deadlock_fps/pages/performance.py, deadlock_fps/settings.py, deadlock_fps/ui.py, scripts/dev/perf_facts.py, scripts/i18n_tool.py]
tests: [tests/test_perf.py]
---

# Task - Performance Details

> **للمستخدم:** هذه المهمة بنت نافذة «ماذا يغيّر هذا المستوى؟»: جدول شرح لكل إعداد، حالته حسب Valve، وخيار استثناء أي إعداد. كل شي مجرّب بالاختبارات ومرئي بلقطات بالعربي والإنجليزي، لكن **لم يُجرَّب داخل اللعبة**.

Implements [[Performance Details]].

## Steps
1. **Analysis (read-only):** every setting the slider can write (all 201 levels, both aspect modes, cpu on and off) was compared with the reference catalogue's convar list and Valve's stock `gameinfo.gi` history (build 5044 to 6801, 42 builds). Finding: 31 of 95 are not active, 9 unverifiable ([[Performance Details]]).
2. **Facts file generated** by `scripts/dev/perf_facts.py` (`--check` mode included); **explanations written** in `perf/knowledge.py` (95 entries, 11 categories, a "may change what you see" mark).
3. **Skip mechanism:** `Settings.skip` (default empty), validated (names only, at most 200, the three protected controls refused), normalised after JSON, applied in `values()` to `gameinfo.gi` convars, `SceneSystem` keys and the `video.txt` twin. `Studio` needed no change: the plan starts from the baseline, so a setting left out returns to the file's own value, and the recorded footprint (`owned`) is computed from the same `values()`.
4. **Window** `perf_ui.PerfDialog` and the button on the Graphics page (`ui.py`: `skip`, `show_perf_details`, `refresh_perf_button`, the two `Settings` hooks).
5. **Translations:** 136 Arabic and 2 English entries; `scripts/i18n_tool.py` now also reads `perf/` and `store/` (before, strings in subpackages were not checked at all).

## Evidence (IMPLEMENTED, not VERIFIED)
* **37 tests** in `tests/test_perf.py`: coverage of every setting both ways, hand-checked facts, report arithmetic, the skip mechanism, a **real `Studio`** (preview, apply, change the choice, restore to the exact original bytes, the footprint), the window (rows, ticking, filters, protected rows, plain text), and the main window (settings carry the choice, cancel keeps the old one, presets reset it).
* **19 checks disabled one at a time** (`scripts/dev/mutation_perf.py`): **19 of 19 caught**; one (the window returning protected names) first survived because another check hid it, and got its own isolating test.
* Existing graphics tests (`test_core`, `test_101` to `test_104`, `test_ui`) unchanged and green; the whole suite is 574 tests with only the known Windows symlink error and one skip.
* The window and the page were rendered offscreen in English and Arabic (`scripts/dev/shot_perf.py`). Findings from looking: the arrow glyph in a "from → to" column showed as a box, so it became two columns.
* A trap found on the way: `assets/reference/gameinfo.gi` and `video.txt` are themselves outputs of this recipe, so applying level 80 to them changes nothing; the Studio tests use level 0 ([[Known Issues]]).

## Not verified
* **Nothing ran in the real game.** Whether a blocked or removed line is really ignored, and whether the "cheat" ones apply, is inferred from Valve's flags.
* The facts come from one catalogue copy dated 2026-11-13 (convar build 6857). A newer game build may differ.

Implements: [[Performance Details]]. Decision: [[ADR-013 Facts come from Valve's data and the explanations are written here]].
