---
title: Mod Hub
type: feature
status: IMPLEMENTED
tags: [feature, discovery]
updated: 2026-11-14
code: [deadlock_fps/pages/sources.py, deadlock_fps/pages/browse_host.py, deadlock_fps/hub_ui.py, deadlock_fps/mod_service.py, deadlock_fps/repos/search.py, deadlock_fps/repos/compat.py]
tests: [tests/test_sources_view.py]
---

# Mod Hub

> **2026-11-14 (Phase 3, step 3):** the Hub page is now **Mods › Browse › My sources** (`pages/sources.py`, a card grid and a sheet like GameBanana's; the switch is hidden until you add a source); see [[Classic Pack and Sources]]. `hub_ui.py` kept only `failure_text`, the table of plain sentences for engine failures. The old page's trust filter was dropped (every source label is shown on the card's sheet instead).

> Shown in the app as **Source Mods** (مودات المصادر) and placed under *Advanced* in the rail: it lists the mods of the sources the user added in **Manage Sources**. The Mod Store is the simple path for most people ([[Mod Store]]).

Page index 10, first entry of the **Mod Manager** group. Discovery plus the install flow.

* **Find:** search across every enabled repository's saved catalogue (offline, instant), category, repository, trust level, "installable only", and five sort orders ([[Repository Search]]).
* **Read:** name, author, licence, summary, description, the repository and its trust label with the explanation, a **version** selector (stable, pre-release, withdrawn and unsupported versions are marked), publish date, download size, whether a checksum is published, dependencies and conflicts, the changelog of the selected version, and whether that version fits the game build (`compat.fit`; *unknown* when either side is missing). Screenshots load lazily from the repository's own servers on request (checkbox), size- and dimension-capped.
* **Install / update / reinstall / uninstall** from the same page. Installing is never one click: prepare (download, verify, inspect, stage; the game is untouched), then an **Install preview** showing source, trust, integrity status, the files and their `pakNN` names, overlaps and every warning, then the user's confirmation; UNVERIFIED sources and missing hashes additionally need an explicit acknowledgement. Success is announced only after the engine has re-verified the installed files ([[Installation Engine]]).
* Every failure has a plain explanation with the engine's own detail (hash mismatch, unsafe archive, game running, no disk space, blocked by a dependency or conflict…). The game must be closed; a linked game folder is required.
* Text from repositories is rendered as plain text.

Not yet: grouping the same mod id across repositories into one card (each source is its own row, deliberately, so trust stays visible); a card grid instead of a table.

Evidence: 18 page tests (install through preview, cancel, refusal paths, update, restore, disable, remove, update-all); renders inspected in English and Arabic.

Related: [[Installed Mods]] · [[Repository Manager]] · [[Trust System]] · [[Design System]] · [[Mod Store]]
