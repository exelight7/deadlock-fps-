---
title: Task - Provider abstraction and built-in providers
type: task
status: VERIFIED
tags: [task]
updated: 2026-11-14
implements: [Repository Providers, Trust System]
code: [deadlock_fps/repos/providers/base.py, deadlock_fps/repos/providers/github.py, deadlock_fps/repos/providers/gitlab.py, deadlock_fps/repos/providers/native.py, deadlock_fps/repos/trust.py]
tests: [tests/test_repos_providers.py, tests/test_repos_manager.py]
---

# Task - Provider abstraction and built-in providers

Provider contract and registry (a fake Gitea provider registers without touching other modules), GitHub, GitLab and custom HTTPS providers, the bundled trust registry.

**Evidence.** GitHub and GitLab classification checked live (manual, not-found, unsupported); the native-index path is tested with fakes only because no real native repository exists yet.

Implements: [[Repository Providers]] · [[Trust System]].
