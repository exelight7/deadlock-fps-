---
title: Task - Stats
type: task
status: IMPLEMENTED
tags: [task, stats]
updated: 2026-11-14
implements: [Stats]
code: [deadlock_fps/stats/api.py, deadlock_fps/stats/cache.py, deadlock_fps/stats/source.py, deadlock_fps/stats/maths.py, deadlock_fps/stats/steam.py, deadlock_fps/stats/model.py, deadlock_fps/stats/clean.py, deadlock_fps/stats_service.py, deadlock_fps/pages/stats.py, deadlock_fps/ui.py, deadlock_fps/shell/base.py, scripts/i18n_tool.py, scripts/dev/stats_live_check.py, scripts/dev/mutation_stats.py, scripts/dev/shot_stats.py]
tests: [tests/test_stats_core.py, tests/test_stats_api.py, tests/test_stats_source.py, tests/test_stats_ui.py, tests/stats_fixtures.py, tests/test_repos_ui.py, tests/test_mod_inspector.py]
---

# Task - Stats

> **للمستخدم:** هذه المهمة بنت صفحة «الإحصائيات». الأرقام العامة جُرّبت على الموقع الحقيقي، وكل الباقي مجرّب بخادم وهمي. **جرّبت «إحصائياتي» بحسابك الحقيقي بموافقتك**: اشتغلت. حسابك ما له مباريات في آخر 30 يوم ولا مباريات تنافسية، فأضفت لتبويبك فترة ونمط خاصين به (الافتراضي «كل الفترات»). رقم حسابك ما انحفظ في أي ملف.

Implements [[Stats]]. Decision: [[ADR-014 Statistics are fetched on request and nothing personal is kept]].

## Steps
1. **Probe (read-only).** The OpenAPI document of the service was fetched (125 paths) and the public endpoints were called: `hero-stats`, `game-stats`, `badge-distribution`, `assets/heroes`, `assets/ranks`. Findings that shaped the code: a bad `match_mode` is HTTP 400 (so "all modes" means *leave the parameter out*); wins plus losses equal matches; hero rows add up to about twelve times the match count; a rank tier is six badges; the player hero endpoint returns `matches_played` (a count) and `matches` (a list of ids, ignored).
2. **Engine** `deadlock_fps/stats/` (Qt-free): `clean` (strict readers), `maths` (rate, KDA, Wilson), `steam` (account number spellings), `model`, `api` (client and response readers), `cache`, `source` (cache plus client plus stale fallback).
3. **Service** `stats_service.py` (off-thread jobs, one at a time, `cached_overview` for disk-only reads) and **page** `stats_ui.py` (three tabs, numeric sorting, answers to an older choice dropped).
4. **Window:** nav label, group *Play*, hint, `PAGES`/`NAV_ICONS` entries (`gauge` icon), `Window.steam_account`; the two tests that pin the page count were updated (17 pages).
5. **Translations:** 72 Arabic and 4 English entries; `scripts/i18n_tool.py` now also reads `stats/`, `stats_ui.py` and `stats_service.py`.

## Evidence (IMPLEMENTED, not VERIFIED)
* **148 new tests** in four files (core 28, client 35, cache and source 30, page, service, main window and an Arabic-ordering guard 55). They cover: every Steam id spelling and refusal, Wilson reference values, the exact addresses and parameters built, hostile JSON (wrong types, negative and boolean numbers, contradicting rows, rows about another player, non-list bodies, nesting bomb, huge lists), the cache (age, future, corrupt, oversized, bad keys, failed writes), the stale fallback, the privacy rules (account number only in player addresses, never on disk), the page (nothing requested on open, saved copy shown, answers to an older choice dropped, numeric sorting, colours, plain-text names, failures, one load at a time) and the main window.
* **47 checks disabled one at a time** (`scripts/dev/mutation_stats.py`): **47 of 47 caught**. Two survived the first run (the mode parameter sent empty; the cache size limit) because the fake server hid blank parameters and the oversized test file was not valid JSON; both were fixed in the tests, not the code.
* **A side effect found by the mutation run:** with the "changing a choice starts a request" mutation, the tests that build the real main window made a real request to the public API and wrote cache files into the real `%APPDATA%\python\stats` (public numbers and test data only; nothing personal). They were deleted, and the window tests now replace the transport and the AppData folder, so even a wrong page cannot reach the network from the suite.
* Tests also found two real bugs before any user could: a bracket-like input (`[U:1:abc]`) crashed the Steam id reader with a `ValueError`, and a cache file holding an infinite number crashed the cache reader.
* **Real lookup (2026-11-14, with the user's approval, their own Deadlock account, all-time and 30 days):** the player endpoints answered as the schemas say; every row belonged to the account, wins never exceeded matches played, and kills, deaths and assists are **totals** (the stated kills per minute equals kills divided by minutes). The account had 47 matches over 14 heroes, **none in the last 30 days and no ranked data** (rank, sub-rank and badge all 0, `last_match` null), which the page shows as "No matches found" and "No rank on record". One analytics call for the comparison timed out once; the page leaves the comparison column blank then. The lookup showed that the default (14 days, ranked) would have shown this user nothing, so **My stats got its own period and mode, defaulting to All time and All modes**; all time is compared with everyone's last 30 days.
* **Live, read-only** (`scripts/dev/stats_live_check.py`, no account number): 19 of 19 checks passed in 4.5 s (see [[Stats]] for the numbers).
* The page was rendered offscreen in English and Arabic (`scripts/dev/shot_stats.py`, whole window, fake server): empty, heroes, ranks, my stats, server error. Findings from looking: the rank bar was a hairline that clipped its own text (now a separate percentage and a bar); Arabic sentences that began with a number flipped their order (the Arabic strings now begin with a word, and a test guards it); percentages in an Arabic table sat on the wrong side of the number (wrapped for left-to-right).

## Not verified
* A lookup of an account **with ranked matches and recent matches**: the one tried had neither, so the rank line and the comparison column were exercised by the fake server only.
* The lookup went through the engine (`scripts/dev/stats_player_check.py`), not by pressing the button in the window.
* No second source was used to check the public numbers.
* Nothing was committed.

Implements: [[Stats]]. Related: [[Task - Mod Store page]] · [[Task - Performance Details]]
