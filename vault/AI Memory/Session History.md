---
title: Session History
type: guide
tags: [ai-memory, history]
updated: 2026-11-14
---

# Session history (curated)

One long session, 2026-11-14, titled "Deadlock Mod Manager platform evolution" (CLI session `dbcb763e-4a0a-49b5-8c4a-eee8576f60fc`, model Sonnet 5.5). The user sent **five messages** ([[User Brief - Original Requirements]]). The word-for-word conversation is in `Conversation (readable)` (local only); this note is the curated version: what was asked, what was done, what was found, in order.

## Turn 1: the brief (English). Milestones 1 and 2

**Asked:** evolve the project into a multi-repository mod manager; audit first; Obsidian mandatory; start with the codebase, create the knowledge base, implement the first meaningful milestone.

**Audit findings** ([[Codebase Structure]], [[Technical Debt]]):
* Python 3.12 + PySide6 6.11.2, 216 tracked files, ~8 600 lines of dense `;`-chained code, 158 tests (1 environmental failure: a Windows symlink privilege test).
* Mods were a closed set of four hash-pinned reference VPKs (`settings.MODS`, `mods.HASHES`) installed by `core.Studio` into `citadel/fps_studio`, with `gameinfo.gi` edited through the same class.
* Two hazards found: `Studio.plan_mods([])` strips the `fps_studio` search path; `Studio.baseline()` raises if `gameinfo.gi` was edited by anyone else.
* The UI is a `QStackedWidget` with hard-coded integer page indexes pinned by tests.
* The user's Obsidian vaults on the machine are personal (Arabization); a new vault was created inside the repo instead ([[ADR-006 Vault lives in the repository]]).

**Built:** the Qt-free `deadlock_fps/repos/` engine (errors, versions/ranges, URL safety and canonical identity, immutable model, spec validator, pinned HTTPS transport, GitHub/GitLab/custom-HTTPS providers, trust registry, atomic store, manager, search, game-build fit), the Repositories page (`repo_ui.py`, stack index 9), `docs/REPOSITORY_SPEC.md` with an example, ~100 tests, the vault ([[Repository Manager]], [[Repository Providers]], [[Manifest Specification]], [[Trust System]], ADR-001..006), `scripts/check_vault.py`.

**Found and fixed on the way:** `urllib.request.build_opener` silently adds proxy/http/file/ftp handlers (a hand-built opener fixed it); CRLF written by Python on Windows (whole-file diffs); `QTableWidget.selectRow` selects nothing under RTL; mixed-direction table cells.

**Checked live:** the transport and providers against github.com and gitlab.com. The project's own repo has 26 ZIP release assets, none are mods, so it is classified **MANUAL** and never listed as mods.

**Reply was English.** Result: Milestones 1 and 2 done; the Install button deliberately absent.

## Turn 2: "تكلم معي عربي"
The user asked for Arabic. The previous summary was repeated in Arabic. All later replies are Arabic.

## Turn 3: "continue; this is an upgrade to 4.0.0; make it something big"
**Decision order:** resolve the open folder question first ([[Research Findings]]), then make `Studio` own the `addons` search path ([[ADR-007 The installer must go through Studio]]), then the installer, then the pages, then the graph, then packaging and docs.

**Built** ([[Installation Engine]] and the rest):
* `Studio.enable_addons()` and `kv.add_addons_path()`; Steam resets repaired for mods-only states.
* `Transport.download()` streaming; the `installer/` package: `vpk.py` (streaming VPK validation), `archive.py` (hardened ZIP), `records.py`, `engine.py` (prepare/commit/uninstall/set_enabled/restore_previous/recover/analyze/repair, a write-ahead journal of moves: [[ADR-009 Installation is a journaled set of moves]]), `updates.py`.
* `ModService`, `hub_ui.py`, `installed_ui.py` (Installed, Compatibility, Downloads), `ui_common.py`.
* `graph/` (model, build, layout), `graph_ui.py`, `vault.py`; 13 task notes so "Feature is implemented by Task" is real ([[Knowledge Graph]], [[ADR-010 The graph is derived from real data and drawn with QPainter]]).
* Page indexes 10 to 14; a "Mod Manager" rail group; rail entries shrunk to 36 px; 241 new translations (Arabic and English).
* Version bumped to 4.0.0; CI release job and README links stopped pinning 3.5.5; `build.py` packages `vault/`; `docs/RELEASE_v4.0.0.md`, `docs/MOD_MANAGER.md`.

**Verification** ([[Verification Cookbook]]): tests 158 to 393; 14 deliberately weakened safety checks (6 repository, 8 installer) all caught or shown redundant; a real streaming download through GitHub's redirect; every new page rendered offscreen in English and Arabic.

**Bugs that tests/renders found and were fixed:** a failed download deleted a pre-existing destination file; `//` and `./` in archive names slipped past a `pathlib` check; re-enabling a mod could pick an occupied pak slot; the Hub overwrote its own feedback message; clipped columns; an overlapping label; a rail overflow; startup recovery failure posing as "no game linked".

**Existing tests changed on purpose:** nav count 9 to 15; the minimum-size test now checks the scrolling rail can reach every entry; stack count 10 to 15.

**Reply (Arabic)** listed what was done and the limits; offered to commit (the user did not answer that).

## Turn 4: "لا شغل لي البرنامج بشوف" (run it so I can see)
The app was launched with `.venv/Scripts/python.exe main.py` in the background. It exited with code 0 with no error output, i.e. started and was closed normally. The assistant suggested things to try and warned that there is no real repository with mods to demo the install flow. **It never learned what the user saw.**

## Turn 5: this one
The user said they did not like the current state and would open a new chat. They asked for **everything known about the project to be moved into the Obsidian vault, as complete project information and as memory for the AI**, so nothing is ever forgotten. What was done:
* exported the raw transcript, generated `Conversation (readable)`, and extracted the verbatim requirements;
* wrote the `AI Memory` notes (this folder) and a root `CLAUDE.md` that sends any new session here;
* found that the user had opened the **project root** as an Obsidian vault (registered 2026-11-14), so Obsidian settings were adapted ([[Environment and Pitfalls]]);
* saved the dev scripts to `scripts/dev/`.

## Turn 6 (new chat, 2026-11-14): reverse engineering the reference app
The user opened a new chat, asked for the memory to be read and summarised, then asked to **reverse engineer the community Deadlock Mod Manager (installed app + source) to bring its mod store, performance and stats into their own program**, using the `reverse-engineer-anything` skill. They did **not** answer the question about what they disliked in the current version. Done: read-only analysis with REA (PE certificates, resources, release-exposure audit), source reading and live read-only API checks; result in [[Reference App Analysis]]. Findings that change the plan: the store is GameBanana (6 114 mods, so it needs a local SQLite catalogue, not a repository provider); the installed exe is 2.3.0 but the source is 2.4.0; the reference is GPL-3.0, so nothing may be copied. **No code in the application was changed**; nothing committed.

## Turn 7 (same chat): the store, then installing from it
The user answered "start with the store" and later "install from the store". Built in that order ([[Mod Store]], [[Task - Mod Store install]]). Midway the user wrote (Gulf Arabic) that they did not understand a long technical reply and asked to continue and write everything in the vault: **replies must be short and in plain words; the detail belongs in the vault** ([[User Profile and Working Rules]]). The user then approved one real download (`pak52_dir_3154a.zip`, 7.5 MB). It installed and uninstalled cleanly in a throwaway game folder and exposed one bug (a version number built from a date with a leading zero), now fixed with a regression test. The next choice was performance: [[Performance Details]] (explanations, Valve-data statuses, leave-out). Still unanswered: what they disliked in the first result.

## Turn 9 (same chat): a simpler store and clearer names
The user asked (Gulf Arabic) to develop the existing store, make it simpler and better looking, and said "repositories" was not understandable to them. Done: "repository" became "source" everywhere the user reads, the page is *Manage Sources* with an explanation, the Hub is *Source Mods*, the rail has an *Advanced* group, and the store page was simplified with Install at the top of the detail pane ([[Mod Store]], [[Implementation Log]]). Earlier in the turn the user wrote "شغلي لي بشوف ابو ثاني", which was not understood; the app was started and the question was asked; the answer was the store request above.

## Turn 8 (same chat): stats
The user answered "الإحصائيات". Built [[Stats]]: the hero meta, the rank spread and a personal tab, from the public Deadlock API, written from its OpenAPI description. The privacy rules were decided first ([[ADR-014 Statistics are fetched on request and nothing personal is kept]]): nothing is requested until a button is pressed, the account number is sent only by **Look up**, nothing personal is saved, and my tests never sent a real number. 144 new tests (718 in the suite), 45 of 45 mutations caught, public numbers checked live, page rendered in English and Arabic. The user then approved one real lookup of their own account: it worked, found that the account has no ranked or recent matches (so the page now lets "My stats" choose its own period and mode, default all time), and confirmed that kills, deaths and assists are totals; 148 stats tests and 47 mutations in the end, 722 in the suite ([[Task - Stats]]). Still unanswered: what they disliked in the first result.

Related: [[00 Start Here]] · [[Open Items and Next Steps]] · [[Implementation Log]] · [[Reference App Analysis]]
