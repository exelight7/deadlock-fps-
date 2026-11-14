---
title: Task - Pinned HTTPS transport
type: task
status: VERIFIED
tags: [task]
updated: 2026-11-14
implements: [Repository Providers]
code: [deadlock_fps/repos/transport.py, deadlock_fps/repos/urls.py]
tests: [tests/test_repos_providers.py, tests/test_repos_core.py]
---

# Task - Pinned HTTPS transport

Standard-library HTTPS with the resolved address checked and connected to directly, validated redirects, streamed size caps and no compression ([[ADR-005 Standard-library HTTP with a pinned connection]]).

**Evidence.** Verified live against github.com and gitlab.com (2026-11-14): TLS, redirects, 404 handling, refusal of `http://` and `127.0.0.1`.

Implements: [[Repository Providers]].
