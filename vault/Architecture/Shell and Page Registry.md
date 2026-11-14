---
title: Shell and Page Registry
type: architecture
status: IMPLEMENTED
tags: [architecture, ui, redesign, shell]
updated: 2026-11-14
code: [deadlock_fps/shell/registry.py, deadlock_fps/shell/tokens.py, deadlock_fps/shell/theme.py, deadlock_fps/shell/components.py, deadlock_fps/shell/style.qss, deadlock_fps/ui.py, deadlock_fps/shell/base.py]
tests: [tests/test_shell.py]
---

# Shell and page registry (redesign, Phase 2)

> **للمستخدم (بالعربي، ببساطة):** البرنامج صار يعرف صفحاته بأسماء بدل أرقام. فيه قائمة وحدة فيها كل الصفحات، والقائمة الجانبية والتبويبات تنبني منها. الألوان والمقاسات تجي من ملف التصميم مباشرة. الصفحات القديمة شغالة داخل الإطار الجديد لين تنبني من جديد.

Built in Phase 2 of [[Redesign Plan]] from the contract in [[06 Handoff to Build]]. Decision: [[ADR-015 Pages are addressed by name through one registry]].

## The parts
| Part | File | What it does |
|---|---|---|
| Page registry | `deadlock_fps/shell/registry.py` (no Qt) | `Page(id, title, group, icon, tabs, slot, hint)`, `Tab(id, title, slot, hint)`, `Registry.register/get/group/resolve/address_of/slots/addresses`, `default_registry()` (the 9 places of [[02 Information Architecture]]), `FLAGS` (start-up flags → addresses), `LEGACY_SLOTS` |
| Tokens | `deadlock_fps/shell/tokens.py` + `tokens.json` (no Qt) | `Theme(mode, accent, scale)`: `t['color.bg.surface']`, `t.px('space.4')` (scaled by text size), `t.qss(name)`, `t.render(template)` (an unknown name raises), `rgba/qss_color/argb` (the one place `#RRGGBBAA` is converted) |
| Theme (Qt) | `deadlock_fps/shell/theme.py` | `apply(app, mode, accent, scale)` re-applies the stylesheet at once, `current()`, `choice()`, `color(name)` → `QColor`, `watch(widget, method)` (weakly held; called after every switch), `icon(name, token, size)` (tinted, `chev/back/ext` mirrored in right-to-left), `apply_direction(app, rtl)`, `dark_title_bar(window, dark)` (Windows DWM; does nothing elsewhere) |
| Stylesheet | `deadlock_fps/shell/style.qss` | a template with token names in braces; rules match `*[component="Button"][variant="primary"]` |
| Components | `deadlock_fps/shell/components.py` | the 39 names of [[04 Components]] (`COMPONENTS`); `set_props(widget, variant=…, state=…)` re-polishes |
| Icons | `assets/icons2/*.svg` | the 31 mock-up icons written by `scripts/dev/export_icons.py` (`--check` compares) |
| Window | `deadlock_fps/ui.py` | `Window(registry=None)`: `Sidebar` of `NavItem`s from the `main` and `bottom` groups, `TopBar` (title, the old game chip), `Tabs`, the stack of slots |
| Base and motion | `deadlock_fps/shell/base.py`, `deadlock_fps/shell/motion.py` | fonts, the dark palette for native dialogs and the emblem; the page hand-over and the launch reveal (all that is left of the old `design.py` / `motion.py`) |

## Addresses and slots
* An **address** is `page` or `page.tab`: `home`, `mods.health`, `settings.update`. `navigate(address)` is the only way to change page; a number raises `TypeError`, an unknown name `KeyError`.
* A **slot** is the name of a widget the window built (`window.slots['compatibility']`). A tab (or a page without tabs) points at one slot. A page with one tab shows no tab row; a page with `section_list=True` (Settings) shows its tabs as its own list.
* State after a move: `window.current_address` (always with the tab, e.g. `mods.browse` for `mods`), `window.current_slot`, `window.nav[page_id].isChecked()`, `window.tabs.current()`.
* `Ctrl+Tab` / `Ctrl+Shift+Tab` move between tabs. An app update puts a dot on **Settings** and on its **Update** tab (`show_update_dot`).

## The pages (all of them rebuilt, Phase 3 finished)
| Address | Slot | Module |
|---|---|---|
| `home` | `home` | `pages/home.py` ([[Home Page]]) |
| `mods.browse` · `mods.installed` · `mods.health` · `mods.activity` | `store` · `installed` · `compatibility` · `downloads` | `pages/browse.py` + `browse_host.py` + `sources.py` ([[Browse Page]]), `installed.py` + `classic.py` ([[Installed Page]], [[Classic Pack and Sources]]), `check.py`, `activity.py` |
| `performance.level` · `performance.all` | `graphics` · `perf_all` | `pages/performance.py` ([[Rebuilt Pages - Performance to Map]]) |
| `stats.heroes` · `stats.ranks` · `stats.me` | `stats` · `stats_ranks` · `stats_me` | `pages/stats.py` ([[Stats]]) |
| `crosshair` · `servers` · `backups` | `crosshair` · `servers` · `recovery` | `pages/crosshair.py`, `pages/servers.py`, `pages/backups.py` |
| `settings.general` · `.game` · `.protection` · `.update` · `.sources` · `.advanced` · `.about` | `settings` (one slot; the page has `section_list=True`, so the window draws no tab bar and `SettingsPage.show_section()` follows the address) | `pages/settings.py`, `pages/update.py`, `pages/source_list.py` |
| `map` (hidden from the sidebar; Settings › Advanced opens it, the top bar has Back) | `graph` | `pages/map.py` |

Flags: `--crosshair` → `crosshair`, `--updates` → `settings.update`, `--inspector` → `mods.health`, `--mods` → `mods.installed`, `--install` → `settings.update` then installs the downloaded copy.

The top bar carries a `GamePill` (`window.game_pill`, states `none`, `linked`, `running`); pressing it opens Home with the link card visible. The window has no hero banner, hint line, status line or action bar any more: each page draws its own, and `Window.notify(text)` shows a passing toast.

## Look (theme, accent, text size)
* Saved in `workspace.json` as `look: {mode, accent, scale}`; read by `ui.start_look()` before the window opens; `Window.set_look(mode=…, accent=…, scale=…)` switches at once and saves. Bad values fall back to dark, blue, 100.
* **Every page follows the theme.** Settings › General has the look (System / Dark / Light) and the text size (90 / 100 / 115 / 130 %); both switch at once and are remembered with `less_motion` and `pictures` in the same `look` object (`set_look` updates it, it never replaces it).
* Fonts: `font.family.ui` is an ordered list; IBM Plex is not bundled (user decision pending), the bundled Noto faces are used.

## How to add a page (for Phase 3)
1. Build the widget from `shell.components`.
2. In `Window.build_slots()` (or a builder method in a new module), call `self.add_slot('<slot>', widget)`.
3. In `default_registry()` point the page or tab at `'<slot>'` (new tab: add a `Tab(id, tr(title), slot, tr(hint))`). Titles go through `tr()`; add the English or Arabic text to `lang_en.py` / `lang_ar.py`.
4. Navigate with `window.navigate('<page>.<tab>')`; test with `current_address` / `current_slot`.
5. When a temporary tab is replaced, remove its slot from the registry and its builder; `build_slots()` refuses to start if the registry names a slot with no widget.

## Checks
`tests/test_shell.py` (23 tests): the registry against the design ids, every old page reachable, the token copy identical to `docs/design-prototype/tokens.json`, every token in every theme/accent/size, the stylesheet has no unfilled names, every component name exists and builds, states, theme switching re-applies and repaints, mirrored icons, navigation by name in the real window, the look saved, and a scan that no module calls `navigate` with a number.

Related: [[How The Code Works]] · [[Architecture Overview]] · [[Design System]] · [[Handoff - Phase 2 Infrastructure (Opus 5.5)]]
