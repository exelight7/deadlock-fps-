---
title: Task - Studio addons search path
type: task
status: IMPLEMENTED
tags: [task]
updated: 2026-11-14
implements: [Installation Engine, Existing Mod Library]
code: [deadlock_fps/core.py, deadlock_fps/kv.py]
tests: [tests/test_studio_addons.py]
---

# Task - Studio addons search path

Register `citadel/addons` through `Studio` so graphics, the reference mods and Steam resets keep working ([[ADR-007 The installer must go through Studio]]).

**Evidence.** 9 tests; existing Studio tests unchanged and passing.

Implements: [[Installation Engine]] · [[Existing Mod Library]].
