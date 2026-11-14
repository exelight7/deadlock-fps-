"""Named pages: the one list the window, the sidebar, the tabs and the start-up flags read.

No Qt here. A page has an id, a title, a group (`main`, `bottom`, `hidden`), an icon name and its
tabs. Every tab (or a page without tabs) shows one *slot*: the name of a widget the window builds.
An address is `page` or `page.tab` (for example `mods.health`); `resolve()` turns it into the page,
the tab and the slot.

During the redesign the old pages live in the slots named in `LEGACY_SLOTS`; Phase 3 replaces them
one by one by changing only the slot a tab points at (see vault/Architecture/Shell and Page Registry.md).
"""
from dataclasses import dataclass, field

from ..i18n import tr

GROUPS = ('main', 'bottom', 'hidden')

# The widgets the window builds today, by name. The order is the order they are created in.
LEGACY_SLOTS = ('home', 'graphics', 'perf_all', 'stats', 'stats_ranks', 'stats_me', 'recovery', 'servers', 'crosshair', 'settings',
                'installed', 'compatibility', 'downloads', 'graph', 'store')


@dataclass(frozen=True)
class Tab:
    id: str
    title: str
    slot: str
    hint: str = ''


@dataclass(frozen=True)
class Page:
    id: str
    title: str
    group: str
    icon: str
    tabs: tuple = ()
    slot: str = ''                  # the slot of a page without tabs
    hint: str = ''
    badge: bool = False             # True while the page has news (for example an app update)
    section_list: bool = False      # the page shows its tabs as a list inside itself (Settings), so the window draws no tab bar

    def __post_init__(self):
        if self.group not in GROUPS:
            raise ValueError('unknown group: %s' % self.group)
        if bool(self.tabs) == bool(self.slot):
            raise ValueError('a page has either tabs or one slot: %s' % self.id)

    @property
    def default_tab(self):
        return self.tabs[0] if self.tabs else None


@dataclass
class Registry:
    pages: list = field(default_factory=list)

    def register(self, page):
        if any(p.id == page.id for p in self.pages):
            raise ValueError('page already registered: %s' % page.id)
        ids = [t.id for t in page.tabs]
        if len(set(ids)) != len(ids) or any('.' in i for i in ids + [page.id]):
            raise ValueError('bad tab ids on page: %s' % page.id)
        self.pages.append(page)
        return page

    def get(self, page_id):
        for page in self.pages:
            if page.id == page_id:
                return page
        raise KeyError(page_id)

    def group(self, name):
        return [p for p in self.pages if p.group == name]

    def resolve(self, address):
        """`'mods.health'` → (page, tab or None, slot). Unknown pages or tabs raise KeyError."""
        if not isinstance(address, str):
            raise TypeError('navigate by name, for example "mods.health", not by number')
        page_id, _, tab_id = address.partition('.')
        page = self.get(page_id)
        if not page.tabs:
            if tab_id:
                raise KeyError(address)
            return page, None, page.slot
        tab = next((t for t in page.tabs if t.id == tab_id), None) if tab_id else page.default_tab
        if tab is None:
            raise KeyError(address)
        return page, tab, tab.slot

    def address_of(self, slot):
        """The first address that shows a slot (used when old code asks for a widget by its slot)."""
        for page in self.pages:
            if page.slot == slot:
                return page.id
            for tab in page.tabs:
                if tab.slot == slot:
                    return '%s.%s' % (page.id, tab.id)
        raise KeyError(slot)

    def slots(self):
        found = []
        for page in self.pages:
            for slot in ([page.slot] if page.slot else [t.slot for t in page.tabs]):
                if slot not in found:
                    found.append(slot)
        return found

    def addresses(self):
        out = []
        for page in self.pages:
            out.append(page.id)
            out.extend('%s.%s' % (page.id, t.id) for t in page.tabs)
        return out


def default_registry():
    """The pages of Deadlock Toolbox (ids from vault/Design/New Design/06 Handoff to Build.md).

    Titles reuse strings that already have English and Arabic translations; Phase 3 renames them
    to the words of the new design.
    """
    r = Registry()
    r.register(Page('home', tr('الرئيسية'), 'main', 'home', slot='home',
                    hint=tr('حالة اللعبة وأدواتك في نظرة واحدة. اختر بطاقة للانتقال إليها.')))
    r.register(Page('mods', tr('Mods'), 'main', 'box', tabs=(
        Tab('browse', tr('Browse'), 'store'),
        Tab('installed', tr('Installed'), 'installed'),
        Tab('health', tr('Check'), 'compatibility'),
        Tab('activity', tr('Activity'), 'downloads'),
    )))
    r.register(Page('performance', tr('Performance'), 'main', 'gauge', tabs=(
        Tab('level', tr('Level'), 'graphics'),
        Tab('all', tr('Every setting'), 'perf_all'),
    )))
    r.register(Page('stats', tr('الإحصائيات'), 'main', 'chart', tabs=(
        Tab('heroes', tr('Heroes'), 'stats'),
        Tab('ranks', tr('Ranks'), 'stats_ranks'),
        Tab('me', tr('My stats'), 'stats_me'),
    )))
    r.register(Page('crosshair', tr('الكروس هير'), 'main', 'crosshair', slot='crosshair',
                    hint=tr('اختر تصميمًا جاهزًا، جرّب المعاينة، ثم راجع تطبيقه على حسابك.')))
    r.register(Page('servers', tr('السيرفرات'), 'main', 'globe', slot='servers',
                    hint=tr('انتظر القياس ← حدد المناطق ← اختر السماح بها فقط أو الحظر. فك كل الحظر متاح دائمًا.')))
    r.register(Page('backups', tr('Backups'), 'bottom', 'history', slot='recovery',
                    hint=tr('تبي ترجع؟ استرجع الأصل. تبي تنقل خياراتك؟ صدّر إعداداتك.')))
    r.register(Page('settings', tr('الإعدادات'), 'bottom', 'settings', section_list=True, tabs=(
        Tab('general', tr('General'), 'settings'),
        Tab('game', tr('Game'), 'settings'),
        Tab('protection', tr('Protection'), 'settings'),
        Tab('update', tr('App update'), 'settings'),
        Tab('sources', tr('Extra mod sources'), 'settings'),
        Tab('advanced', tr('Advanced'), 'settings'),
        Tab('about', tr('About'), 'settings'),
    )))
    r.register(Page('map', tr('الرسم المعرفي'), 'hidden', 'map', slot='graph',
                    hint=tr('خريطة تفاعلية: حرّك، كبّر، ابحث، واضغط على أي عقدة لترى ما يرتبط بها.')))
    return r


# Start-up flags → addresses (main.py / ui.main).
FLAGS = {'--crosshair': 'crosshair', '--updates': 'settings.update', '--inspector': 'mods.health', '--mods': 'mods.installed'}
