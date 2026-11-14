/* Prototype pages 1 of 2: Home, Mods, Performance, Stats and the overlays. Sample data only. */
'use strict';
const PAGES = {};
const OVERLAYS = {};

function door(icon, name, line, action, target, off) {
  return '<button class="card click door" ' + (off ? 'disabled style="opacity:.55;cursor:default"' : go(target)) + '><span class="ico">' + ic(icon) + '</span><h2>' + name +
    '</h2><p class="soft">' + line + '</p><span class="go">' + action + ic('chev', 'sm') + '</span></button>';
}
function item(kind, title, desc, action) {
  const icon = { bad: 'warn', warn: 'warn', ok: 'check', info: 'info' }[kind] || 'info';
  return '<div class="item"><span class="badge ' + kind + '" style="width:28px;height:28px;padding:0;justify-content:center">' + ic(icon) + '</span><div class="grow"><div class="t">' + title +
    '</div><div class="d">' + desc + '</div></div>' + (action || '') + '</div>';
}

/* ------------------------------------------------------------------ Home */
PAGES.home = function (state) {
  const doors = function (off) {
    return '<div class="grid g3">' +
      door('box', T('Mods', 'المودات'), off ? T('Skins, HUDs, sounds and more from the community.', 'سكنات وواجهات وأصوات وأكثر من المجتمع.') : T('12 installed · 2 updates', '12 مثبّتة · تحديثان'), T('Browse mods', 'تصفّح المودات'), { page: 'mods', tab: 'browse' }, off) +
      door('gauge', T('Performance', 'الأداء'), off ? T('One slider for more frames per second.', 'شريط واحد لإطارات أكثر في الثانية.') : T('Level 80 · Balanced', 'المستوى 80 · متوازن'), T('Tune the game', 'اضبط اللعبة'), { page: 'performance', tab: 'level' }, off) +
      door('chart', T('Stats', 'الإحصائيات'), T('Which heroes win now, the rank spread, and your own record.', 'من يفوز الآن، توزيع الرتب، وسجلّك أنت.'), T('Open stats', 'افتح الإحصائيات'), { page: 'stats', tab: 'heroes' }) + '</div>';
  };
  if (state === 'empty') {
    return { body: '<div class="limit"><div class="card" style="gap:var(--space-4)"><div class="row top"><span class="door"><span class="ico">' + ic('folder') + '</span></span><div class="grow"><h2>' +
      T('First, link your game', 'أولًا، اربط لعبتك') + '</h2><p class="soft">' + T('Toolbox needs to know where Deadlock is installed. It only looks; nothing is changed until you apply something.', 'يحتاج Toolbox أن يعرف أين Deadlock مثبّتة. هو يبحث فقط؛ لا شيء يتغيّر إلا عندما تطبّق أنت.') +
      '</p></div></div><div class="row">' + btn(T('Find it automatically', 'ابحث تلقائيًا'), { kind: 'primary', icon: 'search' }) + btn(T('Choose the folder', 'اختر المجلد'), { icon: 'folder', go: { page: 'settings', tab: 'game' } }) + '</div></div>' +
      doors(true) + '<p class="muted">' + T('Mods and Performance open after the game is linked. Stats works without it.', 'المودات والأداء تُفتح بعد ربط اللعبة. الإحصائيات تعمل بدونها.') + '</p></div>' };
  }
  if (state === 'loading') {
    return { body: '<div class="limit"><div class="card"><div class="row"><span class="spin"></span><h2>' + T('Looking for Deadlock…', 'جارٍ البحث عن Deadlock…') + '</h2></div><div class="progress wait"><i></i></div><p class="muted">' +
      T('Checking the Steam libraries on every drive.', 'نفحص مكتبات Steam في كل الأقراص.') + '</p></div><div class="grid g3">' + [1, 2, 3].map(function () { return '<div class="card">' + skel('40px', '40px') + skel('50%') + skel('80%') + '</div>'; }).join('') + '</div></div>' };
  }
  if (state === 'error') {
    return { body: '<div class="limit">' + banner('bad', T('Deadlock was not found on this PC', 'لم نجد Deadlock في هذا الجهاز'), T('Looked in the Steam libraries on C: and D:. If the game is somewhere else, choose its folder.', 'بحثنا في مكتبات Steam على C: و D:. إذا كانت اللعبة في مكان آخر، اختر مجلدها.'),
      btn(T('Choose the folder', 'اختر المجلد'), { size: 'sm', icon: 'folder' }) + btn(T('Search again', 'ابحث مجددًا'), { size: 'sm', kind: 'ghost' })) + doors(true) + '</div>' };
  }
  return { body: '<div class="limit">' + doors(false) +
    '<div class="card flat"><div style="padding:var(--space-4) var(--space-4) var(--space-2)">' + head(T('Needs your attention', 'يحتاج انتباهك'), badge('3', 'warn')) + '</div><div class="list">' +
    item('bad', T('Your mods are switched off in the game', 'موداتك متوقفة في اللعبة'), T('Steam restored a game file. One press puts it back.', 'Steam أعاد ملفًا من ملفات اللعبة. ضغطة واحدة ترجعه.'), btn(T('Repair', 'أصلِح'), { size: 'sm', kind: 'primary', go: { page: 'mods', tab: 'health' } })) +
    item('info', T('2 mods have updates', 'مودان لهما تحديث'), 'Clean HUD · Night Skyline', btn(T('See updates', 'شوف التحديثات'), { size: 'sm', go: { page: 'mods', tab: 'installed' } })) +
    item('info', T('Toolbox 4.1 is ready', 'Toolbox 4.1 جاهز'), T('You have 4.0.0.', 'عندك 4.0.0.'), btn(T('Update', 'حدّث'), { size: 'sm', go: { page: 'settings', tab: 'update' } })) + '</div></div>' +
    '<div class="grid g3">' +
    '<button class="card click" ' + go({ page: 'crosshair' }) + '><div class="row">' + ic('crosshair') + '<h2>' + T('Crosshair', 'الكروس هير') + '</h2></div><p class="soft">' + T('Your own design is applied', 'تصميمك الخاص مطبّق') + '</p></button>' +
    '<button class="card click" ' + go({ page: 'servers' }) + '><div class="row">' + ic('globe') + '<h2>' + T('Servers', 'السيرفرات') + '</h2></div><p class="soft">' + T('2 regions blocked', 'منطقتان محظورتان') + '</p></button>' +
    '<button class="card click" ' + go({ page: 'backups' }) + '><div class="row">' + ic('history') + '<h2>' + T('Backups', 'النسخ والاسترجاع') + '</h2></div><p class="soft">' + T('Originals saved on 12 Nov', 'الأصل محفوظ في 12 نوفمبر') + '</p></button></div></div>' };
};

/* ------------------------------------------------------------------ Mods */
const MODS = [
  ['Clean HUD', 'HUD', 'mira', 205, 1], ['Night Skyline', 'Map', 'oskar', 255, 1], ['Abrams · Steel', 'Abrams', 'vento', 18, 0], ['Soft Hit Sounds', 'Sound', 'noor', 150, 0],
  ['Haze · Ember', 'Haze', 'kael', 340, 0], ['Minimal Map', 'HUD', 'mira', 190, 1], ['Lash · Arctic', 'Lash', 'juno', 215, 0], ['Clear Skies', 'Map', 'oskar', 45, 0],
];
function modCard(m, i) {
  return '<button class="card click mod' + (S.over === 'mod' && i === 2 ? ' on' : '') + '" ' + go({ over: 'mod' }) + '><div class="pic" style="background:linear-gradient(135deg,hsl(' + m[3] + ' 45% 34%),hsl(' + (m[3] + 40) + ' 40% 18%))">' +
    ic('box', 'lg') + (m[4] ? badge(T('Installed', 'مثبّت'), 'ok', 'check') : '') + '</div><div class="meta"><div class="name">' + m[0] + '</div><div class="by"><span>' + m[1] + '</span><span>·</span><span>' + m[2] + '</span></div></div></button>';
}
function modToolbar() {
  return '<div class="row wrap">' + field(T('Search mods, heroes, authors', 'ابحث عن مود أو بطل أو صانع'), 'search') +
    select([T('All types', 'كل الأنواع'), T('Skins', 'سكنات'), 'HUD', T('Sounds', 'أصوات'), T('Maps', 'خرائط')]) + select([T('All heroes', 'كل الأبطال'), 'Abrams', 'Haze', 'Lash']) +
    select([T('Recently updated', 'المحدّثة مؤخرًا'), T('Newest', 'الأحدث'), T('Name', 'الاسم')]) + '</div>' +
    '<div class="row wrap"><button class="chip on">' + ic('check', 'sm') + T('Hide outdated', 'أخفِ القديمة') + '</button><button class="chip">' + T('Show adult content', 'أظهر محتوى البالغين') + '</button><span class="end muted">' +
    T('6,104 mods · list checked 2 hours ago', '6,104 مود · آخر فحص قبل ساعتين') + '</span>' + btn(T('Check for new mods', 'افحص الجديد'), { size: 'sm', kind: 'ghost', icon: 'refresh' }) + '</div>';
}
function modRows(loading) {
  const rows = [
    ['Clean HUD', 'mira', '1.4.0', '1.5.0', 'GameBanana', badge(T('Update', 'تحديث'), 'info'), 1],
    ['Night Skyline', 'oskar', '2.0.1', '2.1.0', 'GameBanana', badge(T('Update', 'تحديث'), 'info'), 1],
    ['Minimal Map', 'mira', '0.9.2', '', 'GameBanana', badge(T('Up to date', 'محدّث'), 'ok', 'check'), 1],
    ['Tracer Pack', 'devkit', '3.2.0', '', T('Source: devkit', 'مصدر: devkit'), badge(T('Source unreachable', 'المصدر لا يردّ'), 'warn', 'warn'), 1],
    ['Old Announcer', 'noor', '1.0.0', '', 'GameBanana', badge(T('Off', 'متوقف')), 0],
  ];
  return '<table class="table"><thead><tr><th>' + T('On', 'تشغيل') + '</th><th>' + T('Mod', 'المود') + '</th><th>' + T('Version', 'الإصدار') + '</th><th>' + T('Status', 'الحالة') + '</th><th></th></tr></thead><tbody>' +
    rows.map(function (r) {
      if (loading) return '<tr><td>' + skel('36px', '20px') + '</td><td>' + skel('140px') + '</td><td>' + skel('50px') + '</td><td>' + skel('70px', '22px') + '</td><td></td></tr>';
      return '<tr><td>' + check('', r[6], true) + '</td><td><div class="keep">' + r[0] + '</div><div class="sub keep">' + r[1] + ' · ' + r[4] + '</div></td><td class="keep">' + ltr(r[2]) + (r[3] ? ' <span class="muted">' + ic('chev', 'sm') + '</span> ' + ltr(r[3]) : '') +
        '</td><td>' + r[5] + '</td><td class="acts">' + (r[3] ? btn(T('Update', 'حدّث'), { size: 'sm' }) : '') + btn('', { size: 'sm', kind: 'ghost', icon: 'more', title: T('More actions', 'إجراءات أخرى') }) + '</td></tr>';
    }).join('') + '</tbody></table>';
}

PAGES.mods = function (state, tab) {
  if (tab === 'browse') {
    if (state === 'empty') return { body: empty('download', T('Get the mod list first', 'نزّل قائمة المودات أولًا'), T('Toolbox keeps a searchable copy of every Deadlock mod on GameBanana. About 2 minutes and 26 MB, once. Nothing is downloaded before you press the button.', 'يحفظ Toolbox نسخة قابلة للبحث من كل مودات Deadlock في GameBanana. حوالي دقيقتين و26 م.ب، مرة واحدة. لا شيء يتنزّل قبل أن تضغط الزر.'), btn(T('Get the mod list', 'نزّل القائمة'), { kind: 'primary', size: 'lg', icon: 'download' })) };
    if (state === 'loading') return { body: '<div class="limit"><div class="card"><div class="row"><span class="spin"></span><h2>' + T('Getting the mod list…', 'جارٍ تنزيل قائمة المودات…') + '</h2><span class="end muted">' + T('page 41 of 123', 'صفحة 41 من 123') + '</span></div><div class="progress"><i style="width:33%"></i></div><div class="row"><span class="muted grow">' +
      T('You can stop or close the app; it continues from here next time.', 'تقدر توقف أو تقفل البرنامج؛ يكمل من هنا المرة الجاية.') + '</span>' + btn(T('Stop', 'أوقف'), { size: 'sm' }) + '</div></div></div><div class="modgrid">' + [1, 2, 3, 4].map(function () { return '<div class="card mod">' + skel('100%', '110px') + '<div class="meta">' + skel('70%') + skel('40%') + '</div></div>'; }).join('') + '</div>' };
    return { body: (state === 'error' ? banner('bad', T("Couldn't reach GameBanana", 'تعذّر الوصول إلى GameBanana'), T('Showing the list saved 3 days ago. Installing needs a connection.', 'نعرض القائمة المحفوظة قبل 3 أيام. التثبيت يحتاج اتصالًا.'), btn(T('Try again', 'حاول مجددًا'), { size: 'sm' })) : '') +
      modToolbar() + '<div class="modgrid">' + MODS.map(modCard).join('') + '</div>' };
  }
  if (tab === 'installed') {
    if (state === 'empty') return { body: empty('box', T('No mods yet', 'لا توجد مودات بعد'), T('Mods you install show up here, where you can switch them off, update them or remove them.', 'المودات التي تثبّتها تظهر هنا، وتقدر توقفها أو تحدّثها أو تحذفها.'), btn(T('Browse mods', 'تصفّح المودات'), { kind: 'primary', go: { tab: 'browse' } })) };
    const tools = '<div class="row wrap"><span class="soft">' + (state === 'loading' ? T('Reading your mods…', 'نقرأ موداتك…') : T('12 mods · 2 updates · 1 off', '12 مود · تحديثان · واحد متوقف')) + '</span><div class="end row">' +
      btn(T('Check for updates', 'افحص التحديثات'), { icon: 'refresh', busy: state === 'loading', off: state === 'loading' }) + btn(T('Update all (2)', 'حدّث الكل (2)'), { kind: 'primary', off: state !== 'filled' }) + '</div></div>';
    if (state === 'error') return { body: banner('bad', T("The list of installed mods couldn't be read", 'تعذّرت قراءة قائمة المودات المثبّتة'), T('The file was damaged. Toolbox kept a copy and started a clean list; your mod files in the game were not touched.', 'الملف كان تالفًا. احتفظ Toolbox بنسخة وبدأ قائمة نظيفة؛ ملفات المودات في اللعبة لم تُلمس.'), btn(T('Open the folder', 'افتح المجلد'), { size: 'sm', icon: 'folder' })) + tools +
      empty('box', T('The list is empty now', 'القائمة فارغة الآن'), T('Files found in the game are listed below as "not installed by Toolbox".', 'الملفات الموجودة في اللعبة تظهر تحت كـ«لم يثبّتها Toolbox».')) };
    return { body: tools + '<div class="card flat">' + modRows(state === 'loading') + '</div>' +
      '<div class="card flat"><div class="list"><div class="item">' + ic('chev') + '<div class="grow"><div class="t">' + T('Classic pack', 'الحزمة الكلاسيكية') + ' <span class="muted">(4)</span></div><div class="d">' + T('The four mods Toolbox has always supported. You add their files yourself.', 'المودات الأربعة التي يدعمها Toolbox من زمان. تضيف ملفاتها بنفسك.') + '</div></div>' + badge(T('2 on', '2 شغّالة'), 'ok') + '</div>' +
      '<div class="item">' + ic('chev') + '<div class="grow"><div class="t">' + T('Not installed by Toolbox', 'لم يثبّتها Toolbox') + ' <span class="muted">(2)</span></div><div class="d">' + T('Other files in the game\'s mod folder. Toolbox lists them and never touches them.', 'ملفات أخرى في مجلد مودات اللعبة. Toolbox يعرضها ولا يلمسها أبدًا.') + '</div></div></div></div></div>' };
  }
  if (tab === 'health') {
    if (state === 'empty') return { body: empty('check', T('Everything looks fine', 'كل شيء سليم'), T('12 mods checked a minute ago: all files are in place and none of them clash.', 'فُحص 12 مودًا قبل دقيقة: كل الملفات في مكانها ولا تعارض بينها.'), btn(T('Check again', 'افحص مجددًا'), { icon: 'refresh' })) };
    if (state === 'loading') return { body: '<div class="limit"><div class="card"><div class="row"><span class="spin"></span><h2>' + T('Checking your mod files…', 'نفحص ملفات موداتك…') + '</h2><span class="end muted">' + T('7 of 12', '7 من 12') + '</span></div><div class="progress"><i style="width:58%"></i></div><div class="row"><span class="grow muted">' + T('Read-only: nothing is changed.', 'قراءة فقط: لا شيء يتغيّر.') + '</span>' + btn(T('Cancel', 'إلغاء'), { size: 'sm' }) + '</div></div></div>' };
    if (state === 'error') return { body: empty('warn', T('The check could not finish', 'الفحص لم يكتمل'), T('A file in the game folder could not be read. Close the game and anything else that uses it, then try again.', 'ملف في مجلد اللعبة تعذّرت قراءته. أغلق اللعبة وأي برنامج يستخدمه ثم حاول مجددًا.'), btn(T('Try again', 'حاول مجددًا'), { kind: 'primary' }), true) };
    return { body: '<div class="limit"><div class="row"><span class="soft">' + T('Checked a minute ago · game build', 'فُحص قبل دقيقة · نسخة اللعبة') + ' ' + ltr('6857') + '</span><div class="end">' + btn(T('Check again', 'افحص مجددًا'), { icon: 'refresh' }) + '</div></div>' +
      '<div class="card flat"><div class="list">' +
      item('bad', T('Your mods are switched off in the game', 'موداتك متوقفة في اللعبة'), T('Steam restored a game file, so the game no longer loads the mod folder.', 'Steam أعاد ملفًا من ملفات اللعبة، فاللعبة ما عادت تحمّل مجلد المودات.'), btn(T('Repair', 'أصلِح'), { size: 'sm', kind: 'primary' })) +
      item('warn', T('Two mods change the same files', 'مودان يغيّران نفس الملفات'), T('Clean HUD wins over Minimal Map (it has the lower number). Switch one off if something looks wrong.', 'Clean HUD يغلب Minimal Map (رقمه أصغر). أوقف واحدًا إذا شيء يبدو غلط.'), btn(T('Show', 'اعرض'), { size: 'sm' })) +
      item('ok', T('10 mods are fine', '10 مودات سليمة'), T('Files are in place and match what was installed.', 'الملفات في مكانها وتطابق ما ثُبّت.')) + '</div></div>' +
      '<div class="card flat"><div style="padding:var(--space-4)">' + head(T('Do they fit your game version?', 'هل تناسب نسخة لعبتك؟')) + '</div><table class="table"><thead><tr><th>' + T('Mod', 'المود') + '</th><th>' + T('Made for', 'مصنوع لـ') + '</th><th>' + T('Fit', 'التوافق') + '</th></tr></thead><tbody>' +
      '<tr><td>Tracer Pack</td><td>' + ltr('6700 – 6800') + '</td><td>' + badge(T('Older game version', 'نسخة لعبة أقدم'), 'warn', 'warn') + '</td></tr><tr><td>Clean HUD</td><td class="muted">' + T('not stated', 'غير مذكور') + '</td><td>' + badge(T('Unknown', 'غير معروف')) + '</td></tr></tbody></table></div></div>' };
  }
  // activity
  const history = '<div class="card flat"><div style="padding:var(--space-4) var(--space-4) var(--space-2)">' + head(T('History', 'السجل')) + '</div><div class="list">' +
    (state === 'error' ? item('bad', T('Haze · Ember was not installed', 'Haze · Ember لم يُثبّت'), T('The downloaded file did not match its checksum, so it was deleted. Nothing in the game changed.', 'الملف المنزَّل لم يطابق بصمته فحُذف. لا شيء تغيّر في اللعبة.'), btn(T('Try again', 'حاول مجددًا'), { size: 'sm' })) : '') +
    item('ok', T('Installed Night Skyline 2.0.1', 'ثُبّت Night Skyline 2.0.1'), T('Today 18:42 · from GameBanana', 'اليوم 18:42 · من GameBanana')) +
    item('ok', T('Updated Clean HUD to 1.4.0', 'حُدّث Clean HUD إلى 1.4.0'), T('Yesterday 21:10', 'أمس 21:10')) +
    item('', T('Switched off Old Announcer', 'أُوقف Old Announcer'), T('10 Nov 16:03', '10 نوفمبر 16:03')) +
    item('', T('Removed Glow Trails', 'حُذف Glow Trails'), T('8 Nov 12:30 · files kept in the recovery folder', '8 نوفمبر 12:30 · الملفات محفوظة في مجلد الاسترجاع')) + '</div></div>';
  if (state === 'empty') return { body: empty('clock', T('Nothing has happened yet', 'لم يحدث شيء بعد'), T('Every install, update and removal is written here, newest first.', 'كل تثبيت وتحديث وحذف يُكتب هنا، الأحدث أولًا.')) };
  return { body: '<div class="limit">' + (state === 'loading' ? '<div class="card"><div class="row"><span class="spin"></span><div class="grow"><div><b>Haze · Ember</b></div><div class="muted">' + T('Downloading · 11.2 of 24.8 MB', 'جارٍ التنزيل · 11.2 من 24.8 م.ب') + '</div></div>' + btn(T('Cancel', 'إلغاء'), { size: 'sm' }) + '</div><div class="progress"><i style="width:45%"></i></div></div>' :
    '<p class="muted" style="margin:0">' + T('Nothing is downloading right now.', 'لا يوجد تنزيل الآن.') + '</p>') + history + '</div>' };
};

OVERLAYS.mod = function () {
  return '<div class="scrim side"><aside class="sheet" role="dialog" aria-label="Abrams · Steel"><div class="head"><h2 class="grow">Abrams · Steel</h2>' + btn('', { kind: 'ghost', icon: 'x', title: T('Close', 'إغلاق'), go: { over: '' } }) + '</div><div class="body">' +
    '<div class="mod"><div class="pic" style="border-radius:var(--radius-md);background:linear-gradient(135deg,hsl(18 45% 34%),hsl(58 40% 18%))">' + ic('box', 'lg') + '</div></div>' +
    '<div class="row wrap"><span class="soft">' + T('by', 'من') + ' vento</span>' + badge('Abrams') + badge(T('Skin', 'سكن')) + '</div>' +
    '<div class="col gap-2"><div class="fieldwrap"><label>' + T('File', 'الملف') + '</label>' + select(['abrams_steel_v3.zip · 24.8 MB', 'abrams_steel_lite.zip · 9.1 MB']) + '</div>' + btn(T('Install', 'ثبّت'), { kind: 'primary', size: 'lg', icon: 'download', go: { over: 'review' } }) + '</div>' +
    banner('warn', T('Not reviewed', 'لم يُراجَع'), T('From GameBanana. Made by the community; Toolbox has not reviewed it.', 'من GameBanana. صنعه المجتمع؛ Toolbox لم يراجعه.')) +
    '<dl class="kv"><dt>' + T('Updated', 'آخر تحديث') + '</dt><dd>' + T('3 days ago', 'قبل 3 أيام') + '</dd><dt>' + T('File check', 'فحص الملف') + '</dt><dd>' + T('Checksum published', 'البصمة منشورة') + '</dd><dt>' + T('Virus scan', 'فحص الفيروسات') + '</dt><dd>' + T('Clean, says GameBanana', 'نظيف حسب GameBanana') +
    '</dd><dt>' + T('Likes', 'إعجابات') + '</dt><dd>' + ltr('1,204') + '</dd><dt>' + T('Licence', 'الرخصة') + '</dt><dd>' + ltr('CC BY-NC') + '</dd></dl>' +
    '<p class="soft" style="margin:0">' + T('A brushed-steel look for Abrams with matching ability effects. Sample text standing in for the description from the mod page.', 'مظهر فولاذي لأبرامز مع مؤثرات قدرات مطابقة. نص تجريبي يمثّل وصف صفحة المود.') + '</p>' +
    '<div class="row">' + btn(T('Open on GameBanana', 'افتح في GameBanana'), { icon: 'ext' }) + btn(T('Show pictures', 'أظهر الصور'), { kind: 'ghost', icon: 'eye' }) + '</div></div></aside></div>';
};
OVERLAYS.review = function () {
  return '<div class="scrim"><div class="dialog" role="dialog" aria-modal="true"><div class="head"><h2 class="grow">' + T('Review before installing', 'راجِع قبل التثبيت') + '</h2>' + btn('', { kind: 'ghost', icon: 'x', title: T('Close', 'إغلاق'), go: { over: 'mod' } }) + '</div><div class="body">' +
    '<dl class="kv"><dt>' + T('Mod', 'المود') + '</dt><dd>Abrams · Steel ' + ltr('(abrams_steel_v3.zip)') + '</dd><dt>' + T('From', 'من') + '</dt><dd>GameBanana ' + badge(T('Not reviewed', 'لم يُراجَع'), 'warn') + '</dd><dt>' + T('File check', 'فحص الملف') + '</dt><dd>' + badge(T('Matches the published checksum', 'يطابق البصمة المنشورة'), 'ok', 'check') + '</dd></dl>' +
    '<div class="col gap-2"><b>' + T('What will be added to the game', 'ما الذي سيُضاف إلى اللعبة') + '</b><div class="card flat"><div class="list"><div class="item">' + ic('plus') + '<div class="grow">' + mono('game/citadel/addons/pak07_dir.vpk') + '</div><span class="muted">' + ltr('24.1 MB') + '</span></div></div></div><span class="muted">' + T('Nothing is replaced. Removing the mod deletes exactly this file.', 'لا شيء يُستبدل. حذف المود يحذف هذا الملف بالضبط.') + '</span></div>' +
    banner('warn', T('It changes the same files as Clean HUD', 'يغيّر نفس ملفات Clean HUD'), T('Clean HUD keeps winning because it has the lower number.', 'Clean HUD يبقى الغالب لأن رقمه أصغر.')) +
    check(T('I understand this mod was not reviewed by Toolbox', 'أفهم أن Toolbox لم يراجع هذا المود'), false) + '</div><div class="foot">' + btn(T('Cancel', 'إلغاء'), { go: { over: 'mod' } }) + btn(T('Install', 'ثبّت'), { kind: 'primary', off: true }) + '</div></div></div>';
};

/* ----------------------------------------------------------- Performance */
PAGES.performance = function (state, tab) {
  const stuck = state === 'empty' ? banner('warn', T('Link the game to apply', 'اربط اللعبة لتطبّق'), T('You can look around, but nothing can be written yet.', 'تقدر تتصفّح، لكن لا شيء يُكتب الآن.'), btn(T('Link the game', 'اربط اللعبة'), { size: 'sm', go: { page: 'settings', tab: 'game' } })) :
    state === 'error' ? banner('bad', T('Close Deadlock first', 'أغلق Deadlock أولًا'), T('Settings can\'t be written while the game is running. Nothing was changed.', 'لا يمكن كتابة الإعدادات واللعبة شغّالة. لا شيء تغيّر.'), btn(T('Try again', 'حاول مجددًا'), { size: 'sm' })) : '';
  const bar = state === 'loading' ? '<span class="spin"></span><span class="grow">' + T('Saving the originals, then writing 2 files…', 'نحفظ الأصل ثم نكتب ملفين…') + '</span>' + btn(T('Review and apply', 'راجِع وطبّق'), { kind: 'primary', off: true }) :
    '<span class="grow soft">' + T('Level 80 · View width 1.78 · 3 settings left out', 'المستوى 80 · عرض الرؤية 1.78 · 3 إعدادات مستثناة') + '</span>' + btn(T('Undo my changes', 'تراجع عن تغييراتي'), { kind: 'ghost' }) + btn(T('Review and apply', 'راجِع وطبّق'), { kind: 'primary', off: state === 'empty', go: { over: 'apply' } });
  if (tab === 'all') {
    const rows = [
      ['r_shadows', T('Dynamic shadows on or off.', 'تشغيل أو إيقاف الظلال المتحركة.'), '1', '0', badge(T('Blocked', 'محظور'), 'bad'), 0, 0],
      ['r_texture_stream_mip_bias', T('How blurry far textures get.', 'مقدار ضبابية الخامات البعيدة.'), '0', '2', badge(T('Works', 'يعمل'), 'ok', 'check'), 0, 1],
      ['r_enable_volume_fog', T('Thick fog in the lanes. Turning it off lets you see further.', 'الضباب الكثيف في الممرات. إيقافه يخلّيك تشوف أبعد.'), '1', '0', badge(T('Blocked', 'محظور'), 'bad'), 1, 0],
      ['panorama_max_fps', T('Frame limit for menus.', 'حد الإطارات في القوائم.'), '120', '60', badge(T('Removed', 'محذوف'), 'warn'), 0, 0],
      ['r_particle_max_detail_level', T('How detailed ability effects are.', 'تفاصيل مؤثرات القدرات.'), '3', '2', badge(T('Works', 'يعمل'), 'ok', 'check'), 0, 1],
      ['HairShading', T('Hair lighting quality.', 'جودة إضاءة الشعر.'), '—', '0', badge(T('Unverified', 'غير مؤكد')), 0, 1],
    ];
    if (state === 'empty') return { body: empty('search', T('No setting matches', 'لا يوجد إعداد مطابق'), T('Try another group or clear the filter.', 'جرّب مجموعة أخرى أو امسح الفلتر.'), btn(T('Clear the filter', 'امسح الفلتر'))), bar: bar };
    return { body: (state === 'error' ? banner('warn', T('These facts are for an older game version', 'هذه المعلومات لنسخة لعبة أقدم'), T('Checked against build 6857; your game is 6902. Some statuses may have changed.', 'فُحصت على النسخة 6857؛ لعبتك 6902. بعض الحالات ربما تغيّرت.')) : '') +
      '<p class="lead">' + T('Everything level 80 writes, in plain words, and whether the game really uses it. The status comes from Valve\'s public data; nobody checked it in the game.', 'كل ما يكتبه المستوى 80 بكلمات بسيطة، وهل اللعبة تستخدمه فعلًا. الحالة من بيانات Valve العامة؛ لم يتحقق منها أحد داخل اللعبة.') + '</p>' +
      '<div class="grid g4">' + tile('73', T('will be written', 'ستُكتب')) + tile('46', T('confirmed to work', 'مؤكد أنها تعمل')) + tile('23', T('the game ignores', 'تتجاهلها اللعبة')) + tile('4', T('not sure', 'غير متأكد')) + '</div>' +
      '<div class="row wrap">' + select([T('All groups', 'كل المجموعات'), T('Shadows', 'الظلال'), T('Fog', 'الضباب'), T('Textures', 'الخامات')]) + check(T('Only what the game ignores', 'فقط ما تتجاهله اللعبة'), false, true) + '<div class="end row">' + btn(T('Leave out the ignored ones', 'استثنِ المتجاهَلة')) + btn(T('Write everything', 'اكتب الكل'), { kind: 'ghost' }) + '</div></div>' +
      '<div class="card flat"><table class="table"><thead><tr><th>' + T('Write', 'اكتب') + '</th><th>' + T('Setting', 'الإعداد') + '</th><th class="num">' + T('Valve', 'Valve') + '</th><th class="num">' + T('Toolbox', 'Toolbox') + '</th><th>' + T('Status', 'الحالة') + '</th></tr></thead><tbody>' +
      rows.map(function (r) {
        if (state === 'loading') return '<tr><td>' + skel('18px', '18px') + '</td><td>' + skel('220px') + '</td><td>' + skel('24px') + '</td><td>' + skel('24px') + '</td><td>' + skel('64px', '22px') + '</td></tr>';
        return '<tr><td>' + check('', r[6]) + '</td><td>' + mono(r[0]) + (r[5] ? ' <span title="' + T('Can change how much you see', 'قد يغيّر ما تراه') + '" style="color:var(--color-warning-text)">' + ic('eye', 'sm') + '</span>' : '') + '<div class="sub">' + r[1] + '</div></td><td class="num">' + r[2] + '</td><td class="num">' + r[3] + '</td><td>' + r[4] + '</td></tr>';
      }).join('') + '</tbody></table></div>', bar: bar };
  }
  return { body: '<div class="limit">' + stuck +
    '<div class="card" style="gap:var(--space-4)"><div class="row wrap">' + seg([T('Balanced', 'متوازن'), T('Performance', 'أداء'), T('Maximum', 'أقصى')], 0) + '<span class="end muted">' + T('Screen resolution and FSR/DLSS are never changed.', 'دقة الشاشة و FSR/DLSS لا تتغيّر أبدًا.') + '</span></div>' +
    '<div class="row" style="align-items:baseline"><span style="font-size:var(--font-size-display);font-weight:var(--font-weight-semibold);line-height:1" class="ltr">80</span><span class="muted ltr">/ 200</span><span class="soft">' + T('Lighter textures, no bloom. Good for a mid-range PC.', 'خامات أخف وبدون توهّج. مناسب لجهاز متوسط.') + '</span></div>' +
    '<div class="row"><span class="muted">' + T('Best looks', 'أجمل شكل') + '</span>' + slider(40) + '<span class="muted">' + T('Most frames', 'أكثر إطارات') + '</span></div>' +
    '<div class="row wrap">' + badge(T('Textures: simpler', 'الخامات: أبسط')) + badge(T('Shadows: on', 'الظلال: شغّالة')) + badge(T('Fog: on', 'الضباب: شغّال')) + badge(T('Effects: medium', 'المؤثرات: متوسطة')) +
    '<button class="btn ghost sm end" ' + go({ tab: 'all' }) + '>' + T('See every setting (73)', 'شوف كل الإعدادات (73)') + ic('chev', 'sm') + '</button></div></div>' +
    '<div class="grid g2"><div class="card"><h2>' + T('View width', 'عرض الرؤية') + '</h2><p class="soft">' + T('A wider picture shows more to the sides. 1.78 is the normal 16:9.', 'صورة أعرض تُظهر أكثر على الجانبين. 1.78 هو 16:9 العادي.') + '</p><div class="row">' + slider(0) + '<div class="field" style="width:76px"><input value="1.78" class="ltr" aria-label="' + T('View width', 'عرض الرؤية') + '"></div></div></div>' +
    '<div class="card"><h2>' + T('Frame limit', 'حد الإطارات') + '</h2><p class="soft">' + T('Stops the game from drawing more frames than you need.', 'يمنع اللعبة من رسم إطارات أكثر مما تحتاج.') + '</p><div class="row">' + select([T('No limit', 'بدون حد'), '60', '120', '144', '240'], 'grow') + check(T('Limit in menus too', 'حد في القوائم أيضًا'), true) + '</div></div></div></div>', bar: bar };
};
OVERLAYS.apply = function () {
  return '<div class="scrim"><div class="dialog" role="dialog" aria-modal="true"><div class="head"><h2 class="grow">' + T('Review your changes', 'راجِع تغييراتك') + '</h2>' + btn('', { kind: 'ghost', icon: 'x', title: T('Close', 'إغلاق'), go: { over: '' } }) + '</div><div class="body">' +
    banner('ok', T('The originals are saved first', 'الأصل يُحفظ أولًا'), T('You can go back any time from Backups.', 'تقدر ترجع في أي وقت من النسخ والاسترجاع.')) +
    '<div class="card flat"><table class="table"><thead><tr><th>' + T('File', 'الملف') + '</th><th>' + T('What changes', 'ما الذي يتغيّر') + '</th></tr></thead><tbody><tr><td>' + mono('game/citadel/gameinfo.gi') + '</td><td>' + T('58 settings', '58 إعدادًا') + '</td></tr><tr><td>' + mono('cfg/video.txt') + '</td><td>' + T('12 settings · resolution kept', '12 إعدادًا · الدقة كما هي') + '</td></tr></tbody></table></div>' +
    '<button class="btn ghost sm" style="align-self:flex-start">' + ic('chev', 'sm') + T('Show every line', 'أظهر كل سطر') + '</button></div><div class="foot">' + btn(T('Cancel', 'إلغاء'), { go: { over: '' } }) + btn(T('Apply', 'طبّق'), { kind: 'primary', go: { over: 'done' } }) + '</div></div></div>';
};
OVERLAYS.done = function () {
  return '<div class="toast" role="status"><span style="color:var(--color-success-text)">' + ic('check') + '</span><span>' + T('Applied. Start the game to see it.', 'تم التطبيق. شغّل اللعبة لتشوفه.') + '</span>' + btn(T('Undo', 'تراجع'), { size: 'sm', kind: 'ghost', go: { over: '' } }) + '</div>';
};

/* ----------------------------------------------------------------- Stats */
PAGES.stats = function (state, tab) {
  const stamp = state === 'filled' ? badge(T('Saved copy · 2 hours ago', 'نسخة محفوظة · قبل ساعتين')) : state === 'error' ? badge(T('Old copy · yesterday', 'نسخة قديمة · أمس'), 'warn', 'warn') : '';
  const filters = '<div class="row wrap">' + seg([T('7 days', '7 أيام'), T('14 days', '14 يومًا'), T('30 days', '30 يومًا')], 1) + select([T('All modes', 'كل الأنماط'), T('Ranked', 'مصنّف'), T('Unranked', 'غير مصنّف')]) + select([T('All ranks', 'كل الرتب'), 'Oracle', 'Phantom', 'Ascendant', 'Eternus']) +
    '<div class="end row">' + stamp + btn(state === 'empty' ? T('Load statistics', 'حمّل الإحصائيات') : T('Refresh', 'حدّث'), { kind: state === 'empty' ? 'primary' : '', icon: 'refresh', busy: state === 'loading', off: state === 'loading' }) + '</div></div>';
  const fail = state === 'error' ? banner('bad', T("The stats service didn't answer", 'خدمة الإحصائيات لم تردّ'), T('Too many requests right now. Showing the copy saved yesterday.', 'طلبات كثيرة الآن. نعرض النسخة المحفوظة أمس.'), btn(T('Try again', 'حاول مجددًا'), { size: 'sm' })) : '';
  const nothing = empty('chart', T('Nothing loaded yet', 'لا شيء محمَّل بعد'), T('Press Load statistics. It asks api.deadlock-api.com once and sends only the period, mode and rank you chose. Nothing about you.', 'اضغط «حمّل الإحصائيات». يسأل api.deadlock-api.com مرة واحدة ويرسل فقط الفترة والنمط والرتبة. لا شيء عنك.'));
  if (tab === 'heroes') {
    const rows = [['Seven', '58,210', '13.4%', '53.1%', 'ok', 56, 8, '3.42', '31.2k'], ['Haze', '71,935', '16.6%', '51.2%', 'ok', 52, 6, '3.10', '33.0k'], ['Abrams', '40,118', '9.3%', '50.3%', '', 47, 9, '3.65', '29.8k'], ['Lash', '33,402', '7.7%', '48.1%', 'bad', 38, 8, '2.98', '30.1k'], ['Paradox', '12,044', '2.8%', '47.6%', '', 34, 18, '2.71', '28.4k']];
    if (state === 'empty') return { body: filters + nothing };
    return { body: filters + fail + '<div class="row">' + field(T('Find a hero', 'ابحث عن بطل'), 'search', '') + '<span class="end muted">' + T('432,845 matches · 44 heroes', '432,845 مباراة · 44 بطلًا') + '</span></div>' +
      '<div class="card flat"><table class="table"><thead><tr><th>' + T('Hero', 'البطل') + '</th><th class="num">' + T('Matches', 'المباريات') + '</th><th class="num">' + T('Picked', 'الاختيار') + '</th><th class="num">' + T('Win rate', 'نسبة الفوز') + '</th><th>' + T('How sure (95%)', 'مدى الثقة (95%)') + '</th><th class="num">KDA</th><th class="num">' + T('Net worth', 'الثروة') + '</th></tr></thead><tbody>' +
      rows.map(function (r) {
        if (state === 'loading') return '<tr>' + [90, 50, 40, 40, 110, 30, 40].map(function (w) { return '<td>' + skel(w + 'px') + '</td>'; }).join('') + '</tr>';
        return '<tr><td>' + r[0] + '</td><td class="num">' + r[1] + '</td><td class="num">' + r[2] + '</td><td class="num" style="font-weight:600;' + (r[4] ? 'color:var(--color-' + (r[4] === 'ok' ? 'success' : 'danger') + '-text)' : '') + '">' + r[3] + '</td><td><div class="range ' + r[4] + '"><i style="left:' + r[5] + '%;width:' + r[6] + '%"></i></div></td><td class="num">' + r[7] + '</td><td class="num">' + r[8] + '</td></tr>';
      }).join('') + '</tbody></table></div><p class="muted" style="margin:0">' + T('Green or red only when the whole range is above or below 50%. The middle line is 50%.', 'أخضر أو أحمر فقط إذا كان المدى كله فوق أو تحت 50%. الخط في الوسط هو 50%.') + '</p>' };
  }
  if (tab === 'ranks') {
    const ranks = [['Initiate', 4], ['Seeker', 9], ['Alchemist', 14], ['Arcanist', 18], ['Ritualist', 19], ['Emissary', 15], ['Archon', 10], ['Oracle', 6], ['Phantom', 3], ['Ascendant', 1.5], ['Eternus', 0.5]];
    if (state === 'empty') return { body: filters + nothing };
    return { body: filters + fail + '<div class="card flat"><table class="table"><thead><tr><th>' + T('Rank', 'الرتبة') + '</th><th style="width:55%">' + T('Share of players', 'نسبة اللاعبين') + '</th><th class="num">%</th></tr></thead><tbody>' +
      ranks.map(function (r) { return state === 'loading' ? '<tr><td>' + skel('80px') + '</td><td>' + skel('100%', '8px') + '</td><td>' + skel('30px') + '</td></tr>' : '<tr><td>' + r[0] + '</td><td><div class="bar"><i style="width:' + r[1] * 5 + '%"></i></div></td><td class="num">' + r[1] + '%</td></tr>'; }).join('') +
      '</tbody></table></div><p class="muted" style="margin:0">' + T('A player counts in the rank they had in each match, so someone who climbed appears in more than one row.', 'اللاعب يُحسب في رتبته وقت كل مباراة، فمن صعد يظهر في أكثر من صف.') + '</p>' };
  }
  const form = banner('info', T('This sends a Steam account number', 'هذا يرسل رقم حساب Steam'), T('Look up sends the number to api.deadlock-api.com. Toolbox saves nothing about the player on this PC.', '«ابحث» يرسل الرقم إلى api.deadlock-api.com. لا يحفظ Toolbox شيئًا عن اللاعب في هذا الجهاز.')) +
    '<div class="row top wrap"><div class="fieldwrap grow"><div class="field' + (state === 'error' ? ' is-error' : '') + '">' + ic('user') + '<input class="ltr" value="' + (state === 'empty' ? '' : state === 'error' ? 'steamcommunity.com/id/somebody' : '[U:1:104857600]') + '" placeholder="' + T('Account number or profile link', 'رقم الحساب أو رابط الملف') + '" aria-label="' + T('Steam account', 'حساب Steam') + '"></div>' +
    (state === 'error' ? '<span class="help err">' + T('A profile name can\'t be used here. Paste the number, or a link that has /profiles/ in it.', 'اسم الملف لا ينفع هنا. الصق الرقم، أو رابطًا فيه /profiles/.') + '</span>' : '<span class="help">' + T('A number, a 17-digit Steam ID, or a /profiles/ link.', 'رقم، أو معرّف Steam من 17 خانة، أو رابط /profiles/.') + '</span>') + '</div>' +
    btn(T('Use my Steam account', 'استخدم حسابي'), { icon: 'user' }) + btn(T('Look up', 'ابحث'), { kind: 'primary', busy: state === 'loading', off: state === 'loading' }) + '</div>' +
    '<div class="row wrap">' + seg([T('All time', 'كل الفترات'), T('30 days', '30 يومًا'), T('14 days', '14 يومًا'), T('7 days', '7 أيام')], 0) + select([T('All modes', 'كل الأنماط'), T('Ranked', 'مصنّف')]) + '</div>';
  if (state === 'empty' || state === 'error') return { body: '<div class="limit">' + form + (state === 'empty' ? empty('user', T('Whose stats?', 'إحصائيات من؟'), T('Enter an account above, then press Look up.', 'أدخل حسابًا فوق ثم اضغط «ابحث».')) : '') + '</div>' };
  if (state === 'loading') return { body: '<div class="limit">' + form + '<div class="grid g4">' + [1, 2, 3, 4].map(function () { return '<div class="tile">' + skel('60%', '24px') + '<div style="height:6px"></div>' + skel('40%') + '</div>'; }).join('') + '</div></div>' };
  return { body: '<div class="limit">' + form + '<div class="grid g4">' + tile('Oracle 3', T('rank', 'الرتبة')) + tile('318', T('matches', 'مباريات')) + tile('171', T('wins', 'انتصارات')) + tile('53.8%', T('win rate', 'نسبة الفوز')) + '</div>' +
    '<div class="card flat"><table class="table"><thead><tr><th>' + T('Hero', 'البطل') + '</th><th class="num">' + T('Matches', 'المباريات') + '</th><th class="num">' + T('Your win rate', 'فوزك') + '</th><th class="num">' + T('Everyone', 'الجميع') + '</th><th class="num">' + T('Difference', 'الفرق') + '</th><th class="num">KDA</th></tr></thead><tbody>' +
    [['Haze', '112', '57.1%', '51.2%', '+5.9', 'ok', '3.8'], ['Seven', '74', '51.4%', '53.1%', '−1.7', 'bad', '3.1'], ['Lash', '40', '50.0%', '48.1%', '+1.9', 'ok', '2.9']].map(function (r) {
      return '<tr><td>' + r[0] + '</td><td class="num">' + r[1] + '</td><td class="num">' + r[2] + '</td><td class="num muted">' + r[3] + '</td><td class="num" style="color:var(--color-' + (r[5] === 'ok' ? 'success' : 'danger') + '-text)">' + r[4] + '</td><td class="num">' + r[6] + '</td></tr>';
    }).join('') + '</tbody></table></div></div>' };
};
