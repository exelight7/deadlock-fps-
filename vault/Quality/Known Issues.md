---
title: Known Issues
type: quality
status: IN PROGRESS
tags: [quality, bugs]
updated: 2026-11-15
---

# Known issues and gotchas

## Open

| # | Issue | Impact | Notes |
|---|---|---|---|
| 2 | System HTTP proxies are unsupported by the repository transport | users behind a mandatory proxy cannot sync | [[ADR-005 Standard-library HTTP with a pinned connection]] |
| 3 | Only the first 30 GitHub/GitLab releases are read | old versions of big repositories are missing from translated catalogues | native indexes are unaffected |
| 4 | The shipped trust registry has one entry; no review process exists | no VERIFIED/COMMUNITY repositories | [[Trust System]] |
| 5 | Arrow characters (`→`, `←`) in page hints render as boxes in the offscreen test renders | possibly a bundled-font coverage gap; the same pattern exists in older pages, so likely pre-existing; not checked on a real display | |
| 6 | Everything was verified against throwaway game folders and scripted or real public servers; **no run on a real game install with real community mods** | the first real-world run may find format surprises (multi-file VPKs are refused, not handled) | [[ADR-008 Mod folder and pak naming need verification]] |
| 8 | The rail has 17 destinations: it fits at 1000 px window height and scrolls below that | usable, not elegant | [[Technical Debt]] |
| 9 | The Mod Hub is a table, and the same mod id in two repositories is two rows | no grouping or card view yet | [[Mod Hub]] |
| 10 | Collections do not exist | none | [[Collections]] |
| 11 | Mod Store installs `.zip` and `.vpk` only; `.rar` and `.7z` files are listed but cannot be installed, and store files have **MD5 only** | such mods must be unpacked by hand; MD5 detects damage, not tampering | [[Task - Mod Store install]], [[ADR-011 The store is a local catalogue, not a repository provider]] |
| 12 | Mod Store never prunes: a listing GameBanana later deletes stays in the local catalogue until it is rebuilt; opening it shows "no such page" | a stale row | pruning by crawl snapshot was left out because a page shift during a crawl could hide a legitimate mod; the `seen` column is kept so it can be added with a guard |
| 13 | Mod Store covers the Mod model only (no Sounds, WIPs or Collections) | fewer listings than the reference app shows | [[Mod Store]] |
| 14 | Likes, views and downloads are known only for mods whose page was opened, so the UI has no popularity sort | the engine supports it | [[Mod Store]] |
| 15 | The "about 26 MB" in the first-download text is an estimate (one measured 211 KB page × 123 pages); total bytes were not measured | cosmetic | the 123 requests and 137 s are measured |
| 16 | A crawl resumed after a long pause can miss entries that moved between pages meanwhile | until the next refresh or full download | `sync` falls back to a new crawl when a refresh sees more than 20 changed pages |
| 17 | Store mods get no update check: the Installed page shows "unavailable" with the reason | the user reinstalls from the store by hand | [[Task - Mod Store install]] |
| 18 | Mod pictures show only in the detail Sheet (Settings › Advanced turns on the automatic load); the cards have no thumbnails | cosmetic | [[Rebuilt Pages - Performance to Map]] |
| 19 | The redesigned interface has only been seen in offscreen pictures, never on the user's display, and nothing ran on a real game folder | the first real run may show spacing or colour surprises | ask before running on the real folder |
| 20 | Old artwork (`assets/icons`, `patterns`, `art`, `illustrations`, `scripts/make_assets.py`, `scripts/legacy_tokens.py`) is no longer used by the app but is still in the repository | size only | `scripts/smoke_desktop.py` still checks some of it; delete together |
| 21 | `scripts/dev/mutation_perf.py` and `mutation_stats.py` were re-pointed at the new pages but not re-run | a mutation may no longer match | run them before trusting them |
| 22 | The full suite takes about 20 minutes (it took about 2 before the rebuild): tests create many `Window`s that stay alive, so every later theme switch or window is slower. Each module on its own passes in seconds. | slow CI; a run that deletes windows with a global event flush crashed (access violation) | delete windows per test without a global flush, use `FakeApp` for look switches ([[Rebuilt Pages - Performance to Map]]) |
| 18 | The store install path ran with one real 7.5 MB download in a throwaway game folder, but never against a real Deadlock folder | other mods may have layouts that one single-VPK archive did not show | [[Task - Mod Store install]] |
| 19 | The graphics recipe still writes settings that Valve's data says the game ignores (23 of the 73 written at level 80); nothing changes unless the user leaves them out | the level's description overstates what it does | [[Performance Details]] |
| 20 | The facts behind the status column come from Valve's public data carried by a third-party catalogue (build 6857, read 2026-11-14) and were never checked by running the game; a game update can change them | a status may be stale or wrong | `scripts/dev/perf_facts.py --check` with a newer catalogue lists the differences |
| 21 | `assets/reference/gameinfo.gi` and `video.txt` are themselves outputs of this recipe: they already hold the level-80 values, so applying level 80 to them changes nothing | tests must use another level (they use level 0) | [[Task - Performance Details]] |
| 22 | The Stats page depends on a community-run service (`api.deadlock-api.com`): it can change, rate-limit or disappear, and its terms of use were not read | the page then shows the saved copy marked as old, or an error | [[Stats]] |
| 23 | "My stats" ran **once** against the real server with the user's own account (approved): fields, ownership of rows and totals confirmed, but that account had **no ranked data and no matches in the last 30 days**, so the rank line and the comparison column were never seen with real data | an account with ranked matches may show a surprise | [[Task - Stats]] |
| 24 | The public stats numbers were not compared with another source; "abandon rate" has no documented meaning, so it is labelled neutrally | the page reports what the service reports | [[Stats]] |
| 25 | A Steam vanity name (`steamcommunity.com/id/name`) cannot be turned into an account number without asking Steam, so it is refused | the user pastes a `/profiles/…` link or uses the button that reads the number from the Steam folder | [[Stats]] |
| 7 | The vault checker verifies structure (links, statuses, file paths), not truth: a note can still over-claim in prose | review duty | [[Vault Guide]] |
| 28 | Redesign Phase 3, Installed / Check / Activity / My sources / classic pack: findings use the engine's English sentence (also in Arabic); Installed has no Skeleton loading; no card pictures; the drop onto the classic pack is tested through its file filter only | cosmetic / unfinished, see [[Installed Page]] and [[Classic Pack and Sources]] | [[Classic Pack and Sources]] |
| 27 | Redesign Phase 3, Browse: no card pictures yet (the Settings switch for them is not built); no "My sources" switch; heroes list is a type's subcategories; the tab bar above it is clipped at 130 % text in the smallest window (seven temporary tabs) | cosmetic / unfinished, see [[Browse Page]] | [[Browse Page]] |
| 26 | Redesign Phase 3, Home: (`ListRow` separators were invisible; fixed in step 3); card icons are tinted at build time and ignore a theme switch; the sidebar footer and scroll bars are still old style; light mode is only checked on Home and the frame | cosmetic; light mode is not offered on screen yet | [[Home Page]] |

## Gotchas learned (worth knowing)

* **Line endings.** The repository is LF. Python's `Path.write_text` on Windows writes CRLF, which turns a 3-line change into a whole-file diff. Write with `write_bytes(text.encode())` or `newline='\n'`; check `git ls-files --eol`.
* **RTL selection.** `QTableWidget.selectRow()` selects nothing when the layout is right-to-left. Use `setCurrentCell(row, column)`; guarded by a regression test.
* **Mixed-direction cells.** In RTL tables numbers, dates and addresses scramble unless wrapped in LRM (U+200E).
* **`urllib.request.build_opener`** silently adds proxy, `http`, `file` and `ftp` handlers; the repository transport builds its opener by hand.

## Fixed during this work
* (2026-11-15) The symlink test now skips on a Windows account without the symlink privilege instead of erroring.
* (2026-11-15) Background jobs could still run while the app exited; the Map built its graph twice when opened; the game-process scan opened every process. See [[Implementation Log]].
* RTL table selection lost on refresh (found in the Arabic render; fixed; tested).
* A botched edit of `repos/transport.py` duplicated a class; the transport was rewritten cleanly and its tests were run before anything depended on it.

Related: [[Testing]] · [[Technical Debt]]
