---
title: Mod Store
type: feature
status: IMPLEMENTED
tags: [feature, discovery, store]
updated: 2026-11-14
code: [deadlock_fps/store/gamebanana.py, deadlock_fps/store/catalog.py, deadlock_fps/store/sync.py, deadlock_fps/store/install.py, deadlock_fps/store_service.py, deadlock_fps/pages/browse.py]
tests: [tests/test_store_client.py, tests/test_store_catalog.py, tests/test_store_sync.py, tests/test_store_install.py, tests/test_store_browse.py]
---

# Mod Store

Page: **Mods › Browse** (slot `store`; rebuilt on the new components on 2026-11-14, see [[Browse Page]]; before that it was stack index 15). A searchable local copy of the whole Deadlock catalogue on GameBanana, built from the reverse-engineering of the community reference app ([[Reference App Analysis]], [[ADR-012 Reimplement from public interfaces and copy nothing from the GPL reference]]). Design: [[ADR-011 The store is a local catalogue, not a repository provider]].

**How it works**
* **First run:** the page says the catalogue is not downloaded and what that costs (about 125 requests; measured 123 requests, 137 s). The user presses *Download the catalogue*; nothing happens before that. An interrupted download (rate limit, Stop, closing the app) is saved page by page and resumes where it stopped.
* **Afterwards:** *Check for new and updated mods* asks GameBanana for the most recently modified listings and stops at the first page it already knows (one request when nothing changed). If more than 20 pages changed, it falls back to a new full download.
* **Browse:** search by name, author, category, subcategory or tag (full-text, prefix, Arabic works); sort by recently updated, newest, or name; category and subcategory (for Skins these are heroes); adult listings (GameBanana's `hide`/`warn` visibility) and outdated mods are off by default; first 300 matches shown.
* **Read:** selecting a mod fetches its page after a short pause (cached for the session): description as plain text, likes, views, downloads, licence (Creative Commons name when stated), and each file with size, **MD5** and GameBanana's own antivirus verdict; up to four screenshots on request.
* **Trust:** every listing is labelled UNVERIFIED with the sentence "Community content that Toolbox has not reviewed" ([[Trust System]]).
* **The page (rebuilt in Phase 3 of the redesign, 2026-11-14: [[Browse Page]]; the paragraph below describes the earlier table-and-detail-pane page, whose behaviour the cards and the sheet keep):** a slim status line with one button (*Get the mod list* the first time, *Check for new mods* afterwards), one search box with the category filters under it, a list (*Mod, Hero / type, Author, Updated*: a skin shows its hero, a HUD or map its category) and a detail pane whose **first block is the file picker and the Install button**, then the description, the screenshots and the file facts. Mods already installed are marked *· installed* in green and the mark follows installs and removals. The trust line is plain ("From GameBanana. Made by the community; Toolbox has not reviewed it."); the first-download text says "about 2 minutes and 26 MB, once".
* **Install:** pick one of the mod's files (the first installable one is chosen) and press *Install*. It goes through the same engine as the Mod Hub ([[Installation Engine]]): the file is downloaded into a private folder, its MD5 is checked, the zip is inspected, and a preview shows exactly what would be copied with every warning. Only after the user confirms (and acknowledges the warnings, which the engine enforces) is anything copied into the game. `.zip` and `.vpk` files work; `.rar` and `.7z` are listed but cannot be installed yet. **Open on GameBanana** and **Show in Installed Mods** are the other buttons. Details: [[Task - Mod Store install]].

**Security.** GameBanana's JSON is untrusted: types and sizes checked, control and bidirectional-override characters removed, HTML reduced to plain text, image URLs kept only when https on a GameBanana host with a plain file name, every download and page address built from numeric ids, all SQL parameters bound, FTS input reduced to quoted word tokens, a damaged cache moved aside. All text is shown as plain text ([[Security Model]]). Installing adds: the download must end on a GameBanana host, the MD5 is checked, the zip is inspected, nothing is installed without the user's confirmation, and the preview names the source as UNVERIFIED.

**Evidence.** [[Task - Mod Store engine]] (VERIFIED: 79 tests, 15/15 mutations caught, a full live crawl), [[Task - Mod Store page]] (IMPLEMENTED: 21 page tests, rendered with live data in English and Arabic, not seen on a real display) and [[Task - Mod Store install]] (IMPLEMENTED: 33 engine tests and 11 page tests, 14 of 14 mutations caught; one real download installed and removed cleanly in a throwaway game folder; never run on a real game).

**Not built:** update checks for store mods (the Installed page says so); `.rar` and `.7z` files; multi-file VPKs (refused, as everywhere); Sounds, WIPs, Collections; popularity sort in the UI; pruning of listings GameBanana deletes. See [[Known Issues]] and [[Open Items and Next Steps]].

Related: [[Mod Hub]] · [[Repository Providers]] · [[Installation Engine]]
