---
title: Trust System
type: feature
status: IMPLEMENTED
tags: [feature, security, trust]
updated: 2026-11-14
code: [deadlock_fps/repos/trust.py, assets/trust/registry.json]
tests: [tests/test_repos_manager.py]
---

# Trust system

Labels: **OFFICIAL**, **VERIFIED**, **COMMUNITY**, **UNVERIFIED**. They describe an actual *review decision*, so they must not come from the hosting provider or from the repository itself ([[ADR-003 Trust comes from a bundled registry]]).

| Label | Means | How a repository gets it |
|---|---|---|
| OFFICIAL | published by the Toolbox project | listed in the shipped registry |
| VERIFIED | reviewed by the maintainers: contents inspected, publisher identified | listed in the shipped registry |
| COMMUNITY | known community-maintained source, files not individually reviewed | listed in the shipped registry |
| UNVERIFIED | everything else — **every repository a user adds** | default |

## Rules (all tested)
* A GitHub/GitLab address earns nothing; a fork or look-alike name (`deadlock-fps` vs `deadlock-fps-`) does not inherit a label.
* `trust`, `verified` or similar fields in an index are ignored.
* A locally imported index can never claim a remote identity (`local:` prefix is forced).
* If the registry is missing, damaged or contains an unknown label, **everything is UNVERIFIED** (fail safe).
* The registry changes only with an application update, so no remote party can promote a repository.

## Where it is shown
Trust column in the repository list and in search results, with the explanation as a tooltip and in the details panel. **Install-time warnings for unverified content are PROPOSED** ([[Installation Engine]]).

## Limits
* The registry currently holds **one entry** (the project's own repository). There is no review process yet, so no VERIFIED or COMMUNITY entries exist ([[Technical Debt]] #10). Trust is per repository, not per mod or per file hash.
* Labels are not cryptographically signed; the integrity of the registry is that of the application package ([[Security Model]]).

Related: [[Repository Manager]] · [[Manifest Specification]]
