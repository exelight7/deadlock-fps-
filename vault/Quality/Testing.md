---
title: Testing
type: quality
status: IN PROGRESS
tags: [quality, testing]
updated: 2026-11-14
code: [tests/, scripts/ci_tests.py, scripts/i18n_tool.py, scripts/check_vault.py]
---

# Testing

## How to run
```bash
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests          # everything
python -m unittest discover -s tests -p "test_installer_*.py"             # one group
python scripts/i18n_tool.py check                                         # every tr() string has both translations
python scripts/check_vault.py                                             # the vault agrees with the repository
```
(`scripts/ci_tests.py` wraps the first command for CI. On Windows use the project's `.venv\Scripts\python.exe`.)

## Suite (845 tests, 2026-11-15; one environmental failure and one skip, both pre-existing; the full run took about 20 minutes, see Known Issues 22)

| Group | Tests | Qt | Network |
|---|---:|:-:|:-:|
| Pre-existing (17 modules) | 158 | partly | none |
| `test_repos_core`, `_providers`, `_manager`, `_docs` | 24 + 27 + 29 + 4 | no | none (scripted transport, fake opener and resolver) |
| `test_repos_ui` | 16 | offscreen | none |
| `test_studio_addons` | 9 | no | none |
| `test_installer_inspect` (VPK, hostile ZIPs, streaming download) | 18 | no | none |
| `test_installer_engine` (pipeline, rollback, recovery, health) | 49 | no | none |
| `test_mod_pages` (Hub, Installed, Compatibility, Downloads) | 18 | offscreen | none |
| `test_graph` (model, builders, layout) | 20 | no | none |
| `test_graph_ui` (canvas with real mouse, wheel and key events) | 16 | offscreen | none |
| `test_vault` | 4 | no | none |
| `test_store_client` (request shape, hostile JSON, error mapping) | 32 | no | none (fake GameBanana) |
| `test_store_catalog` (storage, FTS, filters, recovery) | 26 | no | none |
| `test_store_sync` (crawl, resume, refresh, rate limit, cancel) | 21 | no | none |
| `test_store_ui` (the old page; replaced on 2026-11-14 by `test_store_browse`) | 32 | offscreen | none |
| `test_store_install` (adapter, zip discovery, MD5 and host checks, install and uninstall through the real engine) | 33 | no | none |
| `test_perf` (settings coverage, skip mechanism through the real Studio, the window, the main window) | 37 | offscreen | none |
| `test_stats_core` (strict readers, formulas with reference values, Steam id spellings, data shapes) | 28 | no | none |
| `test_stats_api` (addresses and parameters, hostile JSON, failures, player calls) | 35 | no | none (fake Deadlock API) |
| `test_stats_source` (disk cache, freshness, stale fallback, privacy of player numbers) | 30 | no | none |
| `test_stats_ui` (page, service, main window, Arabic ordering guard) | 55 | offscreen | none |
| `test_store_browse` (the rebuilt Mods › Browse page: cards, sheet, review dialog, 130 % width, the install flow through the real engine) | 51 | offscreen | none |
| `test_installed_pages` (Mods › Installed, Check and Activity through the real engine; 130 % width of all four Mods pages, classic pack open) | 30 | offscreen | none |
| `test_mod_workflow` / `test_mod_inspector` (engines, and the classic pack and Check's classic section in the real window) | 19 / 8 | offscreen | none |
| `test_sources_view` (Mods › Browse › My sources and the Browse host; replaces `test_mod_pages`, the Hub tests) | 15 | offscreen | none |

`test_ping_ui` (the old server page) switched off the page's own 300 ms automatic measurement in its one UI test (2026-11-14): on a slow machine the timer fired inside `processEvents()` and the first row said "measuring"; the full run now takes 15 to 30 minutes on this machine, so such timing races show up. Tests that change the look must use `tests/look_fixture.keep_look`.

Existing tests updated for intended changes: the navigation count (9 → 15), and the minimum-size test, which now checks that every rail entry can be scrolled into view instead of assuming the rail never scrolls. When the Mod Store page was added: the stack count and the rail labels (15 → 16) in `test_repos_ui` and `test_mod_inspector`.

## What the tests are worth
* **Mutation spot-checks.** Security-relevant checks were disabled one at a time: 6 in the repository engine (5 caught, 1 redundant with another check) and 8 in the installer (all caught, after two isolating tests were added because the first run showed two checks hiding behind others). An RTL selection regression test was confirmed to fail against the old code.
* **Real bugs the tests found:** a failed download deleted a pre-existing destination file; a `pathlib`-based archive check hid `//` and `./`; re-enabling a mod whose slot was taken could pick the occupied slot; the Hub's feedback message was overwritten by its own refresh.
* **Real-network checks** (outside the suite, 2026-11-14): the transport and providers against github.com and gitlab.com, and a streaming download through GitHub's redirect.
* **Mod Store:** 29 checks disabled one at a time (`scripts/dev/mutation_store.py`: 15 in the engine, 14 in the install path), all 29 caught (re-run after the Browse rebuild, with the two page checks pointed at `pages/browse.py`). A full live crawl on 2026-11-14 (`scripts/dev/store_live_check.py`): 123 requests, 6 115 listings, 0 skipped, 137 s, a refresh of 1 request. And one real download through the install path (`scripts/dev/real_install_check.py`, 2026-11-14, 7.5 MB, throwaway game folder): it found a version-number bug that the tests had missed.
* **Performance Details:** 19 checks disabled one at a time (`scripts/dev/mutation_perf.py`), all 19 caught (one needed an isolating test). `scripts/dev/perf_facts.py --check` compares the facts file with a catalogue.
* **Stats:** 47 checks disabled one at a time (`scripts/dev/mutation_stats.py`), all 47 caught (two survived the first run because the fake server hid blank parameters and an oversized test file was not valid JSON; the tests were fixed). The tests found two real bugs: `[U:1:abc]` crashed the Steam id reader, and an infinite number in a cache file crashed the cache reader. A read-only live check of the public endpoints (`scripts/dev/stats_live_check.py`, 19 checks, no account number) passed on 2026-11-14. One real personal lookup with the user's approval (`scripts/dev/stats_player_check.py`) confirmed the shape of the player answers.
* **Visual checks:** every new page rendered offscreen in English and Arabic and inspected; defects found that way (clipped columns, overlapping labels, RTL selection) were fixed.

## Not covered
* A real display, a real game install with real community mods, a real native repository, live DNS rebinding, multi-gigabyte packages, 5 000-mod catalogues, slow or hostile servers beyond the scripted cases.
* A screen-reader pass and a systematic keyboard audit ([[Design System]]).
* Whether the vault's *claims* are true; `tests/test_vault.py` checks structure only.

Related: [[Known Issues]] · [[Security Model]]
