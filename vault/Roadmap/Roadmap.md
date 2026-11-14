---
title: Roadmap
type: roadmap
status: IN PROGRESS
tags: [roadmap]
updated: 2026-11-14
---

# Roadmap

Priority order from the brief: (1) reliable multi-repository system, (2) safe installation, (3) discovery and management, (4) polish, (5) the graph, (6) extensibility. Real functionality first.

## Milestone 1
**Audit and second brain: IMPLEMENTED.** [[Codebase Structure]], [[Technical Debt]], this vault ([[ADR-006 Vault lives in the repository]]).

## Milestone 2
**Repository engine: IMPLEMENTED.** [[Repository Manager]], [[Repository Providers]], [[Manifest Specification]], [[Trust System]], [[Repository Search]].

## Milestone 3
**Mod Hub: IMPLEMENTED.** [[Mod Hub]]: search, filters, details, version history, fit with the game build, install flow. Not yet: card grid, grouping one mod across repositories.

## Milestone 4
**Installation engine: IMPLEMENTED.** [[Installation Engine]]: download, verify, inspect, stage, backup, install, verify, commit, rollback, recovery, uninstall ([[ADR-007 The installer must go through Studio]], [[ADR-008 Mod folder and pak naming need verification]], [[ADR-009 Installation is a journaled set of moves]]).

## Milestone 5
**Installed mods and updates: IMPLEMENTED.** [[Installed Mods]] and [[Compatibility and Downloads]]: versions, sources, update one/all, restore previous, disable/enable, remove, health check, history.

## Milestone 6
**Knowledge graph: IMPLEMENTED.** [[Knowledge Graph]] ([[ADR-010 The graph is derived from real data and drawn with QPainter]]).

## Milestone 7
**UI refinement: IN PROGRESS.** Done: one navigation group for the mod manager, a denser rail, consistent pages, English and Arabic including right-to-left, plain-text rendering of remote content. Open: named pages instead of indexes, a systematic keyboard and screen-reader pass, responsive layouts below the 940 px window minimum, a light theme, card grid for the Hub ([[Design System]], [[Technical Debt]] #4).

## Milestone 8
**Testing and verification: IN PROGRESS and continuous.** [[Testing]]. Open: a run against a real game install with real community mods, a real native repository, real-display checks, large catalogues.

## Milestone 9
**Mod Store: IN PROGRESS.** Browsing and installing `.zip`/`.vpk` files are [[Mod Store]] (engine VERIFIED live; page and install IMPLEMENTED). Open: a run on a real game folder (one real download already worked in a throwaway one), `.rar`/`.7z`, update checks, Sounds/WIPs/Collections.

## Milestone 10
**Performance: IN PROGRESS.** [[Performance Details]]: every setting the slider writes is explained and checked against Valve's data, and the user can leave any of them out (IMPLEMENTED, never run in the real game). Open: a real-game check of the statuses, importing community configs, presets.

## Milestone 11
**Stats: IN PROGRESS.** [[Stats]]: a page with the hero meta, the rank spread and the user's own record from the public Deadlock API, fetched only on request, nothing personal kept ([[ADR-014 Statistics are fetched on request and nothing personal is kept]]). IMPLEMENTED; public numbers checked live. One real lookup of the user's own account was done (approved; it had no ranked or recent matches). Open: a lookup of an account with ranked matches (ask first), a hero detail page, items and builds, match history, a performance overlay.

## Milestone 12
**Interface redesign: PLANNED.** A new coherent design in three phases and three models ([[Redesign Plan]]).

## Next
0. The interface redesign: [[Redesign Plan]].
1. Run the whole flow on a real Deadlock install with a few real community mods; fix what that finds ([[Known Issues]]).
2. Publish a real native repository (a `deadlock-repo.json`) for the project and a review process behind the trust labels ([[Trust System]]).
3. [[Collections]] (PROPOSED): named sets of mods, shareable and installable together.
4. Multi-file VPKs; per-mod load-order control; a JSON Schema file and conformance corpus for third-party repository authors ([[Repository Specification]]).
5. Mod Store: a run on a real Deadlock folder (ask first), more real mods, `.rar`/`.7z` support, update checks for store installs ([[Mod Store]], [[Task - Mod Store install]]).
6. Stats follow-ups ([[Stats]]): a lookup of an account with ranked matches (ask the owner first), then maybe a hero detail page. Performance follow-ups: a real-game check of the statuses, then maybe leaving the ignored settings out by default, and importing community configs ([[Performance Details]]).

Related: [[00 Home]] · [[Implementation Log]]
