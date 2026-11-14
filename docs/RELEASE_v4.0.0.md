Deadlock Toolbox 4.0 turns the toolbox into a **mod manager**: add mod repositories from anywhere, browse them, install, update, disable and roll back mods, all inside the app. For **Windows and Linux x64**.

### What's new

- **Repositories.** Add a source by address: a GitHub or GitLab project, any HTTPS server, or an imported file. Toolbox classifies each one honestly (native, translated from release files, needs manual mapping, unsupported), shows when it last synced and why it failed if it did, and never treats an arbitrary file as a mod. Nothing is fetched until you ask.
- **Trust you can read.** Every repository is labelled OFFICIAL, VERIFIED, COMMUNITY or UNVERIFIED. The label comes from a registry shipped inside the app: a repository cannot grant itself a label and a GitHub address earns none. Everything you add yourself is UNVERIFIED until it has been reviewed.
- **Mod Hub.** Search across all enabled repositories, filter by category, trust or repository, read descriptions, changelogs and version history, and see whether a mod says it fits your game build.
- **Safe installation.** Installing is two steps: Toolbox downloads, verifies and inspects the package first (your game folder is untouched), then shows a preview of exactly what would change and where it came from. Only your confirmation installs it. The SHA-256 published by the repository is checked, ZIP archives are inspected for unsafe paths, symlinks, encrypted entries and zip bombs, only `.vpk` files are ever copied into the game, and the game must be closed. Every copy is a journaled move with a backup; if verification fails, or the app is killed mid-way, everything is put back as it was.
- **Installed Mods.** See what is installed, from where, which version, and what is newer. Update one or all, restore the previous version, disable a mod (its files really leave the addons folder), or remove it. Removed files are kept in a recovery folder.
- **Compatibility and Downloads.** A health check of every installed file, `gameinfo.gi` and overlaps between mods (lower `pakNN` number wins), with a one-click repair for when Steam restores `gameinfo.gi`; plus a history of everything Toolbox downloaded and changed.
- **Knowledge Graph.** An interactive map of repositories, mods, versions, authors, dependencies, conflicts, game builds, and the project's own features, decisions and tasks, drawn only from real data. Pan, zoom, search, filter, focus on a node, expand and collapse groups, and jump to the matching page or note.
- **Open specification.** Anyone can publish a compatible repository: [docs/REPOSITORY_SPEC.md](REPOSITORY_SPEC.md) with a working example.
- **Mod Store.** Browse and search the GameBanana catalogue for Deadlock inside the app and install `.zip` and `.vpk` mods through the same safe installer.
- **Stats.** Hero win and pick rates, the rank spread, and your own record, read on request from the public Deadlock API. Nothing personal is kept.
- **Performance details.** A window that explains what each graphics level changes, setting by setting, and lets you leave settings out.
- **A new interface.** Every page rebuilt on one design: named pages, a cleaner navigation, a light theme, text size and less-motion options in Settings.
- **Faster and steadier.** Background work is stopped cleanly when you close the app, the game-detection check is lighter, and the Map opens faster.
- English and Arabic throughout, including right-to-left.

### Good to know

- Mods install to `game/citadel/addons` as `pakNN_dir.vpk`, the folder other mod managers use. Single-file VPKs only: a VPK that needs separate data files is refused with an explanation.
- Hashes protect against a corrupted or swapped download, not against a malicious publisher. That is what trust labels are for, and only the project's own repository is labelled for now.
- System HTTP proxies are not used. Only the first 30 GitHub or GitLab releases of a project are read.
- The four built-in reference mods and the graphics tools are unchanged.

**Updating from 2.5 or later:** use the update centre in the app (Check → Download → Install).

**Coming from an older version:** download and extract the whole package once, then open `Install.cmd` on Windows or run `bash Install.sh` on Linux.

---

<div dir="rtl">

**Deadlock Toolbox 4.0** يحوّل الأداة إلى **مدير مودات**: أضف مستودعات مودات من أي مصدر، وتصفّحها، وركّب المودات وحدّثها وعطّلها وارجع عنها، كل ذلك داخل البرنامج.

- **المستودعات:** أضف مصدرًا بعنوانه (GitHub أو GitLab أو أي خادم HTTPS أو ملف مستورد). يُصنَّف كل مستودع بصدق، ولا يُعامل أي ملف عشوائي كمود.
- **ثقة مقروءة:** OFFICIAL وVERIFIED وCOMMUNITY وUNVERIFIED، من سجل داخل البرنامج. المستودع لا يمنح نفسه وسمًا، وكل ما تضيفه بنفسك يبدأ UNVERIFIED.
- **مركز المودات:** بحث في كل المستودعات، وتفاصيل وسجل تغييرات وتوافق مع إصدار لعبتك.
- **تركيب آمن:** يُنزَّل الملف ويُفحص أولًا دون لمس اللعبة، ثم تظهر معاينة بما سيتغير ومصدره، ولا يُركَّب شيء إلا بتأكيدك. تُتحقق بصمة SHA-256 ويُفحص الأرشيف، ولا تُنسخ إلا ملفات `.vpk`، وكل نسخ مُسجَّل بنسخة احتياطية ويُعاد كل شيء كما كان عند أي فشل.
- **المودات المركّبة والتحديثات والاسترجاع والتعطيل**، مع صفحة **التوافق** لفحص السلامة وصفحة **التنزيلات** للسجل.
- **الرسم المعرفي:** خريطة تفاعلية للمستودعات والمودات والمشروع نفسه من بيانات حقيقية فقط.
- **متجر المودات:** تصفّح وابحث في مودات GameBanana داخل البرنامج، وركّب ملفات `.zip` و`.vpk` بنفس التركيب الآمن.
- **الإحصائيات:** نسب فوز واختيار الأبطال وتوزيع الرتب وسجلّك أنت، من Deadlock API العام عند الطلب فقط، ولا يُحفظ شيء شخصي.
- **تفاصيل الأداء:** نافذة تشرح ما يغيّره كل مستوى رسوميات إعدادًا بإعداد، ويمكنك استثناء إعدادات.
- **واجهة جديدة بالكامل:** صفحات أوضح، وثيم فاتح، وحجم خط، وتقليل الحركة من الإعدادات.
- **أسرع وأثبت:** تتوقف الأعمال الخلفية بأمان عند الإغلاق، وفحص اللعبة أخف، والخريطة تفتح أسرع.
- **مواصفة مفتوحة** لمن يريد نشر مستودع متوافق: `docs/REPOSITORY_SPEC.md`.

المودات تُركَّب في `game/citadel/addons` باسم `pakNN_dir.vpk`. ملفات VPK المفردة فقط.

</div>
