---
title: 00 Start Here
type: guide
tags: [ai-memory, moc]
updated: 2026-11-14
---

# 00 Start Here: read this first in any new session

> **للمستخدم (بالعربي):** هذا هو مدخل ذاكرة المشروع. أي محادثة جديدة مع الذكاء الاصطناعي تبدأ بقراءة هذه الملاحظة ثم الملاحظات المرتبطة بها، فلا يضيع شيء مما حدث. الملف `CLAUDE.md` في جذر المشروع يوجّه الذكاء الاصطناعي إلى هنا تلقائيًا.

## What this project is
**Deadlock Toolbox**: a Windows/Linux desktop app (Python 3.12 + PySide6, `exelight7/deadlock-fps-` on GitHub, MIT) for the game *Deadlock*: graphics tuning, crosshair designer, Steam server picker, a small built-in mod library, and an update centre. The user asked for it to be evolved into a **serious multi-repository mod manager** (the original brief is in [[User Brief - Original Requirements]]), and then for version **4.0.0** to be "something big". That work is done in the working tree and **nothing has been committed, pushed or released**: see [[Git and Release State]].

## The user, in five lines
* Writes Arabic (Gulf dialect) and English. **Reply in Arabic** unless asked otherwise ([[User Profile and Working Rules]]).
* Wants real, working, verified things; hates fake buttons and over-claiming. Honest statuses matter ([[Status Legend]]).
* Obsidian is mandatory for project knowledge: this vault is it. Their personal vaults elsewhere are off limits.
* Does not want commits, pushes or releases unless they ask.
* **Their last message said they did not like the current result ("ما اعجبني حاليا") and gave no reason.** The first thing to do in the new session is to ask what exactly they disliked; see [[Open Items and Next Steps]] for informed guesses.

## State of the work (2026-11-14, version 4.0.0 in the working tree)
All eight roadmap milestones of the brief were attempted ([[Roadmap]]):

| Area | State | Note |
|---|---|---|
| Multi-repository engine (GitHub, GitLab, custom HTTPS, local import) | implemented, tested, partly checked live | [[Repository Manager]] |
| Open manifest specification | implemented, doc + example kept true by tests | [[Manifest Specification]] |
| Trust labels | implemented; only the project's own repo is labelled | [[Trust System]] |
| Installation engine (journaled, rollback, recovery) | implemented, heavily tested; **never run on a real game install** | [[Installation Engine]] |
| Mod Hub, Installed Mods, Compatibility, Downloads pages | implemented, tested, rendered offscreen | [[Mod Hub]], [[Installed Mods]], [[Compatibility and Downloads]] |
| Interactive Knowledge Graph | implemented, tested | [[Knowledge Graph]] |
| Mod Store (GameBanana catalogue) | engine **verified live** (full crawl); page and **install of `.zip`/`.vpk`** implemented and tested (one real download installed and removed cleanly in a throwaway game folder; never run on a real game) | [[Mod Store]], [[Task - Mod Store install]], [[Reference App Analysis]] |
| Performance Details (the "What does this level change?" window) | implemented and tested; statuses come from Valve's public data, never checked in the game | [[Performance Details]] |
| Stats (hero meta, rank spread, your own record, from the public Deadlock API) | implemented and tested; public numbers checked live; **"My stats" ran once with the user's own account (approved)**, which had no ranked or recent matches | [[Stats]], [[ADR-014 Statistics are fetched on request and nothing personal is kept]] |
| Collections | **not built** | [[Collections]] |
| Manual import of an arbitrary local VPK/ZIP into the new installer | **not built** (only the four reference mods have manual import) | [[Open Items and Next Steps]] |
| Light theme, card grid, named pages, accessibility audit | not done | [[Open Items and Next Steps]] |

766 tests pass except one pre-existing Windows-symlink one ([[Verification Cookbook]]). The app was launched once on the user's machine and exited with code 0; **whether the user saw the window, and what they saw, is unknown**.

## NEXT: the interface redesign (decided 2026-11-14)
The user wants a completely new, coherent interface in three phases with three models: **Fable 5.2 designs, Opus 5.5 (low) builds the infrastructure, Sonnet 5.5 does the rest**. Plan and ready-to-paste prompts: [[Redesign Plan]], [[Handoff - Phase 1 Design (Fable 5.2)]], [[Handoff - Phase 2 Infrastructure (Opus 5.5)]], [[Handoff - Phase 3 Build (Sonnet 5.5)]]. Each model ends with a fixed line so the user knows to open the next chat. **If you are a new session, check which phase's Result is empty and do only that phase's job.**

**Phase 1 (design) is done (2026-11-14):** the design is in `vault/Design/New Design/` ([[01 Principles]] · [[02 Information Architecture]] · [[03 Visual Language]] · [[04 Components]] · [[05 Screens]] · [[06 Handoff to Build]]), the clickable mock-up in `docs/design-prototype/index.html`. It is a browser mock-up; no application code changed. Six decisions wait for the user, each with a default ([[Handoff - Phase 1 Design (Fable 5.2)]]).

**Phase 2 (infrastructure) is done (2026-11-14):** pages by name through one registry, the new shell, tokens and theme, the 39 base components; the old pages work inside it as tabs ([[Shell and Page Registry]]). **Phase 3 (build) is done (2026-11-14):** every page is on the new components: Home, Mods (Browse, Installed, Check, Activity), Performance (Level, Every setting), Stats, Settings (seven sections, with the light theme and text size), Backups, Servers, Crosshair and the Map ([[Rebuilt Pages - Performance to Map]]); the old system (`design.py`, `theme.py`, `motion.py`, `legacy/`) is deleted. What is left is checking, not building: it was never seen on the user's display and never run on a real game folder. See "Progress" in [[Handoff - Phase 3 Build (Sonnet 5.5)]].

## Reading order for a new session
1. This note, then [[User Profile and Working Rules]] (how to behave).
2. [[Session History]] (what happened and why), then [[Open Items and Next Steps]].
3. [[Environment and Pitfalls]] before touching files or running commands (Windows traps cost hours).
4. [[How The Code Works]] before changing code; [[Codebase Structure]] and [[Architecture Overview]] for the map.
5. [[Verification Cookbook]] before claiming anything works.
6. [[Research Findings]] for the external facts that shaped decisions, [[Git and Release State]] before any git command.
7. The verbatim requirements: [[User Brief - Original Requirements]]. The full raw conversation is in `AI Memory/Raw/` (local only, git-ignored): `Conversation (readable)`.
8. The community reference app the user asked to reverse engineer (mod store, performance, stats; GPL-3.0, so no code copying): [[Reference App Analysis]].

## The rules that matter most (details in the notes above)
* Never commit, push, tag or publish without being asked; never modify the user's other vaults or Obsidian's global config.
* Never describe something as implemented or verified without evidence; update the vault when code changes (`python scripts/check_vault.py` must pass).
* Security is never weakened for convenience. The codebase is the source of truth, the vault explains it.
* Python on Windows: write files as **LF bytes** (the repo is LF); scripts with backslashes go in files, not heredocs.

## Where the knowledge is
[[00 Home]] (project map) · [[Architecture Overview]] · the ADR notes (linked from the Home map) · [[Implementation Log]] · [[Known Issues]] · [[Testing]] · [[Security Model]] · [[Design System]]
