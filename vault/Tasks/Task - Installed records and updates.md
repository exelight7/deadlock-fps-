---
title: Task - Installed records and updates
type: task
status: IMPLEMENTED
tags: [task]
updated: 2026-11-14
implements: [Installed Mods]
code: [deadlock_fps/installer/records.py, deadlock_fps/installer/updates.py]
tests: [tests/test_installer_engine.py]
---

# Task - Installed records and updates

The installed-mod store, history, previous versions, and update detection against the saved catalogues, per source repository.

**Evidence.** Covered by the engine tests, including a damaged record file that is kept rather than overwritten.

Implements: [[Installed Mods]].
