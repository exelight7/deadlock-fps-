---
title: Knowledge Graph
type: feature
status: IMPLEMENTED
tags: [feature, graph]
updated: 2026-11-14
code: [deadlock_fps/graph/model.py, deadlock_fps/graph/build.py, deadlock_fps/graph/layout.py, deadlock_fps/pages/map.py, deadlock_fps/vault.py]
tests: [tests/test_graph.py, tests/test_graph_ui.py]
---

# Interactive knowledge graph

Page index 14 (rail label **Graph**). It draws what the application and the project really contain; nothing is filled in ([[ADR-010 The graph is derived from real data and drawn with QPainter]]).

## Nodes and relations (all derived)

| Node | From |
|---|---|
| Repository, Mod, Version, Author, Game version | the saved catalogues and the installed-mod records |
| Feature, Decision, Task, Documentation | the notes of this vault, by `type` |
| Module | source files named in feature notes' `code:`, only if the file exists, grouped by package |

Relations: Repository *publishes* Mod · Mod *has version* Version · Mod *depends on* / *conflicts with* Mod (from the newest version; an unknown target becomes a marked placeholder) · Version *supports* Game version · Mod *by* Author · Module *contains* Feature · Feature *implemented by* Task (`implements:`) · Documentation *describes* Feature · Decision *affects* note (`affects:`) · plain links between notes (hidden by default; dense). Installed mods carry a green ring; PROPOSED nodes a dashed ring; withdrawn, source-gone and not-in-any-catalogue nodes an amber one.

## Interaction
Pan (drag), zoom around the cursor (wheel, `+`/`-`), fit (`F`), select a node (click or `Tab`/`Shift+Tab`), highlight its relations and dim the rest, **focus mode** (only the selection and what it touches), search (matches halo; `Enter` cycles; a hit inside a folded group lights the group), per-kind filters with live counts, double-click or `Enter` to expand or collapse a group (versions fold into mods, files into packages by default), expand/collapse all. The details panel lists the node's lines and a clickable list of its connections, so every relation is readable as text. Navigation: repository → Repositories page, mod → Mod Hub filtered to it, note → Obsidian (`obsidian://open?path=`, falling back to the file), module → the source file.

Layout is a force-directed layout with a spatial grid, deterministic, incremental (an expanded group settles beside its parent without scrambling the rest), capped at 400 mods (installed first) with a visible note.

## Evidence
36 tests: model operations, builders (including a test that builds the graph from **this vault** and checks every note, edge and file path), layout properties (determinism, cooling, separation, 1 500 nodes inside a time budget), and the canvas driven with real mouse, wheel and key events. Rendered offscreen with the real vault plus a sample catalogue and inspected. Not run on a real display; no accessibility audit with a screen reader.

Related: [[Vault Guide]] · [[Repository Manager]] · [[Design System]]
