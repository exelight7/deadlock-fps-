---
title: Handoff - Phase 2 Infrastructure (Opus 5.5)
type: guide
tags: [handoff, redesign, infrastructure]
updated: 2026-11-14
---

# Handoff · Phase 2 · Infrastructure (Opus 5.5, low effort)

> **للمستخدم:** بعد ما يقول Fable **`✅ المرحلة 1 انتهت (Fable 5.2)`**، افتح دردشة جديدة، اختر **Opus 5.5** (جهد low)، والصق البرومت. لما يخلص لازم يختم بـ **`✅ المرحلة 2 انتهت (Opus 5.5)`**. بعدها افتح دردشة مع **Sonnet 5.5** وادخل [[Handoff - Phase 3 Build (Sonnet 5.5)]].

Plan: [[Redesign Plan]]. Needs: the Result of [[Handoff - Phase 1 Design (Fable 5.2)]] and the notes it created under `vault/Design/New Design/`.

## The prompt to paste

```text
أنت Opus 5.5 (جهد low) في المرحلة 2 (البنية التحتية) من إعادة تصميم واجهة Deadlock Toolbox.

اقرأ بالترتيب: CLAUDE.md، vault/AI Memory/00 Start Here.md، vault/Roadmap/Redesign Plan.md، ثم كل ملاحظات vault/Design/New Design/ (خصوصًا 06 Handoff to Build) والقسم Result في vault/AI Memory/Handoff - Phase 1 Design (Fable 5.2).md. ثم vault/AI Memory/How The Code Works.md و Environment and Pitfalls.md.
إذا ما لقيت تصميم المرحلة 1 مكتوبًا، لا تبدأ: قل للمستخدم أن المرحلة 1 ما خلصت.
رد عليّ بالعربي، قصير وبسيط. ممنوع commit/push. ما تلمس vaults أوبسيديان الثانية.

مهمتك: هيكل جديد للواجهة، بدون تغيير المحرّكات (repos/, installer/, store/, perf/, stats/, graph/) وبدون رسم الصفحات الجديدة (هذا شغل Sonnet).
1. سجل صفحات مسمّاة (page registry) بدل أرقام الصفحات: كل صفحة لها id نصي، عنوان، مجموعة، أيقونة، دالة بناء. إلغاء الاعتماد على الأرقام في ui.py وdesign.PAGES وNAV_ICONS والتلميحات.
2. غلاف جديد (shell): الشريط الجانبي والعنوان والتنقل والانتقال، يقرأ من السجل.
3. نظام tokens: يحمّل tokens المرحلة 1 (داكن/فاتح) ويولّد QSS منها؛ تبديل الثيم؛ اتجاه RTL/LTR.
4. مكوّنات أساسية (base widgets) بأسماء المرحلة 1: زر، بطاقة، حقل، جدول، حالة فارغة، شارة، حوار، تبويبات، تنبيه، إلخ، بنفس الأسماء والحالات المحددة.
5. الصفحات الحالية (الـ17) تظل تعمل داخل الغلاف الجديد كما هي مؤقتًا، وتُسجَّل في السجل.
6. تقسيم ui.py الضخم إلى وحدات صغيرة واضحة؛ نص واجهة واحد مصدره واحد (انظر i18n) إن أمكن بدون كسر الترجمات.
7. حدّث الاختبارات التي تثبّت أرقام الصفحات لتستخدم ids. شغّل: QT_QPA_PLATFORM=offscreen .venv/Scripts/python.exe -m unittest discover -s tests (يجب أن تنجح كلها عدا خطأ symlink المعروف)، ثم scripts/i18n_tool.py check و scripts/check_vault.py. شغّل البرنامج للتأكد أنه يفتح.
8. وثّق في الـvault: ملاحظة معمارية جديدة (Shell and Page Registry)، حدّث How The Code Works، وسجّل كل شي في Implementation Log، واكتب في آخر vault/AI Memory/Handoff - Phase 2 Infrastructure (Opus 5.5).md قسم "Result": ما أنجزت، ما لم تنجزه، كيف تضيف صفحة جديدة بالنظام الجديد (خطوات قصيرة) لـSonnet.

لا تنسخ شيئًا من التطبيق المرجعي (GPL). اتبع Windows pitfalls في الـvault (ملفات LF، سكربتات بدون heredoc طويل).

لما تخلص فعلًا والاختبارات خضراء: اختم رسالتك الأخيرة بهذا السطر بالضبط:
✅ المرحلة 2 انتهت (Opus 5.5)
وقل للمستخدم بجملة واحدة أن يفتح دردشة جديدة مع Sonnet 5.5 ويلصق برومت المرحلة 3.
إذا ما خلصت، قل ما تبقى ولا تكتب ذلك السطر.
```

## Result
**Phase 2 is finished (2026-11-14, Opus 5.5).** Nothing was committed. Details: [[Shell and Page Registry]], [[ADR-015 Pages are addressed by name through one registry]], [[Implementation Log]].

> **للمستخدم (بالعربي، ببساطة):** البنية الجديدة جاهزة. القائمة الجانبية صارت ٨ أماكن بدل ١٧، والصفحات القديمة صارت تبويبات داخلها وتشتغل مثل قبل. الشكل الجديد الكامل يجي في المرحلة ٣.

### Done
1. **Page registry** (`deadlock_fps/shell/registry.py`): ids, titles, groups, icons, tabs, hints, builder slot; flags mapped to addresses. No page numbers left in `ui.py`, `design.PAGES`/`NAV_ICONS` (now keyed by slot), the hints, or any `navigate()` call (a test scans for it).
2. **Shell** (`deadlock_fps/ui.py`): `Sidebar` + `NavItem` from the registry (main group, bottom group pinned), `TopBar` with the page title and the game chip, `Tabs` (Ctrl+Tab), the page transition kept, update dot on Settings and its Update tab.
3. **Tokens and theme** (`shell/tokens.py`, `shell/theme.py`, `shell/style.qss`, `shell/tokens.json` = the docs copy, tested): dark/light/system, three accents, four text sizes, re-applied without restart (`Window.set_look`, saved as `look` in `workspace.json`); right-to-left via `apply_direction`; Windows title bar follows the theme.
4. **Base components** (`shell/components.py`): all 39 names with their variants and states (`Button` primary/secondary/ghost/danger/danger-quiet, sm/md/lg, busy; `Badge` six variants; `Banner` four; `Dialog` confirm/review; `EmptyState` neutral/danger; painted `Switch`, `Slider`, `Bar`, `ConfidenceBar`, `Spinner`, `Skeleton`). Icons in `assets/icons2/`.
5. **The 17 old pages work inside the shell**, placed as in [[06 Handoff to Build]] (table in [[Shell and Page Registry]]).
6. **`ui.py` split**: 505 dense lines → `ui.py` (shell, ~330 readable lines) + `deadlock_fps/shell/base.py/{home,performance,backups,general,classic}.py`. Strings were not moved to a new single source: they still go through `tr()` and the two catalogues (that already is one source per language); `i18n_tool.py check` now scans `shell/` and `legacy/` too.
7. **Tests**: every test that pinned a page number now uses addresses; 23 new tests. Suite: 749, all pass except the known symlink error. `i18n_tool.py check`, `check_vault.py` pass. The app was opened on Windows (temporary data folder) and photographed in English and Arabic; two defects fixed.

### Not done, not verified
* **The new look is only on the frame** (sidebar, title, tabs). Every page inside still uses the old style; that is Phase 3.
* **Light theme and other text sizes work in code and tests but are not offered on screen**: the old pages stay dark, so light mode looks half-done. No button calls `set_look` yet.
* `Toast`, `Sheet`, `Dialog`, `Menu` were built and constructed in tests but not seen in a real page; shadows and the 4 px focus ring of every control were not checked by eye.
* IBM Plex not bundled (decision 2 still open); the bundled Noto faces are used.
* The `performance.all` tab does not exist yet (the details window is still a window); `--mods` and `--inspector` still open the temporary tabs.
* Not run on a real game folder.

### How to add or rebuild a page (for Sonnet)
1. Build the page widget from `deadlock_fps.shell.components` (Button, Card, DataTable, EmptyState, ...); colours only through `theme.color('color.…')` or the stylesheet; text through `tr()`.
2. Put it in the window: in `Window.build_slots()` call `self.add_slot('<slot>', widget)` (keep slot names short; one widget per slot).
3. Point the registry at it: in `shell/registry.py` `default_registry()` set the page's `slot=` or a `Tab('<id>', tr('<title>'), '<slot>', tr('<hint>'))`. Remove a temporary tab and its old builder when its content has moved.
4. Navigate and test by address: `window.navigate('mods.installed')`, then `window.current_address` / `window.current_slot` / `window.slots['<slot>']`.
5. Run the three gates (suite, `i18n_tool.py check`, `check_vault.py`) and look at the page in English and Arabic, dark and light, at 940 × 680. Once every page is rebuilt, offer the look switch in Settings (`Window.set_look`) and delete `design.py` widgets, `theme.py`, `deadlock_fps/shell/base.py/`.

Next: [[Handoff - Phase 3 Build (Sonnet 5.5)]]
