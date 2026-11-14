---
title: ADR-008 Mod folder and pak naming need verification
type: decision
status: IMPLEMENTED
tags: [decision, installer]
updated: 2026-11-14
affects: [Installation Engine, Installed Mods, Manifest Specification]
code: [deadlock_fps/installer/records.py, deadlock_fps/installer/engine.py]
tests: [tests/test_installer_engine.py]
---

# ADR-008 · Mods go to `game/citadel/addons` as `pakNN_dir.vpk`

**Open question from Milestone 2.** The existing installer used a private folder (`citadel/fps_studio`); the wider convention was unverified.

**Findings (web search, 2026-11-14, third-party guides and forum posts; Valve's wiki has nothing Deadlock-specific).**
* Mods are VPKs placed in `Deadlock/game/citadel/addons`, which needs `Game citadel/addons` in `gameinfo.gi`'s `SearchPaths`, **above** the existing `Game citadel` line.
* Installed addons must be named `pakXX_dir.vpk`; several can coexist as `pak01_dir.vpk`, `pak02_dir.vpk`, …
* Load order: **the lowest number wins** when two mods provide the same file.
* Steam updates and *Verify integrity* restore Valve's `gameinfo.gi`, removing the line; users must re-apply it. A malformed edit makes the game fail to launch.
* Other mod managers automate the same edit and can import VPKs from the folder.
* One site describes an alternative using `AddonRoot` / `AddonConfig` entries; treated as an alternative method, not an addition.
* The bundled `assets/reference/gameinfo.gi` (from the community) also lists `Game "citadel/addons"`.

**Decision (implemented).** Repository mods use `addons/` so they coexist with other managers' files. The four built-in reference mods keep `fps_studio`. Pak numbers are allocated lowest-free (skipping every `pakNN_dir.vpk` already present, whoever owns it), reused on update, reserved while a mod is disabled, and never taken from the package. Overlaps are reported with which side wins. `gameinfo.gi` goes through `Studio` ([[ADR-007 The installer must go through Studio]]).

**Still unverified:** behaviour on a real game folder with real mods; multi-file VPKs (`_dir` plus numbered data files) are refused with an explicit reason rather than guessed at.

**Spec impact:** none; the manifest leaves destination and slot to the application ([[Manifest Specification]]).

Affects [[Installation Engine]].
