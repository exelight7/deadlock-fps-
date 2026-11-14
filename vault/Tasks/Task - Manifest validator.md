---
title: Task - Manifest validator
type: task
status: IMPLEMENTED
tags: [task]
updated: 2026-11-14
implements: [Manifest Specification]
code: [deadlock_fps/repos/spec.py, deadlock_fps/repos/model.py, deadlock_fps/repos/versions.py]
tests: [tests/test_repos_core.py, tests/test_repos_docs.py]
---

# Task - Manifest validator

Executable form of the repository specification: limits, forward compatibility, fault tolerance, safe install paths, plain-text fields.

**Evidence.** 24 tests plus 4 that tie the published document and its examples to the code; 4 of 5 deliberately weakened checks were caught, the fifth is redundant defence in depth.

Implements: [[Manifest Specification]].
