---
title: ADR-009 Installation is a journaled set of moves
type: decision
status: IMPLEMENTED
tags: [decision, installer, safety]
updated: 2026-11-14
affects: [Installation Engine, Mod Lifecycle, Security Model]
code: [deadlock_fps/installer/engine.py]
tests: [tests/test_installer_engine.py]
---

# ADR-009 · Every change to the game folder is a journaled move that never overwrites

**Requirement.** "Never overwrite files without a recovery strategy"; roll back failed installations; survive crashes.

**Options.** (a) Copy new files over old ones and keep copies of the old ones: needs a correct undo for every partial state, and overwrites live files. (b) A two-phase scheme with a temp directory swap: not possible for a shared folder that other tools also write to. (c) **Express every operation as a list of `(source, destination)` moves, write each into a journal *before* doing it, refuse any move whose destination exists, and undo by replaying the journal backwards.**

**Decision.** (c). Staged files, replaced files and removed files all live on the same volume as the game (inside `.deadlock-fps-studio/mods/`), so each move is an atomic rename. Install = move old out to `backups/<tx>`, move new in. Uninstall = move to `trash/<tx>`. Disable/enable = move to/from `disabled/`. Restore = two sets of moves. Undo is idempotent (a move that did not happen is a no-op), so the same code serves a failed run and the recovery after a crash. If even the undo fails the journal is kept and `recover()` finishes it at the next start.

**Consequences.** Nothing is ever deleted by the engine (backups and trash are pruned, newest kept, only after success). A move across volumes would not be atomic, so the store must stay on the game's volume (it does, by construction). The journal file is the only extra state.

Affects [[Installation Engine]].
