---
title: Repository Search
type: feature
status: IMPLEMENTED
tags: [feature, repositories, search]
updated: 2026-11-14
code: [deadlock_fps/repos/search.py, deadlock_fps/repos/compat.py]
tests: [tests/test_repos_manager.py, tests/test_repos_ui.py]
---

# Repository search

Pure functions over the cached catalogues of **enabled, compatible** repositories (native or translated, status ok or stale-error). Works offline and instantly.

* **Matching:** every word must match; weights name 5 > id 4 > categories/tags 3 > author 2 > summary/description 1, with a bonus for prefix matches.
* **Filters:** category, repository, trust label, "installable only" (latest stable version has a package and is not unsupported or yanked).
* **Sorting:** relevance (ties broken by trust, then name), name, recently updated, repository, largest download.
* **Same mod in two repositories** appears as two hits, one per repository — the user can see which source each comes from. Grouping belongs to the [[Mod Hub]].
* **Game fit** (`compat.fit`): compatible / untested / incompatible / unknown against a Steam build id; *unknown* is returned whenever either side is missing. The UI does not use it yet.

In the interface this is the lower panel of the Repositories page ([[Repository Manager]]), capped at 500 rows with a note.

Related: [[Mod Hub]] · [[Manifest Specification]]
