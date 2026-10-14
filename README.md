<div dir="rtl">

# Deadlock FPS Studio

برنامج مكتبي مفتوح المصدر لتخفيف رسوم Deadlock على **Windows وLinux**. واجهة عربية، أوضاع جاهزة، تحكم يدوي، معاينة التغييرات ونسخ احتياطية قابلة للاسترجاع.

![الواجهة](docs/screenshot.png)

## تشغيل البرنامج

حمّل حزمة نظامك من [Releases](https://github.com/exelight7/deadlock-fps-/releases/latest)، فك الضغط **كاملًا** ثم شغّل `DeadlockFPSStudio.exe` في Windows أو `DeadlockFPSStudio` في Linux. لا يحتاج البناء المحمول إلى تثبيت Python. بناء Linux المحلي يتطلب glibc 2.34 أو أحدث؛ بناء GitHub يُنتج على Ubuntu 22.04. بنية x64 فقط.

للتشغيل من المصدر: ثبّت Python 3.12 ثم افتح `run-windows.bat` أو شغّل `./run-linux.sh`. يحتاج التشغيل الأول إلى الإنترنت لتنزيل الاعتماديات. في Linux قد تحتاج حزمة `python3-venv` ومكتبات Qt النظامية مثل EGL وOpenGL وxcb-cursor. يمكن استخدام Wayland عبر `QT_QPA_PLATFORM=wayland` أو X11 عبر `QT_QPA_PLATFORM=xcb` حسب النظام.

## الاستخدام

1. شغّل اللعبة مرة واحدة لإنشاء إعدادات الفيديو، ثم أغلقها.
2. افتح البرنامج. يكتشف Steam ومكتباته تلقائيًا، أو اختر مجلد `Deadlock` يدويًا.
3. اختر حساب Steam المطلوب من قائمة ملفات الفيديو؛ لا يغيّر حساباتك الأخرى.
4. اختر **متوازن** أو **أداء قوي** أو **أقصى تخفيف**، ثم عدّل الرسوم حسب حاجتك.
5. اختياريًا: اختر مجلد `MODS` من حزمتك الأصلية وفعّل المودات المطلوبة.
6. اضغط **معاينة وتطبيق**، راجع الفروقات، ثم طبّق. جرّب وضوح المؤثرات في التدريب.

دقة العرض الداخلية: 25–100%. تبسيط الخامات: 0–4. حد الإطارات: 0–500، والصفر بدون حد. يمكن تعديل الظلال والضباب والوهج والتظليل المحيطي والجزيئات والدقة، وتخفيف الحطام والجثث والقوائم. وضع أقصى تخفيف يستخدم 1280×720 مع عرض داخلي 50%؛ قد يصبح المشهد شديد الضبابية. المعالج قد يظل عنق الزجاجة، ولا يضمن البرنامج زيادة محددة في الإطارات.

تعطيل تعديلات المحرك يسترجع ملف `gameinfo.gi` الأساسي مع استمرار تعديلات الفيديو والمودات المختارة. التحكم الدقيق في بعض المؤثرات وخيار تخفيف المعالج يتطلب تفعيل تعديلات المحرك.

## الملفات والاسترجاع

- إعدادات الفيديو: `Steam/userdata/<account>/1422450/local/cfg/video.txt`، مع دعم ملف الفيديو داخل اللعبة إن وجد. تُحفظ VendorID وDeviceID وإعدادات الشاشة غير المختارة.
- المحرك: `Deadlock/game/citadel/gameinfo.gi`. يُدمج فقط نطاق ConVars الرسومي وSceneSystem المحدد؛ لا يُستبدل الملف بالنسخة القديمة المرفقة.
- المودات: `Deadlock/game/citadel/fps_studio/pak*_dir.vpk`. يُضاف مسار بحث خاص عند الحاجة، ولا يُحذف مجلد addons أو المودات الخارجية.
- النسخ: `Deadlock/.deadlock-fps-studio/`. لا تحذف هذا المجلد ما دمت تريد الاسترجاع. يحفظ الأصل مرة واحدة وحالات ما قبل الاسترجاع في `history`.

إذا غيّر تحديث اللعبة ملفًا مُدارًا، يرفض البرنامج الكتابة فوقه. احفظ الحالة الحالية عبر خيار الاسترجاع المخصص في صفحة النسخ. هذا يعيد نسخة **قديمة** من gameinfo؛ بعد ذلك استخدم Steam → Properties → Installed Files → Verify integrity قبل تطبيق إعدادات جديدة، كي تبني التعديلات على ملف حديث. إذا أزيل البرنامج، تبقى التعديلات حتى الاسترجاع أو إصلاح ملفات اللعبة. Steam Cloud أو اللعبة قد يعيدان كتابة إعدادات الفيديو.

## المودات والملفات المرجعية

قرأنا الحزمة كاملة، وراجعنا بنية VPK ومواردها. يتعارض Remove Name Tags مع Old Healthbars لأنهما يعدّلان `unit_status_overlay_v2.vxml_c`؛ يمنع البرنامج جمعهما. Daylock يغيّر الإضاءة/السماء، وSinner Fix يحتوي نموذجًا وخامة. **حزم المودات والبرامج الخارجية غير معاد توزيعها هنا**؛ استورد المودات من مجلدك الأصلي. يحتفظ المستودع بملفات الإعدادات الأصلية للرجوع إليها في `assets/reference`؛ ليست قالبًا يُكتب بالكامل فوق لعبتك.

قد تتجاهل اللعبة إعدادات معينة أو تتوقف المودات بعد تحديث. لا يستخدم البرنامج حقن DLL أو فتح أوامر مقفلة أو تعديل ملفات التنفيذ. لم يتم قياس FPS أو التحقق من سلوك المودات داخل مباراة. إرشاد DX11 في readme الأصلي يتعلق بمشكلات المؤثرات؛ البرنامج لا يفرض محرك عرض، وLinux يستخدم Vulkan حسب إعداد اللعبة الحالية.

## التطوير والبناء

</div>

```sh
python -m venv .venv
# Linux:
. .venv/bin/activate
# Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt pyinstaller==6.20.0
python -m unittest discover -s tests -v
python main.py
python build.py
```

Build on the target OS. Outputs are in `dist/`; GitHub Actions tests and packages both platforms and publishes v1.0.0 after successful main builds. Windows executables are unsigned. Linux desktop libraries are still required; this is a portable folder, not an AppImage.

App source: MIT. Third-party files and Qt dependencies retain their own licenses; see [THIRD_PARTY.md](THIRD_PARTY.md). Deployment reference: [Qt for Python packaging](https://doc.qt.io/qtforpython-6/deployment/index.html).
