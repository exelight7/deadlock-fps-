---
title: ADR-012 Reimplement from public interfaces and copy nothing from the GPL reference
type: decision
status: IMPLEMENTED
tags: [decision, licence, store]
updated: 2026-11-14
affects: [Mod Store, Performance Tuning]
---

# ADR-012 · Reimplement from public interfaces; copy nothing from the GPL reference

**Context.** The user asked for the mod store, performance and stats of the community Deadlock Mod Manager to be brought into their own program. That app is **GPL-3.0**, its performance catalogue embeds data derived from other GPL-3.0 projects, and Deadlock Toolbox is **MIT** ([[Reference App Analysis]]).

**Decision.**
* No source code, curated text, preset or catalogue data is copied from the reference. The reference's source was read to learn *which* services it uses and which request parameters work, and that reading shaped the design (a local catalogue, a resumable cursor). The code here was written independently, and every behaviour it relies on was confirmed against the live interfaces (GameBanana API v11 and, later, api.deadlock-api.com).
* Facts such as endpoint paths, parameter names, and field names are interface descriptions, not expression; they are used.
* When performance presets arrive they must be authored here or taken from sources whose licence is compatible, with the licence written down.

**Consequences.** The store cannot reuse the reference's code; the benefit is that the project stays MIT. This is an engineering reading, not legal advice: the user should confirm before distributing, and should read GameBanana's and deadlock-api's terms (the client identifies itself, caches, and paces its requests).

Affects [[Mod Store]], [[Performance Tuning]].
