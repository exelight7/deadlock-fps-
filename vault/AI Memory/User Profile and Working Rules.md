---
title: User Profile and Working Rules
type: guide
tags: [ai-memory, preferences]
updated: 2026-11-14
---

# The user, and how to work with them

Only what was observed in the sessions. No personal details beyond what the work needs.

## Who
* Project owner of `exelight7/deadlock-fps-` on GitHub. Builds game tools; has several Obsidian vaults for **game Arabization projects** (a `_Brain` vault, a game-specific vault, a skills folder) and has Arabization-related skills installed, so game localization is a real part of their work. These vaults are personal and unrelated: **never read from or write to them, and never change Obsidian's global config** ([[ADR-006 Vault lives in the repository]]).
* Writes in a Gulf-style Arabic dialect (e.g. "ابيك", "بسوي", "ما اعجبني") and fluent English. After the first English brief they wrote "عيد سوالك تكلم معي عربي" (repeat what you said, talk to me in Arabic). **Reply in Arabic from then on.** Keep code, identifiers, file names, commit messages and the English parts of the product in English.

## How they communicate
* Short, direct, sometimes with typos. They give ambitious goals ("make it something big") and expect autonomous work, not questions about ordinary choices.
* They react to the *result*, not the process: after the app ran they said they did not like it, and did not say why. Ask a specific, concrete question when that happens (what they saw, which page), rather than guessing.
* The harness sometimes tells the assistant "the user hasn't heard from you in a while". Give a one-line status (what is being done now) and continue.

## Working rules (from the brief and from what worked)
1. **Honesty over polish.** Never call something implemented or verified without evidence; downgrade statuses openly; say what was not tested ([[Status Legend]]).
2. **Real functionality first.** No fake implementations, no nonfunctional buttons (Collections has no nav entry because it does not exist).
3. **Preserve working features.** The four reference mods, graphics tools, crosshair, servers and update centre must keep working; their tests must stay green.
4. **Security is not negotiable.** HTTPS only, hash verification, archive inspection, backups and rollback, no execution of downloaded files ([[Security Model]]).
5. **Obsidian is mandatory** and must be updated with every significant change; `python scripts/check_vault.py` has to pass ([[Vault Guide]]).
6. **Do not publish.** No commit, push, tag, release or PR unless the user explicitly asks. When asked to commit, end the message with the attribution line the harness provides (Co-Authored-By: Claude Sonnet 5.5, at the time of writing).
7. **Ask only for real decisions.** Pick sensible defaults, document them as an ADR, move on.
8. **Verify like a skeptic.** Mutation-check security code, render every new page in English and Arabic, run real network checks where safe ([[Verification Cookbook]]).
9. **Do not touch** the user's unrelated files; do not put personal details (name, email) into the repository, the vault or any request to an outside service.

## Reply style that worked
* Arabic, structured with short headings and bullets; lead with what is done and what is not; list limits and risks plainly; end with the single most useful next step.
* No long preambles. Numbers instead of adjectives ("393 tests, one environmental failure").
* **Plain words (2026-11-14).** After a reply full of technical terms the user wrote that they did not understand and asked to continue and document everything in the vault. Keep chat answers short, in simple Arabic, one idea per line, no jargon without a half-sentence explaining it; put the technical detail in the vault.

Related: [[00 Start Here]] · [[Session History]]

## Plain words in the product (2026-11-14)
The user said the word "repositories" (المستودعات) was not understandable to them and asked for the store to be simpler. In the interface say **sources** (مصادر), explain a page in one plain sentence at its top, and put the thing the user came for first (for the store: Install under the mod's name). Technical words stay in code, specifications and notes ([[Mod Store]], [[Repository Manager]]).
