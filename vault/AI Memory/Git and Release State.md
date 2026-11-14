---
title: Git and Release State
type: guide
tags: [ai-memory, git]
updated: 2026-11-15
---

# Git and release state (as of the end of the session)

> **2026-11-15: 4.0.0 released at the user's request.** The 4.0.0 work was committed on `v3.5.5`, merged into `main` with the message `Release Deadlock Toolbox v4.0.0`, and pushed; the CI release job builds and publishes the Windows and Linux packages. Before it: 845 tests passed (2 skipped), i18n and vault checks passed. The text below describes the state before that release.

* Repository: `https://github.com/exelight7/deadlock-fps-` (`origin`). Working branch **`v3.5.5`**; main branch is `main`. `HEAD` is `c6d020f` "3.5.5: English and Arabic interface, regrouped navigation, smart game detection" (previous: `4ae2fb0 wip: navigation restructure…`, `4cc4004 Release Deadlock Toolbox v3.0.0`).
* **Nothing from the 4.0.0 work is committed, pushed, tagged or released.** The user was asked once whether to commit and did not answer; do not commit unless they ask.
* If asked to commit: end the commit message with the attribution line the harness supplies (at the time: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`); PR bodies end with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`. Run `python -m unittest discover -s tests` (offscreen), `python scripts/i18n_tool.py check`, `python scripts/check_vault.py` first. A branch name like `v4.0.0` would suit; branching is not committing.
* **Releasing:** the CI release job runs only on a push to `main` whose commit message contains `Release Deadlock Toolbox v4.0.0`. Never write that phrase unless the user explicitly asks to release. README download links now use `releases/latest/download/…`, so they work before and after a release.

## Modified tracked files (15)
`.github/workflows/build.yml` (v3.5.5 → v4.0.0), `README.md`, `build.py` (adds `vault`), `deadlock_fps/__init__.py` (4.0.0), `core.py`, `design.py`, `kv.py`, `lang_ar.py`, `lang_en.py`, `motion.py` (rail entry height), `ui.py`, `docs/UPDATE_CENTER.md` (header), `scripts/i18n_tool.py` (English-file list), `tests/test_mod_inspector.py` (nav count), `tests/test_updates.py` (rail reachability).

## New (untracked) groups
* `deadlock_fps/repos/`, `deadlock_fps/installer/`, `deadlock_fps/graph/`, and `repo_ui.py`, `hub_ui.py`, `graph_ui.py`, `mod_service.py`, `ui_common.py`, `vault.py`, and for the Mod Store `deadlock_fps/store/`, `store_service.py` (the page is `pages/browse.py`, in `pages/` with Home).
* `assets/trust/registry.json`; `docs/REPOSITORY_SPEC.md`, `docs/MOD_MANAGER.md`, `docs/RELEASE_v4.0.0.md`, `docs/repository-example/`.
* `tests/`: `repo_fixtures.py`, `installer_fixtures.py`, `installed_fixture.py`, and `test_repos_*`, `test_studio_addons`, `test_installer_*`, `test_mod_pages`, `test_graph*`, `test_vault`, `store_fixtures.py`, `test_store_*`.
* `scripts/check_vault.py`, `scripts/dev/` (screenshot, mutation and transcript helpers), `CLAUDE.md`.
* `vault/` (this knowledge base). `vault/AI Memory/Raw/` and the root `.obsidian/` are **git-ignored** on purpose: the raw transcript is 13 MB and personal; Obsidian's UI state is per user.

## Privacy rule for anything that gets committed
The curated notes avoid the user's name, email and home path (they use `<home>`). The raw transcript and the readable conversation contain real paths and the user's own words: keep them out of git (they are ignored). Do not add them to a commit or a PR.

Related: [[00 Start Here]] · [[Verification Cookbook]] · [[Implementation Log]]
