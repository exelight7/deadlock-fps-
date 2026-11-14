---
title: 05 Screens
type: design
status: PROPOSED
tags: [design, redesign, screens]
updated: 2026-11-14
---

# 05 · Screens

> **للمستخدم (بالعربي، ببساطة):** كل صفحة مرسومة في النموذج بأربع حالات (ممتلئ، فارغ، تحميل، خطأ)، بالعربي والإنجليزي، داكن وفاتح. افتح `docs/design-prototype/index.html` بالمتصفح وغيّر من القوائم اللي فوق. الأرقام والأسماء في النموذج أمثلة فقط.

Part of the Phase 1 design ([[01 Principles]]). Places and names: [[02 Information Architecture]]. Parts: [[04 Components]].

## How to look at the mock-up
* Open `docs/design-prototype/index.html` in any browser (no server). The dark strip at the top is the **prototype's own controls** and is not part of the app: Page, State, Language, Theme, Accent, Window size (1180 × 760 or the 940 × 680 minimum). The sidebar, tabs, mod cards and the Install / Review buttons are clickable.
* Any view has an address: `index.html#page=mods&tab=health&state=error&lang=ar&theme=light`. Keys: `page`, `tab`, `state` (`filled`, `empty`, `loading`, `error`), `lang` (`en`, `ar`), `theme` (`dark`, `light`), `accent`, `size` (`std`, `min`), `over` (`mod`, `review`, `apply`, `done`).
* 48 reference pictures are in `docs/design-prototype/shots/`: every view filled in English-dark and Arabic-light, plus chosen states and overlays. `scripts/dev/design_shots.py` regenerates them or photographs any address.
* **Everything on screen is sample data.** The mock-up proves layout, words and states; it does not run the app's code. The fonts shown are whatever the viewer's PC has ([[03 Visual Language]]).

## The window
Native window frame (title, minimise, maximise, close: drawn by the system). Inside: **Sidebar** 216 at the leading side, then a column: **TopBar** 56, optional **Tabs**, the page content (the only part that scrolls), optional **ActionBar**. Content padding 24. Minimum 940 × 680.

## What "empty, loading, error" mean on every page
| State | Rule |
|---|---|
| Empty | The page has nothing to show yet. An EmptyState (or the page's own first-run card) says what will appear and offers the one action that fills it. Filters that find nothing use the same component with "Clear the filter". |
| Loading | Work the user started. Known length: ProgressBar with a count and Stop/Cancel when safe. Unknown or short: a busy button plus Skeleton rows where content will land. The rest of the page stays usable. |
| Error | A danger Banner at the top (or a danger EmptyState when the whole page could not load): what happened, that nothing was harmed, one action. If an older saved copy exists it is shown under the banner and marked as old. |
| No game linked | Pages that need the game show a warning Banner with "Link the game", keep their controls visible, and disable the action that writes. |
| Game running | The game pill turns blue ("Game is running"); pressing a writing action shows the danger Banner "Close Deadlock first. Nothing was changed." |

## Screen by screen
Pictures are named `shots/<view>.en-dark.png` and `shots/<view>.ar-light.png`.

### Home (`home`)
* **Filled:** three DoorCards in a row (Mods: "12 installed · 2 updates" → Browse mods; Performance: "Level 80 · Balanced" → Tune the game; Stats → Open stats). Then a flat Card "Needs your attention" with a count badge and ListRows, most serious first, each with one small button (mods switched off → Repair; mods with updates → See updates; app update → Update). The card is hidden when there is nothing. Then three small clickable Cards: Crosshair, Servers, Backups, each with one status line.
* **Empty (no game):** a Card "First, link your game" with *Find it automatically* (primary) and *Choose the folder*; the Mods and Performance doors are dimmed, Stats stays active; one line explains why. Picture: `shots/home.empty.png`.
* **Loading:** "Looking for Deadlock…" with a sliding ProgressBar; three Skeleton cards.
* **Error:** danger Banner "Deadlock was not found on this PC" naming where it looked, with *Choose the folder* and *Search again*.

### Mods › Browse (`mods.browse`)
* **Filled:** row 1: SearchField (grows), Select type, Select hero, Select order. Row 2: Chips "Hide outdated" (on) and "Show adult content" (off), then at the trailing side "6,104 mods · list checked 2 hours ago" and a ghost button *Check for new mods*. Then the ModCard grid (three columns at the minimum window, five at 1180). When the user has extra sources, a SegmentedControl "GameBanana · My sources" starts row 1.
* **Press a card:** the Sheet opens (`over=mod`, `shots/overlay-mod.png`): picture, author and type badges, **the file Select and the Install button first**, then the "Not reviewed" warning Banner, KeyValue facts (updated, file check, virus scan as GameBanana reports it, likes, licence), the description, *Open on GameBanana*, *Show pictures*.
* **Install:** the review Dialog (`over=review`, `shots/overlay-review.png`): mod and file, source with its "Not reviewed" badge, the file-check result, "What will be added to the game" (the exact path, monospace), any warning as a Banner, the acknowledgement Checkbox that enables *Install*.
* **Empty (first run):** EmptyState "Get the mod list first": about 2 minutes and 26 MB, once; nothing is downloaded before the press. One large primary button.
* **Loading:** a Card with "page 41 of 123", a ProgressBar, *Stop*, and the note that it continues next time; Skeleton cards below.
* **Error:** danger Banner "Couldn't reach GameBanana", the saved list stays usable underneath, *Try again*.

### Mods › Installed (`mods.installed`)
* **Filled:** a line "12 mods · 2 updates · 1 off" with *Check for updates* and the primary *Update all (2)*. A DataTable: Switch (on/off), mod name with "author · where it came from" under it, version (with "→ new version" when there is one), a status Badge (Update, Up to date, Source unreachable, Off), then *Update* when available and the "more" IconButton (Menu: Update, Previous version, Show files, History, Open its page, then Remove in danger). Under it a flat Card with two folded rows: **Classic pack (4)** and **Not installed by Toolbox (2)**. At the minimum window: `shots/minimum-window.ar.png`.
* **Empty:** EmptyState "No mods yet" with *Browse mods*.
* **Loading:** Skeleton rows; *Check for updates* is busy.
* **Error:** danger Banner "The list of installed mods couldn't be read": a copy was kept, the game files were not touched, *Open the folder*.

### Mods › Check (`mods.health`)
* **Filled:** "Checked a minute ago · game build 6857" and *Check again*. A List of findings, problems first, each with a coloured icon, a plain title, one sentence, and one action (*Repair*, *Show*); a last green row sums up the mods that are fine. Then a Card "Do they fit your game version?" with a small table (mod, made for, fit badge).
* **Empty (all clear):** EmptyState with a tick: "Everything looks fine", *Check again*.
* **Loading:** "Checking your mod files… 7 of 12", ProgressBar, *Cancel*, "Read-only: nothing is changed."
* **Error:** danger EmptyState "The check could not finish" with *Try again*.

### Mods › Activity (`mods.activity`)
* **Filled:** "Nothing is downloading right now." then a List "History", newest first: what happened, to which mod, when, from where.
* **Loading (a download is running):** a Card on top: the mod, "Downloading · 11.2 of 24.8 MB", ProgressBar, *Cancel*. The top bar of every page shows the "1 download" pill.
* **Empty:** EmptyState "Nothing has happened yet".
* **Error:** the failed item is the first history row, in the danger look, with the reason and *Try again*.

### Performance › Level (`performance.level`)
* **Filled:** one Card: SegmentedControl of presets (Balanced, Performance, Maximum) and the promise "Screen resolution and FSR/DLSS are never changed"; the level as a display number "80 / 200" with one sentence that describes it; the Slider with the end labels "Best looks" and "Most frames"; a row of neutral Badges that say what this level does (textures, shadows, fog, effects) and a LinkButton "See every setting (73)". Then two Cards side by side: **View width** (Slider plus number field) and **Frame limit** (Select plus Checkbox). ActionBar: a summary of what is pending, *Undo my changes* (ghost), *Review and apply* (primary).
* **Review and apply:** a review Dialog (`over=apply`, `shots/overlay-apply.ar-light.png`): a success Banner "The originals are saved first", a table of files and what changes, "Show every line", *Cancel* and *Apply*. Then a Toast "Applied. Start the game to see it." with *Undo*.
* **Empty (no game):** warning Banner "Link the game to apply"; the controls work; *Review and apply* is disabled.
* **Loading (applying):** the ActionBar shows a Spinner and "Saving the originals, then writing 2 files…".
* **Error:** danger Banner "Close Deadlock first" (`shots/performance-level.error.png`).

### Performance › Every setting (`performance.all`)
* **Filled:** one sentence that says what this is and that the status is Valve's data, not a test in the game. Four StatTiles (will be written, confirmed, the game ignores, not sure). A row: Select group, Switch "Only what the game ignores", then *Leave out the ignored ones* and *Write everything*. A DataTable: Checkbox "Write", the setting's name (monospace) with a plain sentence under it and an eye icon when it can change how much you see, Valve's value, Toolbox's value, a status Badge (Works green, Blocked red, Removed amber, Cheat-only amber, Unverified neutral; each with a Tooltip that defines it). The same ActionBar as the Level tab.
* **Empty:** "No setting matches" with *Clear the filter*. **Loading:** Skeleton rows. **Error:** warning Banner when the facts are for an older game build than the linked game.

### Stats (`stats.heroes`, `stats.ranks`, `stats.me`)
* **Shared filter row (Heroes and Ranks):** SegmentedControl 7 / 14 / 30 days, Select mode, Select rank; at the trailing side a Badge "Saved copy · 2 hours ago" and *Refresh* (or the primary *Load statistics* when nothing is loaded). Changing a filter never asks the server.
* **Heroes, filled:** SearchField and "432,845 matches · 44 heroes"; a DataTable: hero, matches, picked, win rate (bold; green or red only when the whole range is on one side of 50 %), the ConfidenceBar "How sure (95%)", KDA, net worth. One line under the table explains the colours.
* **Ranks, filled:** a DataTable: rank, a Bar for the share of players, the percentage; one line explains that a player is counted in the rank of each match.
* **My stats, filled:** an info Banner "This sends a Steam account number" (where it goes; nothing is saved); a TextField for the account with a help line, *Use my Steam account*, the primary *Look up*; its own SegmentedControl (All time, 30, 14, 7 days) and mode Select; four StatTiles (rank, matches, wins, win rate); a DataTable per hero: matches, your win rate, everyone's, the difference in green or red, KDA.
* **Empty:** EmptyState "Nothing loaded yet" that says exactly what is sent (`shots/stats-heroes.empty.png`); for My stats "Whose stats?".
* **Loading:** the button is busy, Skeleton rows or tiles.
* **Error:** danger Banner "The stats service didn't answer", the older copy stays visible with an amber "Old copy" badge. My stats: the field turns red with the reason (a profile *name* cannot be used).

### Crosshair (`crosshair`)
* **Filled:** a row: *Ready designs (50)* (opens a Dialog with a grid of designs), a Badge that names the current design, then *Save* and *Share code*. Two Cards side by side: **Preview** (the picture, always left-to-right, a Select for the background, a SegmentedControl 1× 2× 4×) and the controls (SegmentedControl Shape / Outline / Movement; colour swatches with a code field; Sliders with number fields; Switches). ActionBar: *Read from game*, *Bring back the last one* (ghost), then *Review and apply* (primary). At the minimum window the two cards stay side by side (each about 330 wide).
* **Empty:** warning Banner "No crosshair was read from the game yet" with the steps; designing and saving still work; applying is disabled.
* **Loading:** *Read from game* is busy. **Error:** danger Banner "Close Deadlock first".

### Servers (`servers`)
* **Filled:** a row: SearchField, Select region group, Select order, *Measure again*. A DataTable: Checkbox, region name with its short code (monospace, muted), servers, ping in ms (green, amber or red by speed, bold), a status Badge (Allowed with a tick, Blocked with the block icon). One muted line: this is the relay answer time, not the ping in a match. ActionBar: "2 selected", *Block these* (danger-quiet), *Allow only these*, then at the trailing side *Unblock everything* (ghost).
* **Empty:** EmptyState "Get the server list" with one primary button.
* **Loading:** ProgressBar "14 of 32"; rows not measured yet show a Skeleton in the ping cell.
* **Error:** danger Banner "Administrator permission was refused… Nothing was blocked."

### Backups (`backups`)
* **Filled:** a Card "Go back to the original game files": one sentence, the Checkbox "Keep changes made outside Toolbox", *Restore the originals* (danger-quiet; opens a confirm Dialog) and *Open the backups folder*. A flat Card "Undo one tool only": ListRows for Performance, Crosshair, Classic pack mods, Servers, each with *Review undo*. Two Cards side by side: "Move your settings" (*Save to a file*, *Load from a file*) and "Saved copies" (dated rows).
* **Empty:** EmptyState "Nothing to restore yet". **Loading:** a Card with a ProgressBar. **Error:** danger Banner "The game files changed outside Toolbox" that points at the Checkbox.

### Settings (`settings.*`)
A list of the seven sections at the leading side (180 wide), the section's content beside it (at most 760 wide). Settings rows are ListRows: title, one muted sentence, the control at the trailing side.
* **General:** Language (Select; "changes after the app restarts"), Look (System / Dark / Light), Text size (90 / 100 / 115 / 130 %), Less motion (Switch).
* **Game:** a Card "Where Deadlock is installed": PathField, *Choose*, *Find automatically*; KeyValue: game version, game state, Steam account folder. Empty: warning Banner "The game is not linked". Loading: *Find automatically* is busy. Error: the field is red: "Deadlock is not in this folder…".
* **Protection:** the Switch "Put my settings back after the game closes" with its condition (Toolbox stays open; never writes while the game runs); a row *Check and repair* with the last result.
* **App update:** filled: a Card "Toolbox 4.1.0 is ready" with the release notes, *Download and install* (primary), *Releases page*; rows: your version, "Check when the app starts". Empty: "You have the latest version", *Check now*. Loading: ProgressBar with megabytes and *Cancel*. Error: danger Banner "The download did not pass its check… Nothing was installed."
* **Extra mod sources:** the plain explanation of what a source is; a TextField for an address and *Add* (primary); a List: Switch, name, address (monospace), a Badge (number of mods, Official, Not reviewed, Off, "Didn't answer · saved list shown"), the "more" IconButton; *Refresh all*, *Load a list*, *Save my list*. Empty: EmptyState "No extra sources".
* **Advanced:** Switch "Show mod pictures while browsing" (off by default: see the decisions in [[Handoff - Phase 1 Design (Fable 5.2)]]); *Project map*; *Open the app data folder*.
* **About:** the mark and name, version, one sentence (free, open source, not affiliated with Valve), *GitHub*, *Licences*.

### Project map (`map`)
Back arrow to Settings › Advanced. A row: SearchField, Chips per kind with counts, *Fit*. The canvas fills the rest; the drawing itself stays the existing QPainter canvas, recoloured from tokens (source: accent, installed mod: success, author: warning, other: muted). Selecting an item opens a Sheet with its lines and its connections as text. Empty: "Nothing to draw yet". Loading: "Arranging 56 items…". Error: "The map could not be built".

## Not drawn in the mock-up (specified by reference)
The ready-designs Dialog of Crosshair, the confirm Dialog (drawn once in `components.html`), the Files and History dialogs of an installed mod (KeyValue plus a DataTable in a 600 Dialog), the open state of the two folded sections in Installed, the "Game is running" pill, the classic pack's "Add their files" flow, and the 115 % and 130 % text sizes. They use only components from [[04 Components]].

Related: [[06 Handoff to Build]] · [[Mod Store]] · [[Stats]] · [[Performance Details]]
