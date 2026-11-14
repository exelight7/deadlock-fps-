---
title: Implementation Log
type: history
tags: [history]
updated: 2026-11-15
---

# Implementation log

Newest first. Entries say what changed in the code and what was (not) verified.

## 2026-11-15: stability and speed pass before the 4.0.0 release
**Changed:**
* `ui.py`: closing the window also cancels the Mod Store download; after the event loop ends, `main()` waits up to 5 s for background jobs (store, stats, pings) so none is still running while Python shuts down (a known cause of crashes at exit).
* `core.running_game_root`: reads only process names for every process and the executable path only for a Deadlock match (it opened every process before; this runs every 20 s on the interface thread while no game is linked).
* `repos/transport.py`: one verified default SSL context is shared instead of loading the Windows certificate store for every client (~40 ms each, three at startup). Same settings, so security is unchanged.
* `pages/map.py`: changes and showing the page are coalesced into one rebuild on the next event-loop turn (opening the Map built the graph twice); the layout may use at most 1 s of the interface thread (was 2 s). First open measured 1.09 s → 0.69 s offscreen.
* `tests/test_core.py`: the symlink test skips when Windows refuses to create a symlink (Known Issue 1).

**Verified:** the touched modules' tests pass (core, 102, repos, graph incl. a new "a burst of changes costs one rebuild" check); the full suite, i18n and vault checks were run before release (see the release entry in [[Git and Release State]]).

**Not verified:** not run on the user's display or a real game folder.

## 2026-11-14 (redesign, phase 3, the rest): Performance, Stats, Settings, Backups, Servers, Crosshair, Map; the old system deleted

Phase 3 of [[Redesign Plan]] (Sonnet 5.5), finished in one chat. **Built:** `pages/performance.py` (`LevelPage`, `AllSettingsPage`, `ApplyReview`, `PerformanceMixin`), `pages/stats.py`, `pages/settings.py` (+ `update.py`, `source_list.py`), `pages/backups.py`, `pages/servers.py`, `pages/crosshair.py`, `pages/map.py`, `shell/base.py`, `shell/motion.py`. **Deleted:** `design.py`, `theme.py`, `motion.py`, `legacy/`, `perf_ui.py`, `stats_ui.py`, `server_ui.py`, `server_delegate.py`, `crosshair_ui.py`, `crosshair_style.py`, `update_ui.py`, `repo_ui.py`, `graph_ui.py`. **Changed:** `ui.py` has no hero, hint line, status line or action bar; the registry has `Page.section_list` and the Settings tabs share one slot; `set_look` keeps the other remembered choices; light theme, text size, less motion and mod pictures are in Settings; `Job` moved to `ui_common.py`; `scripts/dev/add_arabic.py` merges translations. Details: [[Rebuilt Pages - Performance to Map]].

**Verified:** each page against its tests (ported or new: `test_perf` incl. the end-to-end apply/undo through the window, `test_stats_ui`, `test_settings_page`, `test_backups_page`, `test_server_selection`, `test_repos_ui`, `test_crosshair`, `test_graph_ui`, `test_motion`, `test_shell`), `scripts/i18n_tool.py check`, `scripts/check_vault.py`, LF line endings, and offscreen pictures in English dark, Arabic light and English light. A real bug was found by the new apply test (`dialog.Accepted` on a Dialog instance) and fixed.

**Not done / not verified:** never seen on the user's display; no run on a real game folder; card pictures; the mutation scripts were re-pointed but not re-run. See [[Known Issues]].

## 2026-11-14 (redesign, phase 3, step 3, part 2): the temporary tabs folded in

Phase 3 of [[Redesign Plan]] (Sonnet 5.5). **Built:** `pages/sources.py` (`SourcesView`) and `pages/browse_host.py` (`BrowseHost`, the switch) for "My sources"; `pages/classic.py` (`ClassicPack`, `ClassicReview`) inside the Classic pack row of Installed; the classic scan in `pages/check.py`; `Window.check_stale()`, `scan_inputs()`, `search_sources()`; 73 Arabic strings; `tests/test_sources_view.py` (15). **Deleted:** `mod_ui.py`, `inspector_ui.py`, the Hub page (`hub_ui.py` is now only `failure_text`), `tests/test_mod_pages.py`; the registry tabs Source Mods, Library and Inspection and the slots `classic`, `inspector`, `hub`. Behaviour changes: pictures of a source's mods are opt-in; the Hub's trust filter is gone; `--inspector` opens Check and `--mods` opens Installed; `graph/build.py` leads "Hub" to `mods.browse`. The engines (`mods.py`, `mod_install.py`, `mod_inspector.py`, `repos/`, `installer/`) are unchanged. Feature note: [[Classic Pack and Sources]].

## 2026-11-14 (redesign, phase 3, step 3, part 1): Mods › Installed, Check and Activity on the new components

Phase 3 of [[Redesign Plan]] (Sonnet 5.5). **Built:** `deadlock_fps/pages/installed.py` (`InstalledPage`, `FilesDialog`, `HistoryDialog`, `BatchReview`, `FoldRow`), `pages/check.py` (`CheckPage`), `pages/activity.py` (`ActivityPage`) replacing `installed_ui.py` (deleted); registry tab titles "Installed", "Check", "Activity" and the order (the temporary tabs last); 71 Arabic strings; components upgraded (`ListRow(lead)`, visible list separators, flat `List`, `List.clear`, `DataTable.fit_height`, `confirm`); `tests/test_installed_pages.py` (30) and the Hub tests left in `tests/test_mod_pages.py` (8); `tests/look_fixture.py`. The engines (`installer/`, `mod_service.py`) are unchanged. Behaviour changes: Repair left the Installed page (it is on Check and Home), the Trust column is gone, a Mod Store mod says *Installed* instead of "Source unavailable", removal and going back use the new confirm Dialog. Feature note: [[Installed Page]].

## 2026-11-14 (redesign, phase 3, step 2): Mods › Browse on the new components

Phase 3 of [[Redesign Plan]] (Sonnet 5.5), second page. **Built:** `deadlock_fps/pages/browse.py` (`BrowsePage`, `InstallReview`) replacing `store_ui.py` (deleted); the registry tab is "Browse" and the Backups page title is "Backups"; components upgraded (`ElidedLabel`, `ModCard`, `Sheet`, `Dialog`, `KeyValue`, `EmptyState`, `breakable`, the tab style); 58 Arabic strings; `scripts/dev/shot_browse.py`; `tests/test_store_browse.py` (51, replaces the 32 of `test_store_ui`). The engines (`store/`, `store_service.py`, `mod_service.py`, `installer/`) are unchanged. Behaviour changes: the mod page is fetched when a card is pressed (no 350 ms wait), pictures are off until *Show pictures*, with no game the Install button is off and a banner offers the link. Feature note: [[Browse Page]].

## 2026-11-14 (redesign, phase 3, step 1): Home on the new components

Phase 3 of [[Redesign Plan]] (Sonnet 5.5), first page. **Built:** `deadlock_fps/pages/home.py` (`HomePage`), `deadlock_fps/game_link.py` (the game-link methods moved out of `legacy/home.py`, which is deleted), `GamePill` in the top bar replaces the old chip (`window.game_pill`, `window.game_linked`), the old hint line and status line are hidden on rebuilt pages (`ui.REBUILT_SLOTS`), `ListRow(tone=...)` and the `DoorIcon`/`RowIcon` styles, `DoorCard` keeps its link at the bottom, a font rule so English text is set in the Latin face first (the Arabic face had doubled the line height), `QMainWindow` takes the token background, `pages` added to the translated sub-packages of `i18n_tool.py`, 50 Arabic strings, `scripts/dev/shot_page.py`. Test patch targets `deadlock_fps.legacy.home.*` became `deadlock_fps.game_link.*`. Feature note: [[Home Page]].

**Verified:** 766 tests (17 new in `tests/test_home.py`) pass except the known Windows symlink error; `i18n_tool.py check` passes; Home looked at in English dark, Arabic light, 940 × 680 and 130 % text; the 130 % test was mutation-checked. `check_vault.py` passes and no file has CRLF. One full run took 531 s instead of about 110 s (the files that matter take 2 to 17 s each; the cause was not investigated, probably machine load). **Not verified:** not seen on the user's display; not run with a real game folder; no screen-reader pass.

## 2026-11-14 (redesign, phase 2): shell, page registry, tokens, base components

Phase 2 of [[Redesign Plan]] (Opus 5.5). **Built:** `deadlock_fps/shell/` — `registry.py` (pages and tabs by name; 9 places; start-up flags as addresses), `tokens.py` + a copy of `tokens.json` (themes, accents, text size; one colour converter), `theme.py` (apply/switch at once, `watch`, tinted and mirrored icons, Windows dark title bar), `style.qss` (template for the new components), `components.py` (all 39 component names of [[04 Components]]). `assets/icons2/` (31 icons from the mock-up, `scripts/dev/export_icons.py`). `ui.py` rewritten as the shell (Sidebar, TopBar, Tabs, slots; `navigate('mods.health')`); the old window methods moved unchanged to `deadlock_fps/shell/base.py/` (home, performance, backups, general, classic). Every `navigate(number)` and `design.PAGES`/`NAV_ICONS` index became a name. `build.py` bundles `tokens.json` and `style.qss`; `i18n_tool.py` also scans `shell/` and `legacy/`. One new string (`إغلاق` → Close). Notes: [[Shell and Page Registry]], [[ADR-015 Pages are addressed by name through one registry]].

**Verified:** 749 tests (23 new in `tests/test_shell.py`; the page-number tests now use addresses) pass except the known Windows symlink error; `i18n_tool.py check` and `check_vault.py` pass; LF everywhere. The window was opened on the Windows platform (temporary data folder, no game) in English and Arabic and photographed; two defects found that way and fixed (old tabs stayed after leaving a page; Arabic tab names were cut). **Not verified:** light theme on the old pages (they stay dark; no button offers it yet), text sizes other than 100 % by eye, a real game folder, a screen reader. **Changed behaviour:** the sidebar has 8 entries instead of 17, the old pages are tabs (Mods: Store, Source Mods, Installed, Compatibility, Downloads, Library, Inspection; Settings: Settings, Update, Manage Sources, Knowledge Graph); the `map` page itself is hidden from the sidebar.

## 2026-11-14 (redesign, phase 1): the new design

Phase 1 of [[Redesign Plan]], design only. **Made:** six design notes ([[01 Principles]] · [[02 Information Architecture]] · [[03 Visual Language]] · [[04 Components]] · [[05 Screens]] · [[06 Handoff to Build]]), a static clickable mock-up of every screen (`docs/design-prototype/`: 9 places, four states each, English and Arabic, dark and light, three accent options, the 940 × 680 minimum), `tokens.json` (39 colours × 2 themes, 51 scale values), a component page, 48 reference pictures, and two dev scripts (`scripts/dev/design_tokens.py`, `scripts/dev/design_shots.py`). The 17 pages become 8 sidebar places with tabs.

**Verified:** 96 contrast pairs pass; the mock-up rendered with Qt WebEngine and 16 views inspected, five defects fixed; `check_vault.py` passes. **Not verified:** the design in Qt widgets, a real display, a screen reader, text sizes other than 100 %. **Changed behaviour of existing code:** none (`deadlock_fps/` untouched). Result and open decisions: [[Handoff - Phase 1 Design (Fable 5.2)]].

## 2026-11-14 (after the stats): simpler store, "repository" becomes "source"

The user asked for the store to be developed, simpler and better looking, and said "repositories" was not understandable. **Built:** every user-visible *repository* is now *source* in English and Arabic (55 strings, scripted, both catalogues kept in step), the Repositories page is **Manage Sources** with a plain explanation card at the top, the Mod Hub is **Source Mods**, the rail has *Mod Manager* (Store, Installed) and *Advanced* groups, the provider-kind column is *Type*. The Mod Store page: a slim status line, one search card, a cleaner list (*Hero / type*), **Install moved to the top of the detail pane**, *installed* marks in the list, plainer first-run and trust wording. Notes: [[Mod Store]], [[Repository Manager]], [[Mod Hub]].

**Verified:** 4 new store UI tests, 5 pinned strings in older tests updated, rendered in English and Arabic (empty, live data, Manage Sources). **Not verified:** the new pages by the user's eyes on a real display. **Changed behaviour of existing code:** `store_ui.py`, `repo_ui.py` (explanation card, placeholder, column), `ui.py` (rail groups, switcher order), `hub_ui.py`/`installed_ui.py`/`graph_ui.py`/`updates.py`/`update_client.py` (wording), `design.py`, `lang_*.py`. Nothing committed.

## 2026-11-14 (after that): stats

The user chose stats. **Built:** `deadlock_fps/stats/` (strict readers, formulas, Steam id spellings, client for the public Deadlock API, disk cache, source with stale fallback), `stats_service.py`, `stats_ui.py` (page index 16, group *Play*: Heroes, Ranks, My stats), 72 Arabic and 4 English strings, `scripts/dev/stats_live_check.py`, `shot_stats.py`, `mutation_stats.py`. Notes: [[Stats]], [[Task - Stats]], [[ADR-014 Statistics are fetched on request and nothing personal is kept]].

**Verified:** 144 new tests (718 in the suite; only the known Windows symlink error and one skip), 45 of 45 mutations caught, a read-only live check of the public endpoints (19 of 19), the page rendered in English and Arabic (found and fixed a hairline rank bar, Arabic sentences flipped by a leading number, percentages on the wrong side in Arabic). **Then, with the user's approval, one real lookup of their own account** (`scripts/dev/stats_player_check.py`): it worked; the account had no ranked data and no matches in 30 days, so My stats got its own period and mode (default All time and All modes) and 4 more tests, 2 more mutations (148 stats tests, 47 mutations, 722 in the suite). **Not verified:** the rank line and the comparison column with real data. **Changed behaviour of existing code:** `ui.py` (nav label, group, hint, stack index 16, `steam_account`), `design.py` (`PAGES`, `NAV_ICONS`), `lang_ar.py`/`lang_en.py`, `scripts/i18n_tool.py`, `tests/test_repos_ui.py` and `tests/test_mod_inspector.py` (counts 16 → 17). Nothing committed.

## 2026-11-14 (then): performance details

The user chose performance. The existing graphics recipe already writes `ConVars`/`SceneSystem` through `Studio`, so the gap was **knowing what it does**. Analysis of all 95 settings it can write against Valve's data (via the reference catalogue, facts only): 55 work, 11 blocked, 13 removed, 7 cheat-only, 9 unverified. **Built:** `perf/` (generated `facts.py`, written `knowledge.py`, `explain.py`), `Settings.skip`, `perf_ui.PerfDialog`, a button on the Graphics page, 138 translations, `scripts/dev/perf_facts.py`, `shot_perf.py`, `mutation_perf.py`; the i18n checker now reads subpackages. Notes: [[Performance Details]], [[Task - Performance Details]], [[ADR-013 Facts come from Valve's data and the explanations are written here]].

**Verified:** 37 new tests (574 in the suite; only the known Windows symlink error and one skip), 19 of 19 mutations caught, existing graphics tests unchanged, rendered in English and Arabic. **Not verified:** anything in the real game; the statuses are Valve's data. **Changed behaviour of existing code:** `settings.py` (a defaulted field, `PROTECTED_SKIP`, one block in `values()`), `ui.py` (a button and four small hooks), `scripts/i18n_tool.py`. Default behaviour is unchanged for anyone who does not open the window. Nothing committed.

## 2026-11-14 (last): the first real download

With the user's explicit OK, one real file (mod 711387, `pak52_dir_3154a.zip`, 7 493 240 bytes) was downloaded through the new install path into a throwaway game folder. **It found a bug the tests had missed**: a version number built from the upload date had a leading zero (`2026.08.29`) and was refused by the version rules. Fixed in `store/install.py` (`2026.8.29`), regression test over every day of a leap year (33 engine tests now, 537 in the suite). The second attempt: download, MD5, inspection, install, analysis and uninstall all clean (details in [[Task - Mod Store install]]). New script `scripts/dev/real_install_check.py`. The throwaway folder was deleted. A real Deadlock folder was never touched.

## 2026-11-14 (later still): install from the Mod Store

The user chose "install from the store" as the next step and then asked for simpler explanations and for everything to be written in the vault. **Built:** the Install button of the store page, through the existing engine: `store/install.py` (adapter), zip discovery, an MD5 check and a final-host check in the engine, `ModService.prepare_store`, store-aware update status and graph label, new preview line, 10 Arabic strings. Notes: [[Task - Mod Store install]] (also linked from [[Mod Store]] and [[Installation Engine]]), [[Security Model]] and [[Known Issues]] updated.

**Verified:** 43 new tests (536 in the suite; only the known Windows symlink error and one skip); 14 new mutations, all caught (29 of 29 with the engine's); 199 older installer, repository, graph and page tests unchanged and green; the page rendered with live data in English and Arabic.

**Changed behaviour of existing code:** `repos/model.py` (three optional fields), `installer/engine.py`, `archive.py`, `vpk.py`, `updates.py`, `graph/build.py`, `hub_ui.py` (one preview line), `mod_service.py`, `store_ui.py`, `ui.py` (the page receives the ModService), `lang_ar.py` (10 added, 1 obsolete removed). No existing test had to change.

**Not done / not verified:** a real download and a real game folder (a download needs the user's OK); `.rar`/`.7z`; update checks for store mods; the performance overlay and stats from [[Reference App Analysis]]; nothing committed.

## 2026-11-14 (later): Mod Store

After the reverse engineering in [[Reference App Analysis]] the user chose to start with the store. **Built:** `deadlock_fps/store/` (GameBanana client, SQLite + FTS5 catalogue, resumable crawl and incremental refresh), `store_service.py`, `store_ui.py` (page index 15, first in the Mod Manager group), 52 Arabic and 4 English strings, `scripts/dev/shot_store.py`, `mutation_store.py`, `store_live_check.py`. Decisions: [[ADR-011 The store is a local catalogue, not a repository provider]], [[ADR-012 Reimplement from public interfaces and copy nothing from the GPL reference]]. Notes: [[Mod Store]], [[Task - Mod Store engine]], [[Task - Mod Store page]].

**Verified:** 100 new tests (493 in the suite; only the known Windows symlink error and one skip remain); 15 of 15 mutations caught; a full live crawl (123 requests, 6 115 listings, 0 skipped, 137 s) and a 1-request refresh; the page rendered offscreen in English and Arabic with live data and real screenshots, which found and fixed a clipped column, elided names, empty boxes and a mixed-direction line.

**Changed behaviour of existing code:** `ui.py` (nav label, group order, switcher button, hint, stack index 15, `StoreService`), `design.py` (`PAGES`, `NAV_ICONS`), `lang_ar.py`/`lang_en.py`, `scripts/i18n_tool.py` (`store_ui.py`, `store_service.py` are English-source files), `tests/test_repos_ui.py` and `tests/test_mod_inspector.py` (counts 15 → 16).

**Not done / not verified:** installing from the store; Sounds, WIPs, Collections; the performance overlay and the stats module of the reference app ([[Reference App Analysis]]); a real display; nothing committed.

## 2026-11-14: AI memory written into the vault

The user said they did not like the current result (no reason given), asked to open a new chat, and asked for everything known about the project to be moved into the Obsidian vault as complete project information and as memory for the AI. Done: `vault/AI Memory/` ([[00 Start Here]], [[User Brief - Original Requirements]] copied verbatim by script, [[User Profile and Working Rules]], [[Session History]], [[Open Items and Next Steps]], [[Environment and Pitfalls]], [[How The Code Works]], [[Verification Cookbook]], [[Research Findings]], [[Git and Release State]]); the raw transcript and a readable conversation under `AI Memory/Raw/` (local, git-ignored); a root `CLAUDE.md` that sends any session to the vault; the dev scripts saved to `scripts/dev/`; the graph skips `type: raw` notes. The user had opened the project root as an Obsidian vault, so Obsidian ignore filters and graph colours were set for it. No product code changed except the graph skipping raw notes.

## 2026-11-14: Version 4.0.0 (Milestones 3 to 6, part of 7)

**Researched** the mod folder facts the first milestone had left open ([[ADR-008 Mod folder and pak naming need verification]]): `game/citadel/addons`, `pakNN_dir.vpk`, lowest number wins, `Game "citadel/addons"` above `Game "citadel"`, and Steam restoring `gameinfo.gi`.

**Installer.** `Studio.enable_addons()` and `kv.add_addons_path()` ([[ADR-007 The installer must go through Studio]]); `Transport.download()` streaming; the `installer/` package ([[Installation Engine]], [[ADR-009 Installation is a journaled set of moves]]): hardened archive and VPK inspection, a journaled transaction with rollback and crash recovery, slot allocation, dependency, conflict and overlap analysis, uninstall, disable, restore, update detection, a health check.

**Pages.** `ModService`, then [[Mod Hub]], [[Installed Mods]], [[Compatibility and Downloads]] and the [[Knowledge Graph]] (page indexes 10 to 14; the rail now has a Mod Manager group). Translations for every new string in both languages.

**Graph.** A typed graph derived from the catalogues, the installed records and this vault; grid-accelerated layout; an interactive canvas ([[ADR-010 The graph is derived from real data and drawn with QPainter]]). Thirteen task notes make "Feature is implemented by Task" a real relation.

**Release.** `__version__` 4.0.0, CI release job and README links no longer pin 3.5.5, packaged `vault/`, `docs/RELEASE_v4.0.0.md`, `docs/MOD_MANAGER.md`. **Nothing was published**: no tag, release, push or commit was made.

**Verified:** 393 tests (235 added since the baseline of 158); eight installer safety checks mutation-tested, all caught; a real streaming download through GitHub's redirect; every new page rendered offscreen in English and Arabic and inspected. **Bugs the tests and renders found and fixed:** a failed download deleting a pre-existing file; archive names with `//` or `./` passing a `pathlib` check; re-enabling a mod could pick an occupied slot; the Hub overwrote its own feedback message; clipped table columns; an overlapping detail label; the rail overflowing.

**Changed behaviour of existing code:** `core.py` (`enable_addons`, `plan`, `plan_mods`, `apply(addons=…)`), `kv.py`, `repos/transport.py`, `motion.py` (rail entry height 42 → 36), `ui.py` (navigation, hints, stack, close guard), `design.py`, `lang_*.py`, `scripts/i18n_tool.py`, `scripts/check_vault.py`, `build.py`; tests for navigation count and minimum-size reachability.

**Not done / not verified:** a real game install with real mods; real display; multi-file VPKs; [[Collections]]; a real native repository; Milestone 7 and 8 remainders. See [[Roadmap]] and [[Known Issues]].

## 2026-11-14 — Milestones 1 and 2

**Audit.** Read `core.py`, `settings.py`, `mods.py`, `mod_install.py`, `mod_inspector.py`, `installation.py`, `updates.py`, `update_client.py`, `detection.py`, `i18n.py`, the navigation in `ui.py` and the design helpers. Baseline: 158 tests, 1 environmental failure. Findings in [[Technical Debt]]; notably the `plan_mods([])` hazard that shapes [[ADR-007 The installer must go through Studio]].

**Vault.** Existing Obsidian vaults were found and left alone; `vault/` created in the repository ([[ADR-006 Vault lives in the repository]]).

**Repository engine** (`deadlock_fps/repos/`, ~2 000 lines, no new dependency): errors, versions and ranges, URL safety and canonical identity, immutable model, specification validator, pinned-address HTTPS transport, provider contract with GitHub, GitLab and custom-HTTPS providers, bundled trust registry, atomic store, manager, search, game-fit. Decisions: [[ADR-002 Repository engine is a Qt-free package]], [[ADR-003 Trust comes from a bundled registry]], [[ADR-004 Translate only VPK release assets]], [[ADR-005 Standard-library HTTP with a pinned connection]].

**Interface.** `repo_ui.py` and stack index 9 (**Repositories**, in the rail after Mods and in the Mods page switcher): add, import, export, refresh one/all, enable/disable, remove, details, cross-repository search. English and Arabic catalogues completed (`i18n_tool.py check` green).

**Documentation.** `docs/REPOSITORY_SPEC.md`, runnable examples, tests that tie them to the code; this vault, with `scripts/check_vault.py` and `tests/test_vault.py` guarding its structure; a README row and link.

**Verified:** 104 new tests (100 for the repository platform, 4 for the vault checker) pass, 262 in the whole suite with only the pre-existing Windows symlink error and one skip; six security checks mutation-tested; real transport exercised against github.com and gitlab.com; page rendered offscreen in English and Arabic. An RTL-only selection defect was found that way and fixed.

**Changed behaviour of existing code:** `design.py` (page table + icon list), `ui.py` (navigation, hint, stack), `lang_en.py`/`lang_ar.py` (new strings), `scripts/i18n_tool.py` (treats `repo_ui.py` as an English-source file), `tests/test_mod_inspector.py` (navigation count 9 → 10).

**Not done / not verified:** installation of anything from a repository; real display; a real native repository; Milestones 3–8. See [[Roadmap]] and [[Known Issues]].

## 2026-11-13 — baseline
Commit `c6d020f`, v3.5.5: English and Arabic interface, regrouped navigation, smart game detection ([[Codebase Structure]]).
