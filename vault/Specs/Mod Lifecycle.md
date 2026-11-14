---
title: Mod Lifecycle
type: spec
status: IMPLEMENTED
tags: [spec, lifecycle, installer]
updated: 2026-11-14
code: [deadlock_fps/installer/engine.py, deadlock_fps/installer/updates.py, deadlock_fps/repos/manager.py, deadlock_fps/pages/sources.py, deadlock_fps/pages/installed.py]
tests: [tests/test_installer_engine.py, tests/test_sources_view.py, tests/test_installed_pages.py]
---

# Mod lifecycle

How a mod travels from a repository to the game and back, as implemented.

```
Discover ─▶ Select ─▶ Download ─▶ Verify ─▶ Inspect ─▶ Stage ─▶ [preview, user confirms] ─▶ Backup ─▶ Install ─▶ Verify ─▶ Commit
   │                      └──────────── prepare(): the game folder is never touched ───────────┘        └─ commit(): one journaled transaction ─┘
   └─ any failure after Backup rolls back to the exact state before it; an interrupted run is rolled back at the next start
Later: Update (same pipeline, same slots, old version kept) · Disable / Enable (move out of / into the load path) · Restore previous · Uninstall (to recovery)
```

| Step | Status | Where |
|---|---|---|
| Discover: sync, validate, classify, search | IMPLEMENTED | [[Repository Manager]] |
| Select: pick a version; source, trust, fit, dependencies, conflicts shown | IMPLEMENTED | [[Mod Hub]] |
| Download: HTTPS, byte cap, declared size, mirrors, cancellable | IMPLEMENTED | `Transport.download`, verified live ([[Task - Streaming package download]]) |
| Verify: published SHA-256; no hash ⇒ warning and acknowledgement | IMPLEMENTED | `Installer.prepare` |
| Inspect: archive and VPK structure | IMPLEMENTED | `installer/archive.py`, `installer/vpk.py` |
| Stage: final names, dependency/conflict/overlap analysis | IMPLEMENTED | `Installer._plan` |
| Preview and confirmation (engine-enforced acknowledgement) | IMPLEMENTED | `InstallPreview`, `Installer.commit` |
| Backup, Install, Verify, Commit | IMPLEMENTED | `Installer.commit`, journal in `.deadlock-fps-studio/mods/journal.json` |
| Roll back, crash recovery | IMPLEMENTED | `_run_moves`, `recover()` |
| Update, restore previous, disable/enable, uninstall, history | IMPLEMENTED | [[Installed Mods]] |
| Health check and repair | IMPLEMENTED | [[Compatibility and Downloads]] |

**Principles kept:** never overwrite without a recovery path (moves refuse to overwrite; replaced files go to `backups/`, removed ones to `trash/`); never claim success before the verify step; never run downloaded code (only `.vpk` is installable and nothing is executed); no installation without an explicit user action; no hidden background activity (no timers, no automatic downloads); one writer for `gameinfo.gi` ([[ADR-007 The installer must go through Studio]]).

Related: [[Installation Engine]] · [[Security Model]] · [[Manifest Specification]]
