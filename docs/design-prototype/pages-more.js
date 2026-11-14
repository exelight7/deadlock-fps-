/* Prototype pages 2 of 2: Crosshair, Servers, Backups, Settings, Project map. Sample data only. */
'use strict';

/* ------------------------------------------------------------- Crosshair */
PAGES.crosshair = function (state) {
  const note = state === 'empty' ? banner('warn', T('No crosshair was read from the game yet', 'لم يُقرأ كروس هير من اللعبة بعد'), T('Open Deadlock once, change the crosshair there, close the game, then press Read from game. You can still design and save here.', 'افتح Deadlock مرة، غيّر الكروس هير هناك، أغلق اللعبة، ثم اضغط «اقرأ من اللعبة». تقدر تصمّم وتحفظ هنا في كل الأحوال.')) :
    state === 'error' ? banner('bad', T('Close Deadlock first', 'أغلق Deadlock أولًا'), T('The crosshair can\'t be written while the game is running. Nothing was changed.', 'لا يمكن كتابة الكروس هير واللعبة شغّالة. لا شيء تغيّر.'), btn(T('Try again', 'حاول مجددًا'), { size: 'sm' })) : '';
  const control = function (name, percent, value) { return '<div class="row"><span style="width:110px" class="soft">' + name + '</span>' + slider(percent) + '<div class="field" style="width:64px"><input class="ltr" value="' + value + '" aria-label="' + name + '"></div></div>'; };
  return { body: note + '<div class="row wrap">' + btn(T('Ready designs (50)', 'تصاميم جاهزة (50)'), { icon: 'box' }) + badge(T('Your own design', 'تصميمك الخاص'), 'info') + '<div class="end row">' + btn(T('Save', 'احفظ')) + btn(T('Share code', 'كود المشاركة'), { icon: 'ext' }) + '</div></div>' +
    '<div class="grid g2" style="align-items:start"><div class="card"><h2>' + T('Preview', 'المعاينة') + '</h2><div class="xhair"></div><div class="row">' + select([T('Dark street', 'شارع مظلم'), T('Bright sky', 'سماء ساطعة'), T('Plain grey', 'رمادي سادة')], 'grow') + seg(['1×', '2×', '4×'], 0) + '</div></div>' +
    '<div class="card" style="gap:var(--space-4)">' + seg([T('Shape', 'الشكل'), T('Outline', 'الحدّ'), T('Movement', 'الحركة')], 0) +
    '<div class="row"><span style="width:110px" class="soft">' + T('Colour', 'اللون') + '</span>' + ['#ffffff', '#aaff78', '#6ee7ff', '#ffd166', '#ff7aa8', '#ff5d5d'].map(function (c) { return '<span class="swatch" style="background:' + c + '"></span>'; }).join('') + '<div class="field end" style="width:104px"><input class="ltr" value="#AAFF78" aria-label="' + T('Colour code', 'كود اللون') + '"></div></div>' +
    control(T('Thickness', 'السماكة'), 12, '2') + control(T('Length', 'الطول'), 18, '6') + control(T('Gap', 'الفراغ'), 35, '3.0') + control(T('Opacity', 'الشفافية'), 100, '100') + check(T('Dot in the middle', 'نقطة في الوسط'), false, true) + '</div></div>',
    bar: btn(T('Read from game', 'اقرأ من اللعبة'), { icon: 'refresh', busy: state === 'loading', off: state === 'loading' }) + btn(T('Bring back the last one', 'أرجِع السابق'), { kind: 'ghost', off: state === 'empty' }) + '<span class="grow"></span>' + btn(T('Review and apply', 'راجِع وطبّق'), { kind: 'primary', off: state === 'empty' || state === 'loading' }) };
};

/* --------------------------------------------------------------- Servers */
PAGES.servers = function (state) {
  if (state === 'empty') return { body: empty('globe', T('Get the server list', 'نزّل قائمة السيرفرات'), T('Toolbox asks Steam for the list of regions, then measures how fast each one answers from your PC.', 'يسأل Toolbox منصة Steam عن قائمة المناطق، ثم يقيس سرعة ردّ كل منطقة من جهازك.'), btn(T('Get the list and measure', 'نزّل وقِس'), { kind: 'primary', icon: 'download' })) };
  const rows = [['Dubai', 'dxb', 2, 18, 'ok', 1, 0], ['Fujairah', 'djfr', 2, 31, 'ok', 0, 0], ['Frankfurt', 'fra', 6, 96, 'warn', 1, 0], ['Mumbai', 'bom', 4, 74, 'warn', 0, 0], ['Singapore', 'sgp', 5, 142, 'bad', 0, 1], ['Hong Kong', 'hkg', 4, 171, 'bad', 0, 1]];
  const colour = { ok: 'success', warn: 'warning', bad: 'danger' };
  return { body: (state === 'error' ? banner('bad', T('Administrator permission was refused', 'رُفضت صلاحية المسؤول'), T('Blocking a region changes the system firewall, so Windows asks for permission. Nothing was blocked.', 'حظر منطقة يغيّر جدار الحماية، لذلك يطلب ويندوز الإذن. لم يُحظر شيء.'), btn(T('Try again', 'حاول مجددًا'), { size: 'sm' })) : '') +
    '<div class="row wrap">' + field(T('Search: Dubai, Frankfurt…', 'ابحث: دبي، فرانكفورت…'), 'search') + select([T('All regions', 'كل المناطق'), T('Middle East', 'الشرق الأوسط'), T('Europe', 'أوروبا'), T('Asia', 'آسيا')]) + select([T('Fastest first', 'الأسرع أولًا'), T('Name', 'الاسم')]) +
    btn(T('Measure again', 'قِس مجددًا'), { icon: 'refresh', busy: state === 'loading', off: state === 'loading' }) + '</div>' +
    (state === 'loading' ? '<div class="row"><div class="progress"><i style="width:44%"></i></div><span class="muted">' + T('14 of 32', '14 من 32') + '</span></div>' : '') +
    '<div class="card flat"><table class="table"><thead><tr><th></th><th>' + T('Region', 'المنطقة') + '</th><th class="num">' + T('Servers', 'الخوادم') + '</th><th class="num">' + T('Ping', 'البنق') + '</th><th>' + T('Status', 'الحالة') + '</th></tr></thead><tbody>' +
    rows.map(function (r, i) {
      const waiting = state === 'loading' && i > 2;
      return '<tr class="' + (r[5] ? 'sel' : '') + '"><td>' + check('', r[5]) + '</td><td>' + r[0] + ' <span class="mono muted">' + r[1] + '</span></td><td class="num">' + r[2] + '</td><td class="num" style="font-weight:600;color:var(--color-' + colour[r[4]] + '-text)">' + (waiting ? skel('40px') : r[3] + ' ms') +
        '</td><td>' + (r[6] ? badge(T('Blocked', 'محظورة'), 'bad', 'block') : badge(T('Allowed', 'مسموحة'), 'ok', 'check')) + '</td></tr>';
    }).join('') + '</tbody></table></div><p class="muted" style="margin:0">' + T('This is the answer time of Steam\'s relay servers, not your ping inside a match.', 'هذا زمن ردّ خوادم Steam الوسيطة، وليس البنق داخل المباراة.') + '</p>',
    bar: '<span class="soft">' + T('2 selected', 'محدّدتان') + '</span>' + btn(T('Block these', 'احظر هذه'), { kind: 'danger-quiet', icon: 'block' }) + btn(T('Allow only these', 'اسمح بهذه فقط')) + '<span class="grow"></span>' + btn(T('Unblock everything', 'ألغِ كل الحظر'), { kind: 'ghost' }) };
};

/* --------------------------------------------------------------- Backups */
PAGES.backups = function (state) {
  if (state === 'empty') return { body: empty('history', T('Nothing to restore yet', 'لا يوجد ما يُسترجع بعد'), T('Toolbox saves the original game files before its first change. After that, you can always come back here.', 'يحفظ Toolbox ملفات اللعبة الأصلية قبل أول تغيير. بعدها تقدر ترجع هنا دائمًا.')) };
  const undo = function (name, desc) { return '<div class="item"><div class="grow"><div class="t">' + name + '</div><div class="d">' + desc + '</div></div>' + btn(T('Review undo', 'راجِع التراجع'), { size: 'sm' }) + '</div>'; };
  return { body: '<div class="limit">' +
    (state === 'error' ? banner('bad', T('The game files changed outside Toolbox', 'ملفات اللعبة تغيّرت خارج Toolbox'), T('Probably a game update. Tick "Keep those changes" below to restore safely; nothing was changed.', 'غالبًا تحديث للعبة. فعّل «احتفظ بتلك التغييرات» تحت لتسترجع بأمان؛ لا شيء تغيّر.')) : '') +
    (state === 'loading' ? '<div class="card"><div class="row"><span class="spin"></span><h2>' + T('Restoring the original files…', 'نسترجع الملفات الأصلية…') + '</h2></div><div class="progress"><i style="width:70%"></i></div></div>' : '') +
    '<div class="card"><h2>' + T('Go back to the original game files', 'ارجع لملفات اللعبة الأصلية') + '</h2><p class="soft">' + T('Puts back every file Toolbox changed. A copy of how things are now is kept first.', 'يرجّع كل ملف غيّره Toolbox. تُحفظ نسخة من الوضع الحالي أولًا.') + '</p>' +
    check(T('Keep changes made outside Toolbox (for example by a game update)', 'احتفظ بالتغييرات التي صارت خارج Toolbox (مثل تحديث للعبة)'), state === 'error') +
    '<div class="row">' + btn(T('Restore the originals', 'استرجع الأصل'), { kind: 'danger-quiet', icon: 'history', off: state === 'loading' }) + btn(T('Open the backups folder', 'افتح مجلد النسخ'), { kind: 'ghost', icon: 'folder' }) + '</div></div>' +
    '<div class="card flat"><div style="padding:var(--space-4) var(--space-4) 0">' + head(T('Undo one tool only', 'تراجع عن أداة واحدة فقط')) + '</div><div class="list">' +
    undo(T('Performance', 'الأداء'), T('Level 80 was applied on 12 Nov.', 'طُبّق المستوى 80 في 12 نوفمبر.')) + undo(T('Crosshair', 'الكروس هير'), T('Brings back the crosshair the game had before.', 'يرجّع الكروس هير الذي كان في اللعبة قبل.')) +
    undo(T('Classic pack mods', 'مودات الحزمة الكلاسيكية'), T('Removes them and restores the game files.', 'يحذفها ويسترجع ملفات اللعبة.')) + undo(T('Servers', 'السيرفرات'), T('Removes every block Toolbox created.', 'يزيل كل حظر أنشأه Toolbox.')) + '</div></div>' +
    '<div class="grid g2"><div class="card"><h2>' + T('Move your settings', 'انقل إعداداتك') + '</h2><p class="soft">' + T('Save your performance choices to a file, or load them on another PC.', 'احفظ اختيارات الأداء في ملف، أو حمّلها في جهاز آخر.') + '</p><div class="row">' + btn(T('Save to a file', 'احفظ في ملف')) + btn(T('Load from a file', 'حمّل من ملف')) + '</div></div>' +
    '<div class="card flat"><div style="padding:var(--space-4) var(--space-4) 0">' + head(T('Saved copies', 'النسخ المحفوظة')) + '</div><div class="list"><div class="item">' + ic('clock') + '<div class="grow">' + ltr('12 Nov 2026 · 18:40') + '</div><span class="muted">' + T('before Performance', 'قبل الأداء') + '</span></div><div class="item">' + ic('clock') + '<div class="grow">' + ltr('9 Nov 2026 · 21:05') + '</div><span class="muted">' + T('first change', 'أول تغيير') + '</span></div></div></div></div></div>' };
};

/* -------------------------------------------------------------- Settings */
function setRow(title, desc, control) { return '<div class="item"><div class="grow"><div class="t">' + title + '</div>' + (desc ? '<div class="d">' + desc + '</div>' : '') + '</div>' + control + '</div>'; }
PAGES.settings = function (state, tab) {
  const dest = destinations().find(function (d) { return d.id === 'settings'; });
  const sub = '<div class="subnav">' + dest.tabs.map(function (t) { return '<button class="nav' + (t[0] === tab ? ' on' : '') + '" ' + go({ tab: t[0] }) + '>' + t[1] + (t[0] === 'update' && state === 'filled' ? '<span class="badge count" style="margin-inline-start:auto">1</span>' : '') + '</button>'; }).join('') + '</div>';
  let body = '';
  if (tab === 'general') {
    body = '<div class="card flat"><div class="list">' + setRow(T('Language', 'اللغة'), T('Changes after the app restarts.', 'تتغيّر بعد إعادة تشغيل البرنامج.'), select(['English', 'العربية'])) +
      setRow(T('Look', 'المظهر'), T('"System" follows Windows.', '«النظام» يتبع ويندوز.'), seg([T('System', 'النظام'), T('Dark', 'داكن'), T('Light', 'فاتح')], S.theme === 'dark' ? 1 : 2)) +
      setRow(T('Text size', 'حجم النص'), T('Makes everything bigger or smaller.', 'يكبّر أو يصغّر كل شيء.'), seg(['90%', '100%', '115%', '130%'], 1)) +
      setRow(T('Less motion', 'حركة أقل'), T('Turns off the small animations.', 'يوقف الحركات الصغيرة.'), check('', false, true)) + '</div></div>';
  } else if (tab === 'game') {
    const path = state === 'empty' ? '' : state === 'error' ? 'D:\\Games\\Old' : 'C:\\Program Files (x86)\\Steam\\steamapps\\common\\Deadlock';
    body = (state === 'empty' ? banner('warn', T('The game is not linked', 'اللعبة غير مربوطة'), T('Mods, Performance, Crosshair and Backups need it.', 'المودات والأداء والكروس هير والنسخ تحتاجها.')) : '') +
      '<div class="card"><h2>' + T('Where Deadlock is installed', 'أين Deadlock مثبّتة') + '</h2><div class="fieldwrap"><div class="row"><div class="field grow' + (state === 'error' ? ' is-error' : '') + '">' + ic('folder') + '<input class="mono" value="' + path + '" placeholder="' + T('Choose the game folder', 'اختر مجلد اللعبة') + '" aria-label="' + T('Game folder', 'مجلد اللعبة') + '"></div>' +
      btn(T('Choose', 'اختر')) + btn(T('Find automatically', 'ابحث تلقائيًا'), { icon: 'search', busy: state === 'loading', off: state === 'loading' }) + '</div>' + (state === 'error' ? '<span class="help err">' + T('Deadlock is not in this folder. Pick the folder named "Deadlock" inside steamapps/common.', 'Deadlock ليست في هذا المجلد. اختر المجلد المسمّى «Deadlock» داخل steamapps/common.') + '</span>' : '') + '</div>' +
      (state === 'filled' ? '<dl class="kv"><dt>' + T('Game version', 'نسخة اللعبة') + '</dt><dd>' + ltr('build 6857') + '</dd><dt>' + T('Game state', 'حالة اللعبة') + '</dt><dd>' + badge(T('Closed', 'مغلقة'), 'ok') + '</dd><dt>' + T('Steam account folder', 'مجلد حساب Steam') + '</dt><dd>' + ltr('104857600') + '</dd></dl>' : '') + '</div>';
  } else if (tab === 'protect') {
    body = '<div class="card flat"><div class="list">' + setRow(T('Put my settings back after the game closes', 'أرجِع إعداداتي بعد إغلاق اللعبة'), T('The game sometimes resets them. Toolbox must stay open; it never writes while the game runs.', 'اللعبة ترجّعها أحيانًا. يجب أن يبقى Toolbox مفتوحًا؛ ولا يكتب أبدًا واللعبة شغّالة.'), check('', true, true)) +
      setRow(T('Check now', 'افحص الآن'), state === 'error' ? '<span style="color:var(--color-danger-text)">' + T('The game is running. Close it and try again.', 'اللعبة شغّالة. أغلقها وحاول مجددًا.') + '</span>' : T('Last check: today 18:40 · everything in place.', 'آخر فحص: اليوم 18:40 · كل شيء في مكانه.'), btn(T('Check and repair', 'افحص وأصلِح'), { busy: state === 'loading', off: state === 'loading' })) + '</div></div>';
  } else if (tab === 'update') {
    const top = state === 'empty' ? '<div class="card"><div class="row">' + badge(T('Up to date', 'محدّث'), 'ok', 'check') + '<h2>' + T('You have the latest version', 'عندك آخر إصدار') + '</h2></div><p class="muted">' + T('Checked today 09:12.', 'فُحص اليوم 09:12.') + '</p><div class="row">' + btn(T('Check now', 'افحص الآن'), { icon: 'refresh' }) + '</div></div>' :
      state === 'loading' ? '<div class="card"><div class="row"><span class="spin"></span><h2>' + T('Downloading Toolbox 4.1.0…', 'جارٍ تنزيل Toolbox 4.1.0…') + '</h2><span class="end muted ltr">38 / 61 MB</span></div><div class="progress"><i style="width:62%"></i></div><div class="row"><span class="grow muted">' + T('The file is checked before anything is installed.', 'يُفحص الملف قبل تثبيت أي شيء.') + '</span>' + btn(T('Cancel', 'إلغاء'), { size: 'sm' }) + '</div></div>' :
      (state === 'error' ? banner('bad', T('The download did not pass its check', 'التنزيل لم يجتز الفحص'), T('The file did not match the published checksum, so it was deleted. Nothing was installed.', 'الملف لم يطابق البصمة المنشورة فحُذف. لم يُثبّت شيء.'), btn(T('Try again', 'حاول مجددًا'), { size: 'sm' })) : '') +
      '<div class="card"><div class="row">' + badge(T('New', 'جديد'), 'info') + '<h2>' + T('Toolbox 4.1.0 is ready', 'Toolbox 4.1.0 جاهز') + '</h2></div><p class="soft">' + T('What is new: sample release notes stand here. They come from the public releases page.', 'ما الجديد: هنا ملاحظات إصدار تجريبية. تأتي من صفحة الإصدارات العامة.') + '</p><div class="row">' + btn(T('Download and install', 'نزّل وثبّت'), { kind: 'primary', icon: 'download' }) + btn(T('Releases page', 'صفحة الإصدارات'), { kind: 'ghost', icon: 'ext' }) + '</div></div>';
    body = top + '<div class="card flat"><div class="list">' + setRow(T('Your version', 'إصدارك'), '', ltr('4.0.0')) + setRow(T('Check when the app starts', 'افحص عند تشغيل البرنامج'), T('At most once a day. It only reads the public releases page.', 'مرة في اليوم كحد أقصى. يقرأ صفحة الإصدارات العامة فقط.'), check('', true, true)) + '</div></div>';
  } else if (tab === 'sources') {
    const row = function (name, url, status, on) { return '<div class="item">' + check('', on, true) + '<div class="grow"><div class="t">' + name + '</div><div class="d mono">' + url + '</div></div>' + status + btn('', { size: 'sm', kind: 'ghost', icon: 'more', title: T('More actions', 'إجراءات أخرى') }) + '</div>'; };
    body = '<p class="lead">' + T('A source is an extra place that publishes mods, usually a mod maker\'s page on GitHub. The Mods page already covers GameBanana, so most people never need this.', 'المصدر مكان إضافي ينشر مودات، غالبًا صفحة صانع مودات في GitHub. صفحة المودات تغطي GameBanana أصلًا، فأغلب الناس لا يحتاجون هذا.') + '</p>' +
      '<div class="row">' + field(T('Paste a source address (https://…)', 'الصق عنوان المصدر'), 'plus') + btn(T('Add', 'أضِف'), { kind: 'primary' }) + '</div>' +
      (state === 'empty' ? empty('plus', T('No extra sources', 'لا توجد مصادر إضافية'), T('Added sources appear here. Their mods show up in Mods, under "My sources".', 'المصادر المضافة تظهر هنا. موداتها تظهر في المودات تحت «مصادري».')) :
        '<div class="card flat"><div class="list">' + row('devkit mods', 'github.com/devkit/deadlock-mods', state === 'error' ? badge(T("Didn't answer · saved list shown", 'لم يردّ · نعرض المحفوظ'), 'warn', 'warn') : state === 'loading' ? '<span class="spin"></span>' : badge(T('14 mods', '14 مودًا'), 'ok'), true) +
        row('Toolbox', 'github.com/exelight7/deadlock-fps-', badge(T('Official', 'رسمي'), 'info', 'shield'), true) + row('old-pack', 'example.org/mods', badge(T('Off', 'متوقف')), false) + '</div></div>' +
        '<div class="row">' + btn(T('Refresh all', 'حدّث الكل'), { icon: 'refresh' }) + btn(T('Load a list', 'حمّل قائمة'), { kind: 'ghost' }) + btn(T('Save my list', 'احفظ قائمتي'), { kind: 'ghost' }) + '</div>');
  } else if (tab === 'advanced') {
    body = '<div class="card flat"><div class="list">' + setRow(T('Show mod pictures while browsing', 'أظهر صور المودات أثناء التصفّح'), T('Loads small pictures from GameBanana as you scroll. Off: pictures load only when you ask.', 'يحمّل صورًا صغيرة من GameBanana وأنت تتصفّح. إيقافه: الصور تتحمّل فقط إذا طلبت.'), check('', false, true)) +
      setRow(T('Project map', 'خريطة المشروع'), T('A drawing of how the mods, sources and parts of Toolbox connect.', 'رسم يوضّح كيف ترتبط المودات والمصادر وأجزاء Toolbox.'), btn(T('Open', 'افتح'), { go: { page: 'map' } })) +
      setRow(T('App data folder', 'مجلد بيانات البرنامج'), T('The mod list, saved stats and settings live here.', 'قائمة المودات والإحصائيات المحفوظة والإعدادات هنا.'), btn(T('Open the folder', 'افتح المجلد'), { icon: 'folder' })) + '</div></div>';
  } else {
    body = '<div class="card"><div class="row"><div class="brand" style="padding:0"><span class="mark">' + ic('tool') + '</span>Deadlock Toolbox</div><span class="end muted ltr">4.0.0 · Windows x64</span></div><p class="soft">' +
      T('A free, open-source tool made by the community. It is not affiliated with Valve.', 'أداة مجانية مفتوحة المصدر صنعها المجتمع. ليست تابعة لـValve.') + '</p><div class="row">' + btn('GitHub', { icon: 'ext' }) + btn(T('Licences', 'التراخيص'), { kind: 'ghost' }) + '</div></div>';
  }
  return { body: '<div class="row top gap-6" style="flex:1">' + sub + '<div class="col gap-4 grow" style="max-width:760px">' + body + '</div></div>' };
};

/* ----------------------------------------------------------- Project map */
PAGES.map = function (state) {
  const back = { page: 'settings', tab: 'advanced' };
  if (state === 'empty') return { back: back, body: empty('map', T('Nothing to draw yet', 'لا يوجد ما يُرسم بعد'), T('The map fills in when you have mods or sources.', 'تمتلئ الخريطة عندما يكون عندك مودات أو مصادر.')) };
  if (state === 'error') return { back: back, body: empty('warn', T('The map could not be built', 'تعذّر بناء الخريطة'), T('The notes that describe the project were not found in this copy of the app.', 'الملاحظات التي تصف المشروع غير موجودة في هذه النسخة من البرنامج.'), '', true) };
  const node = function (x, y, text, colour) { return '<g><circle cx="' + x + '" cy="' + y + '" r="9" fill="var(--color-' + colour + ')"/><text x="' + x + '" y="' + (y + 26) + '" text-anchor="middle" font-size="12" fill="var(--color-text-secondary)">' + text + '</text></g>'; };
  return { back: back, body: '<div class="row wrap">' + field(T('Find in the map', 'ابحث في الخريطة'), 'search') + '<button class="chip on">' + T('Mods', 'مودات') + ' 12</button><button class="chip on">' + T('Sources', 'مصادر') + ' 3</button><button class="chip">' + T('App parts', 'أجزاء البرنامج') + ' 41</button>' + btn(T('Fit', 'لائم'), { size: 'sm' }) + '</div>' +
    '<div class="map">' + (state === 'loading' ? '<div class="empty"><span class="spin"></span><p>' + T('Arranging 56 items…', 'نرتّب 56 عنصرًا…') + '</p></div>' :
    '<svg viewBox="0 0 800 380" width="100%" height="100%" style="direction:ltr"><g stroke="var(--color-border-control)" stroke-width="1.2"><path d="M400 180 250 90M400 180 560 100M400 180 300 290M400 180 540 280M250 90 140 150M560 100 660 170" fill="none"/></g>' +
    node(400, 180, 'GameBanana', 'accent-fill') + node(250, 90, 'Clean HUD', 'success-text') + node(560, 100, 'Night Skyline', 'success-text') + node(300, 290, 'Minimal Map', 'success-text') + node(540, 280, 'Abrams · Steel', 'text-muted') + node(140, 150, 'mira', 'warning-text') + node(660, 170, 'oskar', 'warning-text') + '</svg>') + '</div>' };
};
