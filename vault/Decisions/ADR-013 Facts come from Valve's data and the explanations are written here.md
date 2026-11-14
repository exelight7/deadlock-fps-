---
title: ADR-013 Facts come from Valve's data and the explanations are written here
type: decision
status: IMPLEMENTED
tags: [decision, performance, licence]
updated: 2026-11-14
affects: [Performance Details, Performance Tuning]
---

# ADR-013 · Facts come from Valve's data; the explanations are written here

**Context.** The user asked for the performance feature of the reference app ([[Reference App Analysis]]). Its performance catalogue bundles presets derived from GPL-3.0 projects and curated labels ([[ADR-012 Reimplement from public interfaces and copy nothing from the GPL reference]]). This app already has a recipe and an engine that writes it ([[Performance Tuning]]); what it lacked was **knowing what its recipe does**.

**Decision.**
* What is taken from the catalogue is only **facts about Valve's game**: a setting's name, Valve's flags, Valve's default and whether Valve still has it. They are written by a script into a generated file (`perf/facts.py`) that names its source, the build and the date, and can be re-checked against any catalogue (`--check`).
* **Every sentence the user reads is written for this project** (`perf/knowledge.py`). No label, description, preset or category of the reference is used.
* The user's recipe is **not changed**: the new tool only explains it and lets the user leave settings out. Whether to stop writing the ignored settings by default is left for a check in the real game.
* Facts that cannot be confirmed are shown as **Unverified**, not guessed; statuses say "Valve's data says…", never "the game does…".

**Consequences.** The window can be wrong only where Valve's data is stale or the flag does not mean what its name says. Both are visible and re-checkable. No GPL text enters the repository.

Affects [[Performance Details]], [[Performance Tuning]].
