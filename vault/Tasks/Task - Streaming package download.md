---
title: Task - Streaming package download
type: task
status: VERIFIED
tags: [task]
updated: 2026-11-14
implements: [Installation Engine]
code: [deadlock_fps/repos/transport.py]
tests: [tests/test_installer_inspect.py]
---

# Task - Streaming package download

`Transport.download`: constant-memory streaming with progress, cancellation, declared-size and byte caps, partial files removed, and never deleting a destination it did not create.

**Evidence.** Run against real GitHub (2026-11-14): a 194-byte release asset through a redirect to another host, size cap, size mismatch and 404 all behaved, leaving no file. A bug found by tests (it deleted a pre-existing destination) is fixed.

Implements: [[Installation Engine]].
