"""The classic pack: the four reference mods Toolbox has always supported, folded into Mods > Installed.

You add their files once (drop a bundle, choose files or a folder, or let Toolbox find them), tick the ones you want in the game,
review, and confirm. The work is the old, tested engine (`mods.py`, `mod_install.py`, `core.Studio`); this widget draws it with the
redesign components and keeps the names the rest of the window uses (`checks`, `labels`, `status`, `busy`, `applying`, `install()`,
`refresh()`...), because the Performance page reads `checks` when it builds its settings and Backups drives `install()`.
"""
import threading
from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool, Signal
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QPlainTextEdit, QVBoxLayout, QWidget

from ..core import Studio, game_root
from ..i18n import tr
from ..mod_install import commit_mods, prepare_mods
from ..ui_common import Job
from ..settings import MODS
from ..shell import theme
from ..shell.components import Badge, Banner, Button, Card, Dialog, KeyValue, List, ListRow, Menu, ProgressBar, Switch, breakable, mark, set_props, text_label


def descriptions():
    """What each of the four does, in plain words. A function, so the words follow the language chosen at start-up."""
    return {'daylock': tr('Daylight on the map. Try it in training to see how clear it is.'),
            'names': tr("Hides players' names. It conflicts with the old health bar."),
            'health': tr('The old health bar. Pick it or hide the names, not both.'),
            'sinner': tr('The bundled Sinner tweak. Check the result inside the game.')}


class ClassicReview(Dialog):
    """What will be in the game after applying, with every warning, before anything is written."""

    def __init__(self, prepared, parent=None):
        installing = bool(prepared.settings.mods)
        super().__init__(tr('Everything is ready. Review your choice.'), tr('Only the mods change. Resolution and graphics stay as they are, and the originals are saved automatically.'),
                         'review', tr('Confirm the install') if installing else tr('Confirm the removal'), tr('Back'), parent=parent)
        installed, removed = [], []
        for path, data in prepared.plan.items():
            if path.suffix != '.vpk':
                continue
            key = next((k for k, (filename, _, _) in MODS.items() if filename.split(' - ')[0] == path.name), None)
            (installed if key in prepared.settings.mods else removed).append(MODS[key][1] if key else path.name)
        facts = KeyValue()
        facts.add(tr('In the game after applying'), ' · '.join(MODS[k][1] for k in prepared.settings.mods) or tr('No mods chosen'))
        if installed:
            facts.add(tr('Install or update'), ', '.join(installed))
        if removed:
            facts.add(tr('Cancel the mod and restore the original'), ', '.join(removed))
        self.body.addWidget(facts)
        for finding in prepared.report.findings:
            if finding.severity == 'warning':
                self.body.addWidget(Banner(breakable(finding.title), breakable(finding.detail), 'warning'))
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setLayoutDirection(Qt.LeftToRight)
        self.details.setPlainText('\n'.join(str(p) + ('  -> remove' if b is None else '  -> %s bytes' % format(len(b), ',')) for p, b in prepared.plan.items()))
        self.details.setMinimumHeight(120)
        self.details.hide()
        more = Button(tr('File details'), 'ghost', 'sm', icon='info')
        more.setCheckable(True)
        more.toggled.connect(self.details.setVisible)
        self.body.addWidget(more, 0, Qt.AlignLeading)
        self.body.addWidget(self.details)


class ClassicPack(QWidget):
    gameRequired = Signal()                 # the user asked to link the game
    inspectRequested = Signal()             # the user asked for the details of the check

    def __init__(self, window):
        super().__init__(window)
        mark(self, 'ClassicPack')
        self.window = window
        self.stage = ''
        self._job = None
        self.sequence = 0
        self.cancel_event = None
        self.cards, self.checks, self.labels = {}, {}, {}
        self._can_install = False
        t = theme.current()
        self.setAcceptDrops(True)
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(t.px('space.3'))

        self.drop = Card(variant='flat')
        self.drop.setProperty('dashed', 'true')
        row = QVBoxLayout()
        row.setContentsMargins(t.px('space.4'), t.px('space.3'), t.px('space.4'), t.px('space.3'))
        row.setSpacing(t.px('space.2'))
        row.addWidget(text_label(tr('Drop the bundle here. Toolbox does the rest.'), 'RowTitle'))
        row.addWidget(text_label(tr('A ZIP, a VPK or a MODS folder. The mods are recognised even if the file was renamed.'), 'Muted'))
        buttons = QHBoxLayout()
        buttons.setSpacing(t.px('space.2'))
        self.add_button = Button(tr('Add the files'), 'primary', 'sm', icon='plus')
        self.add_button.clicked.connect(self.browse_files)
        buttons.addWidget(self.add_button)
        self.more_button = Button(tr('More ways to add'), 'secondary', 'sm')
        menu = Menu(self.more_button)
        menu.add(tr('Choose a folder'), self.browse_folder, 'folder')
        menu.add(tr('Find the files automatically'), self.discover, 'search')
        self.more_button.setMenu(menu)
        buttons.addWidget(self.more_button)
        buttons.addStretch(1)
        row.addLayout(buttons)
        self.drop.body.addLayout(row)
        box.addWidget(self.drop)
        self.import_note = text_label(tr('Add the files once. The mods stay saved for the next sessions.'), 'Muted')
        box.addWidget(self.import_note)

        self.list = List(variant='flat')
        card = Card(variant='flat')
        card.body.addWidget(self.list)
        box.addWidget(card)
        for key in MODS:
            switch = Switch()
            switch.setAccessibleName(tr('I want {0} in the game').format(MODS[key][1]))
            badge = Badge(tr('Add the files'), 'neutral')
            line = ListRow(MODS[key][1], descriptions()[key], control=badge, lead=switch)
            self.list.add(line)
            self.cards[key], self.checks[key], self.labels[key] = line, switch, badge
            switch.toggled.connect(lambda checked, k=key: self.card_toggled(k, checked))
        self.note = text_label(tr('The supported mods are the bundled reference files. Adding the files does not change the game.'), 'Muted')
        box.addWidget(self.note)

        self.status = text_label(tr('Choose what you want in the game, then press install.'), 'CardText')
        box.addWidget(self.status)
        self.progress = ProgressBar()
        self.progress.set_unknown()
        self.progress.hide()
        box.addWidget(self.progress)
        side = QHBoxLayout()                                      # the small buttons, then the one that matters on a row of its own: together they would not fit a narrow window
        side.setSpacing(t.px('space.2'))
        self.link_button = Button(tr('Link the game'), 'secondary', 'sm')
        self.link_button.clicked.connect(self.gameRequired.emit)
        side.addWidget(self.link_button)
        self.inspect_button = Button(tr('Details of the check'), 'ghost', 'sm', icon='shield')
        self.inspect_button.clicked.connect(self.inspectRequested.emit)
        side.addWidget(self.inspect_button)
        self.cancel_button = Button(tr('Cancel'), 'secondary', 'sm')
        self.cancel_button.clicked.connect(self.cancel)
        self.cancel_button.hide()
        side.addWidget(self.cancel_button)
        side.addStretch(1)
        box.addLayout(side)
        main = QHBoxLayout()
        main.addStretch(1)
        self.install_button = Button(tr('Check and install the choice'), 'primary')
        self.install_button.clicked.connect(self.install)
        main.addWidget(self.install_button)
        box.addLayout(main)

    # ---- dropping files -------------------------------------------------------------

    @staticmethod
    def paths(mime):
        """The local files of a drop; anything that is not a local file (an address) makes the whole drop refused."""
        return [Path(url.toLocalFile()) for url in mime.urls()] if mime.hasUrls() and all(url.isLocalFile() for url in mime.urls()) else []

    def dragEnterEvent(self, event):
        if self.isEnabled() and self.paths(event.mimeData()):
            event.acceptProposedAction()
            set_props(self.drop, dragging='true')
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        set_props(self.drop, dragging=None)
        event.accept()

    def dropEvent(self, event):
        set_props(self.drop, dragging=None)
        paths = self.paths(event.mimeData())
        if self.isEnabled() and paths:
            event.acceptProposedAction()
            self.import_paths(paths)
        else:
            event.ignore()

    # ---- state ----------------------------------------------------------------------

    @property
    def busy(self):
        return bool(self.stage)

    @property
    def applying(self):
        return self.stage == 'apply'

    def selected(self):
        return tuple(k for k, c in self.checks.items() if c.isChecked())

    def summary(self):
        """[(name, in the game now)] for the folded row on Installed."""
        try:
            on = self.window.library.installed(self.window.path.text().strip())
        except OSError:
            on = set()
        return [(MODS[key][1], key in on) for key in MODS]

    def card_toggled(self, key, checked):
        set_props(self.cards[key], selected='true' if checked else None)
        self.window.mod_selected(key, checked)

    def refresh(self):
        library = self.window.library
        available, installed = library.available(), library.installed(self.window.path.text().strip())
        try:
            managed = Studio(self.window.path.text()).state().get('files', {})
        except Exception:
            managed = {}
        for key, badge in self.labels.items():
            target = Path(self.window.path.text()) / 'game/citadel/fps_studio' / MODS[key][0].split(' - ')[0]
            if key in installed:
                words, variant = (tr('Installed'), 'success') if str(target.resolve()) in managed else (tr('Already there'), 'success')
            elif key in available:
                words, variant = tr('Ready'), 'info'
            else:
                words, variant = tr('Add the files'), 'neutral'
            badge.setText(words)
            badge.set_variant(variant)
        linked = (Path(self.window.path.text()) / 'game/citadel/gameinfo.gi').is_file()
        self.link_button.setVisible(not linked)
        count = len(self.selected())
        owned = any(str((Path(self.window.path.text()) / 'game/citadel/fps_studio' / name.split(' - ')[0]).resolve()) in managed for name, _, _ in MODS.values())
        self._can_install = bool(count or owned)
        if not self.busy:
            self.status.setText(tr('{0} mods chosen').format(count) + ' · ' + (tr('ready to check and install') if count else tr("Toolbox's installed mods are restored when you confirm.") if owned else tr('Add the files or choose a mod to start.')))
        self.install_button.setText(tr('Check and install the choice') if count else tr("Review removing Toolbox's mods") if owned else tr('Choose a mod to start'))
        self.install_button.setEnabled(not self.busy and self._can_install)

    # ---- adding files ----------------------------------------------------------------

    def browse_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, tr('Add the mod files'), '', 'Mod bundles (*.zip *.vpk*);;All files (*)')
        if paths:
            self.import_paths(paths)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, tr('Choose the mods folder'))
        if folder:
            self.import_paths([folder])

    def discover(self):
        paths = self.window.library.discover()
        if paths:
            self.import_paths(paths)
        else:
            self.status.setText(tr('No bundle was found. Drop a ZIP here, or choose the MODS folder from More ways to add.'))

    def import_paths(self, paths):
        if self.busy:
            return
        library, paths = self.window.library, tuple(paths)
        self.cancel_event = threading.Event()
        event = self.cancel_event
        self.start('import', lambda emit: library.import_report(paths, event, emit), self.imported, True)

    def imported(self, report):
        self.idle()
        matched = report.matched
        for key in matched - {'names', 'health'}:
            self.checks[key].setChecked(True)
        pair = matched & {'names', 'health'}
        if len(pair) == 1:
            self.checks[next(iter(pair))].setChecked(True)
        note = tr('Recognised {0} mods and saved them. Look at the rows, then install.').format(len(matched))
        if len(pair) == 2 and not any(self.checks[k].isChecked() for k in pair):
            note += ' ' + tr('Choose hiding the names or the old health bar; they do not work together.')
        if report.ignored:
            note += ' ' + tr('Ignored {0} files that are not supported.').format(len(report.ignored))
        self.import_note.setText(note)
        self.window.refresh_mod_library()
        self.window.check_stale()
        self.status.setText(note)

    # ---- installing -----------------------------------------------------------------

    def install(self):
        if self.busy:
            return
        root, selected, library = self.window.path.text().strip(), self.selected(), self.window.library
        self.cancel_event = threading.Event()
        event = self.cancel_event
        self.start('prepare', lambda: prepare_mods(root, library, selected, event), self.prepared)

    def prepared(self, prepared):
        if self.cancel_event and self.cancel_event.is_set():
            self.idle()
            self.status.setText(tr('The check was cancelled; the game files did not change.'))
            return
        try:
            if game_root(self.window.path.text()) != prepared.root or self.selected() != prepared.settings.mods:
                raise ValueError(tr('The game folder or the choice changed during the check. Try again.'))
        except Exception as error:
            self.idle()
            self.status.setText(str(error))
            return
        self.stage = 'review'
        self.busy_ui()
        if prepared.plan:
            dialog = ClassicReview(prepared, self)
            accepted = dialog.exec() == Dialog.Accepted
            dialog.deleteLater()
            if not accepted:
                self.idle()
                self.status.setText(tr('The install was cancelled. The game files did not change.'))
                return
        library = self.window.library
        self.idle()
        self.start('apply', lambda: commit_mods(prepared, library), self.applied)

    def applied(self, message):
        self.idle()
        self.window.refresh_mod_library()
        self.window.check_stale()
        self.status.setText(tr('Done') + ' · ' + message + ' ' + tr('Resolution and graphics are kept.'))
        self.import_note.setText(tr('Your choice is saved. You can change the mods any time and apply again.'))

    def start(self, stage, fn, success, progress=False):
        self.sequence += 1
        generation = self.sequence
        self.stage = stage
        self.busy_ui()
        self.status.setText({'import': tr('Reading the bundle and recognising the mods…'), 'prepare': tr('Checking the choice and preparing the install…'),
                             'apply': tr('Installing the mods and saving the originals…')}[stage])
        job = Job(fn, progress)
        self._job = job
        job.signals.result.connect(lambda value: self.got(generation, success, value))
        job.signals.failure.connect(lambda message: self.failed(generation, message))
        job.signals.done.connect(lambda: self.finished(generation))
        job.signals.progress.connect(lambda value: self.import_progress(generation, value))
        QThreadPool.globalInstance().start(job)

    def got(self, generation, success, value):
        if generation == self.sequence:
            success(value)

    def failed(self, generation, message):
        if generation != self.sequence:
            return
        self.idle()
        self.status.setText(breakable(message))
        self.import_note.setText(tr('Read the message or open the details of the check. You can import again from the original bundle.'))

    def finished(self, generation):
        if generation == self.sequence and self.stage != 'review':
            self.idle()

    def idle(self):
        self.stage = ''
        self._job = None
        self.busy_ui()

    def busy_ui(self):
        busy = self.busy
        for widget in (self.drop, self.add_button, self.more_button, self.link_button):
            widget.setEnabled(not busy)
        self.install_button.setEnabled(not busy and self._can_install)
        for check in self.checks.values():
            check.setEnabled(not busy)
        self.inspect_button.setEnabled(not self.applying)
        self.cancel_button.setVisible(self.stage in ('import', 'prepare'))
        self.progress.setVisible(busy and self.stage != 'review')
        self.window.path.setEnabled(not self.applying)
        self.window.accounts.setEnabled(not self.applying)

    def cancel(self):
        if self.stage in ('import', 'prepare') and self.cancel_event:
            self.cancel_event.set()
            self.status.setText(tr('Stopping safely…'))

    def import_progress(self, generation, value):
        if generation != self.sequence:
            return
        kind, name = value
        if kind == 'commit':
            self.cancel_button.hide()
            self.status.setText(tr('Saving the mods to the library…'))
        elif name:
            self.status.setText(tr('Reading: ') + name)


class ClassicPackMixin:
    def mods(self):
        self.mods_page=ClassicPack(self);self.mod_checks=self.mods_page.checks;self.mod_labels=self.mods_page.labels;self.mod_status=self.mods_page.status
    def refresh_mod_library(self):self.mods_page.refresh()
    def mod_selected(self,key,checked):
        other={'names':'health','health':'names'}.get(key)
        if checked and other:self.mod_checks[other].setChecked(False)
        self.check_stale()
        self.mods_page.refresh()
    def import_mod_sources(self,paths):self.mods_page.import_paths(paths)
    def discover_mods(self):self.mods_page.discover()
    def import_mod_files(self):self.mods_page.browse_files()
    def install_mods(self):self.mods_page.install()
    def browse_mods(self):self.mods_page.browse_folder()
