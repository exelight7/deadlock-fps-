# Deadlock Toolbox: instructions for any AI session

**Read `vault/AI Memory/00 Start Here.md` first.** It is the project's memory: the user's original requirements, what has been done, what was not, how the code works, the traps on this Windows machine, and what to ask the user first. The rest of `vault/` is an Obsidian vault documenting the architecture, decisions, features and tests. The codebase is the source of truth; the vault explains it.

## Where things stand
The Mod Store (GameBanana catalogue, search, and installing `.zip`/`.vpk` through the existing installer) is built and tested; one real download (with the user's OK) installed and removed cleanly in a throwaway game folder; it was never run on a real game. The Stats page (hero meta, rank spread, your own record from the public Deadlock API) is built and tested; public numbers were checked live, and "My stats" ran once with the user's own account (approved; it had no ranked or recent matches). A lookup sends a Steam account number: ask first. Next candidates: a run on the user's real game folder (ask first), more real mods (each download needs the user's OK), a lookup of an account with ranked matches (ask first), a hero detail page. Performance details (an explanation window with Valve-data statuses and a way to leave settings out) is built: `vault/Features/Performance Details.md`. See `vault/Features/Mod Store.md`, `vault/Features/Stats.md` and `vault/AI Memory/Reference App Analysis.md`. The reference app is GPL-3.0 and this project is MIT: **copy nothing from it** (`vault/Decisions/ADR-012 ...`).

## Interface redesign: finished
The redesign (design, infrastructure, build) is done. **Every page is on the new components** (`deadlock_fps/shell/`, `deadlock_fps/pages/`); the old system (`design.py`, `theme.py`, `motion.py`, `legacy/`) is deleted. Pages are addressed by name (`navigate('settings.update')`, `vault/Architecture/Shell and Page Registry.md`); what each page is: `vault/Features/Rebuilt Pages - Performance to Map.md` and the notes it links. Light theme, text size, less motion and mod pictures are in Settings. **Not done / not verified:** it has only been seen in offscreen pictures (never on the user's display), never run on a real game folder, mod pictures on cards, and the mutation scripts were not re-run (`vault/Quality/Known Issues.md`). Phase 3 chats: read "Progress" in `vault/AI Memory/Handoff - Phase 3 Build (Sonnet 5.5).md`.

## The user
* Writes Arabic; **reply in Arabic** (keep code, identifiers, commit messages and product strings in English where the file is English).
* They once said they did not like the first result and never said why; they then chose the work order themselves (store first, then installing from it). The question is still open: ask it again only when it blocks a decision.
* **Plain words in chat.** They asked (2026-11-14) for simpler explanations: short Arabic, one idea per line, detail goes into the vault.

## Hard rules
* **Never commit, push, tag, release or open a PR unless asked.** Never write the phrase `Release Deadlock Toolbox v4.0.0` in a commit message (it triggers the release job).
* Never touch the user's other Obsidian vaults or Obsidian's global config. Never put personal details (name, email, home path) in the repo, the vault or outside requests.
* Never claim something is implemented or verified without evidence. Statuses follow `vault/Guide/Status Legend.md`.
* Do not weaken security to make something easier. Do not leave buttons that do nothing.
* Update the vault whenever code changes significantly; `python scripts/check_vault.py` must pass.

## Practicalities (Windows)
* Python is `.venv/Scripts/python.exe`. Tests: `QT_QPA_PLATFORM=offscreen .venv/Scripts/python.exe -m unittest discover -s tests` (one known Windows-symlink error). Also `scripts/i18n_tool.py check` and `scripts/check_vault.py`.
* The repo is **LF**: write files with `write_bytes(text.encode('utf-8'))`, never `write_text` (CRLF). Put scripts containing backslashes in files, not Bash heredocs.
* More in `vault/AI Memory/Environment and Pitfalls.md` and `vault/AI Memory/Verification Cookbook.md`.
