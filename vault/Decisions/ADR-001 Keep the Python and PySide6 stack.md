---
title: ADR-001 Keep the Python and PySide6 stack
type: decision
status: IMPLEMENTED
tags: [decision]
updated: 2026-11-14
affects: [Architecture Overview, Dependencies]
---

# ADR-001 · Keep the Python and PySide6 stack

**Context.** The brief says to audit and evolve, not rebuild. The project is a working, tested (158 tests at the start) PySide6 app with a bespoke design system and Arabic/English UI, packaged for Windows and Linux.

**Decision.** Keep Python 3.12 + PySide6; add new code as new modules; no new dependencies ([[Dependencies]]).

**Consequences.** Fast path to a working platform; the dense legacy style and index-based navigation remain ([[Technical Debt]]). A rewrite would have discarded the verified safety machinery in `core.Studio`.

Affects [[Architecture Overview]].
