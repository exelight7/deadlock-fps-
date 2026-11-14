---
title: Repository Specification
type: spec
status: IMPLEMENTED
tags: [spec, repositories]
updated: 2026-11-14
code: [docs/REPOSITORY_SPEC.md, docs/repository-example/deadlock-repo.json, docs/repository-example/repository-list.json, deadlock_fps/repos/spec.py]
tests: [tests/test_repos_docs.py]
---

# Repository specification (pointer)

The authoritative document for independent developers is **`docs/REPOSITORY_SPEC.md`** in the repository (English, shipped in the package with the rest of `docs/`). It covers hosting options per provider, every field with limits, compatibility classes, shareable repository lists, trust, authoring advice, versioning rules and known limits.

This note exists to link it into the graph and to record how the document is kept true:

* The examples in `docs/repository-example/` are parsed by `tests/test_repos_docs.py`; the numbers quoted in the document (8 MiB, 5000 mods, 200 versions, 12 screenshots, 2 GiB, 8 mirrors) are asserted against the constants in `repos/spec.py`.
* Behaviour is described by [[Manifest Specification]]; hosting conventions by [[Repository Providers]]; labels by [[Trust System]].

**Gaps:** no machine-readable JSON Schema file (the validator is the reference); no published conformance-test corpus for third-party implementers.

Related: [[Repository Manager]] · [[Security Model]]
