"""Settings: a list of sections at the leading side, the section's content beside it (at most 760 wide).

Sections: General (language, look, text size, less motion), Game (where Deadlock is), Protection (put the settings back after the
game closes), App update, Extra mod sources, Advanced (mod pictures, project map, app data folder) and About.
The page only draws; the window owns the actions (`set_look`, `browse_game`, `repair_settings`, ...) and is told through signals
and the small callbacks it passes in. The App update and Extra mod sources sections are their own widgets (`update.py`, `source_list.py`).
"""
import sys
from pathlib import Path

from PySide6.QtCore import QProcess, QStandardPaths, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QScrollArea, QStackedWidget, QVBoxLayout, QWidget

from .. import __version__, i18n
from ..i18n import tr
from ..shell import theme
from ..shell.components import Banner, Button, Card, KeyValue, List, ListRow, NavItem, SegmentedControl, Select, Switch, mark, text_label
from .browse import mono

GITHUB = 'https://github.com/exelight7/deadlock-fps-'
SECTIONS = ('general', 'game', 'protection', 'update', 'sources', 'advanced', 'about')
ICONS = {'general': 'settings', 'game': 'folder', 'protection': 'shield', 'update': 'download', 'sources': 'globe', 'advanced': 'tool', 'about': 'info'}
TEXT_SIZES = (90, 100, 115, 130)


def section_titles():
    return {'general': tr('General'), 'game': tr('Game'), 'protection': tr('Protection'), 'update': tr('App update'),
            'sources': tr('Extra mod sources'), 'advanced': tr('Advanced'), 'about': tr('About')}


def scrolled(widget):
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setWidget(widget)
    return scroll


def column(spacing=None):
    """A widget with a vertical layout, at most 760 wide and pinned to the leading side."""
    widget = QWidget()
    widget.setMaximumWidth(760)
    box = QVBoxLayout(widget)
    box.setContentsMargins(0, 0, 12, 0)
    box.setSpacing(spacing if spacing is not None else theme.current().px('space.4'))
    return widget, box


class SettingsPage(QWidget):
    """The section list and the stack. `update_widget` and `sources_widget` are the two sections that are pages of their own."""
    lookChanged = Signal(str, str, int)        # mode, accent (unchanged: ''), text size (0 = unchanged)
    languageChanged = Signal()
    restartRequested = Signal()
    repairRequested = Signal()
    chooseGame = Signal()
    findGame = Signal()
    mapRequested = Signal()
    dataFolderRequested = Signal()
    preferenceChanged = Signal(str, bool)

    def __init__(self, preferences_file, update_widget, sources_widget, parent=None):
        super().__init__(parent)
        mark(self, 'SettingsPage')
        t = theme.current()
        self.preferences_file = preferences_file
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(t.px('space.5'))
        side = QVBoxLayout()
        side.setSpacing(2)
        holder = QWidget()
        holder.setFixedWidth(180)
        holder.setLayout(side)
        side.setContentsMargins(0, 0, 0, 0)
        self.nav = {}
        titles = section_titles()
        for key in SECTIONS:
            item = NavItem(key, titles[key], ICONS[key])
            item.clicked.connect(lambda _=False, k=key: self.show_section(k))
            side.addWidget(item)
            self.nav[key] = item
        side.addStretch(1)
        row.addWidget(holder)
        self.stack = QStackedWidget()
        row.addWidget(self.stack, 1)
        self.sections = {}
        builders = {'general': self._general, 'game': self._game, 'protection': self._protection, 'advanced': self._advanced, 'about': self._about}
        for key in SECTIONS:
            if key == 'update':
                widget = update_widget
            elif key == 'sources':
                widget = sources_widget
            else:
                inner, box = column()
                builders[key](box)
                box.addStretch(1)
                widget = scrolled(inner)
            self.sections[key] = widget
            self.stack.addWidget(widget)
        self.show_section('general')

    def show_section(self, key):
        if key not in self.sections:
            raise KeyError(key)
        self.current = key
        self.stack.setCurrentWidget(self.sections[key])
        for name, item in self.nav.items():
            item.setChecked(name == key)

    def set_update_dot(self, on):
        self.nav['update'].set_dot(on)

    # ---- General -------------------------------------------------------------------------

    def _general(self, box):
        card = Card()
        card.setProperty('variant', 'flat')
        card.body.setContentsMargins(0, 0, 0, 0)
        card.body.setSpacing(0)
        rows = List(variant='flat')
        self.language = Select()
        self.language.setMinimumWidth(160)
        for code, name in i18n.LANGUAGES.items():
            self.language.addItem(name, code)
        self.language.setCurrentIndex(max(0, self.language.findData(i18n.preferred(self.preferences_file))))
        self.language.currentIndexChanged.connect(lambda _i: self.languageChanged.emit())
        rows.add(ListRow(tr('Language'), tr('The language of the app. It changes after the app restarts.'), control=self.language))
        self.look = SegmentedControl([('system', tr('System')), ('dark', tr('Dark')), ('light', tr('Light'))])
        self.look.changed.connect(lambda mode: self.lookChanged.emit(mode, '', 0))
        rows.add(ListRow(tr('Look'), tr('Dark and light both keep the colours readable.'), control=self.look))
        self.size = SegmentedControl([(str(n), '%d %%' % n) for n in TEXT_SIZES])
        self.size.set_value('100')
        self.size.changed.connect(lambda n: self.lookChanged.emit('', '', int(n)))
        rows.add(ListRow(tr('Text size'), tr('Bigger text makes every page taller, never cut off.'), control=self.size))
        self.less_motion = Switch()
        self.less_motion.setAccessibleName(tr('Less motion'))
        self.less_motion.toggled.connect(lambda on: self.preferenceChanged.emit('less_motion', on))
        rows.add(ListRow(tr('Less motion'), tr('Pages change without sliding.'), control=self.less_motion))
        card.body.addWidget(rows)
        box.addWidget(card)
        self.restart_banner = Banner(tr('Restart to change the language'), tr('The new language is saved. The app uses it the next time it starts.'), 'info')
        self.restart_button = Button(tr('Restart now'), 'primary', 'sm')
        self.restart_button.clicked.connect(self.restartRequested.emit)
        self.restart_banner.add_action(self.restart_button)
        self.restart_banner.hide()
        box.addWidget(self.restart_banner)

    def show_restart(self, needed):
        self.restart_banner.setVisible(needed)

    def set_look_choice(self, mode, scale):
        if mode in self.look.buttons:
            self.look.set_value(mode)
        if str(scale) in self.size.buttons:
            self.size.set_value(str(scale))

    # ---- Game ----------------------------------------------------------------------------

    def _game(self, box):
        self.game_banner = Banner(tr('The game is not linked'), tr('Choose the Deadlock folder, or let Toolbox find it.'), 'warning')
        box.addWidget(self.game_banner)
        card = Card(tr('Where Deadlock is installed'))
        self.facts = KeyValue()
        self.game_path = mono(text_label('—', 'KeyValueValue'))
        self.game_version = text_label('—', 'KeyValueValue')
        self.game_state = text_label('—', 'KeyValueValue')
        self.game_account = text_label('—', 'KeyValueValue')
        for key, widget in ((tr('Folder'), self.game_path), (tr('Game version'), self.game_version), (tr('Game state'), self.game_state), (tr('Steam account folder'), self.game_account)):
            self.facts.add(key, widget)
        card.body.addWidget(self.facts)
        buttons = QHBoxLayout()
        self.choose_button = Button(tr('Choose the folder'), 'secondary', icon='folder')
        self.choose_button.clicked.connect(self.chooseGame.emit)
        self.find_button = Button(tr('Find it automatically'), 'secondary', icon='search')
        self.find_button.clicked.connect(self.findGame.emit)
        buttons.addWidget(self.choose_button)
        buttons.addWidget(self.find_button)
        buttons.addStretch(1)
        card.body.addLayout(buttons)
        box.addWidget(card)

    def set_game(self, linked, path='', version='', state='', account=''):
        self.game_banner.setVisible(not linked)
        self.game_path.setText(path or '—')
        self.game_version.setText(version or '—')
        self.game_state.setText(state or '—')
        self.game_account.setText(account or '—')

    # ---- Protection ----------------------------------------------------------------------

    def _protection(self, box):
        card = Card()
        card.body.setContentsMargins(0, 0, 0, 0)
        card.body.setSpacing(0)
        rows = List(variant='flat')
        self.guard = Switch()
        self.guard.setChecked(True)
        self.guard.setAccessibleName(tr('Put my settings back after the game closes'))
        rows.add(ListRow(tr('Put my settings back after the game closes'),
                         tr('Steam or a game update can undo them. Toolbox has to stay open, and it never writes while the game is running.'), control=self.guard))
        self.repair_button = Button(tr('Check and repair'), 'secondary', 'sm', icon='refresh')
        self.repair_button.clicked.connect(self.repairRequested.emit)
        self.guard_status = text_label(tr('الحماية جاهزة • لا يكتب البرنامج ملفات أثناء تشغيل اللعبة.'), 'Muted')
        row = ListRow(tr('Check and repair'), '', control=self.repair_button)
        rows.add(row)
        card.body.addWidget(rows)
        box.addWidget(card)
        box.addWidget(self.guard_status)

    # ---- Advanced ------------------------------------------------------------------------

    def _advanced(self, box):
        card = Card()
        card.body.setContentsMargins(0, 0, 0, 0)
        card.body.setSpacing(0)
        rows = List(variant='flat')
        self.pictures = Switch()
        self.pictures.setAccessibleName(tr('Show mod pictures while browsing'))
        self.pictures.toggled.connect(lambda on: self.preferenceChanged.emit('pictures', on))
        rows.add(ListRow(tr('Show mod pictures while browsing'), tr('Off by default. Turning it on downloads each picture from GameBanana when you open a mod.'), control=self.pictures))
        self.map_button = Button(tr('Open the project map'), 'secondary', 'sm', icon='map')
        self.map_button.clicked.connect(self.mapRequested.emit)
        rows.add(ListRow(tr('Project map'), tr('A picture of how the mods, authors and sources connect.'), control=self.map_button))
        self.data_button = Button(tr('Open the folder'), 'secondary', 'sm', icon='folder')
        self.data_button.clicked.connect(self.dataFolderRequested.emit)
        rows.add(ListRow(tr('App data folder'), tr('Where Toolbox keeps its lists, backups and downloads.'), control=self.data_button))
        card.body.addWidget(rows)
        box.addWidget(card)

    # ---- About ---------------------------------------------------------------------------

    def _about(self, box):
        card = Card('Deadlock Toolbox', tr('Version {0}').format(__version__))
        card.body.addWidget(text_label(tr('Free, open source and made by the community. Not affiliated with Valve.'), 'CardText'))
        buttons = QHBoxLayout()
        self.github_button = Button('GitHub', 'secondary', icon='ext')
        self.github_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GITHUB)))
        self.licence_button = Button(tr('Licences'), 'secondary', icon='info')
        self.licence_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GITHUB + '/blob/main/THIRD_PARTY.md')))
        buttons.addWidget(self.github_button)
        buttons.addWidget(self.licence_button)
        buttons.addStretch(1)
        card.body.addLayout(buttons)
        box.addWidget(card)


class SettingsMixin:
    """What the window does with the Settings page (`self.settings_view`): build it, and the actions behind its controls."""

    def build_settings(self):
        view = self.settings_view = SettingsPage(self.preferences_file, self.updates, self.repositories)
        self.add_slot('settings', view)
        self.language, self.restart_button, self.guard, self.guard_status = view.language, view.restart_button, view.guard, view.guard_status
        view.lookChanged.connect(lambda mode, accent, size: self.set_look(mode or None, accent or None, size or None))
        view.languageChanged.connect(self.language_changed)
        view.restartRequested.connect(self.restart)
        view.repairRequested.connect(self.repair_settings)
        view.chooseGame.connect(self.browse_game)
        view.findGame.connect(self.detect_game)
        view.mapRequested.connect(lambda: self.navigate('map'))
        view.dataFolderRequested.connect(self.open_data_folder)
        view.preferenceChanged.connect(self.set_preference)
        view.set_look_choice(self.saved_look.get('mode', 'dark'), self.saved_look.get('scale', 100))
        for name in ('less_motion', 'pictures'):
            switch = getattr(view, name)
            switch.blockSignals(True)
            switch.setChecked(bool(self.saved_look.get(name)))
            switch.blockSignals(False)

    def set_preference(self, name, on):
        """A yes/no choice that is kept in workspace.json with the look: `less_motion` and `pictures`."""
        self.saved_look[name] = bool(on)
        if name == 'pictures' and hasattr(self, 'store'):
            self.store.auto_pictures = bool(on)
        self.save_workspace()

    def open_data_folder(self):
        folder = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def language_changed(self, *_):
        self.save_workspace()
        self.settings_view.show_restart(self.language.currentData() != i18n.LANGUAGE)

    def restart(self):
        command = [sys.executable] if getattr(sys, 'frozen', False) else [sys.executable, str(Path(sys.argv[0]).resolve())]
        if QProcess.startDetached(command[0], command[1:] + [a for a in sys.argv[1:] if a != '--install'])[0]:
            self.close()

    def repair_settings(self):
        if self.mod_task_busy():
            return
        try:
            self.guard_status.setText(self.studio().repair(self.library.cache))
            self.guard_signature = None
            self.guard_retries = 0
            self.refresh_mod_library()
        except Exception as error:
            self.guard_status.setText(str(error))

    def guard_tick(self):
        if self.mods_page.busy:
            return
        if QApplication.activeModalWidget() or not self.guard.isChecked() or not self.path.text():
            return
        try:
            from ..core import digest, ensure_closed
            ensure_closed()
            studio = self.studio()
            changed = studio.drift()
            if not changed:
                self.guard_signature = None
                self.guard_retries = 0
                self.guard_status.setText(tr('قيم التعديلات محفوظة • اختلاف تنسيق الأرقام لا يُعتبر رجوعًا.'))
                return
            state = studio.state()
            signature = tuple((name, digest(Path(name).read_bytes()) if Path(name).exists() else None) for name in state['files'])
            if signature != self.guard_signature:
                self.guard_signature = signature
                self.guard_retries = 0
                self.guard_status.setText(tr('اكتشفت رجوعًا في: ') + ', '.join(changed) + tr(' • أنتظر استقرار الملفات.'))
                return
            if self.guard_retries >= 1:
                return
            if self.guard_attempts.get(signature, 0) >= 2:
                self.guard_status.setText(tr('تتكرر إعادة ضبط نفس القيم؛ أوقفت الإصلاح التلقائي. استخدم الإصلاح اليدوي بعد مراجعة اللعبة.'))
                return
            self.guard_attempts[signature] = self.guard_attempts.get(signature, 0) + 1
            self.guard_retries += 1
            self.guard_status.setText(studio.repair(self.library.cache))
            self.guard_signature = None
        except Exception as error:
            self.guard_status.setText(str(error))
