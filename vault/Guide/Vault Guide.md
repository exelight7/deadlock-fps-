---
title: Vault Guide
type: guide
tags: [guide, process, obsidian]
updated: 2026-11-14
---

# Vault guide

## AI memory
`vault/AI Memory/` holds the memory a new AI session needs (requirements, history, rules, pitfalls, internals). Start at [[00 Start Here]]. The repository root `CLAUDE.md` points every session there. `AI Memory/Raw/` (the raw transcript, 13 MB) is local only and git-ignored.

## Where this vault is and why

`vault/` inside the repository, so it is versioned with the code it describes ([[ADR-006 Vault lives in the repository]]). Open it in Obsidian with **Open folder as vault**: either `vault/` or the repository root works (the user opened the root, and the root `.obsidian/` is git-ignored). Nothing outside this folder is read or modified. The author's personal vaults were found on the machine and deliberately left alone.

## Conventions

* Markdown with YAML frontmatter: `title`, `type`, `status` (features, specs, tasks), `tags`, `code` (paths relative to the repository root), `updated`.
* `type` is one of `guide`, `architecture`, `feature`, `spec`, `decision`, `design`, `quality`, `roadmap`, `history`. The native Graph View colours nodes by these tags (`vault/.obsidian/graph.json`).
* Link with `[[Wikilinks]]` by note title. A feature links to its [[Architecture Overview]] module, to the decisions that shaped it, and to the spec that describes it. The links are the knowledge structure; [[Knowledge Graph]] will later read them.
* Statuses follow [[Status Legend]].
* One idea per note; long tables live in the note that owns the topic.

## Keeping it in sync

Each milestone ends with an [[Implementation Log]] entry and updates of every affected feature note. The test suite checks that the published repository specification and its examples match the code (`tests/test_repos_docs.py`); `scripts/check_vault.py` (run by `tests/test_vault.py`) fails when a wikilink or heading is missing, a status is invalid, or a note claiming IMPLEMENTED/VERIFIED lists a `code:` or `tests:` path that does not exist. It cannot judge whether a claim is *true*; that remains a review duty ([[Status Legend]]).
