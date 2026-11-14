---
title: Compatibility and Downloads
type: feature
status: IMPLEMENTED
tags: [feature, health]
updated: 2026-11-14
code: [deadlock_fps/pages/check.py, deadlock_fps/pages/activity.py, deadlock_fps/installer/engine.py]
tests: [tests/test_installed_pages.py, tests/test_installer_engine.py]
---

# Compatibility and Downloads pages

> **Rebuilt 2026-11-14 (Phase 3, step 3):** these two pages are now **Mods › Check** (`pages/check.py`) and **Mods › Activity** (`pages/activity.py`) on the redesign components; see [[Installed Page]]. The text below describes what they report, which is unchanged; `installed_ui.py` is gone.

**Compatibility** (index 12) is a read-only health check over what the [[Installation Engine]] installed and the whole addons folder:

| Finding | Level | Meaning |
|---|---|---|
| inactive | problem | `gameinfo.gi` does not list `citadel/addons` (Steam restored it); **Repair** re-registers it through `Studio` |
| missing / modified / damaged | problem | an installed file is gone, differs from its recorded hash, or is no longer a valid VPK |
| overlap | warning | two mods (installed or foreign) provide the same files; the lower `pakNN` number wins, and the page says which |
| dependency | warning | a required mod was removed or disabled |
| unmanaged / unreadable | note / warning | files Toolbox did not install |

A second table compares each installed mod's newest catalogue version with the game build.

**Downloads** (index 13) shows the current transfer (progress, cancel) and the history of every install, update, removal, disable, enable and restore, newest first, from the engine's log.

Both pages say plainly when no game is linked. Evidence: tests plant a modified file and a Steam reset and watch the findings appear, then repair clear the right one.

Related: [[Installed Mods]] · [[Security Model]]
