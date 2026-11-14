---
title: Task - Repository Manager and page
type: task
status: IMPLEMENTED
tags: [task]
updated: 2026-11-14
implements: [Repository Manager, Repository Search]
code: [deadlock_fps/repos/manager.py, deadlock_fps/repos/store.py, deadlock_fps/repos/search.py, deadlock_fps/pages/source_list.py]
tests: [tests/test_repos_manager.py, tests/test_repos_ui.py]
---

# Task - Repository Manager and page

Add, import, export, refresh, enable, remove and search repositories, persisted atomically, with the Repositories page in English and Arabic.

**Evidence.** 45 tests; an RTL-only selection defect was found in a render, fixed and given a regression test.

Implements: [[Repository Manager]] · [[Repository Search]].
