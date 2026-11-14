---
title: Reference App Analysis
type: guide
tags: [ai-memory, research, reverse-engineering]
updated: 2026-11-14
---

# Reference app analysis: the community "Deadlock Mod Manager"

> **للمستخدم (بالعربي):** هذه الملاحظة نتيجة الهندسة العكسية لمدير المودات المجتمعي (التطبيق المثبّت + مصدره). فيها كيف يعمل **متجر المودات** و**الأداء** و**الإحصائيات**، وما الذي يمكن نقله لبرنامجك وما الذي لا يجوز نقله (الرخصة)، وما الذي لم يُفحص بعد. كل بند موسوم: **observed** (رأيته فعلًا)، **inferred** (استنتاج)، **not examined** (لم يُفحص).

## Targets and identity (observed)

| Item | Value |
|---|---|
| Installed app | `<home>\Videos\DEADLOCK\modmanger\Deadlock Mod Manager\deadlock-mod-manager.exe` (the folder name has **no** trailing space; REA rejected the path with one) |
| Installed build | 76 220 800 bytes, SHA-256 `50e36ddc356c20afc4770f92eab975c4bd07bfff0fb486bbc050513f9acd0bd4`, PE32+ x64, version resource **2.3.0** (REA evidence `ev_483a7417…ce72`, bytes read from the RT_VERSION resource) |
| Signature | Authenticode table present, signer **SignPath Foundation** via GlobalSign GCC R45 CodeSigning CA 2020 (REA `ev_06e26dc7…b9a`); the signature was **not cryptographically verified** |
| Source tree | `<home>\Videos\DEADLOCK\modmanger\deadlock-mod-manager-main`, desktop package **2.4.0**, a monorepo (Tauri 2 + React/TypeScript front end, Rust back end; Bun/Hono/oRPC/Drizzle API) |
| **Mismatch** | The installed exe (2.3.0) and the source (2.4.0) are **not the same build**. Source-level claims below describe 2.4.0; shipped-binary claims describe 2.3.0 only. |
| Framework | Tauri, not Electron: REA `audit_release_exposure` found no source maps, no extractable payload, one CodeView PDB path string (`deadlock_mod_manager.pdb`, severity low). |
| Licence | **GPL-3.0** (`LICENSE.md`). Our project is MIT. See [[#Licence boundary]]. |

## Mod store (observed in source, live and in the binary)

**Source of truth is GameBanana, not the project's own server.**
* Rust client `providers/gamebanana/client.rs` talks to `https://gamebanana.com/apiv11/`. Deadlock's GameBanana game id is `20948`. The plain-text strings `gamebanana.com/apiv11`, `Generic_Game`, `Generic_LatestModified` were found inside the installed 2.3.0 exe, so the shipped build uses the same API.
* Endpoints seen in the code: `<Model>/Index` with `_nPerpage=50`, `_aFilters[Generic_Game]=20948`, `_nPage`, `_sSort=Generic_Oldest` (full crawls: the default order is unstable near the tail) or `Generic_LatestModified` (incremental); `<Model>/Categories?_idGameRow=20948&_sSort=a_to_z&_bShowEmpty=true` (child level: `_idCategoryRow=<id>`); `<Model>/<id>/ProfilePage`; `Sound/<id>/Posts`; `Collection/Index`, `Collection/<id>/Items`; legacy host `Core/Item/Data`. Models: Mod, Sound (and Collection).
* Live checks on 2026-11-14 (read-only, generic user agent): `Mod/Index` HTTP 200 with `_nRecordCount` **6114**; `Mod/Categories` 200 with 8 root categories (Skins 4110, HUD 873, Model Replacement 656, Quality of Life/Fixes 170, Other/Misc 160, Maps 45, Gameplay Modifications 39, Animations 30); `Mod/711387/ProfilePage` 200. My first categories call returned 400 because I used `_idCategoryRow=0`; the root scope is `_idGameRow`.
* A file record carries `_sFile` (e.g. `pak52_dir_….zip`), `_nFilesize`, **`_sMd5Checksum` (MD5 only, no SHA-256)**, `_sDownloadUrl` (`https://gamebanana.com/dl/<fileId>`), `_sAvState/_sAvResult` (GameBanana's own antivirus verdict), `_aModManagerIntegrations`. Rate limits are described in the code as aggressive: pages are 50 and "about 190 requests walk every mod and sound".
* **Architecture:** crawl once into a local SQLite database (Diesel, FTS5 search), resume from a cursor (`sync_cursor`: next page, snapshot id, high-water mark), refresh recent changes via `Generic_LatestModified`, re-fetch ~100 profiles per sync for like/download counts, and answer every filter, search and sort **locally**. The `submission` table keeps name, author, category path, hero, audio/map/NSFW/obsolete flags, download and like counts, image URLs, timestamps, tags. Collections have their own tables.
* NSFW handling: content ratings `st, sa, sc, ft, lp, pn, nu` map to NSFW; visibility `hide`/`warn`; the UI can hide NSFW.
* Download manager (Rust): pause/resume/retry, file and variant selection, import of dropped local files. **Not examined** in detail.
* The project's own server (`api.deadlockmods.app`, API v2) mirrors GameBanana for the web site and serves announcements, shared profiles, crosshairs, servers, hash analysis (`/api/v2/vpk-analyse-hashes`) and the performance catalog. The 2.4.0 desktop reads the catalog **directly** from GameBanana; v2 is for ancillary data.
* "Native sources": a second, project-defined catalogue format (RFC `002-mod-sources`, schemas under `deadlockmods.app/v1/…`) that plays the role our [[Manifest Specification]] plays. **Not examined** beyond the file list.

## Performance (observed in source and live)

* "Performance" in the reference is a **gameinfo.gi overlay**, not an FPS meter. `perf_config/mod.rs`: a config is a list of ConVar entries; the overlay edits existing keys in place and injects new ones in **one marked block**, markers record original values (so removal works from the file alone), the chosen config is stored and **re-applied on every launch** because Steam updates and "Reset to Vanilla" replace the file. Companion: the author's `video.txt` (with a backup of the player's own), an autoexec editor, share codes, import of community configs. The game build comes from `ClientVersion` in `game/citadel/steam.inf`.
* Catalogue (`packages/perf-catalog`, served at `GET /api/v2/perf-catalog`, also bundled): live fetch returned HTTP 200, 1 878 119 bytes, version `2026.11.13-1`, schema 1, latest build 6801 / convar build 6857, **5 079 convars**, 42 stock `gameinfo.gi` builds, 8 presets (`dmm-clean`, `optimizationlock`, `eskay`, `sqooky-max-fps`, `kaizu-min-spec`, `optilock-fps`, `optilock-potato`, `optilock-ultra-potato`), 7 community GameBanana configs, 13 categories with weights. It matches the repo's bundled `data/catalog.json` size to within one byte.
* "DMM Clean" is derived by lineage voting over GPL-3.0 community presets (kept when ≥ 3 lineages agree and ≥ 75 % of those changing the key; hidden-information and camera/visibility convars are excluded). A generator pins every upstream file by SHA-256 and runs twice a day in CI.
* **Not examined:** the Rust apply/analyse code beyond the module map, the in-app benchmark and `launch-health`/`bisect` helpers, the Performance page UI.

## Stats (observed in source and live)

* All stats come from the **public** `https://api.deadlock-api.com` (`/v1/...`), not from the project's server. `lib/stats/api.ts` uses: `/v1/players/<id>/match-history`, `/v1/matches/<id>/metadata?disable_steam=true`, `/v1/players/hero-stats`, `/players/<id>/rank`, `/region`, `/mate-stats`, `/enemy-stats`, `/v1/players/steam`, `/v1/analytics/hero-stats`, `/analytics/badge-distribution`, `/analytics/player-stats/metrics`, `/analytics/player-performance-curve`, `/analytics/hero-comb-stats`, `/analytics/hero-counter-stats`, `/analytics/item-stats`, and assets `/v1/assets/heroes`, `/items`, `/ranks`, `/ranked-seasons`. The code deliberately avoids Patreon-only endpoints and refetch flags; documented limits are about 100 req/s per IP for players and 200 req/min for analytics.
* Live checks: `/v1/assets/heroes?only_active=true` 200 (44 heroes, 1.4 MB); `/v1/analytics/badge-distribution` 200 (66 rows). Player endpoints were **not** called (they need a Steam account id).
* Features built on it: match history and match detail, per-hero stats, mates/enemies, item stats, rank and region history, performance curves versus bracket, hero-combination stats, live lobby/grades from the game's console log (`console_log_watcher.rs`, `live_match`, `deadlock-match-sync`). **Not examined** in detail.

## What the binary can and cannot confirm (limits)

* Ghidra, IDA, Kuna are **not configured** here, so no decompilation was done. REA's PE tools, the release-exposure audit and a plain byte scan were used.
* Plain strings in the exe confirm the **Rust side** (GameBanana client, `api.deadlock-api.com`, `api.deadlockmods.app`, `perf_config`, `match_sync`, `live_match`, `gameinfo.gi` ×87). The React front end is embedded compressed, so its routes (for example `/api/v2/perf-catalog`) are known only from the 2.4.0 source. `auth.deadlockmods.app` was **not** found as plain text in 2.3.0.
* The PE import table (large) was retrieved but not analysed; no `cargo-auditable` dependency metadata was recognised.

## Licence boundary

The reference is GPL-3.0 and its performance catalogue embeds data derived from other GPL-3.0 projects. Deadlock Toolbox is MIT. **Do not copy source code, curated texts or preset data** into this repository. What may be reused is the public behaviour: the GameBanana and deadlock-api HTTP interfaces (check their terms and identify the client politely), and the ideas (local catalogue, overlay with markers). Write new code from the observed interfaces. Presets must come from sources whose licence allows it or be authored here. This is an engineering reading, not legal advice; the user should confirm if they intend to distribute.

## Design implications for Deadlock Toolbox (items 1 and 5 are built as [[Mod Store]], item 3 as [[Stats]]; item 4 as [[Performance Details]])

1. **Store is not a repository provider.** GameBanana has 6 114 mods; [[Manifest Specification]] caps an index at 5 000 mods and 8 MiB. Build `deadlock_fps/store/` (Qt-free, like [[Repository Providers]]): a GameBanana client over the existing pinned `UrllibTransport`, a SQLite catalogue with FTS5, a resumable crawl plus incremental refresh, polite backoff on 429. Trust for GameBanana content is COMMUNITY or UNVERIFIED, never VERIFIED ([[Trust System]]).
2. **Install path gap.** GameBanana files are mostly `.zip` (sometimes rar/7z) holding `pakNN_dir.vpk`; hashes are **MD5 only**. The installer supports `vpk` and `zip` and requires acknowledgement for derived or unhashed packages ([[Installation Engine]]); rar/7z would need a decision (refuse with a reason, or add an extractor).
3. **Stats** is a separate module over `deadlock-api.com` plus a Steam account id (not stored anywhere yet); cache responses and respect the limits above.
4. **Performance:** extend [[Performance Tuning]] with a marked-block `gameinfo.gi` overlay through `Studio` and `kv.py` ([[ADR-007 The installer must go through Studio]]); catalogue facts from public dumps (SchemaExplorer is MIT, GameTracking), presets authored or licence-checked.
5. Fill the empty first-run state described in [[Open Items and Next Steps]] with the store.

## What was built from this (later on 2026-11-14)
The user chose the store first. [[Mod Store]] exists: engine, page and tests, with the design in [[ADR-011 The store is a local catalogue, not a repository provider]] and the licence stance in [[ADR-012 Reimplement from public interfaces and copy nothing from the GPL reference]]. The live full crawl confirmed the figures above (6 115 listings, 123 requests). Installing from the store followed ([[Task - Mod Store install]]). Performance followed in a different shape from the reference's presets: [[Performance Details]] explains every setting the existing slider writes and shows what Valve's data says about it (the reference's catalogue was read for facts only, [[ADR-013 Facts come from Valve's data and the explanations are written here]]). **Correction to design point 4 above:** the app already writes `GameInfo/ConVars` and `SceneSystem` through `Studio` with footprint tracking, so no new overlay was needed. **Stats** followed as [[Stats]]: the hero meta, the rank spread and the user's own record, from the same public API, with the privacy rules in [[ADR-014 Statistics are fetched on request and nothing personal is kept]]. Built from the published OpenAPI description (125 paths, read 2026-11-14) and public calls only. **Not built** from the reference's list: match history and details, mates and enemies, items, performance curves, hero combinations, live lobby.

Related: [[00 Start Here]] · [[Research Findings]] · [[Mod Hub]] · [[Security Model]]
