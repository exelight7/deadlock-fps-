---
title: Performance Tuning
type: feature
status: IMPLEMENTED
tags: [feature, existing]
updated: 2026-11-14
code: [deadlock_fps/settings.py, deadlock_fps/core.py, deadlock_fps/kv.py, deadlock_fps/ui.py]
tests: [tests/test_core.py, tests/test_ui.py]
origin: pre-existing
---

# Performance tuning (pre-existing)

One slider (0–200) maps to a set of `video.txt` and `gameinfo.gi` values (`settings.values`); resolution, upscaler and refresh settings are protected (`core.RESOLUTION_KEYS`). Changes are previewed, originals stored, and restorable through [[Recovery]]. A guard timer re-applies saved settings after the game closes (never while it runs).

The graphics code and the mod code share `gameinfo.gi` and the `Studio` state file, which is why mod installation cannot be built separately ([[ADR-007 The installer must go through Studio]]).

Since 2026-11-14 the page also has **What does this level change?** ([[Performance Details]]): every setting the slider writes, explained, with Valve's status for it, and a way to leave any of them out (`Settings.skip`). It found that about a third of what the slider can write is not confirmed to do anything.
