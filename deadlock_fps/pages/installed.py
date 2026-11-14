"""Mods > Installed: what Toolbox installed, which of it can be updated, and the few things you can do to each mod.

Built from the redesign components to the spec in vault/Design/New Design/05 Screens.md. Disabling is offered because it
is real here: a disabled mod's files are moved out of `game/citadel/addons`, the only place the game loads them from.
Nothing on the page pretends to do more than the engine does. The page only draws; `ModService` and the installer
(`installer/`) do the work and are unchanged.
"""
from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFrame, QHBoxLayout, QHeaderView, QLabel, QScrollArea, QVBoxLayout, QWidget

from ..hub_ui import failure_text
from ..i18n import tr
from ..installer import InstallError
from ..installer.updates import STORE_PREFIX
from ..repos.model import GameFit
from ..shell import theme
from ..shell.components import (Badge, Banner, Button, Card, Checkbox, DataTable, Dialog, EmptyState, IconButton, KeyValue, List, ListRow, Menu, Switch, Toast,
                                breakable, confirm, mark, set_props, text_label)
from ..ui_common import ltr, iso_text, size_text
from .browse import InstallReview, mono, plural

MAX_UNMANAGED_SHOWN = 30
ACTION_WORDS = {'install': lambda: tr('Installed'), 'update': lambda: tr('Updated'), 'uninstall': lambda: tr('Removed'), 'disable': lambda: tr('Disabled'),
                'enable': lambda: tr('Enabled'), 'restore': lambda: tr('Restored earlier version')}


def action_word(action):
    return ACTION_WORDS.get(action, lambda: action)()


def status_badge(mod, status):
    """(words, Badge variant) for the state of one installed mod."""
    if not mod.enabled:
        return tr('Off'), 'neutral'
    if status is None or mod.repository_id.startswith(STORE_PREFIX):         # a store mod has no source to ask; its note (the tooltip) says updates are not checked yet
        return tr('Installed'), 'success'
    if status.state == 'update':
        if status.fit is GameFit.INCOMPATIBLE:
            return tr('Update, not for this game version'), 'warning'
        return tr('Update'), 'info'
    if status.state == 'unavailable':
        return tr('Source unreachable'), 'warning'
    if status.state == 'ahead':
        return tr('Newer than the source'), 'neutral'
    return tr('Up to date'), 'success'


class FilesDialog(Dialog):
    """The files of one installed mod and whether each is still where and what it was."""

    def __init__(self, mod, addons, disabled_dir, parent=None):
        super().__init__(tr('Files of {0}').format(mod.name), variant='review', cancel=tr('Close'), parent=parent)
        base = addons if mod.enabled else disabled_dir
        self.table = DataTable([tr('File'), tr('Size'), tr('SHA-256'), tr('Present')], numeric=(1,))
        self.table.setMinimumHeight(44 * min(len(mod.files), 6) + 40)
        for f in mod.files:
            path = base / f.name
            present = path.is_file() and path.stat().st_size == f.size
            self.table.add_row([f.name, ltr(size_text(f.size)), f.sha256, tr('yes') if present else tr('missing or changed')])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        self.body.addWidget(self.table)
        facts = KeyValue()
        facts.add(tr('Location'), mono(text_label(str(base), 'KeyValueValue')))
        facts.add(tr('Package'), mono(text_label(breakable(mod.package_url or '—'), 'KeyValueValue')))
        facts.add(tr('File check'), tr('The download matched the SHA-256 published by the source.') if mod.package_verified else tr('The source published no checksum for this download.'))
        self.body.addWidget(facts)
        row = QHBoxLayout()
        folder = Button(tr('Open folder'), 'secondary', 'sm', icon='folder')
        folder.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(base))))
        row.addWidget(folder)
        row.addStretch(1)
        self.body.addLayout(row)


class HistoryDialog(Dialog):
    """What happened to one installed mod, newest first."""

    def __init__(self, mod, parent=None):
        super().__init__(tr('History of {0}').format(mod.name), variant='review', cancel=tr('Close'), parent=parent)
        self.table = DataTable([tr('When'), tr('What'), tr('Version'), tr('Note')])
        self.table.setMinimumHeight(44 * min(max(len(mod.history), 1), 8) + 40)
        for h in reversed(mod.history):
            self.table.add_row([ltr(iso_text(h.get('at', ''))), action_word(h.get('action', '')), ltr(h.get('version', '')), h.get('note', '')])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.body.addWidget(self.table)
        if mod.previous:
            self.body.addWidget(text_label(tr('Earlier versions kept for restoring: ') + ', '.join(p.version for p in mod.previous), 'Muted'))


class BatchReview(Dialog):
    """Update all: every prepared update in one list, acknowledged once."""

    def __init__(self, plans, skipped, parent=None):
        super().__init__(tr('Review updates'), tr('{0} updates are ready. Nothing has been changed yet.').format(len(plans)), 'review', tr('Update all'), tr('Cancel'), parent=parent)
        self.plans = plans
        needs = False
        updates = List()
        for plan in plans:
            updates.add(ListRow(tr('{0}, from {1} to {2}').format(plan.mod_name, plan.replaces, plan.version), '%s · %s' % (plan.repository_name, plan.trust)))
            needs = needs or plan.requires_ack
        self.body.addWidget(updates)
        for plan in plans:
            for warning in plan.warnings:
                self.body.addWidget(Banner(breakable(warning), '', 'warning'))
        for name, reason in skipped:
            self.body.addWidget(Banner(tr('Skipped {0}: {1}').format(name, reason), '', 'danger'))
        self.needs = needs
        self.ack = Checkbox(tr('I understand the warnings and want to install these updates'))
        self.ack.setVisible(needs)
        self.ack.toggled.connect(self.refresh)
        self.body.addWidget(self.ack)
        self.go = self.action_button
        self.refresh()

    def refresh(self, *_):
        self.go.setEnabled(bool(self.plans) and (not self.needs or self.ack.isChecked()))

    @property
    def acknowledged(self):
        return self.ack.isChecked() or not self.needs


class FoldRow(QFrame):
    """A closed row that opens to show more: a chevron, a title with a count, one muted sentence, a badge at the trailing side."""

    def __init__(self, title, line, parent=None):
        super().__init__(parent)
        mark(self, 'ListRow')
        t = theme.current()
        self.expanded = False
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(0)
        self.head = QFrame()
        row = QHBoxLayout(self.head)
        row.setContentsMargins(t.px('space.4'), t.px('space.3'), t.px('space.4'), t.px('space.3'))
        row.setSpacing(t.px('space.3'))
        self.arrow = QLabel()
        row.addWidget(self.arrow, 0, Qt.AlignTop)
        copy = QVBoxLayout()
        copy.setSpacing(2)
        self.title = text_label(title, 'RowTitle')
        copy.addWidget(self.title)
        self.line = text_label(line, 'Muted')
        copy.addWidget(self.line)
        row.addLayout(copy, 1)
        self.badge = Badge('', 'success')
        self.badge.hide()
        row.addWidget(self.badge, 0, Qt.AlignVCenter)
        self.head.setCursor(Qt.PointingHandCursor)
        self.head.mousePressEvent = lambda event: self.toggle()
        self.head.setFocusPolicy(Qt.StrongFocus)
        self.head.keyPressEvent = lambda event: self.toggle() if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space) else QFrame.keyPressEvent(self.head, event)
        box.addWidget(self.head)
        self.body = QWidget()
        self.inner = QVBoxLayout(self.body)
        self.inner.setContentsMargins(t.px('space.4'), 0, t.px('space.4'), t.px('space.3'))
        self.inner.setSpacing(t.px('space.2'))
        self.body.hide()
        box.addWidget(self.body)
        self.refresh_arrow()
        theme.watch(self, 'refresh_arrow')

    def refresh_arrow(self):
        self.arrow.setPixmap(theme.icon('down' if self.expanded else 'chev', 'color.text.secondary', 16).pixmap(16, 16))

    def toggle(self):
        self.expanded = not self.expanded
        self.body.setVisible(self.expanded)
        self.refresh_arrow()


class InstalledPage(QWidget):
    openRequested = Signal(str)             # an address such as 'mods.browse'
    gameRequired = Signal()                 # the user asked to link the game (the window brings up Home's link card)

    def __init__(self, service, classic=None, parent=None):
        """`classic` is the ClassicPack widget (pages/classic.py): it sits inside the folded "Classic pack" row; without it that row is left out."""
        super().__init__(parent)
        mark(self, 'InstalledPage')
        self.service = service
        self.classic = classic
        self.statuses = {}
        self.rows = {}                      # mod key → ListRow
        self.message = ''                   # the last thing an action said, for the record
        self.banner = None
        self.checking = False
        self.mods = []
        self._plans, self._skipped, self._queue = [], [], []
        t = theme.current()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(self.scroll)
        inner = QWidget()
        self.scroll.setWidget(inner)
        self.column = QVBoxLayout(inner)
        self.column.setContentsMargins(0, 0, 12, 0)
        self.column.setSpacing(t.px('space.4'))
        self.notice = QVBoxLayout()
        self.column.addLayout(self.notice)
        self.game_notice = Banner(tr('Link your game first'), tr('These pages work on a Deadlock folder. Link it on the Home page, or let Toolbox find it.'), 'warning')
        link = Button(tr('Link the game'), 'secondary', 'sm')
        link.clicked.connect(self.gameRequired.emit)
        self.game_notice.add_action(link)
        self.game_notice.hide()
        self.column.addWidget(self.game_notice)

        top = QHBoxLayout()
        top.setSpacing(t.px('space.2'))
        self.summary = text_label('', 'CardText')
        top.addWidget(self.summary, 1)
        self.check_button = Button(tr('Check for updates'), 'secondary', icon='refresh')
        self.check_button.setToolTip(tr('Refreshes your sources, then compares versions'))
        self.check_button.clicked.connect(self.check_updates)
        top.addWidget(self.check_button)
        self.all_button = Button(tr('Update all'), 'primary')
        self.all_button.clicked.connect(self.update_all)
        top.addWidget(self.all_button)
        self.column.addLayout(top)

        self.card = Card(variant='flat')
        self.list = List(variant='flat')
        self.card.body.addWidget(self.list)
        self.column.addWidget(self.card)
        self.browse_button = Button(tr('Browse mods'), 'primary')
        self.browse_button.clicked.connect(lambda: self.openRequested.emit('mods.browse'))
        self.empty = EmptyState('box', tr('No mods yet'), tr('Mods you install from Browse appear here, with their updates.'), self.browse_button)
        self.empty.layout().setContentsMargins(0, t.px('space.8'), 0, 0)
        self.empty.hide()
        self.column.addWidget(self.empty)

        self.folds = Card(variant='flat')
        self.classic_fold = FoldRow(tr('Classic pack'), tr('The four mods Toolbox has always supported. You add their files yourself.'))
        if classic is not None:
            self.classic_fold.inner.addWidget(classic)
        self.other_fold = FoldRow(tr('Not installed by Toolbox'), tr("Other files in the game's mod folder. Toolbox lists them and never touches them."))
        self.other_names = text_label('', 'CardText')
        self.other_fold.inner.addWidget(self.other_names)
        self.other_open = Button(tr('Open addons folder'), 'secondary', 'sm', icon='folder')
        self.other_open.clicked.connect(self.open_folder)
        self.other_fold.inner.addWidget(self.other_open, 0, Qt.AlignLeading)
        self.folds.body.addWidget(self.classic_fold)
        self.folds.body.addWidget(self.other_fold)
        self.column.addWidget(self.folds)
        self.column.addStretch(1)

        service.changed.connect(self.reload)
        service.busyChanged.connect(lambda _: self.sync())
        self.reload()

    def showEvent(self, event):
        super().showEvent(event)
        self.reload()

    def show_classic(self):
        """Open the Classic pack row and bring it into view (Backups and the start-up flag --mods lead here)."""
        if not self.classic_fold.expanded:
            self.classic_fold.toggle()
        self.scroll.ensureWidgetVisible(self.classic_fold)

    # ---- data ------------------------------------------------------------------------

    def installer(self):
        try:
            return self.service.installer()
        except InstallError:
            return None

    def set_notice(self, variant='', title='', text='', open_folder=False):
        """One banner about the last problem; an empty `variant` clears it."""
        if self.banner is not None:
            self.banner.setParent(None)
            self.banner.deleteLater()
            self.banner = None
        if variant:
            self.banner = Banner(breakable(title), breakable(text), variant)
            if open_folder:
                button = Button(tr('Open the folder'), 'secondary', 'sm')
                button.clicked.connect(self.open_folder)
                self.banner.add_action(button)
            self.notice.addWidget(self.banner)

    def notice_text(self):
        return '' if self.banner is None else (self.banner.title.text() + '\n' + self.banner.text.text()).strip()

    def reload(self, *_):
        installer = self.installer()
        linked = installer is not None
        self.game_notice.setVisible(not linked)
        mods, failed = [], False
        if linked:
            try:
                mods = installer.installed()
                self.statuses = {s.mod.key: s for s in self.service.statuses()}
            except (InstallError, OSError, ValueError):
                mods, failed, self.statuses = [], True, {}
        else:
            self.statuses = {}
        self.mods = mods
        if failed:
            self.set_notice('danger', tr("The list of installed mods couldn't be read"), tr('A copy was kept and your game files were not touched.'), open_folder=True)
        elif self.banner is not None and self.banner.property('variant') == 'danger' and self.notice_text().startswith(tr("The list of installed mods couldn't be read")):
            self.set_notice()
        self.list.clear()
        self.rows = {}
        for mod in mods:
            row = self.make_row(mod, self.statuses.get(mod.key))
            self.list.add(row)
            self.rows[mod.key] = row
        self.card.setVisible(bool(mods))
        self.empty.setVisible(linked and not mods and not failed)
        updates = [s for s in self.statuses.values() if s.updatable]
        off = sum(1 for m in mods if not m.enabled)
        if not linked:
            self.summary.setText(tr('No game linked.'))
        else:
            parts = [plural(len(mods), tr('{0} mod'), tr('{0} mods')), plural(len(updates), tr('{0} update'), tr('{0} updates'))]
            if off:
                parts.append(tr('{0} off').format(off))
            build = self.service.game_build()
            if build:
                parts.append(tr('game build {0}').format(build))
            self.summary.setText(' · '.join(parts))
        self.all_button.setText(tr('Update all ({0})').format(len(updates)) if updates else tr('Update all'))
        other = installer.unmanaged() if linked else []
        self.other_fold.setVisible(bool(other))
        self.other_fold.title.setText(tr('Not installed by Toolbox ({0})').format(len(other)))
        shown = [p.name for p in other[:MAX_UNMANAGED_SHOWN]]
        self.other_names.setText('\n'.join('• ' + n for n in shown) + ('\n…' if len(other) > MAX_UNMANAGED_SHOWN else ''))
        classic = self.classic.summary() if self.classic is not None else []
        self.classic_fold.setVisible(bool(classic))
        on = sum(1 for _, is_on in classic if is_on)
        self.classic_fold.title.setText(tr('Classic pack ({0})').format(len(classic)))
        self.classic_fold.badge.setVisible(on > 0)
        self.classic_fold.badge.setText(tr('{0} on').format(on))
        self.folds.setVisible(self.classic_fold.isVisibleTo(self.folds) or self.other_fold.isVisibleTo(self.folds))
        set_props(self.classic_fold, last='false' if bool(other) else 'true')           # the last visible row has no line under it
        set_props(self.other_fold, last='true')
        self.sync()

    def make_row(self, mod, status):
        t = theme.current()
        switch = Switch()
        switch.setAccessibleName(tr('{0} is on').format(mod.name))
        switch.setToolTip(tr('Enabled: the game loads this mod. Disabling moves its files out of the addons folder.'))
        switch.setChecked(mod.enabled)
        switch.toggled.connect(lambda on, key=mod.key: self.toggled(key, on))
        label, variant = status_badge(mod, status)
        badge = Badge(label, variant)
        if status is not None and status.note:
            badge.setToolTip(status.note)
        holder = QWidget()
        controls = QHBoxLayout(holder)
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(t.px('space.2'))
        controls.addWidget(badge)
        update = None
        if status is not None and status.updatable and mod.enabled:
            update = Button(tr('Update'), 'secondary', 'sm')
            update.clicked.connect(lambda _=False, key=mod.key: self.update_one(key))
            controls.addWidget(update)
        more = IconButton('more', tr('More about {0}').format(mod.name), 'ghost')
        more.clicked.connect(lambda _=False, key=mod.key, button=more: self.show_menu(key, button))
        controls.addWidget(more)
        version = tr('{0} to {1}').format(mod.version, status.latest) if status is not None and status.updatable and status.latest else mod.version
        line = ' · '.join(part for part in (version, mod.author, mod.repository_name or mod.repository_id) if part)
        row = ListRow(breakable(mod.name), breakable(line), control=holder, lead=switch)
        row.switch, row.badge, row.update_button, row.more = switch, badge, update, more
        row.key = mod.key
        return row

    def sync(self):
        busy = self.service.busy
        linked = self.installer() is not None
        self.check_button.setEnabled(linked and not busy and not self.checking)
        self.all_button.setEnabled(linked and not busy and any(s.updatable for s in self.statuses.values()))
        self.other_open.setEnabled(linked)

    # ---- the menu of one mod ----------------------------------------------------------

    def mod_of(self, key):
        installer = self.installer()
        return installer.get(*key) if installer else None

    def build_menu(self, key):
        """The "more" menu of one mod: Update, Previous version, Show files, History, Open its page, then Remove."""
        mod = self.mod_of(key)
        menu = Menu(self)
        if mod is None:
            return menu
        status = self.statuses.get(key)
        busy = self.service.busy
        if status is not None and status.updatable and mod.enabled:
            menu.add(tr('Update to {0}').format(status.latest), lambda: self.update_one(key), 'download').setEnabled(not busy)
        if mod.previous:
            menu.add(tr('Go back to {0}').format(mod.previous[-1].version), lambda: self.restore(key), 'history').setEnabled(not busy)
        menu.add(tr('Show files'), lambda: self.show_files(key), 'folder')
        menu.add(tr('History'), lambda: self.show_history(key), 'clock')
        if mod.source_url:
            menu.add(tr('Open its page'), lambda: self.open_source(key), 'ext')
        menu.add(tr('Remove'), lambda: self.remove(key), 'trash', danger=True).setEnabled(not busy)
        return menu

    def show_menu(self, key, button):
        menu = self.build_menu(key)
        menu.exec(button.mapToGlobal(button.rect().bottomLeft()))

    # ---- actions ------------------------------------------------------------------------------

    def say(self, message):
        """A result that went well: remembered, shown as a toast."""
        self.message = message
        self.set_notice()
        Toast(self, message)

    def failed(self, message, code):
        self.message = failure_text(code, message)
        lead, _, detail = self.message.partition('\n')
        self.set_notice('danger', lead, detail or tr('Nothing was changed.'))
        self.checking = False
        self.reload()

    def toggled(self, key, want):
        self.message = tr('Enabling…') if want else tr('Disabling…')
        self.service.operate('set_enabled', (key[0], key[1], want),
                             lambda mod: (self.say((tr('Enabled {0}.') if want else tr('Disabled {0}. The game no longer loads it.')).format(mod.name)), self.reload()), self.failed)
        self.reload()

    def check_updates(self):
        self.checking = True
        self.check_button.set_busy(True)
        self.message = tr('Refreshing your sources…')

        def done(views):
            self.checking = False
            self.check_button.set_busy(False)
            self.reload()
            self.say(tr('Checked {0} sources. {1} updates available.').format(len(views), sum(1 for s in self.statuses.values() if s.updatable)))

        def failed(message, code):
            self.check_button.set_busy(False)
            self.failed(message, code)
        self.service.run(self.service.manager.refresh_all, done, failed)

    def update_one(self, key):
        mod, status = self.mod_of(key), self.statuses.get(key)
        if not (mod and status and status.updatable):
            return
        self.message = tr('Downloading and checking {0} {1}…').format(mod.name, status.latest)
        self.service.prepare(mod.repository_id, mod.mod_id, status.latest, self.prepared_one, self.failed)

    def prepared_one(self, plan):
        dialog = InstallReview(plan, self)
        if dialog.exec() != Dialog.Accepted:
            self.service.discard(plan)
            self.message = tr('Cancelled. Nothing was changed.')
            self.set_notice('info', self.message)
            return
        self.service.commit(plan, dialog.acknowledged, lambda mod: (self.say(tr('Updated {0} to {1}. Every file was re-checked after copying.').format(mod.name, mod.version)), self.reload()), self.failed)

    def update_all(self):
        self._queue = [s for s in self.statuses.values() if s.updatable]
        self._plans, self._skipped = [], []
        if self._queue:
            self.message = tr('Downloading {0} updates…').format(len(self._queue))
            self._prepare_next()

    def _prepare_next(self):
        if not self._queue:
            self._review_batch()
            return
        status = self._queue.pop(0)
        self.service.prepare(status.mod.repository_id, status.mod.mod_id, status.latest, self._batch_prepared, lambda message, code, s=status: self._batch_failed(s, message, code))

    def _batch_prepared(self, plan):
        if plan.can_install:
            self._plans.append(plan)
        else:
            self._skipped.append((plan.mod_name, ' '.join(plan.blockers)))
            self.service.discard(plan)
        self._prepare_next()

    def _batch_failed(self, status, message, code):
        self._skipped.append((status.mod.name, failure_text(code, message).split('\n')[0]))
        self._prepare_next()

    def _review_batch(self):
        if not self._plans:
            self.message = tr('Nothing could be prepared. ') + ' '.join('%s: %s' % s for s in self._skipped)
            self.set_notice('warning', self.message)
            return
        dialog = BatchReview(self._plans, self._skipped, self)
        if dialog.exec() != Dialog.Accepted:
            for plan in self._plans:
                self.service.discard(plan)
            self.message = tr('Cancelled. Nothing was changed.')
            self.set_notice('info', self.message)
            return
        self._acknowledged = dialog.acknowledged
        self._done, self._errors = [], []
        self._commit_next()

    def _commit_next(self):
        if not self._plans:
            self.reload()
            self.say(tr('Updated {0} mods.').format(len(self._done)) + ((tr(' Problems: ') + '; '.join(self._errors)) if self._errors else ''))
            return
        plan = self._plans.pop(0)
        self.service.commit(plan, self._acknowledged, lambda mod: (self._done.append(mod.name), self._commit_next()),
                            lambda message, code, p=plan: (self._errors.append('%s: %s' % (p.mod_name, failure_text(code, message).split('\n')[0])), self._commit_next()))

    def ask(self, title, text, action, danger=False):
        return confirm(self, title, text, action, danger)

    def restore(self, key):
        mod = self.mod_of(key)
        if not mod or not mod.previous:
            return
        target = mod.previous[-1].version
        if not self.ask(tr('Go back to an earlier version'), tr('Go back to {0} {1}? The current version is kept so you can switch again.').format(mod.name, target), tr('Go back')):
            return
        self.service.operate('restore_previous', (mod.repository_id, mod.mod_id), lambda m: (self.say(tr('{0} is back to version {1}.').format(m.name, m.version)), self.reload()), self.failed)

    def remove(self, key):
        mod = self.mod_of(key)
        if not mod:
            return
        users = self.installer().dependents(mod)
        extra = (' ' + tr('These mods need it: {0}.').format(', '.join(m.name for m in users))) if users else ''
        if not self.ask(tr('Remove {0}?').format(mod.name), tr('Its files are moved to the Toolbox recovery folder, not deleted.') + extra, tr('Remove'), danger=True):
            return
        if users:
            installer = self.installer()
            self.service.run(lambda: installer.uninstall(mod.repository_id, mod.mod_id, force=True),
                             lambda _: (self.service.changed.emit(), self.say(tr('Removed {0}.').format(mod.name))), self.failed)
        else:
            self.service.operate('uninstall', (mod.repository_id, mod.mod_id), lambda _: (self.say(tr('Removed {0}.').format(mod.name)), self.reload()), self.failed)

    def show_files(self, key):
        mod = self.mod_of(key)
        if mod:
            installer = self.installer()
            FilesDialog(mod, installer.addons, installer._disabled_dir(mod), self).exec()

    def show_history(self, key):
        mod = self.mod_of(key)
        if mod:
            HistoryDialog(mod, self).exec()

    def open_source(self, key):
        mod = self.mod_of(key)
        if mod and mod.source_url:
            QDesktopServices.openUrl(QUrl(mod.source_url))

    def open_folder(self):
        installer = self.installer()
        if installer:
            installer.addons.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(installer.addons)))
