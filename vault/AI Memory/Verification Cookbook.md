---
title: Verification Cookbook
type: guide
tags: [ai-memory, testing]
updated: 2026-11-14
---

# Verification cookbook: how things were checked, and how to do it again

Run from the project root. On Windows use `.venv/Scripts/python.exe`. Always set `QT_QPA_PLATFORM=offscreen` and `PYTHONIOENCODING=utf-8`.

## The standard gate (must be green before saying "done")
```bash
.venv/Scripts/python.exe -m unittest discover -s tests            # 393 tests, ~90 s; 1 expected error (Windows symlink privilege), 1 skip
.venv/Scripts/python.exe scripts/i18n_tool.py check               # "catalogues complete: 650 Arabic and 474 English source strings"
.venv/Scripts/python.exe scripts/check_vault.py                   # "vault consistent"
git ls-files --eol -m                                             # every touched file i/lf w/lf
```
One group: `-p "test_installer_*.py"`. One test: `-k name`. Output is huge on failure with PySide signature dumps: pipe through `grep -E "^(FAIL|ERROR|Ran|OK)"` and `cut -c1-240`.

## Mutation spot-checks (are the tests able to fail?)
Performance: `scripts/dev/mutation_perf.py <root>` (19 checks; 19 of 19 caught on 2026-11-14).
Stats: `scripts/dev/mutation_stats.py <root> [words]` (47 checks; 47 of 47 caught on 2026-11-14; the words pick mutations by description). Same rule: run nothing else in the tree while it works.
Store engine and install path: `scripts/dev/mutation_store.py <root>` is self-contained (29 checks; 29 of 29 caught on 2026-11-14). It edits source files temporarily and restores them in a `finally`: run nothing else in the tree while it works. `shot_store.py` renders 1950 px tall so the install row is visible.

`scripts/dev/mutation_check.py <repo root> "<test pattern>"` disables listed checks one at a time with regex substitutions, runs the matching tests and restores the file in a `finally`. Edit its `mutations` list for new safety code. Results in 2026-11: repository engine 6 checks (5 caught, 1 redundant); installer 8 checks (all caught after two isolating tests were added). Pattern: if a mutation is "missed", find out whether the check is redundant or merely masked by another check, and add a test that isolates it.

## Visual checks (every new page, English and Arabic)
* `scripts/dev/shot_mod_pages.py <root> <outdir> en|ar` builds a throwaway game with sample mods through the real engine and saves Hub, Installed, Compatibility, Downloads PNGs. `shot_repositories.py` and `shot_graph.py <root> <png> en|ar [select|expand]` do the Repositories and Graph pages. They set the app style (`Fusion`, `design.STYLE`, `dark_palette`), set `w.intro_played = True` (otherwise the intro curtain makes the frame black), and wait ~1.2 s for page transitions.
* `scripts/dev/shot_store.py <root> <png> en|ar [empty|live]`: the Mod Store page; `live` reads two real GameBanana pages (read-only) so the picture has real names, a real profile and real screenshots.
* `scripts/dev/shot_perf.py <root> <png> en|ar dialog|skipped|page`: the "What does this level change?" window and the Graphics page with its button.
* `scripts/dev/shot_stats.py <root> <png> en|ar empty|heroes|ranks|me|failed`: the whole window on the Stats page against a scripted fake of the server (no network, no real account number).
* Then **look at the PNG** (the Read tool shows images). Defects found this way in 2026-11: RTL selection loss, clipped table columns, overlapping labels, a scrolling rail, a toolbar too wide.
* Offscreen has no `→` glyph in hints; a real display was never checked.

## Live checks (real network; safe, read-only)
```python
from deadlock_fps.repos import UrllibTransport, RepositoryManager, RepositoryStore
# classify a repository against the real API (use a temp folder for the store)
m = RepositoryManager(RepositoryStore(tmp), UrllibTransport()); view = m.add_and_sync('https://github.com/exelight7/deadlock-fps-')
# stream a real small file through GitHub's redirect
UrllibTransport().download('https://github.com/exelight7/deadlock-fps-/releases/latest/download/SHA256SUMS.txt', tmp/'x', max_bytes=1<<20)
```
`scripts/dev/store_live_check.py <root>` runs a full GameBanana crawl into a throwaway folder (about 125 paced requests, ~2.5 minutes) and then a refresh; use it after touching `deadlock_fps/store/`.

`scripts/dev/real_install_check.py <root> <new empty folder>` installs **one real GameBanana file** into a throwaway game folder and uninstalls it. It downloads a file: **ask the user and name the file first**. Run it with `python -I`; delete the folder afterwards.

`scripts/dev/stats_live_check.py` calls the **public** statistics endpoints of api.deadlock-api.com (about ten requests, a throwaway cache, no account number) and checks the figures for sense; use it after touching `deadlock_fps/stats/`. A personal lookup is **not** part of it: `scripts/dev/stats_player_check.py <root> <account number> [days] [mode]` does one and **sends the account number**, so run it only with the owner's OK (it was run once on 2026-11-14 with the user's approval).

`scripts/dev/perf_facts.py <root> <catalogue.json> [--check]` regenerates (or, with `--check`, only compares) `deadlock_fps/perf/facts.py` from a catalogue file carrying Valve's convar dump. Read-only, no network.

Never point checks at private hosts; the transport refuses them anyway.

## Writing new tests
* Engines: no Qt; use `FakeTransport`/`ServingTransport`; build mods with `catalogue_mod`/`mod_document`; use `GameCase` for a game folder (it patches `deadlock_fps.core.ensure_closed` and exposes `self.running` to simulate the game running). Inject faults by patching `deadlock_fps.installer.engine.os.replace` (make the fault **one-shot** unless you also want the rollback to fail).
* Pages: create a `QApplication`, use the offscreen platform, call `QThreadPool.globalInstance().waitForDone()` then `processEvents()` a few times to settle jobs, patch `QMessageBox.question`, `QFileDialog.*`, `InstallPreview.exec`, `QDesktopServices.openUrl`.
* Windows-level tests must patch `QStandardPaths.writableLocation`, `deadlock_fps.ui.detect_games`, `deadlock_fps.mods.ModLibrary.discover`.
* Keep any user-visible string translated (`tr`) and add both catalogue entries.

## Documentation that is tested
`tests/test_repos_docs.py` parses `docs/repository-example/*` and checks the numbers in `docs/REPOSITORY_SPEC.md` against `repos/spec.py`. `tests/test_vault.py` runs the vault checker on the real vault. Change the spec, the code and these together.

## Regenerating this memory
`scripts/dev/conversation_to_markdown.py <exported zip> "vault/AI Memory/Raw"` rebuilds `Conversation (readable).md` from a session export (the `export_transcript` tool writes the zip to Downloads). Keep `Raw/` git-ignored.

Related: [[Testing]] · [[Environment and Pitfalls]] · [[00 Start Here]]
