---
title: Task - Mod Store page
type: task
status: IMPLEMENTED
tags: [task, store, ui]
updated: 2026-11-14
implements: [Mod Store]
code: [deadlock_fps/store_service.py, deadlock_fps/pages/browse.py, deadlock_fps/ui.py, deadlock_fps/shell/base.py]
tests: [tests/test_store_browse.py, tests/test_repos_ui.py, tests/test_mod_inspector.py]
---

# Task - Mod Store page

`StoreService` (Qt object owning the catalogue; background jobs; cancelled when the application quits) and `StorePage` (stack index **15**, first entry of the Mod Manager group and the first button of the Mods page switcher): first-run state with the stated cost, manual download or resume, refresh, search, sort, category and subcategory, adult and outdated switches, a details panel (page fetched after the selection rests, cached for the session), screenshots on request, and **Open on GameBanana** (the address is built from the numeric id). No Install button exists because installing from the store is not built.

**Evidence.** 21 offscreen page tests (first run, download, refresh, 429 resume, network failure, single sync, filters, detail, cache, 404 page, trust text, no install button, URL from id, plain-text rendering of hostile names, row cap, selection kept, unusable location). Rendered offscreen in English and Arabic with **live GameBanana data** (real names, a real screenshot, real file line with MD5) via `scripts/dev/shot_store.py`; two layout defects found that way and fixed (a clipped "Updated" column, elided names, empty detail boxes, mixed-direction file line). Existing tests changed on purpose: stack count 15 → 16, rail labels 15 → 16.

**Not verified.** A real display; the user has not looked at it yet.

Implements: [[Mod Store]].
