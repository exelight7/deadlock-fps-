---
title: ADR-005 Standard-library HTTP with a pinned connection
type: decision
status: IMPLEMENTED
tags: [decision, security, networking]
updated: 2026-11-14
affects: [Repository Providers, Security Model, Dependencies]
---

# ADR-005 · Standard-library HTTP with a pinned connection

**Context.** The repository URL is user- and remote-supplied; the app must not be usable to probe the user's machine or LAN, and must be testable without Qt.

**Options.** (a) Qt Network like `update_client.py` — async, but Qt-bound and no hook to validate the resolved address before connecting. (b) A third-party HTTP library — new dependency. (c) **`urllib` + `http.client`**, with a custom connection that resolves once, requires every answer be public, connects to that address and verifies TLS against the hostname; a hand-built opener exposing only that HTTPS handler; redirects handled manually.

**Decision.** (c). Zero new dependencies; address validated at the point of connection, closing the DNS-rebinding window.

**Consequences.** Blocking calls (run on worker threads); no system proxy support, so users behind a mandatory proxy cannot sync ([[Known Issues]]); a second networking stack beside Qt's ([[Technical Debt]] #6). Package downloads in the installer should reuse this transport or the update client's policy.

Affects [[Repository Providers]], [[Security Model]].
