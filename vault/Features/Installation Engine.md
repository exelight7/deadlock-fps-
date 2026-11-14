---
title: Installation Engine
type: feature
status: IMPLEMENTED
tags: [feature, installer, security]
updated: 2026-11-14
code: [deadlock_fps/installer/engine.py, deadlock_fps/installer/archive.py, deadlock_fps/installer/vpk.py, deadlock_fps/installer/records.py, deadlock_fps/installer/errors.py, deadlock_fps/core.py, deadlock_fps/kv.py, deadlock_fps/repos/transport.py]
tests: [tests/test_installer_engine.py, tests/test_installer_inspect.py, tests/test_studio_addons.py]
---

# Installation engine

Qt-free package `deadlock_fps/installer/` that installs, updates, disables, restores and removes mods from repositories into `game/citadel/addons` as `pakNN_dir.vpk` ([[ADR-008 Mod folder and pak naming need verification]]). The pipeline of the [[Mod Lifecycle]] is real:

| Phase | What happens | Guarantee |
|---|---|---|
| `prepare()` Download | streamed to a private temp file with a byte cap and the declared size; mirrors tried in order | the game folder is not touched |
| Verify | the SHA-256 published in the index must match; a mismatch discards the file | no unverified byte is staged silently: no hash ⇒ a warning and a required acknowledgement |
| Inspect | ZIP: every entry name, symlinks, encryption, case collisions, entry count, declared size, compression ratio; VPK: header, directory tree, every entry inside the file | refuses multi-file VPKs with a stated reason; only listed `.vpk` members are extracted, counting real bytes |
| Stage | named `pakNN_dir.vpk` in a private folder; dependencies, declared conflicts and file overlaps computed | overlaps are warnings (lower pak number wins), declared conflicts and missing dependencies are blockers |
| `commit()` Backup + Install | one journaled transaction of *moves*; old files move to `backups/`, never deleted; a move never overwrites | write-ahead journal: a crash or failure is undone, also at the next start (`recover()`) |
| Verify + Commit | size, hash and VPK structure re-checked on the installed files, then `installed.json` is written | success is reported only after this; on failure everything is put back |

Also: close-the-game check, free-space check, stale-plan detection (staged bytes or target slots changed since the preview), a required acknowledgement enforced **by the engine** (not only by the dialog) for UNVERIFIED sources, derived catalogues and missing hashes, uninstall into a recovery `trash/` (last 5 kept), enable/disable by moving files out of the load path, restore of the previous version (last 3 kept, the swap is itself reversible), and a read-only health check (`analyze()`).

`gameinfo.gi` is handled through `core.Studio.enable_addons()` so graphics settings, the four reference mods and Steam resets all keep working ([[ADR-007 The installer must go through Studio]]).

## Additions for store packages (2026-11-14)
Three optional fields let a package without a manifest use the same pipeline. None is part of the published [[Manifest Specification]]: repository authors cannot set them, only the store adapter does.
* `InstallSpec.discover` (zip): install every `.vpk` the archive contains instead of a manifest's list. None is an error, more than 8 is an error, and every other archive check still covers all entries.
* `Package.md5`: when no SHA-256 exists, the MD5 must match or the file is discarded. The plan then says plainly that this detects damage, not tampering (`InstallPlan.md5_verified`), and the acknowledgement is still required.
* `Package.hosts`: the download must end on one of these domains or their subdomains, whatever the redirects did; otherwise it is discarded and the next mirror is tried.
A repository id that starts with `store:` means "installed from the Mod Store": there is no catalogue for it, the update check says so, and the graph labels it MOD STORE. See [[Task - Mod Store install]].

## Evidence
* 76 tests, including fault injection at every stage (a failed move, a corrupted copy, a failing rollback that `recover()` then finishes), a simulated power cut, hostile archives, and tampered staged files.
* Eight safety checks were disabled one at a time to see whether tests notice; all eight are caught (two needed new isolating tests, which found nothing wrong in the code but showed two checks were hiding behind others).
* Bugs found by the tests and fixed: a failed download could delete a pre-existing destination file; `//` and `./` in archive names slipped past a `pathlib`-based check; re-enabling a mod whose slot had been taken could pick the occupied slot again.
* The streaming download was exercised against real GitHub (a redirect to another host, size caps, 404): [[Task - Streaming package download]].
* **Not done:** a run against a real game install with real community mods; real multi-GB packages.

Related: [[Security Model]] · [[Installed Mods]] · [[Mod Hub]] · [[Repository Manager]]
