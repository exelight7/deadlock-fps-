---
title: 01 Principles
type: design
status: PROPOSED
tags: [design, redesign, principles]
updated: 2026-11-14
---

# 01 · Principles of the new interface

> **للمستخدم (بالعربي، ببساطة):** الواجهة الجديدة هادئة ونظيفة: ٨ أماكن في القائمة بدل ١٧، لون واحد مميز (أزرق) بدل النحاسي، زوايا ناعمة بدل الزوايا المقطوعة، وبدون زخارف. أهم ثلاثة أشياء (المودات، الأداء، الإحصائيات) هي أول ما تشوفه. افتح `docs/design-prototype/index.html` بالمتصفح لتشوفها وتجرّبها.

Phase 1 of [[Redesign Plan]]. This is a **design**, nothing here is built in the app yet. The clickable mock-up is `docs/design-prototype/index.html`; the reference pictures are in `docs/design-prototype/shots/`. Next notes: [[02 Information Architecture]], [[03 Visual Language]], [[04 Components]], [[05 Screens]], [[06 Handoff to Build]].

## What the app is for
Someone who plays Deadlock opens Toolbox to do one of three things: **get a mod, make the game run faster, look at the numbers.** Everything else (crosshair, servers, backups, settings) supports those. The interface is judged by how fast a first-time user reaches one of the three.

## The seven principles
1. **Three doors first.** Mods, Performance and Stats are the first three entries after Home in the sidebar and the three big cards on Home. Nothing competes with them.
2. **One place per thing.** A destination is a place the user thinks of ("my mods"), never an internal part ("downloads", "compatibility", "repositories"). Parts become tabs inside the place. Eight destinations in total, and that number does not grow: a new feature becomes a tab or a section.
3. **Plain words.** Labels say what the user gets. No *repository*, *manifest*, *hash*, *convar*, *pak* in a label; technical names appear only as data (a file name, a setting's name) and are set in the monospace face so they read as data. Every page that needs explaining gets one sentence, never a paragraph.
4. **Quiet surface, one accent.** Neutral graphite or paper surfaces; one accent colour that means "the main action here" or "the selected thing". Green, amber and red only ever mean good, caution and problem, and always come with an icon or a word.
5. **Nothing changes silently.** Anything that writes to the game goes through the same three steps everywhere: a sticky bar that says what is pending, a review dialog that lists what will change, then a confirmation with Undo. Anything that talks to the internet happens only after a press, and the page says what is sent.
6. **Every screen has four faces.** Filled, empty, loading and error are designed for each page. An empty page says what will appear and offers the one action that fills it. An error says what happened, that nothing was harmed, and what to do next.
7. **Arabic and English are equals.** The whole window mirrors; one type family covers both scripts; nothing relies on capital letters, letter-spacing or italics (Arabic has none of them).

## Tone of voice
* Short sentences, the user is "you", the app is "Toolbox". Verbs on buttons: *Install*, *Check again*, *Review and apply*.
* A button says what happens next, and keeps that name through the flow (the *Install* button opens *Review before installing*, whose button is *Install*).
* Errors never blame and never say "failed" alone: *"Close Deadlock first. Nothing was changed."*
* Honest about limits, in the same plain voice: *"The status comes from Valve's public data; nobody checked it in the game."*
* Arabic is simple modern Arabic that a Gulf reader finds natural (شوف، تقدر), not formal bureaucratic phrasing and not heavy dialect.

## Why it is different from the old one
| | Old (3.5 to 4.0) | New |
|---|---|---|
| Idea | a 1931 brass-and-ink switchboard | a clean workbench: the content is the decoration |
| Navigation | 17 pages in 5 groups, addressed by number | 8 destinations, tabs inside, addressed by name |
| Colour | teal-black with aged brass, verdigris, crimson | neutral graphite or paper with one blue accent; dark **and** light |
| Shape | chamfered "cut corner" panels with brass ticks, 2 px controls | rounded 6 / 10 / 14 px, no ornaments |
| Type | Reem Kufi display + Noto Sans, small-caps kickers with tracking | one family (IBM Plex Sans Arabic + IBM Plex Sans), no kickers, no tracking |
| Page top | breadcrumb, title, chips, hint line, deco rule, sometimes a skyline banner | the title and, when needed, one sentence |
| Lists | tables everywhere | cards with pictures for mods, tables only for numbers |
| Icons | square caps, mitred joins | round caps and joins, redrawn |
| Motion | 300 to 500 ms page fades, intro curtain | 120 to 260 ms, no intro, can be turned off |

## What we avoid
* Decoration that carries no information: banners, patterns, corner ticks, rules, kickers, breadcrumbs with one level.
* More than one filled (primary) button in a view.
* A sidebar entry for something that is a step or a part (Downloads, Compatibility, Inspector, Sources).
* Colour as the only signal; text smaller than 12 px; a control lower than 28 px.
* Jargon, numbers of pages, arrows typed as characters (`→` was a box in the old renders): arrows are icons and they mirror.
* Shadows on cards (Qt cannot do them cheaply): depth comes from surface tone and a 1 px border; shadows are for dialogs, sheets, menus and toasts only.
* Anything copied from the GPL reference app ([[ADR-012 Reimplement from public interfaces and copy nothing from the GPL reference]]): every icon, layout and sentence here was made for this project.

## Accessibility promises
* Text contrast at least 4.5:1 and control outlines at least 3:1, in both themes and all three accent options: 96 pairs are checked by `scripts/dev/design_tokens.py` and all pass ([[03 Visual Language]]).
* A visible 2 px focus ring on everything reachable by keyboard; Tab order follows reading order; Esc closes the top overlay.
* Text size 90, 100, 115 or 130 % from Settings; the layout is specified at 940 × 680 and 100 %.
* "Less motion" turns animations off.
* Not verified: a screen reader, a real display, the 130 % size at the minimum window. They are checks for Phase 3 ([[06 Handoff to Build]]).

Related: [[Design System]] (the old system, kept until Phase 3 removes it) · [[User Profile and Working Rules]]
