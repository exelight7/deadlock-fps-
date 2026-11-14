---
title: ADR-014 Statistics are fetched on request and nothing personal is kept
type: decision
status: IMPLEMENTED
tags: [decision, stats, privacy]
updated: 2026-11-14
affects: [Stats]
---

# ADR-014 · Statistics are fetched on request, and nothing personal is kept

**Context.** The reference app's stats module ([[Reference App Analysis]]) talks to the public Deadlock API and needs a Steam account number for the personal part. A Steam account number identifies a person. The project has a rule that nothing runs by itself ([[ADR-011 The store is a local catalogue, not a repository provider]]) and a rule against personal details leaving the machine without the user's say ([[User Profile and Working Rules]]).

**Decision.**
1. **No automatic requests.** Opening the page, changing a filter or starting the program asks the server for nothing. The page may show what is already saved on disk. A request starts only from a button.
2. **Two kinds of request, kept apart.** The *public* calls (meta, rank spread, names) carry only the period, the mode and the rank. The *personal* calls carry one account number and are made only from **Look up**; the page says what it sends before the button and the engine refuses anything that is not a plain 32-bit number.
3. **Nothing personal is saved.** The cache holds public answers only. A player's answer lives in memory until the page is closed. The account number is not stored in settings, the cache or the workspace file. (The "use my Steam account" button reads the number from the user's own Steam folder at the time it is pressed and fills a text field; it sends nothing.)
4. **Fixed host, strict reading.** The host is a constant. Responses are treated as untrusted data ([[Security Model]]).
5. **Tests do not send a real account number.** The engine and the page are tested against a fake server shaped from the published schemas. A live check of the personal calls needs the user's explicit OK.

**Consequences.** The first look at a filter costs one button press. The page can be wrong only where the community service is. A user who never presses **Look up** never sends anything about themselves.

Affects [[Stats]].
