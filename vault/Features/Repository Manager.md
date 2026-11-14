---
title: Repository Manager
type: feature
status: IMPLEMENTED
tags: [feature, repositories, module]
updated: 2026-11-14
code: [deadlock_fps/repos/manager.py, deadlock_fps/repos/store.py, deadlock_fps/pages/source_list.py]
tests: [tests/test_repos_manager.py, tests/test_repos_ui.py]
---

# Repository Manager

**Names in the app (2026-11-14):** the user found "Repositories" incomprehensible, so every user-visible "repository" became **"source"**, the Repositories page became **Manage Sources** (Arabic: إدارة المصادر), the Mod Hub became **Source Mods** (مودات المصادر), and the rail now has two groups: *Mod Manager* (Mod Store, Installed Mods) and *Advanced* (Source Mods, Manage Sources, Compatibility, Downloads, Mods). Code, notes and the specification keep the word *repository*; only what the user reads changed. Manage Sources starts with a plain explanation: a source is an extra place that publishes mods, usually a GitHub page of an author; the Mod Store already covers GameBanana, so most people never need it.

The user-facing core of the platform: **add any repository by URL, see what it offers, keep it fresh, search across all of them.** Implemented as an engine (`RepositoryManager`) and a page (**Repositories**, stack index 9, in the rail between Mods and Servers).

## What works (all covered by automated tests)

| Capability | Notes |
|---|---|
| Add by URL | GitHub, GitLab and custom HTTPS are auto-detected; a self-hosted GitLab is chosen explicitly. Nothing is fetched on add. Bad addresses are refused before anything is stored. |
| De-duplication | by canonical identity: `github:owner/repo` is the same however the URL is written (`.git`, case, `/releases`). |
| Refresh one / all | network on a worker thread; failures become a **status**, never an exception; the last good catalogue is kept and stays searchable ("Unreachable… showing saved catalogue"). Conditional requests (`ETag`/`304`). |
| Enable / disable | disabled repositories are excluded from search and from refresh-all. |
| Remove | confirmation dialog; deletes cached state/index. (Installed mods are not touched — there is no installer yet.) |
| Status & metadata | compatibility class, reason, last sync, last attempt, mod count, parse warnings, trust label with explanation. |
| Import / export | import an index file (becomes a local repository) or a shareable list of URLs; export your list. Imports never fetch and every imported address is `UNVERIFIED`. |
| Search | across enabled repositories, from saved catalogues (works offline). See [[Repository Search]]. |
| Persistence | atomic JSON files; damaged files are survived and reported. |

## What it deliberately does not do
* **Install.** The page has no Install button; it says so. See [[Installation Engine]].
* Auto-refresh in the background. There is no timer and no hidden network activity (a requirement of the [[Security Model]]).

## Verification evidence
* 29 manager tests + 16 page tests, scripted transport (no network).
* Live runs of the real transport (2026-11-14): `github.com/exelight7/deadlock-fps-` → **Needs manual mapping** (26 app ZIPs, none listed as mods) and trust OFFICIAL; a non-existent GitHub repo and a non-existent GitLab project → unsupported with an explanation; `gitlab.com/gitlab-org/gitlab-runner` → unsupported; `https://127.0.0.1/…` refused.
* Rendered offscreen in English (LTR) and Arabic (RTL) and inspected; an RTL-only defect (`QTableWidget.selectRow` selects nothing) was found this way, fixed and given a regression test.
* **Not done:** run on a real display; run against a real *native* repository (none exists yet); long-run behaviour with hundreds of repositories.

Related: [[Repository Providers]] · [[Manifest Specification]] · [[Trust System]] · [[Architecture Overview]] · [[ADR-002 Repository engine is a Qt-free package]]
