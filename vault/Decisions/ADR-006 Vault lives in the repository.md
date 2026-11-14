---
title: ADR-006 Vault lives in the repository
type: decision
status: IMPLEMENTED
tags: [decision, process]
updated: 2026-11-14
affects: [Vault Guide, Knowledge Graph]
---

# ADR-006 · The project vault lives in the repository (`vault/`)

**Context.** The brief asks for an existing suitable vault, else a dedicated one, without modifying unrelated personal notes. Obsidian's registry on this machine lists vaults for Arabization projects (`…/تعريباتي/_Brain`, a game-specific vault) and a skills folder — personal and unrelated.

**Decision.** Create `vault/` in the repo. It versions with the code, can be reviewed in pull requests, can be read by the future in-app [[Knowledge Graph]] with no path configuration, and touches nothing of the user's. Obsidian's global config was **not** modified; the user opens the folder as a vault.

**Consequences.** Notes ship in the source tree (not in the PyInstaller bundle). Per-user Obsidian state is git-ignored; only the graph colour groups are shared.

Affects [[Vault Guide]].
