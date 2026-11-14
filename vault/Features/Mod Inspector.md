---
title: Mod Inspector
type: feature
status: IMPLEMENTED
tags: [feature, existing, security]
updated: 2026-11-14
code: [deadlock_fps/mod_inspector.py, deadlock_fps/pages/check.py]
tests: [tests/test_mod_inspector.py]
origin: pre-existing
---

# Mod Inspector (pre-existing)

> **2026-11-14 (Phase 3, step 3):** the Inspector page is now the **Classic pack** section of Mods › Check (`pages/check.py`: it scans when Check is shown, again when the choice or the files change, rows and findings, *Save the report*); see [[Classic Pack and Sources]]. The engine (`mod_inspector.py`) is unchanged.

Read-only diagnostics, run on a worker thread and cancellable, with JSON export. For the four reference mods it classifies library and installed copies as missing / intact / modified (VPK size, structure via `core.vpk_entries`, SHA-256), reports the known Name Tags ⇄ Healthbars conflict as an error, and **file overlaps** between selected or installed mods as warnings (overlap ≠ incompatibility). It does not claim compatibility with game updates.

Reachable from the Mods page switcher, not the rail. Its overlap logic is the model for conflict detection on repository mods ([[Installation Engine]]).

Related: [[Existing Mod Library]] · [[Security Model]]
