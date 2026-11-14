"""Settings › Extra mod sources: add, switch on or off, refresh, remove, load and save the list of places mods can come from, besides the Mod Store.

All logic is `deadlock_fps.repos` (`RepositoryManager`); this page draws it and moves the slow work (network) off the interface thread.
Browsing what a source offers is on Mods › Browse (My sources). Nothing is installed from here.
"""
from pathlib import Path

from PySide6.QtCore import Qt, QStandardPaths, QThreadPool, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QFrame, QHBoxLayout, QScrollArea, QToolButton, QVBoxLayout, QWidget

from ..i18n import tr
from ..repos import RepoError, RepositoryManager, RepositoryStore, Trust, UrllibTransport
from ..repos.spec import MAX_INDEX_BYTES
from ..shell import theme
from ..shell.components import (Badge, Banner, Button, Card, EmptyState, IconButton, List, ListRow, Menu, Switch, TextField, breakable, confirm, mark, text_label)
from ..ui_common import Job, ltr
from .browse import plural

TRUST_BADGE = {Trust.OFFICIAL: ('Official', 'info'), Trust.VERIFIED: ('Verified', 'success'), Trust.COMMUNITY: ('Community', 'neutral'), Trust.UNVERIFIED: ('Not reviewed', 'warning')}


def trust_badge(view):
    text, variant = TRUST_BADGE[view.trust]
    return tr(text), variant


def status_badge(view):
    """(text, variant) for the state of a source, honest about every state."""
    state = view.state
    if not view.source.enabled:
        return tr('Off'), 'neutral'
    if state.status == 'new':
        return tr('Not loaded yet'), 'neutral'
    if state.status == 'error':
        return (tr("Didn't answer · saved list shown") if state.mod_count else tr("Didn't answer")), 'warning'
    return plural(state.mod_count, tr('{0} mod'), tr('{0} mods')), 'success'


class SourceList(QWidget):
    def __init__(self, window=None, manager=None):
        super().__init__(window)
        mark(self, 'SourceList')
        self.window = window
        if manager is None:
            folder = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / 'repositories'
            manager = RepositoryManager(RepositoryStore(folder), UrllibTransport())
        self.manager = manager
        self.jobs = 0
        self._keep = []                     # running jobs; Qt does not own a QRunnable's Python wrapper
        t = theme.current()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)
        inner = QWidget()
        inner.setMaximumWidth(760)
        page = QVBoxLayout(inner)
        page.setContentsMargins(0, 0, 12, 0)
        page.setSpacing(t.px('space.4'))
        scroll.setWidget(inner)

        page.addWidget(text_label(tr('A source is a list of mods kept somewhere else on the internet. Toolbox only reads the list; nothing is installed from this page, and every source starts as not reviewed.'), 'CardText'))
        card = Card()
        row = QHBoxLayout()
        row.setSpacing(t.px('space.3'))
        self.address_field = TextField(placeholder=tr('Paste a source address (https://…)'))
        self.address = self.address_field.edit
        self.address.returnPressed.connect(self.add)
        row.addWidget(self.address_field, 1)
        self.add_button = Button(tr('Add'), 'primary', icon='plus')
        self.add_button.clicked.connect(self.add)
        row.addWidget(self.add_button, 0, Qt.AlignTop)
        card.body.addLayout(row)
        page.addWidget(card)
        self.notice = None
        self.notice_box = QVBoxLayout()
        page.addLayout(self.notice_box)
        self.list_card = Card(variant='flat')
        self.list = List(variant='flat')
        self.list_card.body.addWidget(self.list)
        page.addWidget(self.list_card)
        self.empty = EmptyState('globe', tr('No extra sources'), tr('Add an address above, or load a list you saved before.'))
        page.addWidget(self.empty)
        buttons = QHBoxLayout()
        self.refresh_all_button = Button(tr('Refresh all'), 'secondary', 'sm', icon='refresh')
        self.refresh_all_button.clicked.connect(self.refresh_all)
        self.import_button = Button(tr('Load a list'), 'secondary', 'sm', icon='folder')
        self.import_button.clicked.connect(self.import_file)
        self.export_button = Button(tr('Save my list'), 'secondary', 'sm', icon='download')
        self.export_button.clicked.connect(self.export_list)
        for button in (self.refresh_all_button, self.import_button, self.export_button):
            buttons.addWidget(button)
        buttons.addStretch(1)
        page.addLayout(buttons)
        page.addStretch(1)
        self.reload()

    # ---- drawing -------------------------------------------------------------------------

    def reload(self):
        """Redraw everything from the manager's saved state."""
        views = self.manager.list()
        self.list.clear()
        self.switches = {}
        for view in views:
            self.list.add(self.row(view))
        self.list_card.setVisible(bool(views))
        self.empty.setVisible(not views)
        self.sync_buttons()

    def row(self, view):
        source = view.source
        switch = Switch()
        switch.setAccessibleName(tr('Include this source'))
        switch.setChecked(source.enabled)
        switch.toggled.connect(lambda on, i=source.id: self.set_enabled(i, on))
        self.switches[source.id] = switch
        holder = QWidget()
        lay = QHBoxLayout(holder)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(theme.current().px('space.2'))
        for text, variant in (trust_badge(view), status_badge(view)):
            lay.addWidget(Badge(text, variant))
        more = IconButton('more', tr('More'), 'ghost', 'sm')
        menu = Menu(more)
        menu.add(tr('Refresh this source'), lambda _=False, i=source.id: self.refresh_one(i), 'refresh')
        opener = menu.add(tr('Open the address'), lambda _=False, i=source.id: self.open_source(i), 'ext')
        opener.setEnabled(bool(source.url))
        menu.add(tr('Remove'), lambda _=False, i=source.id: self.remove(i), 'trash', danger=True)
        more.setMenu(menu)
        more.setPopupMode(QToolButton.InstantPopup)
        lay.addWidget(more)
        line = (source.url or tr('Imported from a file'))
        if view.state.status == 'error':
            line += '\n' + view.state.error_message
        row = ListRow(ltr(view.name), '', control=holder, lead=switch)
        row.line.setText(breakable(line))
        row.line.show()
        row.source_id = source.id
        row.more = more
        row.menu = menu
        return row

    def sync_buttons(self):
        busy = self.jobs > 0
        for button in (self.add_button, self.import_button, self.refresh_all_button):
            button.setEnabled(not busy)
        self.export_button.setEnabled(bool(self.list.rows))
        self.refresh_all_button.setEnabled(not busy and bool(self.list.rows))

    def say(self, message, variant='info', title=''):
        """One notice at a time, above the list, in the colour that matches what happened."""
        while self.notice_box.count():
            old = self.notice_box.takeAt(0).widget()
            if old is not None:
                old.hide()
                old.setParent(None)
                old.deleteLater()
        self.notice = Banner(title or message, message if title else '', variant)
        self.notice_box.addWidget(self.notice)

    # ---- slow work -----------------------------------------------------------------------

    def run(self, work, done):
        """Run slow work off the interface thread; `done(result)` runs on it."""
        job = Job(work)
        self.jobs += 1
        self._keep.append(job)

        def finish():
            self.jobs -= 1
            if job in self._keep:
                self._keep.remove(job)
            self.sync_buttons()
        job.signals.result.connect(done)
        job.signals.failure.connect(lambda message: self.say(tr('Something went wrong: ') + message, 'danger'))
        job.signals.done.connect(finish)
        self.sync_buttons()
        QThreadPool.globalInstance().start(job)

    def explain(self, error):
        messages = {
            'bad-url': tr('That address cannot be used. Sources must be public HTTPS addresses.'),
            'duplicate': tr('That source is already in your list.'),
            'invalid-index': tr('That file is not a valid source index.'),
            'unsupported-schema': tr('That source uses a newer specification than this version of Toolbox understands.'),
            'too-large': tr('That file is larger than the limit for source indexes.'),
            'bad-provider': tr('That source type is not available.'),
        }
        return messages.get(error.code, tr('Could not complete the request.')) + '\n' + error.message

    # ---- actions -------------------------------------------------------------------------

    def add(self):
        address = self.address.text().strip()
        if not address:
            self.address_field.set_error(tr('Paste a source address first.'))
            return
        try:
            view = self.manager.add(address)
        except RepoError as error:
            self.address_field.set_error(self.explain(error))
            return
        self.address_field.set_error('')
        self.address.clear()
        self.reload()
        self.say(tr('Added. Loading its list…'))
        self.run(lambda: self.manager.refresh(view.source.id), lambda result: self.loaded(result, True))

    def loaded(self, view, announce=False):
        self.reload()
        if announce:
            label = status_badge(view)[0]
            self.say('%s: %s' % (view.name, label) + ('' if view.state.mod_count else '. ' + (view.state.error_message or view.state.reason)),
                     'warning' if view.state.status == 'error' else 'success')

    def refresh_one(self, repository_id):
        self.say(tr('Refreshing…'))
        self.run(lambda: self.manager.refresh(repository_id), lambda view: self.loaded(view, True))

    def refresh_all(self):
        if not self.list.rows:
            self.say(tr('Add a source first.'), 'warning')
            return
        self.say(tr('Refreshing every enabled source…'))

        def done(views):
            self.reload()
            failed = sum(1 for v in views if v.state.status == 'error')
            self.say(tr('Refreshed {0} sources; {1} could not be reached.').format(len(views), failed), 'warning' if failed else 'success')
        self.run(self.manager.refresh_all, done)

    def set_enabled(self, repository_id, on):
        self.manager.set_enabled(repository_id, on)
        self.reload()

    def remove(self, repository_id):
        view = self.manager.get(repository_id)
        if confirm(self, tr('Remove this source?'), tr('Remove {0} from your list? Its saved list is deleted. Mods you already installed are not touched.').format(view.name), tr('Remove'), danger=True):
            self.manager.remove(repository_id)
            self.reload()
            self.say(tr('Removed {0}.').format(view.name))

    def open_source(self, repository_id):
        url = self.manager.get(repository_id).source.url
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def import_file(self):
        name, _ = QFileDialog.getOpenFileName(self, tr('Load a list'), '', tr('Source files (*.json)'))
        if not name:
            return
        try:
            path = Path(name)
            if path.stat().st_size > MAX_INDEX_BYTES:
                raise RepoError('too-large', 'file is larger than the index limit')
            data = path.read_bytes()
            try:
                result = self.manager.import_config(data)
            except RepoError as error:
                if error.code != 'duplicate' or 'local repository' not in error.message:
                    raise
                if not confirm(self, tr('Replace this source?'), tr('A source with this id was imported before. Replace it with this file?'), tr('Replace')):
                    return
                result = self.manager.import_config(data, replace_existing=True)
        except (RepoError, OSError) as error:
            self.say(self.explain(error) if isinstance(error, RepoError) else tr('Could not read that file: ') + str(error), 'danger')
            return
        self.reload()
        skipped = len(result.skipped)
        self.say(tr('Imported {0} sources.').format(len(result.added)) + (tr(' {0} were skipped (already added or invalid).').format(skipped) if skipped else '')
                 + (tr(' Press Refresh all to load them.') if result.kind == 'list' and result.added else ''), 'success')

    def export_list(self):
        name, _ = QFileDialog.getSaveFileName(self, tr('Save my list'), 'deadlock-repositories.json', tr('Source files (*.json)'))
        if not name:
            return
        try:
            Path(name).write_bytes(self.manager.export_config())
        except OSError as error:
            self.say(tr('Could not save the file: ') + str(error), 'danger')
            return
        self.say(tr('Saved your source list. Imported files are not included because they have no address.'), 'success')
