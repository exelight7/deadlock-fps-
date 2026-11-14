---
title: Performance Details
type: feature
status: IMPLEMENTED
tags: [feature, performance]
updated: 2026-11-14
code: [deadlock_fps/perf/facts.py, deadlock_fps/perf/knowledge.py, deadlock_fps/perf/explain.py, deadlock_fps/pages/performance.py, deadlock_fps/settings.py, deadlock_fps/ui.py]
tests: [tests/test_perf.py]
---

# Performance Details

> **للمستخدم (بالعربي، ببساطة):** في صفحة «الرسوم والأداء» صار فيه زر **«ماذا يغيّر هذا المستوى؟»**. يفتح نافذة تشرح كل إعداد يكتبه الشريط بكلمات بسيطة، وتقول لك هل اللعبة تطبّقه فعلًا (حسب بيانات Valve نفسها)، وتخليك تستثني أي إعداد تبي تتركه على قيمة Valve. أهم اكتشاف: **من 95 إعدادًا يقدر الشريط يكتبها، 31 ما تأثيرها مضمون** (ممنوعة أو محذوفة أو «cheat»)، و9 ما أقدر أتحقق منها.

A window on the Graphics page, opened by the button **What does this level change?**, built from the reverse engineering in [[Reference App Analysis]] ([[ADR-013 Facts come from Valve's data and the explanations are written here]]). It sits on top of the existing slider ([[Performance Tuning]]) and changes nothing by itself.

## What it shows
For the current level (and view width): every setting the level writes, grouped by category, each with
* the **name**, Valve's own **default** and the value **Toolbox writes**, and where it goes (`gameinfo.gi`, `video.txt` or both);
* **what it controls**, in one plain sentence written for this project, and a mark when turning it down **can change how much of the world you see** (fog, grass, clutter, view width);
* a **status** from Valve's data: *Works*, *Blocked* (Valve's flag says gameinfo.gi cannot change it), *Removed* (Valve's dump no longer has it; the build is shown when known), *Cheat-only* (Valve marks it as a cheat command; whether gameinfo.gi may change it is not documented), *Unverified* (not in Valve's data at all). Hovering a status says what it means.
* a summary line: how many settings would be written, how many are confirmed, how many the game should ignore, how many cannot be confirmed, how many were left out.

## What the user can do
* **Leave any setting out** (untick *Write*): it is then written nowhere, neither in `gameinfo.gi` nor in `video.txt`, and the file keeps its own value. *Leave out the settings the game ignores* ticks off every removed or blocked one; *Write everything* puts them all back. Filters: by category, and "only settings the game may ignore".
* The frame-rate limit and the view width have their own controls, so they **cannot** be left out here.
* The choice is part of `Settings.skip`: it travels with the usual preview, apply, backup and restore ([[Recovery]]), is saved in the Studio state, and is cleared when a preset is loaded (a preset is a whole recipe). Default: nothing is left out, so **nothing changes for anyone who does not open the window**.

## What it found (2026-11-14, the numbers are Valve's data for build 6857)
Of the **95 settings** the slider can write (66 convars, 16 `SceneSystem` keys, 13 `video.txt`-only keys): **55 work, 11 are blocked, 13 are removed, 7 are cheat-only, 9 are unverified**. At the default level 80 it writes 73 settings: **46 confirmed, 23 the game should ignore, 4 uncertain**, and 13 of them can change what you see. Examples: `r_shadows`, the three `r_enable_*_fog` convars and `lb_enable_dynamic_lights` are blocked; `panorama_max_fps`, `mat_vsync` and `r_particle_shadows` are removed; the three `FogCachedShadow…` scene keys left Valve's own `gameinfo.gi` after build 6779; seven scene keys (`HairShading`, `CharacterDecals`, `PerVertexLighting`, …) appear in no stock file of Valve's. Fog and shadows are still covered by active `SceneSystem` keys, so the level is not empty, but a part of it is a no-op.

## How the facts are made
`deadlock_fps/perf/facts.py` is **generated** by `scripts/dev/perf_facts.py` from a catalogue file that carries Valve's public convar dump and the history of Valve's stock `gameinfo.gi` (the reference app ships one; it is GPL, so it is read and never copied). Only names, flags, default values and presence are kept. `--check` prints every difference between the file and a catalogue (use it after a game update). `knowledge.py` holds the explanations, written here. A test requires both to cover exactly the settings the recipe can write, so a new recipe line without an explanation fails the suite.

## Limits
* The statuses are **Valve's data, never the game's behaviour**: nobody ran the game to see whether a "blocked" line really is ignored. A game update can change them.
* The recipe still **writes** the ignored settings unless the user leaves them out: making that the default is a decision for after a real-game check ([[Known Issues]]).
* Not built: importing community configs, a catalogue of presets, share codes, free-form custom values, an FPS estimate (there is none, on purpose: nothing was measured).

Evidence: [[Task - Performance Details]]. Related: [[Performance Tuning]] · [[Recovery]] · [[Reference App Analysis]]
