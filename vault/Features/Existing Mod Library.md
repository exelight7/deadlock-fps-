---
title: Existing Mod Library
type: feature
status: IMPLEMENTED
tags: [feature, existing, mods]
updated: 2026-11-14
code: [deadlock_fps/mods.py, deadlock_fps/mod_install.py, deadlock_fps/pages/classic.py, deadlock_fps/settings.py, deadlock_fps/core.py]
tests: [tests/test_mod_workflow.py, tests/test_installation.py]
origin: pre-existing
---

# Existing mod library (pre-existing, preserved unchanged)

> **2026-11-14 (Phase 3, step 3):** the page of the classic pack (`mod_ui.py`) is now the **Classic pack** row inside Mods › Installed (`pages/classic.py`, `ClassicPack`, same engine, same names for the window: `checks`, `labels`, `status`, `busy`, `applying`, `install()`); see [[Classic Pack and Sources]].

How mods work **today**, before the repository platform:

* A mod is one of four keys of `settings.MODS` — Daylock, Remove Name Tags, Old Healthbars, Sinner Fix — each mapped to a file name (`pak01_dir.vpk`, `pak02_dir.vpk`, `pak03_dir.vpk`, `pak26_dir.vpk`) and a **pinned SHA-256** (`mods.HASHES`). Mods are *not bundled*.
* **Import** (`ModLibrary.import_report`): drop ZIP / VPK / a MODS folder; each candidate is read under limits (64 MB per file, 256 MB total, ≤ 4096 entries, depth 4, no symlinks), hashed, and kept only if it equals a pinned hash; others are ignored. Transactional with rollback. The library lives in the app's data folder.
* **Install** (`mod_install.prepare_mods` → `Studio.plan_mods` → `Studio.apply(mod_only=True)`): VPKs are copied to `<game>/game/citadel/fps_studio/`, and `gameinfo.gi` gets `citadel/fps_studio` as a search path. Originals are backed up under `.deadlock-fps-studio/`; the plan is re-checked at commit time and applied transactionally.
* **Inspect:** [[Mod Inspector]].
* Known conflict encoded in code: Remove Name Tags ⇄ Old Healthbars.

## Why it matters for the new platform
It is a working, careful installer for a *closed set*; the platform needs an *open set*. What carries over: the folder, the search-path mechanism, backup/rollback in `Studio`, size and symlink discipline, VPK validation. What does not: recognition by pinned hash. See [[Installation Engine]], [[ADR-007 The installer must go through Studio]], [[Technical Debt]] #1–3.

Related: [[Architecture Overview]] · [[Recovery]]
