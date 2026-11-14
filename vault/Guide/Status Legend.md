---
title: Status Legend
type: guide
tags: [guide, process]
updated: 2026-11-14
---

# Status legend

Every feature, spec and task note carries `status:` in its frontmatter. The meaning is strict, because a vault that over-claims is worse than none.

| Status | Means |
|---|---|
| `PROPOSED` | Designed or wished for. **No code exists**, or only a stub. Never describe it as working. |
| `IN PROGRESS` | Code exists in the repository but is incomplete or not yet tested. |
| `IMPLEMENTED` | Code exists and automated tests cover it and pass. It has **not** been exercised for real (real network, real game folder, real display), or only partly. |
| `VERIFIED` | `IMPLEMENTED`, **and** exercised end to end against the real thing at least once, with the evidence written in the note. |

Rules:

1. If a note says `IMPLEMENTED` or `VERIFIED`, the `code:` frontmatter lists the files, and those files exist.
2. A downgrade is never silent: change the status and add a line to [[Implementation Log]].
3. When code and note disagree, the code is right; fix the note.

See [[Vault Guide]] for how notes are written.
