---
title: Dependencies
type: architecture
tags: [architecture, dependencies]
updated: 2026-11-14
code: [requirements.txt, build.py, THIRD_PARTY.md]
---

# Dependencies

## Runtime (`requirements.txt`)

| Package | Version | Used for |
|---|---|---|
| PySide6 | 6.11.2 | the entire UI, Qt Network in the update client |
| psutil | 7.2.2 | detecting a running game, disk partitions |

## Build

PyInstaller (`build.py`, onedir, `--add-data assets`). Everything under `assets/` ships, which is why the [[Trust System]] registry is at `assets/trust/registry.json`.

## Added by this work

**None.** The repository engine uses only the Python standard library: `urllib`, `http.client`, `ssl`, `socket`, `ipaddress`, `json`, `hashlib`, `dataclasses`. This follows the instruction not to add frameworks unnecessarily and keeps the PyInstaller bundle unchanged. Reasoning for not reusing Qt Network is in [[ADR-005 Standard-library HTTP with a pinned connection]].

## Third-party content
Fonts (Noto Sans, Reem Kufi — OFL), flag icons (MIT). See `THIRD_PARTY.md`.

## Observations
* Python 3.12 is the interpreter of the project's virtual environment; the engine uses `X | None` annotations and `str.removeprefix`, so 3.10+ is required.
* No test dependency beyond `unittest`.

Related: [[Architecture Overview]], [[Technical Debt]].
