---
title: ADR-015 Pages are addressed by name through one registry
type: decision
status: IMPLEMENTED
tags: [decision, ui, redesign]
updated: 2026-11-14
affects: [Shell and Page Registry]
---

# ADR-015 · Pages are addressed by name through one registry

**Context.** The old window kept 17 pages in a `QStackedWidget` addressed by index. Adding a page touched five places (nav labels, groups, a hint array, `design.PAGES`/`NAV_ICONS`, the stack), and tests pinned the numbers ([[How The Code Works]], before 2026-11-14). The redesign turns 17 pages into 8 sidebar places with tabs ([[02 Information Architecture]]).

**Decision.**
1. One list, `shell.registry.default_registry()`, names every page (`id`, `title`, `group`, `icon`, `tabs`, `hint`). The sidebar, the tab row, the page title, the hint line and the start-up flags are built from it.
2. Navigation takes an address string (`mods.health`); a number is a `TypeError`. The widgets are kept by **slot** name, so a tab can be repointed to a rebuilt page without touching anything else.
3. Colours and sizes come from `tokens.json` through `shell.tokens.Theme`; nothing is retyped. The new stylesheet is a template filled from it and re-applied on a switch.
4. The old pages stay in their slots, and the old window methods move to `deadlock_fps/shell/base.py/` unchanged, until Phase 3 rebuilds each page.

**Consequences.** Adding or moving a page is one registry line and one `add_slot` call. Tests speak in addresses. During the transition the new frame and the old pages use two styles; light mode waits for Phase 3.
