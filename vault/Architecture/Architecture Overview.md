---
title: Architecture Overview
type: architecture
tags: [architecture, module]
updated: 2026-11-14
code: [main.py, deadlock_fps/ui.py, deadlock_fps/core.py, deadlock_fps/repos/__init__.py, deadlock_fps/installer/__init__.py, deadlock_fps/graph/__init__.py]
---

# Architecture overview

**Deadlock Toolbox** 4.0.0 (MIT) is a Windows/Linux desktop app: **Python 3.12 + PySide6 6.11.2 + psutil 7.2.2**, packaged with PyInstaller (`build.py`). UI strings are written in Arabic in most older modules and in English in the newer ones, and pass through `tr()` catalogues in both directions ([[Codebase Structure]]).

## Layers

```
 Pages (PySide6)       ui.Window ─ stack of 15 pages addressed by index
   0 Home · 1 Performance · 2 Mods(library) · 3 Recovery · 4 Servers · 5 Crosshair · 6 Updates · 7 Inspection · 8 Settings
   9 Repositories · 10 Mod Hub · 11 Installed Mods · 12 Compatibility · 13 Downloads · 14 Graph · 15 Mod Store
        │  design.py / theme.py / motion.py / ui_common.py      (see [[Design System]])
        ▼
 ModService (Qt)       one object: repository manager + one Installer per game folder + worker jobs; pages call it, never the engines directly
        ▼
 Engines (Qt-free)     repos/      catalogue: spec · providers · transport · trust · store · manager · search
                       installer/  install: archive · vpk · records · engine · updates
                       graph/      model · build · layout        vault.py (note reader)
        ▼
 Legacy core           core.Studio (gameinfo.gi, video.txt, reference mods, now also citadel/addons), settings, mods, servers, firewall, updates
```

* The engines import no Qt and no widgets ([[ADR-002 Repository engine is a Qt-free package]]); each takes an injected transport, so tests script exact server behaviour. The pages are thin.
* Game files are changed **only** by `core.Studio` (graphics, `gameinfo.gi`, the reference mods) and by the [[Installation Engine]] (mod files in `addons`, as journaled moves). `Studio` registers the `citadel/addons` search path for the installer ([[ADR-007 The installer must go through Studio]]).
* Networking: Qt Network in the old update client; standard-library HTTPS with a pinned connection in the engines ([[ADR-005 Standard-library HTTP with a pinned connection]]).
* The Knowledge Graph reads the catalogues, the installed records and this vault ([[ADR-010 The graph is derived from real data and drawn with QPainter]]).

## Data on disk

| What | Where |
|---|---|
| Repository list, sync state, cached catalogues | Qt `AppDataLocation` (e.g. `%APPDATA%/exelight7/DeadlockToolbox`) `/repositories/` |
| Installed mods, history, backups, trash, disabled files, journal | `<game>/.deadlock-fps-studio/mods/` |
| Graphics/`gameinfo.gi` originals and history | `<game>/.deadlock-fps-studio/` |
| Update-centre cache | `AppDataLocation/updates/` |
| Mod files in use | `<game>/game/citadel/addons/pakNN_dir.vpk` (repositories) and `fps_studio/` (the four reference mods) |

## Related
[[Codebase Structure]] · [[Dependencies]] · [[Technical Debt]] · [[Security Model]] · [[Mod Lifecycle]]
