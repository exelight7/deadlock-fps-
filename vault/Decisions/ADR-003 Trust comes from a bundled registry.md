---
title: ADR-003 Trust comes from a bundled registry
type: decision
status: IMPLEMENTED
tags: [decision, security]
updated: 2026-11-14
affects: [Trust System, Repository Manager, Security Model]
---

# ADR-003 · Trust labels come from a registry shipped in the application

**Context.** Labels must describe real review, not hosting reputation ("a GitHub repository is not automatically trusted"). An index is attacker-controlled input.

**Options.**
1. Let the index declare its trust → trivially forgeable. Rejected.
2. Fetch a trust list from a server → a remote party (or a compromised server) can promote repositories; adds a network trust root. Rejected for now.
3. **Ship a registry in `assets/` keyed by canonical repository identity.** Changes only with an application update.

**Decision.** Option 3. Default UNVERIFIED; unreadable registry ⇒ everything UNVERIFIED. Identity is the canonical id (`github:owner/repo`), so forks and look-alikes get nothing.

**Consequences.** Safe and simple; but promotion is slow (needs a release) and no review process exists yet, so the registry has one entry. A signed, independently updatable registry is a possible later step.

Affects [[Trust System]], [[Security Model]].
