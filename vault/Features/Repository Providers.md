---
title: Repository Providers
type: feature
status: IMPLEMENTED
tags: [feature, repositories, providers]
updated: 2026-11-14
code: [deadlock_fps/repos/providers/base.py, deadlock_fps/repos/providers/github.py, deadlock_fps/repos/providers/gitlab.py, deadlock_fps/repos/providers/native.py, deadlock_fps/repos/transport.py]
tests: [tests/test_repos_providers.py]
---

# Repository providers

A **provider** knows one hosting convention. The contract (`providers/base.py`): `identify(url, hint)` — canonical identity, no network; `sync(source, transport, etag)` — fetch and classify. Providers return data and never install or touch the game ([[ADR-002 Repository engine is a Qt-free package]]). `ProviderRegistry.register(provider, first=…)` adds a new hosting source **without changing any other module** (tested with a fake Gitea provider).

## Compatibility classes

| Class | Meaning | Installable? |
|---|---|---|
| **NATIVE** | publisher wrote the [[Manifest Specification]] | yes (when installer exists) |
| **TRANSLATED** | catalogue derived from release metadata (`.vpk` assets only, [[ADR-004 Translate only VPK release assets]]) | only after inspection |
| **MANUAL** | recognised, only archives published — a hand-written mapping index is required | no |
| **UNSUPPORTED** | nothing usable, reason shown | no |

A repository is never silently interpreted: a manifest that exists but is invalid is reported as such rather than falling back to guessing.

## Built-in providers

| Provider | Detects | Order of attempts | Status |
|---|---|---|---|
| `github` | `github.com/owner/repo…` | API metadata → `deadlock-repo.json` in default branch → `deadlock-repo.json` attached to a release → translate `.vpk` assets → `.zip` only = MANUAL → UNSUPPORTED | VERIFIED (live: manual, not-found; tests: native/translated) |
| `gitlab` | `gitlab.com/group/project`; any host when the user picks *Self-hosted GitLab* | API metadata → manifest via files API → translate `.vpk` release links → MANUAL → UNSUPPORTED | IMPLEMENTED (live: not-found and no-assets; translation only with fakes) |
| `https` | any public HTTPS address | the URL itself, or `<url>/deadlock-repo.json` | IMPLEMENTED (live: 404 only; no real native repository exists to test against) |

Translated entries record honestly what they lack: generic description, unknown game compatibility, hash only when GitHub reports a `digest`; GitLab reports neither size nor hash. Asset URLs must be exactly the host's documented download path for that repository (spoofed hosts are skipped and reported as warnings).

Only the first 30 releases are read. Rate limits (403 with `x-ratelimit-remaining: 0`, 429) are *errors*, not verdicts.

## Transport
`repos/transport.py`: HTTPS only, public addresses only (resolved and pinned at connect time), validated redirects (≤ 5), streamed size limits, no compression, 45 s deadline. See [[Security Model]] and [[ADR-005 Standard-library HTTP with a pinned connection]].

Related: [[Repository Manager]] · [[Trust System]] · [[Mod Lifecycle]]
