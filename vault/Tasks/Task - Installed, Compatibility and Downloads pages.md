---
title: Task - Installed, Compatibility and Downloads pages
type: task
status: IMPLEMENTED
tags: [task]
updated: 2026-11-14
implements: [Installed Mods, Compatibility and Downloads]
code: [deadlock_fps/pages/installed.py, deadlock_fps/pages/check.py, deadlock_fps/pages/activity.py]
tests: [tests/test_installed_pages.py]
---

# Task - Installed, Compatibility and Downloads pages

Installed table with update, update-all, restore, enable/disable, remove, files and history; the health check; the activity history.

**Evidence.** A planted modified file and a simulated Steam reset appear in the health check and the repair clears the right one.

Implements: [[Installed Mods]] · [[Compatibility and Downloads]].
