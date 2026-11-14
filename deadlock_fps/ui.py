"""The main window: the new shell (sidebar, top bar, tabs) around the pages, addressed by name.

Pages are listed once, in `shell.registry.default_registry()`. The window builds one widget per *slot*
(`self.slots[name]`) and shows the slot of the address it is asked for: `navigate('mods.health')`.
Every page is built on the shell components (vault/Architecture/Shell and Page Registry.md); the window only owns the
state they share (the game link, the services) and what the controls ask of it.
"""
import json
import sys
from pathlib import Path

from PySide6.QtCore import QSize, QStandardPaths, Qt, QTimer, QUrl, QThreadPool
from PySide6.QtGui import QDesktopServices, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QScrollArea, QStackedWidget, QVBoxLayout, QWidget

from . import __version__, i18n
from .core import ASSETS
from .game_link import GameLinkMixin
from .i18n import tr
from .mod_service import ModService
from .mods import ModLibrary
from .pages.activity import ActivityPage
from .pages.backups import BackupsMixin
from .pages.browse import BrowsePage
from .pages.browse_host import BrowseHost
from .pages.check import CheckPage
from .pages.classic import ClassicPackMixin
from .pages.crosshair import CrosshairPage
from .pages.home import HomePage
from .pages.installed import InstalledPage
from .pages.map import GraphPage
from .pages.performance import PerformanceMixin
from .pages.servers import ServerPage
from .pages.settings import SettingsMixin, SettingsPage
from .pages.source_list import SourceList
from .pages.update import UpdatePage
from .pages.sources import SourcesView
from .pages.stats import StatsPage
from .shell import theme as shell_theme
from .shell.base import brand_logo, dark_palette, load_fonts
from .shell.components import Button, GamePill, NavItem, Sidebar, Tabs, Toast, TopBar, text_label
from .shell.motion import Intro, PageTransition
from .shell.registry import FLAGS, default_registry
from .stats_service import StatsService
from .store_service import StoreService

GITHUB = 'https://github.com/exelight7/deadlock-fps-'


class Window(GameLinkMixin, PerformanceMixin, BackupsMixin, SettingsMixin, ClassicPackMixin, QMainWindow):
    def __init__(self, registry=None):
        super().__init__()
        load_fonts()
        self.setWindowTitle('Deadlock Toolbox')
        self.resize(1200, 820)
        self.setMinimumSize(940, 680)
        window_icon = QIcon(str(ASSETS / 'app.png'))
        for size in (16, 24, 32, 48, 64, 128, 256):
            window_icon.addFile(str(ASSETS / f'brand/icon-{size}.png'), QSize(size, size))
        self.setWindowIcon(window_icon)
        self.preferences_file = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / 'workspace.json'
        self.preferred_account = None
        self.saved_game = ''
        self.saved_look = {}
        try:
            saved = json.loads(self.preferences_file.read_text(encoding='utf-8'))
            if isinstance(saved, dict):
                self.saved_game = saved.get('game', '') if isinstance(saved.get('game'), str) else ''
                self.preferred_account = saved.get('account') if isinstance(saved.get('account'), str) else None
                self.saved_look = saved.get('look') if isinstance(saved.get('look'), dict) else {}
        except (OSError, ValueError):
            pass
        self.controls = {}
        self.mod_checks = {}
        self.mod_labels = {}
        legacy = Path(QStandardPaths.writableLocation(QStandardPaths.GenericDataLocation)) / 'exelight7/DeadlockFPSStudio/mods'
        self.library = ModLibrary(legacy if legacy.exists() else Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / 'mods')
        self.guard_signature = None
        self.guard_retries = 0
        self.guard_attempts = {}
        self.intro_played = False
        self.update_available = False
        self.game_linked = False
        self.registry = registry or default_registry()
        self.slots = {}
        self.current_address = ''
        self.current_slot = ''
        self.build_shell()
        self.build_slots()
        self.path_timer = QTimer(self)
        self.path_timer.setSingleShot(True)
        self.path_timer.setInterval(400)
        self.path_timer.timeout.connect(self.mod_service.changed.emit)
        self.path.textChanged.connect(lambda _: self.path_timer.start())
        self.path.editingFinished.connect(self.check_stale)
        self.update_startup_timer = QTimer(self)
        self.update_startup_timer.setSingleShot(True)
        self.update_startup_timer.timeout.connect(self.updates.automatic_check)
        self.navigate('home')
        self.load_preset('balanced')
        self.link_saved_game()
        try:
            candidates = self.library.discover()
            if candidates:
                self.library.import_sources(candidates)
        except Exception:
            pass
        self.refresh_mod_library()
        self.guard_timer = QTimer(self)
        self.guard_timer.setInterval(5000)
        self.guard_timer.timeout.connect(self.guard_tick)
        self.guard_timer.start()
        self.detect_timer = QTimer(self)
        self.detect_timer.setInterval(20000)
        self.detect_timer.timeout.connect(self.auto_detect)
        self.detect_timer.start()
        self.update_game_status()
        self.refresh_home()

    # --- the shell -------------------------------------------------------------------------------

    def build_shell(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.sidebar = Sidebar()
        side = self.sidebar.box
        side.addWidget(text_label('Deadlock Toolbox', 'SidebarTitle', wrap=False))
        side.addSpacing(12)
        self.nav = {}
        for page in self.registry.group('main'):
            side.addWidget(self.nav_item(page))
        side.addStretch()
        for page in self.registry.group('bottom'):
            side.addWidget(self.nav_item(page))
        meta = text_label(__version__, 'Muted', wrap=False)
        meta.setLayoutDirection(Qt.LeftToRight)
        side.addSpacing(8)
        side.addWidget(meta)
        git = Button('GitHub', 'ghost', 'sm', icon='ext')
        git.setToolTip(GITHUB.removeprefix('https://'))
        git.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GITHUB)))
        side.addWidget(git)
        layout.addWidget(self.sidebar)

        content = QWidget()
        v = QVBoxLayout(content)
        gutter = shell_theme.current().px('space.5')
        v.setContentsMargins(gutter, 8, gutter, 16)
        v.setSpacing(shell_theme.current().px('space.3'))
        self.content_layout = v
        self.topbar = TopBar()
        self.page_title = self.topbar.title
        self.game_pill = GamePill(tr('Game not linked'))
        self.game_pill.setToolTip('Deadlock')
        self.game_pill.clicked.connect(self.focus_game)
        self.topbar.add_trailing(self.game_pill)
        v.addWidget(self.topbar)
        self.tabs = Tabs()
        self.topbar.back.connect(lambda: self.navigate('settings.advanced'))
        self.tabs.changed.connect(lambda tab: self.navigate('%s.%s' % (self.current_address.partition('.')[0], tab)))
        v.addWidget(self.tabs)
        for keys, delta in (('Ctrl+Tab', 1), ('Ctrl+Shift+Tab', -1)):
            QShortcut(QKeySequence(keys), self, activated=lambda d=delta: self.tabs.step(d))
        self.stack = QStackedWidget()
        v.addWidget(self.stack, 1)
        layout.addWidget(content, 1)
        self.transition = PageTransition(content, lambda: self.tabs.geometry().bottom() + 1, lambda: self.stack.geometry().bottom() + 1)

    def nav_item(self, page):
        item = NavItem(page.id, page.title, page.icon)
        item.clicked.connect(lambda _=False, p=page.id: self.navigate(p))
        self.nav[page.id] = item
        return item

    def add_slot(self, name, widget):
        """Put a page widget in the stack under its slot name (see shell/registry.py)."""
        if name in self.slots:
            raise ValueError('slot already built: %s' % name)
        self.slots[name] = widget
        self.stack.addWidget(widget)
        return widget

    def page(self, slot):
        """A form page: one readable column, centred once the window is wider than it. Returns its layout."""
        page = QWidget()
        outer = QHBoxLayout(page)
        outer.setContentsMargins(0, 0, 12, 0)
        outer.setSpacing(0)
        column = QWidget()
        column.setMaximumWidth(1080)
        v = QVBoxLayout(column)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(16)
        outer.addStretch(1)
        outer.addWidget(column, 1000)
        outer.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        self.add_slot(slot, scroll)
        return v

    def build_slots(self):
        """Every old page, in the order its parts depend on each other."""
        v = self.content_layout
        self.build_performance()
        self.build_home()
        self.mods()
        self.build_backups()
        self.servers = ServerPage(self)
        self.add_slot('servers', self.servers)
        self.crosshair = CrosshairPage(lambda: (self.path.text(), self.accounts.currentData()), self)
        self.add_slot('crosshair', self.crosshair)
        self.updates = UpdatePage(self)
        self.updates.updateAvailable.connect(self.show_update_dot)
        self.repositories = SourceList(self)
        self.build_settings()
        if self.updates.release and self.updates.release.version > self.updates.current:
            self.show_update_dot(True)
        self.mod_service = ModService(self.repositories.manager, lambda: self.path.text(), self)
        self.installed = InstalledPage(self.mod_service, self.mods_page)
        self.compatibility = CheckPage(self.mod_service, self.scan_inputs)
        self.mods_page.gameRequired.connect(self.focus_game)
        self.mods_page.inspectRequested.connect(lambda: self.navigate('mods.health'))
        self.downloads = ActivityPage(self.mod_service)
        for page, slot in ((self.installed, 'installed'), (self.compatibility, 'compatibility'), (self.downloads, 'downloads')):
            page.openRequested.connect(self.navigate)
            page.gameRequired.connect(self.focus_game)
            self.add_slot(slot, page)
        self.graph_page = GraphPage(self, self.mod_service)
        self.add_slot('graph', self.graph_page)
        self.store_service = StoreService(parent=self)
        self.store = BrowsePage(self.store_service, self.mod_service)
        self.store.auto_pictures = bool(self.saved_look.get('pictures'))
        self.sources_view = SourcesView(self.mod_service)
        self.browse = BrowseHost(self.store, self.sources_view, self.mod_service)
        self.browse.openRequested.connect(self.navigate)
        self.browse.gameRequired.connect(self.focus_game)
        self.add_slot('store', self.browse)
        self.stats_service = StatsService(parent=self)
        self.stats = StatsPage(self, self.stats_service, self.steam_account)
        self.add_slot('stats', self.stats.heroes_view)
        self.add_slot('stats_ranks', self.stats.ranks_view)
        self.add_slot('stats_me', self.stats.me_view)
        missing = [s for s in self.registry.slots() if s not in self.slots]
        if missing:
            raise RuntimeError('pages in the registry without a widget: %s' % ', '.join(missing))

    def build_home(self):
        """Home on the new components. The game link (path field, account list) lives on it; the window reads them as `path` and `accounts`."""
        self.home = HomePage()
        self.path, self.accounts, self.connection_note = self.home.path, self.home.accounts, self.home.note
        self.accounts.currentIndexChanged.connect(self.remember_account)
        self.path.editingFinished.connect(self.refresh_accounts)
        self.home.find_button.clicked.connect(self.detect_game)
        self.home.choose_button.clicked.connect(self.browse_game)
        self.home.install_button.clicked.connect(self.open_install_page)
        self.home.openRequested.connect(self.navigate)
        self.home.gameRequired.connect(self.focus_game)
        self.page('home').addWidget(self.home)

    def scan_inputs(self):
        """What the classic-pack scan on Check reads: the library, the game folder (or None) and the mods chosen on Installed."""
        return self.library, self.path.text().strip() or None, tuple(k for k, b in self.mod_checks.items() if b.isChecked())

    def search_sources(self, text):
        """Show the "My sources" side of Browse with a search typed in (the project map leads here from a mod)."""
        self.navigate('mods.browse')
        self.browse.show_view('sources')
        self.sources_view.query.setText(text)

    def check_stale(self):
        """The choice or the game files changed: the classic-pack scan on Check is out of date."""
        if hasattr(self, 'compatibility'):
            self.compatibility.invalidate()

    def show_update_dot(self, available):
        """An app update is available: a dot on Settings and on its Update tab."""
        self.update_available = bool(available)
        self.nav['settings'].set_dot(self.update_available)
        self.settings_view.set_update_dot(self.update_available)

    def show_tabs(self, page):
        self.tabs.set_tabs([(t.id, t.title) for t in page.tabs])
        self.tabs.setVisible(len(page.tabs) > 1 and not page.section_list)

    # --- navigation ------------------------------------------------------------------------------

    def navigate(self, address):
        """Show a page or a tab by name: 'home', 'mods', 'mods.health', 'settings.update'."""
        page, tab, slot = self.registry.resolve(address)
        address = page.id + ('.' + tab.id if tab else '')
        old_page = self.current_address.partition('.')[0]
        moving = slot != self.current_slot
        if moving and self.current_slot and not self.saved_look.get('less_motion'):
            order = list(self.slots)
            self.transition.capture(1 if order.index(slot) > order.index(self.current_slot) else -1)
        if page.id != old_page:
            self.show_tabs(page)
        if tab:
            self.tabs.set_current(tab.id)
        self.current_address, self.current_slot = address, slot
        self.stack.setCurrentWidget(self.slots[slot])
        self.page_title.setText(page.title)
        self.topbar.back_button.setVisible(page.id == 'map')           # the map is reached from Settings > Advanced; Back goes there
        for page_id, item in self.nav.items():
            item.setChecked(page_id == page.id)
        self.on_slot_shown(slot, moving)

    def on_slot_shown(self, slot, moving):
        """What a page needs when it appears."""
        if slot == 'perf_all':
            self.all_page.reload()
        if slot == 'recovery':
            self.refresh_backups()
        if slot == 'settings':
            self.settings_view.show_section(self.current_address.partition('.')[2] or 'general')
        if slot == 'home':
            self.update_game_status()
            self.refresh_home()

    def notify(self, message):
        """A short, passing note (a toast): something happened that no page shows by itself."""
        Toast(self.centralWidget(), message, icon='info')

    # --- window events ---------------------------------------------------------------------------

    def showEvent(self, event):
        super().showEvent(event)
        if not self.intro_played:
            self.intro_played = True
            Intro(self.centralWidget(), brand_logo(264), 'Deadlock Toolbox', 'VERSION ' + __version__)
            shell_theme.dark_title_bar(self, shell_theme.current().mode == 'dark')

    def closeEvent(self, event):
        if self.updates.installing:
            self.updates.detail.setText(tr('انتظر اكتمال التثبيت قبل إغلاق البرنامج.'))
            event.ignore()
            return
        if self.mods_page.applying:
            self.mods_page.status.setText(tr('أكمل حفظ الملفات أولًا؛ ينتهي التركيب بعد لحظات.'))
            event.ignore()
            return
        if self.mod_service.busy:
            self.mod_service.cancel()
            self.notify(tr('أكمل أو ألغِ عملية المودات الجارية أولًا؛ لن يُغلق البرنامج وسط تركيب.'))
            event.ignore()
            return
        if self.servers.busy:
            self.servers.say(tr('انتظر اكتمال عملية السيرفرات قبل إغلاق البرنامج.'), '', 'warning')
            event.ignore()
            return
        if hasattr(self, 'guard_timer'):
            self.guard_timer.stop()
        if hasattr(self, 'detect_timer'):
            self.detect_timer.stop()
        self.update_startup_timer.stop()
        self.updates.client.cancel()
        self.compatibility.cancel()
        self.mods_page.cancel()
        self.store_service.cancel()
        super().closeEvent(event)

    # --- look ------------------------------------------------------------------------------------

    def set_look(self, mode=None, accent=None, scale=None):
        """Switch theme ('system', 'dark', 'light'), accent or text size at once and remember it."""
        shell_theme.apply(QApplication.instance(), mode, accent, scale)
        chosen = shell_theme.choice()
        self.saved_look.update({'mode': chosen[0], 'accent': chosen[1], 'scale': chosen[2]})        # keeps the other remembered choices (less motion, pictures)
        shell_theme.dark_title_bar(self, shell_theme.current().mode == 'dark')
        self.save_workspace()


def start_look(app, saved):
    """The theme at start-up from the saved choice (workspace.json `look`); unknown values fall back to the defaults."""
    look = saved if isinstance(saved, dict) else {}
    try:
        return shell_theme.apply(app, look.get('mode', 'dark'), look.get('accent', 'blue'), int(look.get('scale', 100)))
    except (ValueError, TypeError):
        return shell_theme.apply(app, 'dark', 'blue', 100)


def saved_look():
    try:
        path = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / 'workspace.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        return data.get('look', {}) if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('DeadlockToolbox')
    app.setApplicationDisplayName('Deadlock Toolbox')
    app.setOrganizationName('exelight7')
    shell_theme.apply_direction(app, i18n.rtl())
    app.setStyle('Fusion')
    load_fonts()
    app.setPalette(dark_palette())
    start_look(app, saved_look())
    window = Window()
    for flag, address in FLAGS.items():
        if flag in sys.argv:
            window.navigate(address)
    if '--install' in sys.argv:
        window.navigate('settings.update')
        QTimer.singleShot(100, window.updates.install_current)
    window.show()
    window.update_startup_timer.start(3000)
    code = app.exec()
    # Background jobs (store sync, stats, pings) must finish before Python tears the objects down;
    # a job still running at interpreter exit can crash the process. They were cancelled in closeEvent.
    QThreadPool.globalInstance().waitForDone(5000)
    sys.exit(code)
