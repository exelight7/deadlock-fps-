---
title: Update Center
type: feature
status: IMPLEMENTED
tags: [feature, existing, updates]
updated: 2026-11-14
code: [deadlock_fps/updates.py, deadlock_fps/update_client.py, deadlock_fps/pages/update.py, deadlock_fps/installation.py]
tests: [tests/test_updates.py, tests/test_installation.py]
origin: pre-existing
---

# Update Center (pre-existing)

Updates **the application itself**, not mods. Checks the latest stable GitHub release of `exelight7/deadlock-fps-` (API, `ETag`, at most once a day, no background timer), downloads the platform ZIP with a size cap, verifies `SHA256SUMS.txt` and the hash while streaming, and installs a fresh per-user copy without admin rights. Redirects are limited to GitHub hosts over HTTPS; TLS errors are never ignored. ZIP extraction rejects traversal, symlinks and oversized expansions.

It is the closest precedent for a hardened download path ([[Installation Engine]]) and uses Qt Network, unlike the new engine ([[ADR-005 Standard-library HTTP with a pinned connection]]). Its repository is hard-wired, which is the single-source limitation the [[Repository Manager]] removes for mods.

Related: [[Security Model]]
