---
title: Redesign Plan
type: guide
tags: [roadmap, redesign, ui, handoff]
updated: 2026-11-14
---

# Redesign Plan: a new interface, in three phases and three models

> **للمستخدم (بالعربي، ببساطة):** الواجهة الحالية انبنت فوق قائمة الأداء وكل مرة نضيف صفحة تتكدس (17 صفحة، وكلها بأرقام داخل ملف واحد ضخم). القرار: **تصميم جديد كليًا** ما يشبه القديم، ويكون متناسقًا. الشغل على ٣ مراحل، كل مرحلة بنموذج ودردشة جديدة: **١) Fable 5.2 يصمّم**، **٢) Opus 5.5 (low) يبني البنية التحتية**، **٣) Sonnet 5.5 يسوّي كل الباقي**. كل مرحلة لها برومت جاهز في ملاحظة «Handoff» تنسخه وتلصقه في الدردشة الجديدة، وكل نموذج لازم يقول لك جملة محددة لما يخلص عشان تفتح الدردشة التالية.

## Why (what is wrong today)
* The window grew from the **Performance** page: `deadlock_fps/ui.py` (a very long, dense, Arabic-source file) builds 17 pages addressed by **index numbers**; adding a page touches five places ([[How The Code Works]]). Tests pin those numbers.
* The rail has 17 entries in four groups; names mix Arabic-source and English-source strings; the old style (brass and teal, chamfered panels) is spread over `design.py` and `theme.py`.
* The user's words: the interface became messy because it was built on the performance page and things pile up; they want a **new, coherent design, completely different from the past** ([[User Profile and Working Rules]]).

## The three phases
| Phase | Model | Does | Must not | Handoff |
|---|---|---|---|---|
| 1 Design | **Fable 5.2** | The design: ideas, information architecture, visual language, tokens, component specs, a screen-by-screen spec with mock-ups, light and dark, English and Arabic (RTL) | change application code | [[Handoff - Phase 1 Design (Fable 5.2)]] |
| 2 Infrastructure | **Opus 5.5, low effort** | A new shell: page registry with names (no indexes), navigation, theme-from-tokens, component base classes, state wiring; old pages keep working inside it | change the engines or the new visuals | [[Handoff - Phase 2 Infrastructure (Opus 5.5)]] |
| 3 Build | **Sonnet 5.5** | Everything else: rebuild every page on the new components, translations, tests, screenshots, the remaining features, documentation | break the rules below | [[Handoff - Phase 3 Build (Sonnet 5.5)]] |

Order matters: Phase 2 needs the token list and component list from Phase 1; Phase 3 needs the shell from Phase 2.

**Progress:** Phase 1 done 2026-11-14 ([[01 Principles]] · [[02 Information Architecture]] · [[03 Visual Language]] · [[04 Components]] · [[05 Screens]] · [[06 Handoff to Build]]). Phase 2 done 2026-11-14 ([[Shell and Page Registry]], Result in [[Handoff - Phase 2 Infrastructure (Opus 5.5)]]). Phase 3 done 2026-11-14: Home, Mods, Performance, Stats, Settings, Backups, Servers, Crosshair and the Map are all rebuilt ([[Rebuilt Pages - Performance to Map]]), the old system is deleted; the details and what was not verified are in the Progress of [[Handoff - Phase 3 Build (Sonnet 5.5)]].

## How the handoff works
1. Open a **new chat** in this project with the model of the phase.
2. Paste the prompt from the phase's Handoff note (it tells the model to read [[00 Start Here]] first).
3. The model works, writes its results into the vault (a *Result* section in its Handoff note, plus the notes it names), and **ends its last message with a fixed line** (for example `✅ المرحلة 1 انتهت (Fable 5.2)`). When you see that line, open the next chat with the next model and paste the next prompt.
4. A model that is **not done** must say what is left and must **not** print the fixed line.

## Rules every phase keeps
* Never commit, push, tag or release unless the user asks; never touch the user's other Obsidian vaults ([[Git and Release State]]).
* Honest statuses; nothing claimed without evidence ([[Verification Cookbook]]). `python scripts/check_vault.py` and `scripts/i18n_tool.py check` must pass; the suite stays green (one known Windows symlink error).
* Engines (`repos/`, `installer/`, `store/`, `perf/`, `stats/`, `graph/`) are Qt-free and stay as they are; the redesign is the interface layer ([[ADR-002 Repository engine is a Qt-free package]]).
* Plain words in the product (the user finds jargon confusing): no "repository", no index numbers on screen ([[Mod Store]]).
* The reference app is GPL-3.0; copy nothing from it ([[ADR-012 Reimplement from public interfaces and copy nothing from the GPL reference]]).
* Chat replies to the user: short, plain Arabic, one idea per line; detail goes into the vault.

## What is left from the reference app (after the store, performance and stats)
From [[Reference App Analysis]] and [[Open Items and Next Steps]]; none of it is the redesign, all of it is Phase 3 material after the new shell exists.
* **Store:** Sounds, WIPs and Collections listings; `.rar`/`.7z` installs; update checks for store mods; a pause/resume download manager; drag-and-drop of a local file; popularity sort; pruning.
* **Performance:** presets and community configs (authored or licence-checked, never copied), share codes, an autoexec editor, re-applying the chosen config on launch, launch-health and bisect helpers, a benchmark.
* **Stats:** hero detail pages, items and builds, match history, mates and enemies, performance curves, hero combinations, live lobby.
* **Platform:** shared profiles and announcements (the reference's own server), hash analysis, named mod collections ([[Collections]]), local mod import with inspection, light theme, keyboard and screen-reader pass.
* **Never done:** a run on a real Deadlock folder with real mods ([[Known Issues]] #6, #18); a stats lookup of an account with ranked matches (#23).

Related: [[Roadmap]] · [[Design System]] · [[Technical Debt]] · [[00 Home]]
