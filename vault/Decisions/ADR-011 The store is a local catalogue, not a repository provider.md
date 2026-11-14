---
title: ADR-011 The store is a local catalogue, not a repository provider
type: decision
status: IMPLEMENTED
tags: [decision, store, architecture]
updated: 2026-11-14
affects: [Mod Store, Repository Providers, Manifest Specification]
---

# ADR-011 · The mod store is a local SQLite catalogue, not a repository provider

**Context.** The reference app's mod store is the Deadlock catalogue on GameBanana ([[Reference App Analysis]]). The obvious fit would have been one more provider behind [[Repository Providers]]. Facts that argue against it, all observed on 2026-11-14:
* The catalogue holds **6 115 listings**; the [[Manifest Specification]] caps an index at 5 000 mods and 8 MiB, and a provider returns one validated index per sync.
* GameBanana is not a manifest repository: there is no per-mod version history, no dependency or conflict data, and files carry **MD5 only**, so everything would be `derived` and unhashed.
* Its API is rate limited, so a full walk takes 123 paced requests and about two minutes, and must be resumable.
* Search, category and sort over 6 000 rows should be instant and free for the server.

**Decision.** A separate Qt-free package `deadlock_fps/store/`: a client over the existing pinned `UrllibTransport`, a SQLite catalogue with FTS5 search, and a resumable crawl plus incremental refresh. Every filter and sort runs locally. The store itself never touches the game; installing goes through a thin adapter into the existing installer ([[Installation Engine]]), which is where every safety check lives. GameBanana content is shown as **UNVERIFIED** ([[Trust System]]): nobody on this project reviewed it.

**Consequences.**
* The first download is an explicit user action that states its cost (about 125 requests); there is no background sync ([[Security Model]]: no hidden activity).
* The catalogue is a cache: a damaged file is moved aside and rebuilt.
* Installing is an adapter, `store/install.py`, that turns one store file into the (repository, mod, version) the installer already understands, with a pseudo-repository `store:gamebanana` that is always UNVERIFIED ([[Task - Mod Store install]]). Only `.zip` and `.vpk` files work; `.rar` and `.7z` do not.

Affects [[Mod Store]], [[Repository Providers]], [[Manifest Specification]].
