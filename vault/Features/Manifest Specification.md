---
title: Manifest Specification
type: feature
status: IMPLEMENTED
tags: [feature, spec, repositories]
updated: 2026-11-14
code: [deadlock_fps/repos/spec.py, deadlock_fps/repos/model.py, deadlock_fps/repos/versions.py, docs/REPOSITORY_SPEC.md, docs/repository-example/deadlock-repo.json]
tests: [tests/test_repos_core.py, tests/test_repos_docs.py]
---

# Manifest specification (schema `deadlock-mod-repository`, version 1.0)

The versioned contract independent developers follow to publish a compatible repository. Authoritative text: [[Repository Specification]] (`docs/REPOSITORY_SPEC.md`). Executable form: `repos/spec.py`.

## Coverage of the requested manifest fields

| Requested | Field | Status |
|---|---|---|
| Unique ID | `mods[].id` | yes |
| Name, description, author | `name`, `summary`, `description`, `author` | yes |
| Version | `versions[].version` (SemVer-compatible, 1–4 parts) | yes |
| Game compatibility | `versions[].game.min_build / max_build / tested_build` (Steam build ids) | yes; see `repos/compat.py` |
| Package format | `package.format` = `vpk` \| `zip` | yes |
| Download URL, file size, SHA-256 | `package.url / size / sha256 / mirrors` | yes (`sha256` optional but warned about) |
| Installation instructions, target paths | `install.type = vpk`, `install.files[].source` | **partly**: the app chooses the destination on purpose ([[ADR-008 Mod folder and pak naming need verification]]) |
| Dependencies, conflicts | `dependencies[]`, `conflicts[]` with version ranges | parsed and validated; **not yet enforced** (needs [[Installed Mods]]) |
| License, changelog, screenshots | `license`, `changelog`, `screenshots[]` | yes |
| Original source URL, published date | `source_url`, `published` | yes |
| Trust metadata | *intentionally absent* | see [[Trust System]] |

## Properties
* **Forward compatible:** any `1.x` accepted; unknown fields ignored; unknown `package.format` / `install.type` keep the version visible but unsupported, with a reason. Another major is refused clearly.
* **Fault tolerant:** one bad mod/version is skipped with a warning; the rest loads.
* **Safe by construction:** HTTPS and public hosts only, no credentials; install sources are relative paths with a strict character set, **`.vpk` only**; sizes ≤ 2 GiB; text is plain text with control characters rejected; limits of 8 MiB / 5000 mods / 200 versions.
* The publisher cannot assert trust (tested).

## Evidence
24 tests cover versions, URL safety, the specification and game fit; 4 more tie the published document and its examples to the code, so the doc cannot drift. Six security checks were deliberately weakened to see whether a test notices: five made tests fail, one (explicit `..` rejection) was redundant with the path regex and is kept as defence in depth ([[Testing]]).

Related: [[Repository Providers]] · [[Repository Manager]] · [[Mod Lifecycle]]
