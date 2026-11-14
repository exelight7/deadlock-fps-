---
title: ADR-004 Translate only VPK release assets
type: decision
status: IMPLEMENTED
tags: [decision, security, providers]
updated: 2026-11-14
affects: [Repository Providers, Manifest Specification]
---

# ADR-004 · Provider translation accepts only `.vpk` release assets

**Context.** "Do not assume every GitHub repository has a compatible manifest" and "never silently interpret arbitrary files as installable mods". Yet users will paste plain GitHub repositories.

**Observation (live).** This project's own GitHub releases carry 26 `.zip` files, all application packages. A translator that listed zips as mods would have offered them for installation.

**Decision.** A release can be translated into a catalogue only through `.vpk` assets: Valve's package format, structurally validated before any install. `.zip` assets yield the class **MANUAL** with an explanation and a path forward (write a mapping index). The result is labelled TRANSLATED, carries `derived=True` on every mod, and records what is unknown (description, game compatibility, often hash).

**Consequences.** Some legitimate zip-only mod repositories need a mapping index. That friction is deliberate.

Affects [[Repository Providers]], [[Manifest Specification]].
