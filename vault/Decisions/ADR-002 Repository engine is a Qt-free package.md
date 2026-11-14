---
title: ADR-002 Repository engine is a Qt-free package
type: decision
status: IMPLEMENTED
tags: [decision]
updated: 2026-11-14
affects: [Repository Manager, Repository Providers, Architecture Overview]
---

# ADR-002 · The repository engine is a Qt-free package with an injected transport

**Context.** Requirements: providers independent of the installer, UI independent of business logic, everything testable.

**Decision.** `deadlock_fps/repos/` imports no Qt and no game-folder code. Providers receive a `Transport` (interface), so tests script exact server behaviour and a different HTTP stack can be dropped in. The UI calls the manager on worker threads and only draws results. New providers register in a `ProviderRegistry` without touching other modules.

**Consequences.** 84 engine tests run in about a second with no network. The page is thin. The price: the engine cannot use Qt Network's proxy support ([[ADR-005 Standard-library HTTP with a pinned connection]]).

Affects [[Repository Manager]], [[Repository Providers]].
