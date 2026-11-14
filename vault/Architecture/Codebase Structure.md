---
title: Codebase Structure
type: architecture
tags: [architecture, audit]
updated: 2026-11-14
code: [deadlock_fps/, tests/, scripts/, docs/]
---

# Codebase structure

Result of the Milestone 1 audit of `exelight7/deadlock-fps-` at commit `c6d020f` (v3.5.5), 216 tracked files. Line counts are approximate and were measured at that commit.

## `deadlock_fps/` — pre-existing

| Module | Lines | Responsibility | Feature note |
|---|---:|---|---|
| `ui.py` | 463 | Main window, rail navigation, Home, Performance, Recovery, Settings pages | [[Architecture Overview]] |
| `core.py` | 417 | Game detection, `Studio` (preview-first file changes, originals, rollback), VPK reader (`vpk_entries`) | [[Recovery]] |
| `settings.py` | 132 | Graphics presets, the **fixed `MODS` table** of four reference mods | [[Performance Tuning]], [[Existing Mod Library]] |
| `mods.py` | 105 | `ModLibrary`: bounded import of ZIP/VPK/folders, recognises mods **only by pinned SHA-256** | [[Existing Mod Library]] |
| `mod_install.py` | 33 | prepare → commit of mod changes through `Studio` | [[Existing Mod Library]] |
| `mod_inspector.py` | 72 | Read-only structure/hash diagnostics and overlap detection | [[Mod Inspector]] |
| `pages/classic.py`, `pages/sources.py`, `pages/browse_host.py` | 382 / 548 / 65 | the classic pack inside Installed, "My sources" in Browse, and the switch that holds Browse's two views ([[Classic Pack and Sources]]; `mod_ui.py` and `inspector_ui.py` are gone) | |
| `servers.py`, `firewall.py`, `server_ui.py`, `server_delegate.py`, `region_info.py` | | Steam relay ping and block/allow | [[Server Picker]] |
| `crosshair*.py` | | Crosshair designer, 50 presets | [[Crosshair Designer]] |
| `updates.py`, `update_client.py`, `update_ui.py`, `installation.py` | | GitHub release check, checksum-verified download, per-user install | [[Update Center]] |
| `detection.py` | 70 | Is Deadlock installed / updating / absent | |
| `design.py`, `theme.py`, `motion.py` | 697 / 73 / 572 | Tokens, stylesheet, custom widgets, animation | [[Design System]] |
| `i18n.py`, `lang_en.py`, `lang_ar.py` | | `tr()` catalogues, English ⇄ Arabic | |
| `kv.py`, `kv3.py` | | Valve KeyValues text editing for `gameinfo.gi` / `video.txt` | |

## `deadlock_fps/` — added by this work

| Module | Lines | Responsibility |
|---|---:|---|
| `repos/errors.py` | 29 | `RepoError(code, message)` and the stable code list |
| `repos/versions.py` | 124 | Version parsing/ordering, dependency range language |
| `repos/urls.py` | 124 | HTTPS URL safety, canonical repository identity |
| `repos/model.py` | 194 | Immutable data types |
| `repos/spec.py` | 348 | Validator for the [[Manifest Specification]] |
| `repos/transport.py` | 166 | `Transport` interface, pinned-address HTTPS implementation |
| `repos/providers/` | 467 | `base`, `native` (HTTPS), `github`, `gitlab`; see [[Repository Providers]] |
| `repos/trust.py` | 66 | [[Trust System]] registry loader |
| `repos/store.py` | 117 | Atomic on-disk persistence |
| `repos/manager.py` | 266 | [[Repository Manager]] |
| `repos/search.py`, `repos/compat.py` | 75 / 25 | [[Repository Search]], game-build fit |
| `repo_ui.py` | 501 | Repositories page |
| `assets/trust/registry.json` | | Shipped trust decisions |

## `deadlock_fps/` — added for 4.0

| Module | Lines | Responsibility |
|---|---:|---|
| `installer/engine.py` | ~650 | [[Installation Engine]]: prepare, commit, uninstall, disable, restore, recover, health check |
| `installer/archive.py`, `installer/vpk.py` | 119 / 125 | hardened ZIP and streaming VPK inspection |
| `installer/records.py`, `installer/updates.py`, `installer/errors.py` | 129 / 63 / 30 | installed-mod store, update detection, stable error codes |
| `mod_service.py` | 163 | [[Mod Hub]] and friends talk to the engines through this one object |
| `hub_ui.py` | 29 | only `failure_text`, the plain sentences for engine failures (the Hub page moved to `pages/sources.py`) |
| `pages/installed.py`, `pages/check.py`, `pages/activity.py` | 562 / 231 / ~120 | Mods › Installed, Check and Activity on the redesign components ([[Installed Page]]; `installed_ui.py` is gone) |
| `ui_common.py` | 105 | shared table, button and RTL helpers |
| `graph/model.py`, `graph/build.py`, `graph/layout.py` | 168 / 146 / 91 | [[Knowledge Graph]] data, builders, layout |
| `graph_ui.py`, `vault.py` | 631 / 72 | the canvas and page; the vault reader used by the graph and the checker |
| `store/model.py`, `store/gamebanana.py`, `store/catalog.py`, `store/sync.py` | 81 / 287 / 243 / 125 | the [[Mod Store]] engine (Qt-free): GameBanana client, SQLite catalogue, crawl and refresh |
| `store_service.py`, `pages/browse.py` | 122 / 976 | the Mod Store service, and the Mods › Browse page built on the redesign components ([[Browse Page]]; `store_ui.py` is gone) |
| `stats/clean.py`, `maths.py`, `steam.py`, `model.py`, `api.py`, `cache.py`, `source.py` | 35 / 28 / 72 / 90 / 192 / 60 / 142 | the [[Stats]] engine (Qt-free): strict readers, formulas, Steam id spellings, client for the public Deadlock API, disk cache, source with stale fallback |
| `stats_service.py`, `stats_ui.py` | 129 / 437 | the Stats service and page (stack index 16) |
| `core.py`, `kv.py` (edited) | | `Studio.enable_addons()`, `kv.add_addons_path()` |
| `repos/transport.py` (edited) | | `Transport.download()` streaming |

## Everything else

* `tests/` — 17 pre-existing modules plus the `test_repos_*`, `test_studio_addons`, `test_installer_*`, `test_mod_pages`, `test_graph*` and `test_vault` modules and their fixtures ([[Testing]]).
* `scripts/` — `ci_tests.py`, `i18n_tool.py` (translation checker), `make_assets.py`, `make_screenshots.py`, smoke tests.
* `docs/` — user guides **in Arabic**; the English [[Repository Specification]] and its examples were added.
* `.github/workflows/` — build and release description.

## Observations used by later decisions

1. Mods are not first-class: a mod is one of four keys in `settings.MODS`, recognised by content hash. There is no concept of "a mod from somewhere".
2. The same code both detects the game and rewrites `gameinfo.gi`; any new installer must share that machinery ([[ADR-007 The installer must go through Studio]]).
3. The update client already hand-rolls a hardened download path (host allow-list, checksum, size caps) — a useful precedent for [[Installation Engine]].
