---
title: Handoff - Phase 1 Design (Fable 5.2)
type: guide
tags: [handoff, redesign, design]
updated: 2026-11-14
---

# Handoff · Phase 1 · Design (Fable 5.2)

> **للمستخدم:** افتح دردشة جديدة، اختر **Fable 5.2**، والصق البرومت اللي تحت. لما يخلص لازم يختم رسالته بالجملة: **`✅ المرحلة 1 انتهت (Fable 5.2)`**. إذا ما كتبها، فهو ما خلص. بعدها افتح دردشة جديدة مع **Opus 5.5 (low)** وادخل [[Handoff - Phase 2 Infrastructure (Opus 5.5)]].

Plan: [[Redesign Plan]].

## The prompt to paste

```text
أنت Fable 5.2 في المرحلة 1 (التصميم) من إعادة تصميم واجهة Deadlock Toolbox (PySide6).

ابدأ بقراءة: CLAUDE.md ثم vault/AI Memory/00 Start Here.md ثم vault/Roadmap/Redesign Plan.md ثم vault/Design/Design System.md.
رد عليّ بالعربي، قصير وبكلمات بسيطة، سطر لكل فكرة، والتفاصيل تروح في الـvault.
ممنوع commit أو push. ممنوع تعدّل كود التطبيق في deadlock_fps/ . لا تلمس vaults أوبسيديان الثانية للمستخدم.

الهدف: تصميم جديد كليًا، متناسق، لا يشبه القديم (القديم: نحاسي/أخضر مائل، بطاقات بزوايا مقطوعة، 17 صفحة مكدّسة فوق صفحة الأداء). المستخدم قال إن واجهته «خايسة» لأنها انبنت على قائمة الأداء وتكدّست.

اللي عليك تسلّمه (كله في vault/Design/New Design/ كملاحظات .md، والنماذج المرئية كملفات HTML/SVG ثابتة في docs/design-prototype/ تفتح بالمتصفح بدون سيرفر):
1. 01 Principles: مبادئ التصميم، النبرة، ما نتجنبه، ولماذا هو مختلف عن القديم.
2. 02 Information Architecture: كل الصفحات والمجموعات وأسماؤها (بكلمات بسيطة، بدون jargon مثل repository)، وما الذي يُدمج أو يُحذف. الصفحات الحالية: Home, Performance (Graphics), Mods library, Recovery, Servers, Crosshair, Updates, Inspector, Settings, Sources, Source Mods, Installed Mods, Compatibility, Downloads, Graph, Mod Store, Stats. الميزة الأهم أسهل مسار: متجر المودات، الأداء، الإحصائيات.
3. 03 Visual Language: ألوان (فاتح وداكن)، خطوط (عربي ولاتيني)، مقاييس المسافات، الزوايا، الظلال، الأيقونات، الحركة. كل شي كـ design tokens بأسماء ثابتة (جدول: الاسم، القيمة داكن، القيمة فاتح).
4. 04 Components: مواصفات كل مكوّن (زر، حقل، قائمة منسدلة، جدول/قائمة، بطاقة، تبويبات، شريط جانبي، شريط عنوان، حالة فارغة، حوار، تنبيه، شريط تقدم، شارة حالة...) بحالاتها (عادي/hover/focus/disabled/error) وكيف تنعكس في RTL.
5. 05 Screens: لكل صفحة نموذج (wireframe أو mock-up) ومواصفاتها، والحالات: فارغ، تحميل، خطأ، ممتلئ. الإنجليزي والعربي (RTL).
6. 06 Handoff to Build: قائمة tokens النهائية وقائمة المكوّنات ليبني منها Opus البنية، وترتيب ترحيل الصفحات لـSonnet.
7. اكتب في آخر ملاحظة vault/AI Memory/Handoff - Phase 1 Design (Fable 5.2).md قسم "Result" فيه: ما أنجزت، ما لم تنجزه، قرارات تحتاج موافقة المستخدم.

قيود: نافذة الحد الأدنى 940×680. كل النصوص ستكون بالعربي والإنجليزي. الوصولية: تباين كافٍ، التركيز ظاهر، الحجم قابل للتكبير. لا تنسخ شيئًا من برنامج Deadlock Mod Manager المرجعي (GPL).
شغّل: python scripts/check_vault.py وتأكد أنه يمر (الروابط [[...]] لازم تكون صحيحة، وكل ملاحظة لها frontmatter: title, type, updated).

لما تخلص فعلًا وكل شي مكتوب: اختم رسالتك الأخيرة بهذا السطر بالضبط:
✅ المرحلة 1 انتهت (Fable 5.2)
وقل للمستخدم بجملة واحدة أن يفتح دردشة جديدة مع Opus 5.5 ويلصق برومت المرحلة 2.
إذا ما خلصت، قل ما تبقى ولا تكتب ذلك السطر.
```

## Result
**Phase 1 is finished (2026-11-14, Fable 5.2).** No file under `deadlock_fps/` was changed; nothing was committed.

> **للمستخدم (بالعربي، ببساطة):** التصميم خلص. افتح الملف `docs/design-prototype/index.html` بالمتصفح (دبل كلك) وجرّب: القائمة الجانبية تشتغل، وفوق فيه قوائم تغيّر الصفحة والحالة واللغة والثيم واللون. تحت فيه ٦ قرارات أحتاج رأيك فيها؛ كلها لها اختيار افتراضي، فالمرحلة ٢ تقدر تبدأ بدون ما تنتظر.

### What was delivered
| What | Where |
|---|---|
| Principles, tone, what to avoid, why it differs from the old look | [[01 Principles]] |
| 17 pages → 8 places with tabs; names in English and Arabic; where every old page went | [[02 Information Architecture]] |
| 39 colour tokens (dark and light), 51 size, type, motion tokens; 2 optional accents; contrast measured | [[03 Visual Language]], `docs/design-prototype/tokens.json` |
| 39 components with variants, states and right-to-left rules | [[04 Components]], `docs/design-prototype/components.html` |
| Every screen in four states, English and Arabic, dark and light | [[05 Screens]], `docs/design-prototype/index.html`, 48 pictures in `docs/design-prototype/shots/` |
| Token list, component list, page ids, temporary placement of the old pages, order of work | [[06 Handoff to Build]] |
| Two helper scripts (not app code) | `scripts/dev/design_tokens.py`, `scripts/dev/design_shots.py` |

### Evidence
* Contrast: 96 colour pairs checked by `scripts/dev/design_tokens.py` (text 4.5:1, outlines 3:1; dark and light; blue, violet, orange): 0 fail. Five pairs failed on the first run and their colours were changed.
* The mock-up was rendered with Qt WebEngine and the pictures were looked at: 16 views by eye (English and Arabic, dark and light, the 940 × 680 minimum, the sheet and both dialogs, the component page). Five defects were found that way and fixed (a mirrored tick in Arabic, a cramped table at the minimum window, a slider knob touching its number field, a dialog scrim that did not cover the sidebar, invisible progress bars on the component page).
* `python scripts/check_vault.py` passes; the three prototype scripts pass `node --check`; no console errors in the browser.

### Not done, not verified
* **It is a browser mock-up, not Qt.** Spacing and text will differ slightly in the real app; nobody has seen the design in PySide6 yet.
* Not seen on the user's own display; no screen-reader pass; text sizes 90, 115 and 130 % are specified but not drawn.
* The proposed fonts (IBM Plex) are not in the repository, so the mock-up shows the viewer's system font (decision 2).
* Specified in words only, not drawn: the ready-designs dialog of Crosshair, the Files and History dialogs of a mod, the opened "Classic pack" section, the "Game is running" pill ([[05 Screens]], last section).
* No separate SVG wireframes: the HTML mock-up replaces them.
* The 48 pictures in `shots/` were generated by the same script after the fixes; most of them were not inspected one by one.

### Decisions for the user (each has a default; Phase 2 can start without waiting)
1. **Accent colour.** Default **blue**. Alternatives ready in the mock-up (Accent menu): violet, orange. Blue is the only one that cannot be mistaken for a warning or an error.
2. **Font.** Default: the proposed **IBM Plex Sans Arabic + IBM Plex Sans + IBM Plex Mono** (free, OFL). It needs three font files downloaded into the project: say yes and Phase 2 or 3 adds them. If no: the bundled Noto fonts stay and the design still works.
3. **Mod pictures while browsing.** Default **off** (cards show a coloured placeholder; pictures load when you open a mod and ask). Turning it on loads small pictures from GameBanana while you scroll, which is network activity without a press: today's rule is "nothing loads before a press".
4. **Names.** Mods tabs: Browse تصفّح, Installed المثبّتة, Check الفحص, Activity السجل. "Recovery" becomes Backups النسخ والاسترجاع. The four old mods become "Classic pack" الحزمة الكلاسيكية. Change any you dislike.
5. **What moved into Settings:** app updates, extra mod sources, and the project map (was "Graph"). Say if any of them should be a sidebar entry again.
6. **Default look:** follows Windows (dark or light), changeable in Settings.

Next: [[Handoff - Phase 2 Infrastructure (Opus 5.5)]]
