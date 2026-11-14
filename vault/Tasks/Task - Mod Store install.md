---
title: Task - Mod Store install
type: task
status: IMPLEMENTED
tags: [task, store, installer]
updated: 2026-11-14
implements: [Mod Store, Installation Engine]
code: [deadlock_fps/store/install.py, deadlock_fps/installer/engine.py, deadlock_fps/installer/archive.py, deadlock_fps/installer/vpk.py, deadlock_fps/installer/updates.py, deadlock_fps/repos/model.py, deadlock_fps/mod_service.py, deadlock_fps/pages/browse.py, deadlock_fps/hub_ui.py, deadlock_fps/graph/build.py]
tests: [tests/test_store_install.py, tests/test_store_browse.py]
---

# Task - Mod Store install

> **للمستخدم (بالعربي، ببساطة):** هذه الملاحظة تشرح كيف يركّب البرنامج مودًا من المتجر: وش يصير بالترتيب، وإيش الحمايات، وإيش اللي ما جُرّب بعد. الخلاصة: ما يتغير شي في لعبتك إلا بعد ما تقرأ المعاينة وتوافق. ويشتغل مع ملفات `.zip` و`.vpk` فقط. وجرّبته على ملف حقيقي واحد (7 ميغا) داخل مجلد لعبة تجريبي ونجح، وكشفت التجربة خطأ صغيرًا أصلحته. لكن ما جرّبته على لعبتك الحقيقية.

The *Install* button of the [[Mod Store]] page. It uses the same engine as the Mod Hub ([[Installation Engine]]); the store only builds the three things that engine needs.

## What happens, in order
1. The user selects a mod; its page is fetched (files, MD5, GameBanana's scan verdict). The file picker chooses the first file Toolbox can install (`.zip` or `.vpk`). `.rar` and `.7z` files are listed as "not supported" and cannot be installed.
2. *Install* (the game folder must be linked, the game closed): `ModService.prepare_store` builds a pseudo-repository, a mod and a version from the page (`store/install.py`), then `Installer.prepare` runs: **download** to a private folder (the final host must be a GameBanana domain) → **MD5** check → **inspect** the zip (every entry; the `.vpk` files are *discovered*, at most 8) → **stage** as `pakNN_dir.vpk` → plan. The game is untouched so far.
3. The **preview** (`InstallPreview`, the same dialog as the Hub) shows the source as GameBanana / UNVERIFIED, the integrity line ("MD5 matched: detects a damaged download, not a deliberately changed one"), the files, overlaps and warnings. The Install button stays off until the warnings are acknowledged (the engine enforces this too).
4. Only after confirmation: `Installer.commit` (backup, journaled moves, verify, record). Success is announced only after the installed files were re-checked.

## Identities
* Repository id `store:gamebanana` (the prefix `store:` marks "installed from the store": no catalogue exists for it), name "GameBanana", trust always **UNVERIFIED** ([[Trust System]]).
* Mod id `gb-<GameBanana id>`; one mod, one version = the chosen file. Version text: the author's own when it is a valid version number (a leading `v` is dropped), otherwise the file's upload date (`YYYY.MM.DD`), otherwise `0.0.<file id>`.
* Installing a different file of the same mod is an *update* of the same record; the record keeps the file's download address (`.../dl/<file id>`).

## What changed in the code
| Where | Change |
|---|---|
| `store/install.py` (new) | the adapter: `build(profile, file)` → (repository, mod, version); `file_format` (`zip`/`vpk` or a reason code `rar`/`7z`/`other`); `version_text`; constants `STORE_ID`, `HOSTS` |
| `repos/model.py` | optional `Package.md5`, `Package.hosts`, `InstallSpec.discover` (defaults keep every existing caller working; not part of the published manifest specification) |
| `installer/archive.py` | `inspect_zip(..., discover=True)`: wanted = every regular `.vpk`; none is an error; more than 8 is an error; all other checks unchanged |
| `installer/vpk.py` | `md5_file` (marked `usedforsecurity=False`) |
| `installer/engine.py` | MD5 check when no SHA-256 exists; final-host check after redirects (then the next mirror is tried); `InstallPlan.md5_verified`; a warning text for the MD5 case |
| `installer/updates.py` | `STORE_PREFIX`; store mods report "unavailable" with the reason "Installed from the Mod Store. Updates for store mods are not checked yet" instead of the false "repository removed" |
| `graph/build.py` | store mods are labelled `MOD STORE`, not `SOURCE GONE` |
| `mod_service.py` | `prepare_store(profile, file_id, done, failed)` |
| `hub_ui.py` | the preview's integrity line for the MD5 case |
| `pages/browse.py` (was `store_ui.py`, rebuilt 2026-11-14: [[Browse Page]]) | file picker, Install, status line, progress and Cancel, the preview and commit steps, *Show in Installed Mods* |

## Evidence (IMPLEMENTED, not VERIFIED)
* 33 engine-level tests in `tests/test_store_install.py` (adapter, discovery, MD5 and host checks, install, update and uninstall through the real engine on a throwaway game folder, graph and update-status behaviour) and 11 page tests (now in `tests/test_store_browse.py`) (the whole user path: preview, accept, decline, no game, wrong checksum, unsupported file, busy, installed page).
* **14 more safety checks disabled one at a time** with `scripts/dev/mutation_store.py` (MD5 check, final-host check, the `endswith` host match, "no .vpk", the discovery cap, the adapter dropping the host list or the MD5, unsupported files looking installable, zip not discovered, trust label, the update note, the graph label, the page offering install for any file, the game-linked guard): **14 of 14 caught**; 29 of 29 together with the engine's 15.
* Existing tests for the installer, repositories, graph and pages (199 tests) still pass; the whole suite is 536 tests with only the known Windows symlink error and one skip.
* The page was rendered offscreen with live GameBanana data in English and Arabic (file picker and Install button visible).
* **A real download, 2026-11-14, with the user's explicit OK** (`scripts/dev/real_install_check.py`): mod 711387 "Pink Drifter", file 1801337 `pak52_dir_3154a.zip`, 7 493 240 bytes, through the real transport (the redirect chain `gamebanana.com/dl/…` → `files.gamebanana.com` → a `filecache….gamebanana.com` server passed the host check) into a **throwaway game folder** (never a real game). Downloaded in 19 s; MD5 matched; the zip held exactly one file, `pak52_dir.vpk` (28 612 194 bytes, 150 entries), which the engine installed as `pak01_dir.vpk`; the game folder was untouched until the commit; `gameinfo.gi` gained the addons path; the analysis found no problems; the uninstall moved the file to the recovery folder and left no record. The folder was deleted afterwards.
* **That run found a real bug before any download:** a version built from the file's upload date came out as `2026.08.29`, and the version rules refuse leading zeros (`08`). The earlier test used a date without zeros. Fixed (dates are written `2026.8.29`, which still sorts by date) and covered by a test over every day of a leap year; mutation-checked by hand.
* One check was platform-specific: Windows' `zipfile` turns a backslash in a member name into `/` when it reads the list, so the backslash case is tested only where it can occur; the name is never used as a path anyway (members are streamed to a staging name the installer chooses).

## Not verified / limits
* **Never run against a real Deadlock folder.** One real download was tried (above) and it had the simplest possible layout (a single VPK, nothing else). Other mods may not: a `_dir.vpk` with separate chunk files is refused, as everywhere in this installer, and bigger archives were not tried.
* MD5 is weak: it catches damage, not an altered file from whoever controls the download. GameBanana's own antivirus verdict is displayed, not relied on.
* `.rar` and `.7z` are not supported. No update checks for store mods. No dependency data (GameBanana has none). Reinstalling a mod after the author changed its files is manual.
* Every further real download, and any run on the user's real game folder, needs the user's explicit OK first (see [[Open Items and Next Steps]]).

Implements: [[Mod Store]] · [[Installation Engine]]. Decision context: [[ADR-011 The store is a local catalogue, not a repository provider]].
