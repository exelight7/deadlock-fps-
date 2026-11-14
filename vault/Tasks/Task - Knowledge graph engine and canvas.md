---
title: Task - Knowledge graph engine and canvas
type: task
status: IMPLEMENTED
tags: [task]
updated: 2026-11-14
implements: [Knowledge Graph]
code: [deadlock_fps/graph/model.py, deadlock_fps/graph/build.py, deadlock_fps/graph/layout.py, deadlock_fps/pages/map.py, deadlock_fps/vault.py]
tests: [tests/test_graph.py, tests/test_graph_ui.py]
---

# Task - Knowledge graph engine and canvas

Typed graph, builders from the catalogues, installed records and this vault, a grid-accelerated layout, and the interactive canvas ([[ADR-010 The graph is derived from real data and drawn with QPainter]]).

**Evidence.** 36 tests including one that builds the graph from this very vault and checks every note, edge and file path.

Implements: [[Knowledge Graph]].
