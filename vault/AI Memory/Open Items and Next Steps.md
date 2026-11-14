---
title: Open Items and Next Steps
type: guide
tags: [ai-memory, todo]
updated: 2026-11-14
---

# Open items and next steps

## 0. First: find out what the user disliked
Their last message: "ما اعجبني حاليا" (I did not like it currently), with no reason. The app was launched once and exited with code 0. **Ask a concrete question** in the new session: which page, what looked or behaved wrong, or whether it was the whole direction? Candidate causes (guesses, none confirmed, in rough order of likelihood):
1. **Emptiness.** On first launch every new page is empty: no repository is added, no game linked, so Mod Hub, Installed, Compatibility and Downloads show empty states. There is **no real repository with mods** to demonstrate the flow, and the app ships with none. A user who just wants to see mods can see nothing. *Update (later the same day):* the [[Mod Store]] answers this for browsing: after one explicit download the page lists about 6 100 real GameBanana mods; installing them is still missing. *Idea:* ship a curated default list of real community sources, or publish an official `deadlock-repo.json` for the project, or add a demo/sample mode.
2. **Look and feel.** Never seen on a real display: the 15-entry rail, tables instead of cards, fonts (`→`/`←` in hint lines rendered as boxes offscreen), the dense dark theme, the Arabic hint arrows. The Hub being a plain table may feel like a "tool", not a product. *Idea:* card grid with images, larger thumbnails, better empty states.
3. **Missing brief items** (they asked for them explicitly): **Collections** (nav item), **manual installation of a local VPK/ZIP/folder into the new installer** (brief section 2), a light theme, an accessibility pass, proper "Dashboard" content. The user may have looked for these.
4. **Complexity.** Fifteen pages, a graph, many dialogs; the app may feel heavier than the original simple toolbox.
5. **Something broken on their machine** (real game path, fonts, scaling, permission errors) that offscreen tests could not reveal.

## 1. Brief items not done (honest list)
| Item | Brief section | Notes |
|---|---|---|
| Collections | 8 (nav), 10 | [[Collections]] PROPOSED; no nav entry exists |
| Manual import of arbitrary local mods (ZIP/VPK/folder) into `addons` with inspection and preview | 2 | Only the four reference mods have manual import ([[Existing Mod Library]]). Reuse `installer.archive`/`vpk` + a "local package" path in `Installer.prepare` |
| Mod Hub as a card grid with screenshots up front; grouping one mod across repositories | 2, 8 | [[Mod Hub]] |
| Dark **and light** themes | 8 | dark only |
| Keyboard navigation and accessibility audit, responsive layouts | 8 | partial; not audited |
| Nav named exactly Dashboard, Mod Hub, Repositories, Installed Mods, Collections, Compatibility, Downloads, Knowledge Graph, Backup & Restore, Settings | 8 | present under slightly different names, plus legacy pages; Collections missing |
| Restore original files of a mod | 2 | restore *previous version* exists; "original files" of a repository mod = its pre-install state: backups/trash exist but there is no UI to restore a removed mod |
| Per-mod load-order control | 3 | pak numbers are allocated automatically; no reorder UI |
| Repository update scheduling | 1 | deliberately **no** background sync (no hidden activity); refresh is manual |

## 2. Never verified (do these before trusting the installer)
* A real run on a real Deadlock install with real community mods ([[Known Issues]] #6). Close the game, link the folder, add a real `.vpk` GitHub repo, install, launch the game, update, disable, remove, check `gameinfo.gi`.
* Multi-file VPKs (refused today).
* The PyInstaller build (does `--add-data vault:vault` work on Windows? does the Graph find the vault?), Linux CI for the new tests, a real display.
* A real *native* repository: none exists. A good next artifact: publish a small real `deadlock-repo.json`.

## 3. Candidate next steps (pick with the user)
1. Ask what they disliked; fix that first.
2. Make first run meaningful: a sample/demo repository (even a local imported example), default sources, a guided "add your first repository" empty state.
3. Local mod install (brief 2) and Collections (brief 8).
4. Hub as cards; named pages instead of indexes ([[Technical Debt]] #4).
5. Real-game run and fixes; CI/Linux/PyInstaller verification; then, only if the user asks, commit and release ([[Git and Release State]]).
6. A JSON Schema + conformance examples for third-party repository authors ([[Repository Specification]]); a review process behind trust labels ([[Trust System]]).
7. **Mod Store follow-ups:** installing `.zip`/`.vpk` from the store is built ([[Task - Mod Store install]]). Still open: a run on a **real Deadlock folder** (never done; ask first) and more real mods (done once, with approval: file 1801337 `pak52_dir_3154a.zip`, a single-VPK zip, installed and removed cleanly in a throwaway game folder), `.rar`/`.7z`, update checks for store mods, Sounds/WIPs/Collections, popularity sort, pruning ([[Known Issues]] #11 to #18).
8. **Stats** is built ([[Stats]]). One real lookup of the user's own account was done (approved); it had no ranked or recent matches, so a lookup of an account **with** ranked matches is still unseen (ask the owner first: it sends the account number). Still open: a hero detail page, items and builds, match history ([[Known Issues]] #22 to #25). **Performance** is built as [[Performance Details]]; still open there: a real-game check of the statuses, making "leave out the ignored settings" the default if that proves right, importing community configs (users would bring their own files: the reference's presets are GPL and cannot be bundled, [[ADR-012 Reimplement from public interfaces and copy nothing from the GPL reference]]).

Related: [[00 Start Here]] · [[Roadmap]] · [[Known Issues]]
