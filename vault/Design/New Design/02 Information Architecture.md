---
title: 02 Information Architecture
type: design
status: PROPOSED
tags: [design, redesign, navigation]
updated: 2026-11-14
---

# 02 · Information architecture: 17 pages become 8 places

> **للمستخدم (بالعربي، ببساطة):** القائمة الجانبية صارت ٨ فقط: الرئيسية، المودات، الأداء، الإحصائيات، الكروس هير، السيرفرات، النسخ والاسترجاع، الإعدادات. الصفحات القديمة ما انحذفت وظائفها: دخلت كتبويبات داخل مكانها الطبيعي (مثلًا «المثبّتة» و«الفحص» و«السجل» داخل «المودات»). ما فيه وظيفة تشتغل اليوم تنحذف.

Part of the Phase 1 design ([[01 Principles]]). Mock-up: `docs/design-prototype/index.html`.

## The sidebar
Top group (what people come for), in this order: **Home, Mods, Performance, Stats, Crosshair, Servers.** Bottom group (pinned to the bottom): an **Update ready** entry that exists only when a new version of the app is available, then **Backups** and **Settings**, then the version number. No group headings: eight entries do not need them.

| Id | English | العربية | Tabs (id · English · العربية) |
|---|---|---|---|
| `home` | Home | الرئيسية | none |
| `mods` | Mods | المودات | `mods.browse` Browse تصفّح · `mods.installed` Installed المثبّتة · `mods.health` Check الفحص · `mods.activity` Activity السجل |
| `performance` | Performance | الأداء | `performance.level` Level المستوى · `performance.all` Every setting كل الإعدادات |
| `stats` | Stats | الإحصائيات | `stats.heroes` Heroes الأبطال · `stats.ranks` Ranks الرتب · `stats.me` My stats إحصائياتي |
| `crosshair` | Crosshair | الكروس هير | none (Shape, Outline, Movement are a control inside the page) |
| `servers` | Servers | السيرفرات | none |
| `backups` | Backups | النسخ والاسترجاع | none |
| `settings` | Settings | الإعدادات | `settings.general` General عام · `settings.game` Game اللعبة · `settings.protect` Protection الحماية · `settings.update` App update تحديث البرنامج · `settings.sources` Extra mod sources مصادر مودات إضافية · `settings.advanced` Advanced متقدّم · `settings.about` About حول |
| `map` | Project map | خريطة المشروع | none; not in the sidebar, opened from Settings › Advanced, has a Back arrow |

Ids are the names Phase 2 registers ([[06 Handoff to Build]]). A tab is addressed as `page.tab`. Settings shows its tabs as a list at the leading side of the page instead of a tab strip, because there are seven.

## Where every old page went
| Old page (stack number) | New home | What changes for the user |
|---|---|---|
| Home (0) | `home` | Three big cards for Mods, Performance, Stats; a "Needs your attention" list; three small cards for Crosshair, Servers, Backups. The game-folder controls move to Settings › Game; Home shows them only when no game is linked. |
| Performance / Graphics (1) | `performance.level` | Same slider, presets, view width, frame limit. The "What does this level change?" window becomes the second tab. |
| Performance Details window | `performance.all` | A tab instead of a separate window: the same table, filters and "leave out". |
| Mod Store (15) | `mods.browse` | The default tab of Mods. Mods are cards with a picture area; details open in a side sheet with **Install** first. |
| Source Mods / Mod Hub (10) | `mods.browse`, source switch | A switch "GameBanana · My sources" at the top of Browse, shown only when the user has added a source. Same cards, same sheet, same review dialog. |
| Installed Mods (11) | `mods.installed` | One list with a switch per mod and a "more" menu. Two folded sections under it: the classic pack and files Toolbox did not install. |
| Mods library, the four reference mods (2) | `mods.installed`, section "Classic pack" | Folded by default. Opens to the four mods, their tick boxes and "Add their files". |
| Inspector (7) | `mods.health` | Its findings for the classic pack join the same list as the other findings. |
| Compatibility (12) | `mods.health` | Called **Check**: a list of findings with one action each, then the game-version table. |
| Downloads (13) | `mods.activity` | Called **Activity**: what is downloading now, then the history. A small "1 download" pill appears in the top bar of every page while something downloads. |
| Sources / Repositories (9) | `settings.sources` | Called **Extra mod sources**, with the same plain explanation. Most people never open it. |
| Stats (16) | `stats` | Same three tabs; the filters sit in one row above the tabs' content. |
| Crosshair (5) | `crosshair` | Preview on one side, controls on the other, the ready designs open from one button. |
| Servers (4) | `servers` | One table; the block/allow actions sit in the sticky bar. |
| Recovery (3) | `backups` | Called **Backups**. |
| Updates (6) | `settings.update` | A tab of Settings. When an update exists, a sidebar entry "Update ready" and a line on Home lead to it. |
| Settings (8) | `settings.general`, `settings.game`, `settings.protect` | Language, look (system/dark/light), text size, less motion; game folder; the settings guard. |
| Graph (14) | `map` | Called **Project map**, opened from Settings › Advanced. |

**Removed (decoration or duplication, no function lost):** the breadcrumb "Workspace / …", the "Open source" chip (now Settings › About), the per-page hint line with arrows, the skyline banners, the page switcher at the top of the mod pages, the rail footer text and GitHub button (now About), the intro curtain.

**Not designed because it does not exist:** Collections has no entry ([[Collections]] is PROPOSED). When it is built it becomes a fifth tab of Mods, `mods.collections`.

## The top bar
Leading side: an optional Back arrow (only on `map`), then the page name. Trailing side: a download pill while something is downloading (press: `mods.activity`), then the **game pill**: "Game linked" with a green dot, "Game not linked" with an amber dot, "Game is running" with a blue dot (writing is paused). Pressing it opens Settings › Game. There is no search box in the bar: each page that searches has its own field where its results are.

## Paths for the three main jobs
* **Get a mod:** Home → *Browse mods* (or sidebar *Mods*) → press a card → *Install* → review → *Install*. Four presses after the catalogue exists.
* **Make the game faster:** sidebar *Performance* → move the slider → *Review and apply* → *Apply*. Three presses.
* **See the numbers:** sidebar *Stats* → *Load statistics*. Two presses. Stats works without the game.

## Rules for adding things later
1. A new feature is a tab or a section of an existing destination. A ninth sidebar entry needs a written reason in a decision note.
2. A destination has at most five tabs (Settings, shown as a list, is the exception).
3. Words on screen come from this note. Code and specifications keep their own words (*repository*, *manifest*).

Related: [[05 Screens]] · [[How The Code Works]] · [[Mod Store]] · [[Repository Manager]]
