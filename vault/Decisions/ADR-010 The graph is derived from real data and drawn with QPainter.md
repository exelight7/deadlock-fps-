---
title: ADR-010 The graph is derived from real data and drawn with QPainter
type: decision
status: IMPLEMENTED
tags: [decision, graph]
updated: 2026-11-14
affects: [Knowledge Graph, Dependencies, Vault Guide]
code: [deadlock_fps/graph/build.py, deadlock_fps/pages/map.py]
tests: [tests/test_graph.py, tests/test_graph_ui.py]
---

# ADR-010 · The knowledge graph is derived from real data and drawn with plain QPainter

**Requirement.** A real, useful graph of actual project and mod relationships; "do not fill it with fake demo relationships"; no unnecessary dependencies.

**Decision.**
1. *Data:* the graph is built at runtime from the repository catalogues, the installed-mod records and the project vault (notes by `type`, wikilinks, `affects`, `implements`, and `code:` paths that exist). A relation whose far end is unknown becomes a visibly marked placeholder, never a silent drop and never an invention. There is no stored or hand-maintained graph.
2. *Rendering:* a `QWidget` that paints with `QPainter`: no graph or web-view dependency. A grid-accelerated force layout keeps 1 500 nodes within seconds; labels are level-of-detail limited.
3. *Structure:* groups (mod → versions, package → files, repository → mods) collapse, with edges re-routed to the visible ancestor and merged with a count; plain note links are hidden by default.
4. *Accessibility:* every relation is also readable as text in the side panel; keyboard navigation exists.

**Consequences.** The vault has to stay honest (the checker enforces structure); a note's `code:` list drives Module nodes, so a planned file does not appear until it exists. Catalogues above 400 mods are truncated with a visible note (installed first). The vault is read from the source tree or the packaged `vault/` folder; if it is missing the graph says so and shows only repositories and mods.

Affects [[Knowledge Graph]].
