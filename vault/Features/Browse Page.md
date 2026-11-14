---
title: Browse Page
type: feature
status: IMPLEMENTED
tags: [feature, redesign, store, mods]
updated: 2026-11-14
code: [deadlock_fps/pages/browse.py, deadlock_fps/shell/components.py, deadlock_fps/ui.py, scripts/dev/shot_browse.py]
tests: [tests/test_store_browse.py, tests/test_shell.py]
---

# Mods › Browse (rebuilt in Phase 3, step 2)

> **Update (step 3):** the "GameBanana · My sources" switch now exists (`pages/browse_host.py`, `pages/sources.py`): [[Classic Pack and Sources]]. The slot `store` is the `BrowseHost`, and `window.store` is still this GameBanana page.

> **للمستخدم (بالعربي، ببساطة):** صفحة «تصفّح» في المودات انبنت من جديد على الشكل الجديد. بدل الجدول صارت بطاقات (ثلاث في أصغر نافذة، خمس في الكبيرة). تضغط بطاقة تطلع لوحة جانبية فيها زر «تركيب» أول شي، وإذا ضغطته تطلع نافذة مراجعة فيها المسار بالضبط وكل تحذير. ما يتغير شي في اللعبة قبل ما تأكّد. المحرّكات (GameBanana، الكتالوج، التركيب) ما تغيّرت.

The engine is the [[Mod Store]] (catalogue, sync, install adapter); this note is only the page. Spec: [[05 Screens]] (Mods › Browse). Progress: [[Handoff - Phase 3 Build (Sonnet 5.5)]].

## Parts
| Part | File | Role |
|---|---|---|
| `BrowsePage` | `deadlock_fps/pages/browse.py` | The whole page. Constructed as `BrowsePage(store_service, mod_service=None)`; emits `openRequested(address)` (to `mods.installed`) and `gameRequired` (the window brings up Home's link card). Without a `ModService` it only browses. |
| `InstallReview` | same file | The review `Dialog` (variant `review`): mod, source with its trust badge, file check, the exact path under `game/citadel/addons`, blockers and warnings as banners, the acknowledgement checkbox that enables *Install*. Replaces `hub_ui.InstallPreview` for the store path (the Hub still uses its own until step 3). |
| `ModCard`, `ElidedLabel`, `Sheet`, `Dialog`, `KeyValue` | `deadlock_fps/shell/components.py` | Components the page needed and that were upgraded: cards cut long names with "…" instead of widening, show a quiet box icon and the *Installed* badge at the trailing corner; `Sheet` follows the text size and keeps its content off the scroll bar; `Dialog` is as tall as its wrapped text; `KeyValue` takes widgets and keeps values next to their labels in both directions; `EmptyState` text is as tall as it needs; `breakable()` lets a long address wrap. |
| `Window` | `deadlock_fps/ui.py` | Slot `store` is in `REBUILT_SLOTS`; the page's signals go to `navigate` and `focus_game`. The old `store_ui.py` is deleted. |

## Behaviour
* **First run:** an EmptyState "Get the mod list first" with the cost (about 2 minutes and 26 MB, once) and one large button. Nothing is fetched before the press.
* **Downloading:** a Card with "Page N of about M", a ProgressBar, *Stop*, and the note that it continues next time; Skeleton blocks while there is no list yet. An interrupted first download shows an info Banner with *Continue the download* above the list that is already saved.
* **Filled:** search (as you type), three Selects (type, hero, order; the hero list needs a type that has heroes), chips *Hide outdated* (on) and *Show adult content* (off), "N mods · list checked 2 hours ago", *Check for new mods*. The grid is built 48 cards at a time (*Show more*), at most 300; the columns follow the width (three at the smallest window, five at 1180). On a narrow window or a large text size the three Selects and the count move to rows of their own, so nothing scrolls sideways.
* **Press a card:** the Sheet opens from the trailing edge. The mod page is fetched at once (cached for the session). Order: name, author and badges, **file Select and Install first**, the "Not reviewed" warning, facts (version, updated, file check, MD5, virus scan as GameBanana reports it, likes, downloads, licence), description, *Open on GameBanana*, *Show pictures*, the privacy note. Esc or ✕ closes it.
* **Install:** download to a private folder, check, inspect, then the review Dialog; only *Install* there (after the acknowledgement) copies anything. Results are a Banner in the sheet and a Toast. **No game linked:** the Install button is off and a warning Banner offers *Link the game*; even if the game is unlinked after the sheet opened, pressing Install downloads nothing.
* **Errors:** sync failures are a danger Banner (rate limit: warning) with *Try again*; the saved list stays usable. An unusable catalogue folder shows a danger EmptyState.
* **Pictures:** none are requested while browsing; *Show pictures* in the sheet loads up to four for that mod (https, GameBanana hosts only, size and dimension limits unchanged). Card pictures are not built (see below).
* Everything that came from GameBanana is shown as plain text.

## Checked
* `tests/test_store_browse.py` (51): first run, download, refresh, rate limit and network failure, search / chips / selects / sorting / empty filter, the sheet and its profile fetch (never before a press, cached), missing page, trust and browse-only mode, plain-text names, the page-at-a-time cap, selection after reload, columns for the window width, long names, **no sideways scrolling at 940 px and 130 % text**, and the whole install path through the real engine on a throwaway game folder (end to end, decline, no game, wrong checksum, unsupported file, busy, file facts, the Installed tab button, the card badge appearing and going), the review dialog on its own, the unavailable catalogue, the helpers. The install-path tests are the old page's tests moved over to the new widgets; the rest are new.
* `scripts/dev/mutation_store.py` names two page checks (install offered for any file, the game-linked guard); their patterns now point at `pages/browse.py`, and the test file is named `test_store_browse.py` so the script's `test_store_*.py` pattern still runs it. Re-run on 2026-11-14 after the rebuild: all 29 checks caught (the guard's pattern had to be updated first).
* Looked at by eye with `scripts/dev/shot_browse.py` (sample data, no network): English dark and light, Arabic dark and light, every state (first run, filled, downloading, error, interrupted, sheet, no game, review dialog), 1200 × 820 and 940 × 680, 100 % and 130 % text. Four defects the tests had not caught were fixed that way: wrapped text clipped in the dialog and in the empty state, a sentence that began with a direction mark laid out left to right in Arabic, values drifting away from their labels in the sheet, and the filter rows overflowing at 130 %.

## Not done or not verified
* **Card pictures.** Cards show a box icon; the design's per-mod pictures wait for the "Show mod pictures" switch in Settings › Advanced (not built; pictures stay off by default).
* **Heroes for other types.** The second Select says "All heroes" and lists a type's subcategories, which are heroes for Skins; GameBanana may use subcategories for other types too.
* Scroll bars and the sidebar footer are still old style ([[Known Issues]]). No screen-reader pass; not seen on the user's own display; never run against the user's real game folder.

Related: [[Mod Store]] · [[Home Page]] · [[Shell and Page Registry]] · [[Installation Engine]] · [[Task - Mod Store install]]
