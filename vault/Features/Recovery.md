---
title: Recovery
type: feature
status: IMPLEMENTED
tags: [feature, existing, backup]
updated: 2026-11-14
code: [deadlock_fps/core.py, deadlock_fps/ui.py]
tests: [tests/test_core.py, tests/test_workspace.py]
origin: pre-existing
---

# Recovery / backup & restore (pre-existing)

`Studio.restore` returns every managed file to its stored original, after saving the current state to `.deadlock-fps-studio/history/<timestamp>/`; it refuses to overwrite out-of-band changes unless asked to preserve them. The page also offers shortcuts to undo crosshair, mods and server blocks, and JSON export/import of graphics settings.

This is the existing **Backup & Restore** destination; it covers files `Studio` manages (graphics, `gameinfo.gi`, the four reference mods). Repository-installed mods will need the same guarantees ([[Installation Engine]], [[Mod Lifecycle]]).

Related: [[Existing Mod Library]] · [[Performance Tuning]]
