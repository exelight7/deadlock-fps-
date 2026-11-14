---
title: Research Findings
type: guide
tags: [ai-memory, research]
updated: 2026-11-14
---

# Research findings (external facts that shaped decisions)

Everything here was learned during the session; sources are third-party unless stated. Re-verify before relying on it for something irreversible, because the game changes.

## How Deadlock mods work (web search, 2026-11-14)
Query: "Deadlock game mods citadel/addons pak01_dir.vpk gameinfo.gi SearchPaths how to install vpk". Findings, as decided in [[ADR-008 Mod folder and pak naming need verification]]:
* Mods are `.vpk` files in `Deadlock/game/citadel/addons/`; `gameinfo.gi` `SearchPaths` needs `Game citadel/addons` above `Game citadel` (others list it before `Mod citadel`, `Write citadel`, `Game citadel`, `Write core`, `Mod core`, `Game core`).
* Names must be `pakXX_dir.vpk`; **the lowest number wins** on overlap.
* Steam updates and *Verify integrity* restore Valve's `gameinfo.gi`; a malformed edit breaks launching.
* The Deadlock Mod Manager (a community tool) automates the edit (only after the game is first launched in modded mode) and can import VPKs already in `addons`.
* One site describes an alternative `AddonRoot`/`AddonConfig` mechanism (an alternative, not an addition).
* Valve's wiki had no Deadlock install instructions in the results (a page `Gameinfo.gi/Deadlock` exists on developer.valvesoftware.com but was **not read**).

Sources: [mein-mmo.de](https://mein-mmo.de/en/deadlock-mods-skins-installieren,1526972) · [esports.net guide](https://www.esports.net/wiki/guides/deadlock-mod-install) · [Deadlock Mod Manager docs](https://docs.deadlockmods.app/using-mod-manager/getting-started) · [deadlockmodding.pages.dev](https://deadlockmodding.pages.dev/installing-mods) · [Valve Developer Community: Gameinfo.gi/Deadlock](https://developer.valvesoftware.com/wiki/Gameinfo.gi/Deadlock) (listed, unread).

## Facts from the project itself
* `assets/reference/gameinfo.gi` (from the community, shipped in the repo) already contains `Game "citadel/addons"`; the app's four reference mods use `citadel/fps_studio` instead, with `pak01/02/03/26_dir.vpk`.
* Steam app id of Deadlock: `1422450` (`detection.py`). The game process names: `deadlock`, `citadel`, `project8`.
* `docs/` user guides are Arabic. The update centre checks `exelight7/deadlock-fps-` releases (`latest`), downloads `DeadlockToolbox-windows-x64.zip` / `-linux-x64.zip` and `SHA256SUMS.txt`.
* CI (`.github/workflows/build.yml`) runs on every push to `main`, every pull request and manual runs, on `ubuntu-22.04` and `windows-latest`: installs `requirements.txt` + PyInstaller 6.20.0, runs `scripts/ci_tests.py` (the whole unittest suite, offscreen), a Windows firewall smoke test, builds with `build.py`, starts the packaged exe with `--crosshair/--updates/--inspector/--mods`, and uploads zips. The **release** job runs only on a push to `main` whose commit message contains `Release Deadlock Toolbox v4.0.0`, then creates/edits the GitHub release `v4.0.0` from `docs/RELEASE_v4.0.0.md`. **Untested risk:** none of the new tests or the `--add-data vault:vault` packaging line has run on Linux CI or the Windows PyInstaller build yet.

## Live checks performed (2026-11-14, real network)
* `github.com/exelight7/deadlock-fps-`: 26 ZIP release assets (app packages), no `deadlock-repo.json`: classified **MANUAL**, trust OFFICIAL (from the shipped registry); never listed as mods.
* A non-existent GitHub repo and a non-existent GitLab project: UNSUPPORTED with an explanation. `gitlab.com/gitlab-org/gitlab-runner`: UNSUPPORTED (no `.vpk` links). `example.com/deadlock-repo.json`: 404. `https://127.0.0.1/…`: refused.
* Streaming download of `…/releases/latest/download/SHA256SUMS.txt` (194 bytes) through a redirect to `release-assets.githubusercontent.com`: size, hash, progress, size cap, size mismatch and 404 all behaved; no partial files.

## What was **not** researched or checked
* Real community mod repositories or real mods: none were found that publish the project's manifest format, and no real mod VPKs were downloaded or installed.
* Whether real mods are multi-file VPKs (`pakNN_dir.vpk` plus `pakNN_000.vpk` …): assumed to exist; refused with a reason.
* Behaviour on Linux; the packaged (PyInstaller) build; real GitLab releases with `.vpk` links.

Related: [[00 Start Here]] · [[Security Model]] · [[Repository Providers]]
