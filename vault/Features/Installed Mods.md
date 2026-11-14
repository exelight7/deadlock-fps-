---
title: Installed Mods
type: feature
status: IMPLEMENTED
tags: [feature, lifecycle]
updated: 2026-11-14
code: [deadlock_fps/pages/installed.py, deadlock_fps/installer/records.py, deadlock_fps/installer/updates.py, deadlock_fps/mod_service.py]
tests: [tests/test_installed_pages.py, tests/test_installer_engine.py]
---

# Installed mods and updates

> **Rebuilt 2026-11-14 (Phase 3, step 3):** the page is now **Mods › Installed** (`pages/installed.py`), a list of rows with a switch, a status badge, *Update* and a "more" menu instead of a table with a button bar; see [[Installed Page]]. What it does (versions, updates, disable, restore, remove) is unchanged.

Page index 11, in the **Mod Manager** group of the rail and in the page switcher. It draws what the [[Installation Engine]] records in `<game>/.deadlock-fps-studio/mods/installed.json`.

* **Table:** enabled box, name, installed version, available version, source repository, trust label, the `pakNN` files, status (up to date / update / disabled / source unavailable / newer than the repository).
* **Updates:** *Check for updates* refreshes the repositories and compares versions offline against the catalogues. An update is only ever taken from the repository the mod was installed from; the same id elsewhere is a different source. A newest version that declares a build range excluding the installed game is shown but not offered. *Update all* prepares everything, shows one combined review, and acknowledges once.
* **Actions:** update, restore previous version (reversible), remove (files go to a recovery folder after confirmation, with a warning when other mods depend on it), *Files…* (what is on disk, hash, whether it matches), *History…*, open source page, open addons folder, **Repair** (re-registers `citadel/addons` after Steam restores `gameinfo.gi`).
* **Disable is real here:** a disabled mod's files are moved out of `addons`, the only place the game loads them from; its pak numbers stay reserved. The brief's rule "do not pretend a mod can be disabled if the format does not support it" is met because the mechanism is a move, not a flag.
* Files in `addons` that Toolbox did not install are listed and never touched.
* Dependencies and declared conflicts are enforced at install time and at removal; the health check also reports a dependency that disappeared.

Evidence: 18 page tests drive it with real clicks against a throwaway game folder; offscreen renders in English and Arabic were inspected. Not verified on a real display or a real install.

Related: [[Mod Hub]] · [[Compatibility and Downloads]] · [[Existing Mod Library]] · [[Trust System]]
