---
title: Stats
type: feature
status: IMPLEMENTED
tags: [feature, stats, privacy]
updated: 2026-11-14
code: [deadlock_fps/stats/api.py, deadlock_fps/stats/cache.py, deadlock_fps/stats/source.py, deadlock_fps/stats/maths.py, deadlock_fps/stats/steam.py, deadlock_fps/stats/model.py, deadlock_fps/stats/clean.py, deadlock_fps/stats_service.py, deadlock_fps/pages/stats.py, deadlock_fps/ui.py, deadlock_fps/shell/base.py]
tests: [tests/test_stats_core.py, tests/test_stats_api.py, tests/test_stats_source.py, tests/test_stats_ui.py, tests/stats_fixtures.py]
---

# Stats

> **للمستخدم (بالعربي، ببساطة):** صفحة جديدة اسمها **«الإحصائيات»** تحت «اللعب». فيها ثلاث تبويبات: **الأبطال** (من القوي الآن، مع نسبة الفوز ونسبة الاختيار وKDA)، **الرتب** (كم لاعب في كل رتبة)، و**إحصائياتي** (رتبتك وأبطالك مقارنة بالجميع). **ما يتحمّل شي إلا لما تضغط الزر.** تبويبا الأبطال والرتب يرسلان فقط (الفترة، النمط، الرتبة)، لا شي عنك. «إحصائياتي» ترسل **رقم حساب Steam** لموقع api.deadlock-api.com، ولا تحفظ شيئًا عنك في جهازك. جُرّبت الأرقام العامة على الموقع الحقيقي، و«إحصائياتي» جُرّبت بحسابك بموافقتك وتشتغل. تبويب «إحصائياتي» له فترة ونمط خاصين به، والافتراضي «كل الفترات» و«كل الأنماط».

A page, **Stats** (stack index 16, in the rail group *Play*), built from the stats module found in [[Reference App Analysis]] and written only from public interfaces ([[ADR-012 Reimplement from public interfaces and copy nothing from the GPL reference]]). Decision on privacy and data: [[ADR-014 Statistics are fetched on request and nothing personal is kept]].

## Where the numbers come from
The public **Deadlock API** (`https://api.deadlock-api.com`, a community service, OpenAPI 0.1.0, read 2026-11-14). The host is fixed in code; no address from an answer is ever fetched. Requests go through the same pinned HTTPS transport as the store and the repositories ([[ADR-005 Standard-library HTTP with a pinned connection]]): public addresses only, redirects checked, 4 MiB cap.

| Used for | Endpoint | What is sent |
|---|---|---|
| hero names | `/v1/assets/heroes?only_active=true` | nothing |
| rank names | `/v1/assets/ranks` | nothing |
| the meta | `/v1/analytics/hero-stats`, `/v1/analytics/game-stats` | period (hour-rounded start time), `game_mode=normal`, optional `match_mode`, optional badge range of one rank |
| rank spread | `/v1/analytics/badge-distribution` | period and mode |
| a player's rank | `/v1/players/{account}/rank` | the account number |
| a player's heroes | `/v1/players/hero-stats` | the account number, period, mode |

Documented limits: 200 requests a minute for analytics, 100 a second for player calls. One "Load statistics" makes at most 6 requests (names are cached for a day).

## The page
* **What to show:** period (7, 14 or 30 days), mode (all, ranked, unranked), rank (all or one of the 11 tiers). **Load statistics** / **Refresh** is the only thing that asks the server. Changing a choice shows the saved copy for it when there is one, otherwise says nothing is loaded; it never starts a request. Opening the page again shows what an earlier session saved (marked *saved copy*).
* **Heroes:** hero, matches, pick rate (share of matches the hero was in; twelve players share a match, so all heroes add up to 1200 %), win rate (green when the whole 95 % range is above one half, red when it is all below), the **95 % range** (Wilson interval, [[#Numbers]]), KDA, average net worth. Numeric sorting; sorting the range puts the heroes whose strength is best established first, which keeps a hero with 4 matches from topping a "best win rate" list. Search box.
* **Ranks:** players, share of players and matches per tier, with a bar. A player is counted in the tier they had in each match, so someone who climbed appears in several rows (the page says so).
* **My stats:** a field that takes a 32-bit account number, a 17-digit Steam ID, `[U:1:n]` or a `steamcommunity.com/profiles/…` link (`steam.account_id`); a vanity name (`/id/name`) is refused with an explanation, because turning it into a number would need Steam. **Use my Steam account** reads the number from the folder name under Steam's `userdata` that holds the chosen game account's settings (`Window.steam_account`); that sends nothing. **Look up** sends the number and shows rank, matches, wins, win rate and, per hero, the player's win rate beside everyone's with the difference. It has **its own period and mode** (default *All time* and *All modes*, because many accounts have no recent ranked matches); *All time* is compared with everyone's last 30 days (the column's tooltip says which period).

## Numbers
* **Wilson score interval** (z = 1.96) for the win rate; reference values are in the tests (3 of 4 → 30.1 – 95.4 %, 50 of 100 → 40.4 – 59.6 %).
* **KDA** = (kills + assists) ÷ deaths, a match with no deaths counts as one death. The player endpoint's kills, deaths and assists are **totals**: confirmed on a real account (the stated kills per minute equals kills ÷ minutes played).
* A rank tier *t* is the badge range *t*×10+1 to *t*×10+6 (badge = tier×10+sub-rank).
* **Abandon rate** is shown as the server gives it (`abandon_rate` of the game summary); its exact meaning is not documented, so the label is neutral.

## Data handling
* Everything the server sends is untrusted: types and bounds checked, text cleaned of control and direction-override characters, rows contradicting themselves (more wins than matches, rows about another player, a repeated hero) dropped, lists cut at 400 rows, a JSON nesting bomb turns into a normal "bad response" error. Hero names are shown as plain text.
* **Cache** (`<AppData>/stats/*.json`, written atomically, read back through the same strict reader): meta and rank spread 1 hour, names 1 day. When the server cannot be reached the last copy up to 30 days old is shown and the page says so with the reason.
* **A player's numbers are never written to disk**; neither is the account number. A test searches every cache file for it.

## Limits
* **"My stats" ran once against the real server with the user's own account, with their approval** (2026-11-14): it works as the schemas say, but that account had no ranked data and no matches in the last 30 days, so the rank line and the comparison column were seen with the fake server only ([[Task - Stats]], [[Known Issues]] #23). Every other test sends nothing real.
* Public numbers were checked live (2026-11-14, last 14 days, ranked): 432,845 matches, 44 heroes, wins never above matches, win rates averaging 50.0 %, pick rates adding up to 12.0, the busiest hero in 55 % of matches. They were **not** compared with another source, so "correct" means "as the service reports".
* The service is community-run: it can change, rate-limit or disappear, and its terms were not read ([[Known Issues]]).
* Not built: a hero detail page, items and builds, match history, leaderboards, searching a player by name, comparing patches, a performance overlay.
* The arrow in the page hint (Arabic text) shows as a box in the offscreen renders, like the older pages ([[Known Issues]] #5).

A real lookup: `scripts/dev/stats_player_check.py` (asks the account owner first). Evidence: [[Task - Stats]]. Related: [[Mod Store]] · [[Performance Details]] · [[Security Model]]
