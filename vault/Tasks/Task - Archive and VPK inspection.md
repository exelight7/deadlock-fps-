---
title: Task - Archive and VPK inspection
type: task
status: IMPLEMENTED
tags: [task]
updated: 2026-11-14
implements: [Installation Engine]
code: [deadlock_fps/installer/archive.py, deadlock_fps/installer/vpk.py]
tests: [tests/test_installer_inspect.py]
---

# Task - Archive and VPK inspection

Hardened ZIP inspection and extraction and a streaming VPK validator that reads only the header and tree.

**Evidence.** 18 tests with hostile archives; a literal-segment check replaced a `pathlib` one that hid `//` and `./`.

Implements: [[Installation Engine]].
