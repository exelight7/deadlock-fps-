---
title: Task - Mod Store engine
type: task
status: VERIFIED
tags: [task, store]
updated: 2026-11-14
implements: [Mod Store]
code: [deadlock_fps/store/__init__.py, deadlock_fps/store/model.py, deadlock_fps/store/gamebanana.py, deadlock_fps/store/catalog.py, deadlock_fps/store/sync.py]
tests: [tests/test_store_client.py, tests/test_store_catalog.py, tests/test_store_sync.py, tests/store_fixtures.py]
---

# Task - Mod Store engine

The Qt-free engine: GameBanana API v11 client with strict normalisation of untrusted JSON, SQLite catalogue with FTS5 search, resumable crawl and incremental refresh ([[ADR-011 The store is a local catalogue, not a repository provider]]).

**Evidence (VERIFIED).**
* 79 tests (client 32, catalogue 26, sync 21) against a fake server that sorts and pages like the real one, with fault injection (429, 503, bad JSON, cancel).
* 15 safety and logic checks disabled one at a time with `scripts/dev/mutation_store.py`: **15 of 15 caught** (host allow-list, bidi stripping, MD5 validation, profile identity, adult flag, image extensions, file-name separators, FTS input, counts preserved, sort whitelist, cursor, end of crawl, ordering guard, pacing).
* **Live, read-only, 2026-11-14:** a full crawl into a throwaway folder: 123 requests, **6 115 listings, 0 skipped, 137 s**, row count equal to the server's reported total (one mod appeared during the crawl: 6 114 → 6 115); a refresh right after cost **1 request, 0.5 s**; catalogue file 4.1 MB; encoded `_aFilters%5B…%5D` parameters accepted; one real profile page parsed (files, MD5, scan verdict, licence). Reproduce with `scripts/dev/store_live_check.py`.

**Not covered.** Sounds, WIPs and Collections (Mod only); pruning of listings GameBanana later deletes ([[Known Issues]]); a crawl interrupted for days.

Implements: [[Mod Store]].
