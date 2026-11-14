---
title: Technical Debt
type: architecture
tags: [architecture, audit, debt]
updated: 2026-11-14
---

# Technical debt

Found in the Milestone 1 audit, with what has happened to each since. "Hazard" means a concrete way the platform could go wrong.

| # | Finding | Status |
|---|---|---|
| 1 | **Hazard.** `Studio.plan_mods([])` removed the `fps_studio` search path, which would have silently disabled mods installed into it | **resolved**: repository mods use `citadel/addons`, which `Studio` now preserves ([[ADR-007 The installer must go through Studio]]) |
| 2 | **Hazard.** `Studio.baseline()` refuses to continue when `gameinfo.gi` differs from what it applied; a second editor would trip it | **resolved**: the installer registers the path *through* `Studio`; Steam resets are repaired |
| 3 | The mod catalogue was a hard-coded four-key dict with pinned hashes | **bypassed, not removed**: repository mods are tracked separately in `installed.json`; the four reference mods keep their own mechanism ([[Existing Mod Library]]) |
| 4 | Navigation is index-based (`ui.py` literals, hint arrays, `PAGES`, tests pin indexes) | **open and growing**: 15 pages now; each new page touched five places. Named pages are Milestone 7 work |
| 5 | Very dense legacy style (`;`-chained statements) | **open**: new code is conventional; no mass reformat (it would bury real changes) |
| 6 | Two networking stacks (Qt Network and `urllib`) | **open, deliberate** ([[ADR-005 Standard-library HTTP with a pinned connection]]) |
| 7 | User docs are Arabic only; UI sources mix Arabic and English | **partly addressed**: English specification, guide and release notes added; `i18n_tool.py check` enforces both catalogues |
| 8 | `test_symlink_outside_game_rejected` needs the Windows symlink privilege | **open** ([[Known Issues]]) |
| 9 | Python on Windows writes CRLF into an LF repository | **open, documented** ([[Known Issues]]) |
| 10 | The trust registry has one entry and there is no review process | **open** ([[Trust System]]) |

## New debt created by this work
* `installer/engine.py` is the largest module (~650 lines) and mixes planning, transactions and health checks; it should split when it next grows.
* `hub_ui.py` is now only `failure_text`; it could move into `ui_common.py` and the file be deleted.
* The rail has 15 destinations; it fits at 1000 px height and scrolls below that. Grouping or collapsing sections is [[Roadmap]] work.
* The Hub is a table, not a card grid; same-id mods across repositories are separate rows.

Related: [[Codebase Structure]] · [[Architecture Overview]]
