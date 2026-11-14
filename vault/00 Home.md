---
title: Deadlock Mod Manager — Project Map
type: guide
tags: [moc, home]
updated: 2026-11-14
---

# Deadlock Mod Manager — project knowledge base

The second brain for **Deadlock Toolbox 4.0** (a PySide6 desktop app, see [[Architecture Overview]]), which is now a multi-repository mod manager. The **codebase is the source of truth**; these notes explain it and track what is real. Read [[Status Legend]] before trusting a status, and [[Vault Guide]] for conventions.

## AI memory: start here in a new session
[[00 Start Here]] · [[User Brief - Original Requirements]] · [[User Profile and Working Rules]] · [[Session History]] · [[Open Items and Next Steps]] · [[Environment and Pitfalls]] · [[How The Code Works]] · [[Verification Cookbook]] · [[Research Findings]] · [[Reference App Analysis]] · [[Git and Release State]]

## Where things stand (2026-11-14, version 4.0.0)

| Milestone | Status |
|---|---|
| 1 · Audit and second brain | [[Roadmap#Milestone 1|IMPLEMENTED]] |
| 2 · Repository engine | [[Roadmap#Milestone 2|IMPLEMENTED]]: [[Repository Manager]] |
| 3 · Mod Hub | [[Roadmap#Milestone 3|IMPLEMENTED]]: [[Mod Hub]] |
| 4 · Installation engine | [[Roadmap#Milestone 4|IMPLEMENTED]]: [[Installation Engine]] |
| 5 · Installed mods & updates | [[Roadmap#Milestone 5|IMPLEMENTED]]: [[Installed Mods]], [[Compatibility and Downloads]] |
| 6 · Knowledge graph | [[Roadmap#Milestone 6|IMPLEMENTED]]: [[Knowledge Graph]] |
| 7 · UI refinement | [[Roadmap#Milestone 7|IN PROGRESS]] |
| 8 · Testing & verification | [[Roadmap#Milestone 8|IN PROGRESS]]: [[Testing]] |
| 9 · Mod Store | [[Roadmap#Milestone 9|IN PROGRESS]]: [[Mod Store]] |
| 10 · Performance | [[Roadmap#Milestone 10|IN PROGRESS]]: [[Performance Details]] |
| 11 · Stats | [[Roadmap#Milestone 11|IN PROGRESS]]: [[Stats]] |

Not built: [[Collections]] (PROPOSED); update checks for [[Mod Store]] installs. Not yet exercised on a real game install: see [[Known Issues]].

## Next: redesign
[[Redesign Plan]] · [[Handoff - Phase 1 Design (Fable 5.2)]] · [[Handoff - Phase 2 Infrastructure (Opus 5.5)]] · [[Handoff - Phase 3 Build (Sonnet 5.5)]]

**Phase 1 (design) is done, 2026-11-14:** [[01 Principles]] · [[02 Information Architecture]] · [[03 Visual Language]] · [[04 Components]] · [[05 Screens]] · [[06 Handoff to Build]]. Mock-up: `docs/design-prototype/index.html`.

## Architecture
[[Architecture Overview]] · [[Codebase Structure]] · [[Dependencies]] · [[Technical Debt]]

## Features — the new platform
[[Repository Manager]] · [[Repository Providers]] · [[Manifest Specification]] · [[Trust System]] · [[Repository Search]] · [[Mod Hub]] · [[Mod Store]] · [[Performance Details]] · [[Stats]] · [[Home Page]] · [[Browse Page]] · [[Installed Page]] · [[Classic Pack and Sources]] · [[Installation Engine]] · [[Installed Mods]] · [[Compatibility and Downloads]] · [[Collections]] · [[Knowledge Graph]]

## Features — already shipped before this work
[[Existing Mod Library]] · [[Mod Inspector]] · [[Update Center]] · [[Performance Tuning]] · [[Crosshair Designer]] · [[Server Picker]] · [[Recovery]]

## Specifications
[[Repository Specification]] · [[Mod Lifecycle]] · [[Security Model]]

## Decisions
[[ADR-001 Keep the Python and PySide6 stack]] · [[ADR-002 Repository engine is a Qt-free package]] · [[ADR-003 Trust comes from a bundled registry]] · [[ADR-004 Translate only VPK release assets]] · [[ADR-005 Standard-library HTTP with a pinned connection]] · [[ADR-006 Vault lives in the repository]] · [[ADR-007 The installer must go through Studio]] · [[ADR-008 Mod folder and pak naming need verification]] · [[ADR-009 Installation is a journaled set of moves]] · [[ADR-010 The graph is derived from real data and drawn with QPainter]] · [[ADR-011 The store is a local catalogue, not a repository provider]] · [[ADR-012 Reimplement from public interfaces and copy nothing from the GPL reference]] · [[ADR-013 Facts come from Valve's data and the explanations are written here]] · [[ADR-014 Statistics are fetched on request and nothing personal is kept]]

## Design, quality, history
[[Design System]] · [[Testing]] · [[Known Issues]] · [[Roadmap]] · [[Implementation Log]]

## Tasks (what implemented what)
[[Task - Archive and VPK inspection]] · [[Task - Installed records and updates]] · [[Task - Installed, Compatibility and Downloads pages]] · [[Task - Journaled install transaction]] · [[Task - Knowledge graph engine and canvas]] · [[Task - Manifest validator]] · [[Task - Mod Hub and install preview]] · [[Task - Mod Store engine]] · [[Task - Mod Store page]] · [[Task - Mod Store install]] · [[Task - Performance Details]] · [[Task - Pinned HTTPS transport]] · [[Task - Provider abstraction and built-in providers]] · [[Task - Repository Manager and page]] · [[Task - Stats]] · [[Task - Streaming package download]] · [[Task - Studio addons search path]] · [[Task - Version 4.0.0 packaging]]
