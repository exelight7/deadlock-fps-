---
title: ADR-007 The installer must go through Studio
type: decision
status: IMPLEMENTED
tags: [decision, installer]
updated: 2026-11-14
affects: [Installation Engine, Existing Mod Library, Technical Debt]
code: [deadlock_fps/core.py, deadlock_fps/kv.py]
tests: [tests/test_studio_addons.py]
---

# ADR-007 · The installer registers `citadel/addons` through `core.Studio`, not beside it

**Problem (found in the audit, [[Technical Debt]] #1–2).** `Studio` owns `gameinfo.gi`: it records the digest it applied and refuses to continue if the file differs, and `plan_mods([])` removes the `fps_studio` search path. A separate installer editing the file would be undone or would break drift detection.

**Decision (implemented).**
1. `kv.add_addons_path` inserts `Game "citadel/addons"` above the first `citadel` entry, which is where the community convention and the game's search order need it.
2. `Studio.enable_addons()` applies it through the same backup, state and rollback as every other change. The state remembers `addons: true`; `plan()` and `plan_mods()` re-add the line whenever they rebuild the file, so graphics changes, the four reference mods, and removing them all keep it.
3. If Steam replaced `gameinfo.gi` (update or *Verify integrity*), a mods-only state is repaired by re-applying the recipe; if graphics settings are managed too, the user is told to use the existing repair button, because a blind rewrite could lose their settings.
4. `Studio.restore()` still returns the exact original; that deliberately switches mods off, and the health check then reports *inactive* with a one-click **Repair**.
5. The reference-mod behaviour is unchanged and its existing tests still pass.

Nine tests cover each case, including a file already registered by another mod manager (left alone) and a malformed file (refused, not corrupted).

Affects [[Installation Engine]].
