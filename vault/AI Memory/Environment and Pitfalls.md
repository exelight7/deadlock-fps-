---
title: Environment and Pitfalls
type: guide
tags: [ai-memory, environment]
updated: 2026-11-14
---

# Environment and pitfalls (read before running anything)

## The machine
* Windows 11 Pro. Project folder: `<home>\Videos\DEADLOCK\deadlock-fps--main` (a git repo, branch `v3.5.5`, remote `exelight7/deadlock-fps-`). The harness offers **PowerShell** (primary) and **Git Bash**; each has its own syntax.
* Python 3.12.10; the project's virtual environment is `.venv`: use `.venv/Scripts/python.exe` (PySide6 6.11.2, psutil 7.2.2, PyInstaller). System Python 3.12 also exists but lacks the dependencies.
* The game *Deadlock* itself is **not** known to be installed or linked; the app was only run with no game linked. Nothing in this work has touched a real game folder.
* Network works for public GitHub and GitLab APIs (unauthenticated: 60 requests/hour on GitHub). A web search tool exists (deferred; load it with ToolSearch).

## Obsidian
* Obsidian is installed. Its registry lists personal vaults (Arabization `_Brain`, a game vault, `C:\skills`): **never touch them or Obsidian's global config** ([[User Profile and Working Rules]]).
* On 2026-11-14 the user **opened the project root itself as a vault** (registered as `deadlock-fps--main`), so the root contains a local `.obsidian/`. Consequences: they see the whole repo in the file explorer; the project notes are under `vault/`; the memory is under `vault/AI Memory/`.
* Settings applied for that vault: `app.json` ignores `dist/`, `build/` and `vault/AI Memory/Raw/` (build copies of docs and the huge raw transcript would pollute search and graph); `graph.json` colours notes by tag. `.obsidian/` is git-ignored (per-user UI state).
* Wikilinks resolve by note *title* (file name) across the whole vault. The repository checker (`scripts/check_vault.py`) fails on broken links.

## Scripting pitfalls that bit repeatedly
1. **LF vs CRLF.** The repo is LF. Python `Path.write_text` on Windows writes CRLF and turns a 3-line edit into a whole-file diff. Always `path.write_bytes(text.encode('utf-8'))`. Check with `git ls-files --eol`; to normalise, replace `b'\r\n'` with `b'\n'`.
2. **Bash heredocs mangle backslashes** (`\n`, `\t`) inside Python strings, and `'EOF'` heredocs with odd quoting can break the shell. Put scripts in files (the scratchpad folder) and run them, or use the Edit tool for lines that contain escapes. Git Bash maps `/tmp` to a Windows temp folder that Python can read.
3. **Drive-letter colons** break `${var%%:*}` style splitting in shell; use another delimiter.
4. **The Write tool refuses to overwrite a file that changed on disk since it was read**; for notes edited by scripts, stage new content elsewhere and copy it with a script, or Read first.
5. The Edit tool needs the exact text including tabs; tab characters in `kv.py` bit once. Prefer line-based edits in a script for such files.
6. The harness adds notes "file changed on disk since you last read it" after scripted edits: harmless when you made the change.
7. The scratchpad directory is **per session and temporary**. Anything worth keeping goes into the repo (`scripts/dev/`, the vault).
8. Do not run interpreters from inside a downloaded/untrusted directory; downloads go in their own new empty folder.
9. (Stats window tests patch the transport and both `writableLocation` calls; copy that when a test builds the real `Window` and the code under test could make a request.) Tests that load `Window` use the real AppData unless `QStandardPaths.writableLocation` is patched (`patch('PySide6.QtCore.QStandardPaths.writableLocation', return_value=folder)`); the language probe test does that. Also patch `deadlock_fps.core.ensure_closed` and `deadlock_fps.ui.detect_games` in new window tests.

## Qt / PySide6 pitfalls found
* `QTableWidget.selectRow()` selects nothing in a right-to-left layout; use `setCurrentCell(row, col)`.
* Numbers, dates, addresses inside RTL tables scramble; wrap with LRM (`'\u200e…\u200e'`, helper `ui_common.ltr`).
* A page's `parent` argument must be a real `QWidget` (tests that fake the window must subclass `QWidget`).
* Page transitions animate for ~0.5 s; offscreen screenshots taken immediately capture a half-faded blend: wait ~1.2 s while pumping events.
* `QUrl.toString()` decodes percent-escapes; assert on `bytes(url.toEncoded())`.
* `QDesktopServices.openUrl` should be patched in tests; offscreen runs have no `→` glyph in the bundled font (hint lines show boxes offscreen; a real display may fall back to a system font, unchecked).
* PySide `Job`/`QRunnable` wrappers must be kept referenced until finished (the services keep a list).

## i18n rules (a test enforces them)
* Source strings live in the language the module was born in: Arabic for most old modules, **English** for `crosshair*`, `repo_ui`, `hub_ui`, `mod_service`, `graph_ui` (listed in `ENGLISH_FILES` in `scripts/i18n_tool.py`). Every `tr('…')` needs an entry in `lang_ar.py` (English source) or `lang_en.py` (Arabic source) with the same `{0}` placeholders. `python scripts/i18n_tool.py check` lists what is missing.
* Engine error messages (`repos/`, `installer/`) are English diagnostics and are *not* translated; the UI adds a translated lead sentence by error `code`.
* `scripts/i18n_tool.py` reads the top-level modules **and** the subpackages listed in `TRANSLATED_SUBPACKAGES` (`perf`, `store`). Before 2026-11-14 it read only the top level, so a `tr()` string in a subpackage was never checked. A new subpackage that shows text to the user must be added to that tuple (and its English-source files to `ENGLISH_FILES`).

## The harness (Claude desktop app, Code tab)
* Keep a task list with `update_plan` (first call alongside the first tool call) and end a turn that changed files with `wrap_up`; then write the answer. Do not start sessions or commits unprompted.
* Long silent work triggers a "user hasn't heard from you" nudge: say in a few words what you are doing and continue.
* Tools worth knowing: `mcp__ccd_session_mgmt__export_transcript` (exports this session to Downloads as a zip), `Artifact` (publishing pages; not used), the in-app browser, computer-use (not used).

Related: [[00 Start Here]] · [[Verification Cookbook]] · [[Known Issues]]
