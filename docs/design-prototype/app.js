/* Deadlock Toolbox redesign prototype (Phase 1): shell, helpers and the prototype controls.
   Static mock-up. Nothing here talks to a server; every number and name on screen is sample data. */
'use strict';

// Original icons, 20 x 20 grid, 1.5 stroke, round caps and joins. `flip` ones mirror in right-to-left.
const ICONS = {
  home: 'M3 9.5 10 3l7 6.5V16a1 1 0 0 1-1 1h-3.5v-5h-5v5H4a1 1 0 0 1-1-1z',
  box: 'M10 2.5 17 6v8l-7 3.5L3 14V6zM3 6l7 3.5L17 6M10 9.5v8',
  gauge: 'M3.5 14a7 7 0 1 1 13 0M10 11.5l3.5-4.5M10 11.5h.01',
  chart: 'M4 16V9M10 16V4M16 16v-5',
  crosshair: 'M10 2.5v4M10 13.5v4M2.5 10h4M13.5 10h4M10 10h.01',
  globe: 'M10 3a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM3 10h14M10 3c2.2 2 3 4.3 3 7s-.8 5-3 7c-2.2-2-3-4.3-3-7s.8-5 3-7z',
  history: 'M3.5 10a6.5 6.5 0 1 0 2-4.7M3.5 4v3h3M10 6.5V10l2.5 1.5',
  settings: 'M4 6h7M15 6h1M4 14h1M9 14h7M13 4v4M7 12v4',
  search: 'M9 3.5a5.5 5.5 0 1 0 0 11 5.5 5.5 0 0 0 0-11zM13 13l3.5 3.5',
  download: 'M10 3v9M6.5 8.5 10 12l3.5-3.5M4 16h12',
  check: 'M4.5 10.5 8 14l7.5-8',
  warn: 'M10 3 18 16.5H2zM10 8.5v3.5M10 14.3v.2',
  x: 'M5 5l10 10M15 5 5 15',
  chev: 'M8 5l5 5-5 5',
  down: 'M5 8l5 5 5-5',
  folder: 'M3 6a1 1 0 0 1 1-1h3.5l1.5 2H16a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z',
  ext: 'M11 4h5v5M16 4l-7 7M8 5H5a1 1 0 0 0-1 1v9a1 1 0 0 0 1 1h9a1 1 0 0 0 1-1v-3',
  refresh: 'M16 10a6 6 0 1 1-1.8-4.3M16 4v3h-3',
  trash: 'M4 6h12M8 6V4h4v2M6 6l.7 10h6.6L14 6',
  info: 'M10 3a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM10 9v4.5M10 6.5v.2',
  more: 'M5 10h.01M10 10h.01M15 10h.01',
  eye: 'M2.5 10S5.5 5 10 5s7.5 5 7.5 5-3 5-7.5 5-7.5-5-7.5-5zM10 8a2 2 0 1 0 0 4 2 2 0 0 0 0-4z',
  shield: 'M10 2.5 16 5v4.5c0 3.8-2.5 6.6-6 8-3.5-1.4-6-4.2-6-8V5z',
  user: 'M10 10a3.2 3.2 0 1 0 0-6.4 3.2 3.2 0 0 0 0 6.4zM4 17c.6-3 3-4.5 6-4.5s5.4 1.5 6 4.5',
  back: 'M16 10H4M8.5 5.5 4 10l4.5 4.5',
  lock: 'M5 9h10v8H5zM7 9V6.5a3 3 0 0 1 6 0V9',
  block: 'M10 3a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM5 5l10 10',
  plus: 'M10 4v12M4 10h12',
  map: 'M5 6a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM15 9a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM8 18a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM6.8 4.6 13 6.4M5.6 5.9 7.5 14M13.6 8.5 9.2 14.6',
  clock: 'M10 3a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM10 6v4l2.5 2',
  tool: 'M12.5 3a4 4 0 0 0-3.7 5.6L3 14.4V17h2.6l5.8-5.8A4 4 0 0 0 17 7.5l-2.5 2.5-2-2L15 5.5A4 4 0 0 0 12.5 3z',
};
const FLIP = { chev: 1, back: 1, ext: 1 };

const S = { page: 'home', tab: '', lang: 'en', theme: 'dark', state: 'filled', accent: 'blue', size: 'std', over: '', shot: '' };

function T(en, ar) { return S.lang === 'ar' ? ar : en; }
function ic(name, cls) {
  return '<svg class="i ' + (cls || '') + (FLIP[name] ? ' flip' : '') + '" viewBox="0 0 20 20" aria-hidden="true"><path d="' + ICONS[name] + '"/></svg>';
}
function go(change) { return 'onclick="event.stopPropagation();nav(' + JSON.stringify(change).replace(/"/g, '&quot;') + ')"'; }
function btn(label, o) {
  o = o || {};
  return '<button class="btn ' + (o.kind || '') + ' ' + (o.size || '') + (label ? '' : ' icon') + '"' + (o.off ? ' disabled' : '') +
    (o.go ? ' ' + go(o.go) : '') + (o.title ? ' title="' + o.title + '" aria-label="' + o.title + '"' : '') + '>' +
    (o.busy ? '<span class="spin"></span>' : '') + (o.icon ? ic(o.icon, o.size === 'sm' ? 'sm' : '') : '') + (label || '') + '</button>';
}
function badge(text, kind, icon) { return '<span class="badge ' + (kind || '') + '">' + (icon ? ic(icon) : '') + text + '</span>'; }
function field(placeholder, icon, cls) {
  return '<div class="field ' + (cls || 'grow') + '">' + (icon ? ic(icon) : '') + '<input placeholder="' + placeholder + '" aria-label="' + placeholder + '"></div>';
}
function select(options, cls) {
  return '<div class="field ' + (cls || '') + '"><select aria-label="' + options[0] + '">' + options.map(function (o) { return '<option>' + o + '</option>'; }).join('') + '</select></div>';
}
function check(label, on, sw) {
  return '<label class="check"><input type="checkbox"' + (on ? ' checked' : '') + '><span class="' + (sw ? 'sw' : 'box') + '"></span>' + (label ? '<span>' + label + '</span>' : '') + '</label>';
}
function banner(kind, title, desc, action) {
  const icon = { warn: 'warn', bad: 'warn', ok: 'check' }[kind] || 'info';
  return '<div class="banner ' + kind + '" role="status">' + ic(icon) + '<div class="grow"><div class="t">' + title + '</div>' +
    (desc ? '<div class="d">' + desc + '</div>' : '') + '</div>' + (action || '') + '</div>';
}
function empty(icon, title, desc, action, bad) {
  return '<div class="empty"><div class="ico' + (bad ? ' bad' : '') + '">' + ic(icon, 'lg') + '</div><h3>' + title + '</h3><p>' + desc + '</p>' + (action || '') + '</div>';
}
function seg(items, on) {
  return '<div class="seg" role="radiogroup">' + items.map(function (t, i) { return '<button role="radio" aria-checked="' + (i === on) + '" class="' + (i === on ? 'on' : '') + '">' + t + '</button>'; }).join('') + '</div>';
}
function slider(percent) { return '<div class="slider" role="slider" tabindex="0"><i style="width:' + percent + '%"></i><b style="inset-inline-start:' + percent + '%"></b></div>'; }
function skel(width, height) { return '<div class="skel" style="width:' + width + ';' + (height ? 'height:' + height : '') + '"></div>'; }
function tile(number, label) { return '<div class="tile"><div class="n"><span class="ltr">' + number + '</span></div><div class="l">' + label + '</div></div>'; }
function ltr(text) { return '<span class="ltr">' + text + '</span>'; }
function mono(text) { return '<span class="mono">' + text + '</span>'; }
function head(title, right) { return '<div class="row"><h2 class="sec">' + title + '</h2><div class="end row">' + (right || '') + '</div></div>'; }

// The eight destinations. Sub-pages are tabs inside a destination, never extra sidebar entries.
function destinations() {
  return [
    { id: 'home', icon: 'home', name: T('Home', 'الرئيسية') },
    { id: 'mods', icon: 'box', name: T('Mods', 'المودات'), count: S.state === 'filled' ? 2 : 0,
      tabs: [['browse', T('Browse', 'تصفّح')], ['installed', T('Installed', 'المثبّتة')], ['health', T('Check', 'الفحص')], ['activity', T('Activity', 'السجل')]] },
    { id: 'performance', icon: 'gauge', name: T('Performance', 'الأداء'),
      tabs: [['level', T('Level', 'المستوى')], ['all', T('Every setting', 'كل الإعدادات')]] },
    { id: 'stats', icon: 'chart', name: T('Stats', 'الإحصائيات'),
      tabs: [['heroes', T('Heroes', 'الأبطال')], ['ranks', T('Ranks', 'الرتب')], ['me', T('My stats', 'إحصائياتي')]] },
    { id: 'crosshair', icon: 'crosshair', name: T('Crosshair', 'الكروس هير') },
    { id: 'servers', icon: 'globe', name: T('Servers', 'السيرفرات') },
    { id: 'backups', icon: 'history', name: T('Backups', 'النسخ والاسترجاع'), low: 1 },
    { id: 'settings', icon: 'settings', name: T('Settings', 'الإعدادات'), low: 1,
      tabs: [['general', T('General', 'عام')], ['game', T('Game', 'اللعبة')], ['protect', T('Protection', 'الحماية')], ['update', T('App update', 'تحديث البرنامج')],
        ['sources', T('Extra mod sources', 'مصادر مودات إضافية')], ['advanced', T('Advanced', 'متقدّم')], ['about', T('About', 'حول')]] },
    { id: 'map', hidden: 1, icon: 'map', name: T('Project map', 'خريطة المشروع') },
  ];
}

function gamePill() {
  if (S.state === 'empty' && S.page === 'home') return '<button class="gamepill" ' + go({ page: 'settings', tab: 'game' }) + '><span class="dot warn"></span>' + T('Game not linked', 'اللعبة غير مربوطة') + '</button>';
  return '<button class="gamepill" ' + go({ page: 'settings', tab: 'game' }) + ' title="' + T('Game folder and build', 'مجلد اللعبة ورقم النسخة') + '"><span class="dot"></span>' + T('Game linked', 'اللعبة مربوطة') + '</button>';
}

function render() {
  const root = document.documentElement;
  root.lang = S.lang; root.dir = S.lang === 'ar' ? 'rtl' : 'ltr';
  root.dataset.theme = S.theme; root.dataset.accent = S.accent;
  document.body.classList.toggle('shot', !!S.shot);
  const all = destinations();
  const dest = all.find(function (d) { return d.id === S.page; }) || all[0];
  if (dest.tabs && !dest.tabs.some(function (t) { return t[0] === S.tab; })) S.tab = dest.tabs[0][0];
  const page = PAGES[dest.id](S.state, S.tab);
  const side = all.filter(function (d) { return !d.hidden; });
  const navItem = function (d) {
    const on = d.id === dest.id || (dest.id === 'map' && d.id === 'settings');
    return '<button class="nav' + (on ? ' on' : '') + '"' + (on ? ' aria-current="page"' : '') + ' ' + go({ page: d.id, tab: '', over: '' }) + '>' + ic(d.icon) + '<span>' + d.name + '</span>' +
      (d.count ? '<span class="badge count">' + d.count + '</span>' : '') + '</button>';
  };
  const tabs = dest.tabs && dest.id !== 'settings' ? '<div style="padding-inline:var(--space-6)"><div class="tabs" role="tablist">' + dest.tabs.map(function (t) {
    return '<button role="tab" aria-selected="' + (t[0] === S.tab) + '" class="tab' + (t[0] === S.tab ? ' on' : '') + '" ' + go({ tab: t[0], over: '' }) + '>' + t[1] +
      (dest.id === 'mods' && t[0] === 'installed' && S.state === 'filled' ? '<span class="badge count">2</span>' : '') + '</button>';
  }).join('') + '</div></div>' : '';
  const busy = S.state === 'loading' && S.page === 'mods' ? '<button class="gamepill" ' + go({ page: 'mods', tab: 'activity' }) + '><span class="spin"></span>' + T('1 download', 'تنزيل واحد') + '</button>' : '';
  document.getElementById('window').className = 'window' + (S.size === 'min' ? ' min' : '');
  document.getElementById('window').innerHTML =
    '<div class="oscaption">' + ic('tool', 'sm') + 'Deadlock Toolbox<span class="dots ltr">— ☐ ✕</span></div>' +
    '<div class="shell"><nav class="sidebar" aria-label="' + T('Main', 'الرئيسي') + '"><div class="brand"><span class="mark">' + ic('tool') + '</span>Toolbox</div>' +
    side.filter(function (d) { return !d.low; }).map(navItem).join('') + '<div class="gap"></div>' +
    (S.state === 'filled' ? '<button class="nav" ' + go({ page: 'settings', tab: 'update' }) + '>' + ic('download') + '<span>' + T('Update ready', 'تحديث جاهز') + '</span><span class="badge info count" style="margin-inline-start:auto">' + ltr('4.1') + '</span></button>' : '') +
    side.filter(function (d) { return d.low; }).map(navItem).join('') + '<div class="ver ltr">v4.0.0</div></nav>' +
    '<div class="main"><header class="topbar">' + (page.back ? btn('', { kind: 'ghost', icon: 'back', title: T('Back', 'رجوع'), go: page.back }) : '') +
    '<h1>' + (page.title || dest.name) + '</h1><div class="end row">' + busy + gamePill() + '</div></header>' + tabs +
    '<main class="content">' + page.body + '</main>' + (page.bar ? '<div class="actionbar">' + page.bar + '</div>' : '') + '</div>' +
    (S.over && OVERLAYS[S.over] ? OVERLAYS[S.over]() : '') + '</div>';
  for (const key of Object.keys(S)) { const el = document.getElementById('c-' + key); if (el) el.value = S[key]; }
  const hash = Object.keys(S).filter(function (k) { return S[k]; }).map(function (k) { return k + '=' + S[k]; }).join('&');
  if (location.hash.slice(1) !== hash) history.replaceState(null, '', '#' + hash);
}

function nav(change) { Object.assign(S, change); render(); }

function readHash() {
  location.hash.slice(1).split('&').forEach(function (pair) { const p = pair.split('='); if (p[0] in S) S[p[0]] = decodeURIComponent(p[1] || ''); });
}
function boot() {
  readHash();
  window.addEventListener('hashchange', function () { S.tab = ''; S.over = ''; readHash(); render(); });
  ['page', 'lang', 'theme', 'state', 'accent', 'size'].forEach(function (key) {
    const el = document.getElementById('c-' + key);
    if (el) el.onchange = function () { nav(key === 'page' ? { page: el.value, tab: '', over: '' } : { [key]: el.value }); };
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && S.over) nav({ over: '' }); });
  render();
}
