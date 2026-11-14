"""Mods > Browse > My sources: the mods of the extra sources you added (a GitHub or GitLab address, a web address, a local list).

The same cards, sheet and review as the GameBanana side (`pages/browse.py`), drawn from `RepositoryManager.search()`. Installing goes through
`ModService.prepare()` and `commit()` (the journaled installer): download to a private folder, check, inspect, review, and only then copy.
Everything a source says about itself is shown as plain text. The page draws; the managers and the installer are unchanged.
"""
from PySide6.QtCore import QEvent, Qt, QThreadPool, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QImage, QPixmap
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from ..hub_ui import failure_text
from ..i18n import tr
from ..installer import InstallError
from ..repos import Trust
from ..repos.compat import fit
from ..repos.model import GameFit
from ..ui_common import Job
from ..shell import theme
from ..shell.components import (Badge, Banner, Button, EmptyState, KeyValue, ModCard, ProgressBar, SearchField, Select, Sheet, Toast, breakable, confirm, mark, text_label,
                                Chip)
from ..ui_common import ltr, size_text
from .browse import CARD_MIN, GAP, IMAGES_SHOWN, MAX_IMAGE_BYTES, MAX_IMAGE_SIDE, InstallReview, day_text, mono, plural

CARD_LIMIT = 500                # most hits the page shows; narrower filters reach the rest
PAGE_SIZE = 48

FIT_WORDS = {GameFit.COMPATIBLE: (lambda: tr('Fits'), 'success'), GameFit.UNTESTED: (lambda: tr('Not tested on this version'), 'warning'),
             GameFit.INCOMPATIBLE: (lambda: tr('Other game version'), 'danger'), GameFit.UNKNOWN: (lambda: tr('Unknown'), 'neutral')}
TRUST_VARIANT = {Trust.OFFICIAL: 'success', Trust.VERIFIED: 'success', Trust.COMMUNITY: 'neutral', Trust.UNVERIFIED: 'warning'}


def trust_words(trust):
    return {Trust.OFFICIAL: tr('Official'), Trust.VERIFIED: tr('Verified'), Trust.COMMUNITY: tr('Community'), Trust.UNVERIFIED: tr('Not reviewed')}[trust]


class SourcesView(QWidget):
    openRequested = Signal(str)             # an address such as 'settings.sources'
    gameRequired = Signal()

    def __init__(self, service, parent=None):
        super().__init__(parent)
        mark(self, 'SourcesView')
        self.service = service              # the ModService: its manager searches, its installer installs
        self.current = None                 # (repository id, mod id) whose sheet is open
        self.hits = []
        self.cards, self.card_order, self.built, self.columns = {}, [], 0, 0
        self.shown_hit = None
        self.result = None
        self.pictures_on = False
        self._building = True
        self._token = 0
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

        self.filters = QWidget()
        box = QVBoxLayout(self.filters)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(t.px('space.3'))
        row = QHBoxLayout()
        row.setSpacing(t.px('space.2'))
        self.search = SearchField(tr('Search by name, author, type or description'))
        self.query = self.search.edit
        self.query.setAccessibleName(tr('Search mods'))
        self.query.textChanged.connect(self.reload)
        row.addWidget(self.search, 1)
        self.category, self.repository, self.sort = Select(), Select(), Select()
        self.category.setAccessibleName(tr('Type'))
        self.repository.setAccessibleName(tr('Source'))
        self.sort.setAccessibleName(tr('Order'))
        for caption, value in ((tr('Best match'), 'relevance'), (tr('Name'), 'name'), (tr('Recently updated'), 'updated'), (tr('Source'), 'repository'), (tr('Largest download'), 'size')):
            self.sort.addItem(caption, value)
        for select in (self.category, self.repository, self.sort):
            select.setMinimumWidth(120)
            select.currentIndexChanged.connect(self.reload)
            row.addWidget(select)
        box.addLayout(row)
        line = QHBoxLayout()
        self.installable = Chip(tr('Installable only'))
        self.installable.toggled.connect(self.reload)
        line.addWidget(self.installable)
        self.count_label = text_label('', 'Muted')
        self.count_label.setAlignment(Qt.AlignTrailing | Qt.AlignVCenter)
        line.addWidget(self.count_label, 1)
        box.addLayout(line)
        self.column.addWidget(self.filters)

        self.add_button = Button(tr('Add a source'), 'primary')
        self.add_button.clicked.connect(lambda: self.openRequested.emit('settings.sources'))
        self.empty = EmptyState('globe', tr('No mods from your sources yet'), tr('Add a source in Settings, then its mods appear here.'), self.add_button)
        self.empty.layout().setContentsMargins(0, t.px('space.8'), 0, 0)
        self.empty.hide()
        self.column.addWidget(self.empty)
        self.empty_filter = EmptyState('search', tr('No mods match your search'), tr('Try fewer words or another filter.'))
        self.empty_filter.hide()
        self.column.addWidget(self.empty_filter)
        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(GAP)
        self.column.addWidget(self.grid_host)
        self.more = Button(tr('Show more'), 'secondary')
        self.more.clicked.connect(self.show_more)
        self.column.addWidget(self.more, 0, Qt.AlignHCenter)
        self.note = text_label('', 'Muted')
        self.column.addWidget(self.note)
        self.column.addStretch(1)
        self.scroll.viewport().installEventFilter(self)
        self.build_sheet()
        service.changed.connect(self.reload)
        service.progress.connect(self.show_install_progress)
        service.busyChanged.connect(lambda _: self.sync_install())
        self._building = False
        self.reload()

    # ---- construction ---------------------------------------------------------

    def build_sheet(self):
        t = theme.current()
        self.sheet = Sheet(self, '')
        self.sheet.closed.connect(self.sheet_closed)
        body = self.sheet.body
        body.setSpacing(t.px('space.3'))
        self.d_by = text_label('', 'Muted')
        body.addWidget(self.d_by)
        self.d_badges = QHBoxLayout()
        self.d_badges.setSpacing(t.px('space.2'))
        body.addLayout(self.d_badges)
        self.install_block = QWidget()
        block = QVBoxLayout(self.install_block)
        block.setContentsMargins(0, 0, 0, 0)
        block.setSpacing(t.px('space.2'))
        block.addWidget(text_label(tr('Version'), 'FieldLabel'))
        self.version = Select()
        self.version.setAccessibleName(tr('Version'))
        self.version.currentIndexChanged.connect(self.version_changed)
        block.addWidget(self.version)
        self.install_button = Button(tr('Install'), 'primary', 'lg', icon='download')
        self.install_button.clicked.connect(self.install)
        block.addWidget(self.install_button)
        self.d_status = text_label('', 'Muted')
        block.addWidget(self.d_status)
        self.game_notice = Banner(tr('Link your game to install mods'), tr('Toolbox needs to know where Deadlock is installed.'), 'warning')
        link = Button(tr('Link the game'), 'secondary', 'sm')
        link.clicked.connect(self.gameRequired.emit)
        self.game_notice.add_action(link)
        block.addWidget(self.game_notice)
        self.activity = QWidget()
        act = QVBoxLayout(self.activity)
        act.setContentsMargins(0, 0, 0, 0)
        self.act_text = text_label('', 'CardText')
        act.addWidget(self.act_text)
        line = QHBoxLayout()
        self.install_bar = ProgressBar()
        self.install_bar.set_unknown()
        line.addWidget(self.install_bar, 1)
        self.install_cancel = Button(tr('Cancel'), 'ghost', 'sm')
        self.install_cancel.clicked.connect(self.service.cancel)
        line.addWidget(self.install_cancel)
        act.addLayout(line)
        self.activity.hide()
        block.addWidget(self.activity)
        self.result_box = QVBoxLayout()
        block.addLayout(self.result_box)
        body.addWidget(self.install_block)
        self.trust_notice = Banner('', '', 'warning')
        body.addWidget(self.trust_notice)
        self.facts = KeyValue()
        self.facts.form.setVerticalSpacing(t.px('space.2'))
        body.addWidget(self.facts)
        self.d_summary = text_label('', 'CardText')
        body.addWidget(self.d_summary)
        self.d_description = text_label('', 'CardText')
        self.d_description.setTextInteractionFlags(Qt.TextSelectableByMouse)
        body.addWidget(self.d_description)
        self.d_changelog_title = text_label(tr('Changelog'), 'FieldLabel')
        body.addWidget(self.d_changelog_title)
        self.d_changelog = text_label('', 'CardText')
        body.addWidget(self.d_changelog)
        self.pictures_box = QGridLayout()
        self.pictures_box.setSpacing(t.px('space.2'))
        body.addLayout(self.pictures_box)
        actions = QVBoxLayout()
        actions.setSpacing(t.px('space.2'))
        self.open_button = Button(tr('Open source page'), 'secondary', 'sm', icon='ext')
        self.open_button.clicked.connect(self.open_source)
        actions.addWidget(self.open_button, 0, Qt.AlignLeading)
        self.pictures_button = Button(tr('Show pictures'), 'ghost', 'sm', icon='eye')
        self.pictures_button.clicked.connect(self.toggle_pictures)
        actions.addWidget(self.pictures_button, 0, Qt.AlignLeading)
        self.remove_button = Button(tr('Remove'), 'danger-quiet', 'sm', icon='trash')
        self.remove_button.clicked.connect(self.uninstall)
        actions.addWidget(self.remove_button, 0, Qt.AlignLeading)
        body.addLayout(actions)
        body.addStretch(1)

    # ---- layout ---------------------------------------------------------------

    def eventFilter(self, watched, event):
        if watched is self.scroll.viewport() and event.type() == QEvent.Resize:
            self.arrange()
        return super().eventFilter(watched, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.sheet.isVisible():
            self.sheet.reposition()

    def showEvent(self, event):
        super().showEvent(event)
        self.reload()

    def arrange(self):
        width = self.scroll.viewport().width() - self.column.contentsMargins().right()
        columns = max(1, (width + GAP) // (CARD_MIN + GAP))
        if columns == self.columns and self.grid.count() == len(self.card_order):
            return
        while self.grid.count():
            self.grid.takeAt(0)
        for index, card in enumerate(self.card_order):
            self.grid.addWidget(card, index // columns, index % columns)
        for column in range(max(columns, self.columns) + 1):
            self.grid.setColumnStretch(column, 1 if column < columns else 0)
        self.columns = columns

    # ---- the list ---------------------------------------------------------------

    def installed_map(self):
        try:
            return {m.key: m for m in self.service.installer().installed()}
        except InstallError:
            return {}

    def fill_choices(self):
        manager = self.service.manager
        for select, label, items in ((self.category, tr('All types'), [('%s (%s)' % (n, ltr(c)), n) for n, c in manager.categories().items()]),
                                     (self.repository, tr('All sources'), [(v.name, v.source.id) for v in manager.list() if v.source.enabled])):
            current = select.currentData()
            select.blockSignals(True)
            select.clear()
            select.addItem(label, '')
            for caption, value in items:
                select.addItem(caption, value)
            select.setCurrentIndex(max(0, select.findData(current)))
            select.blockSignals(False)

    def reload(self, *_):
        if self._building:
            return
        manager = self.service.manager
        self.fill_choices()
        have_sources = bool(manager.list())
        self.hits = manager.search(self.query.text(), category=self.category.currentData() or '', repository=self.repository.currentData() or '',
                                   installable_only=self.installable.isChecked(), sort=self.sort.currentData() or 'relevance')[:CARD_LIMIT]
        self.clear_cards()
        self.build_cards(PAGE_SIZE)
        enabled = sum(1 for v in manager.list() if v.source.enabled)
        self.filters.setVisible(have_sources)
        self.empty.setVisible(not have_sources)
        self.empty_filter.setVisible(have_sources and not self.hits)
        self.grid_host.setVisible(bool(self.hits))
        self.more.setVisible(self.built < len(self.hits))
        self.count_label.setText(tr('{0} from {1}').format(plural(len(self.hits), tr('{0} mod'), tr('{0} mods')), plural(enabled, tr('{0} source'), tr('{0} sources'))))
        self.note.setText(tr('Showing the first {0}. Narrow the search to see the rest.').format(CARD_LIMIT) if len(self.hits) >= CARD_LIMIT else '')
        self.note.setVisible(bool(self.note.text()))
        if self.current is not None:
            self.sync_install()

    def clear_cards(self):
        while self.grid.count():
            self.grid.takeAt(0)
        for card in self.card_order:
            card.setParent(None)
            card.deleteLater()
        self.cards, self.card_order, self.built, self.columns = {}, [], 0, 0

    def build_cards(self, count):
        installed = self.installed_map()
        end = min(len(self.hits), self.built + count)
        for hit in self.hits[self.built:end]:
            key = (hit.repository.source.id, hit.mod.id)
            line = ' · '.join(part for part in (hit.mod.categories[0] if getattr(hit.mod, 'categories', None) else '', hit.mod.author, hit.repository.name) if part)
            card = ModCard(hit.mod.name, line, key in installed)
            card.setAccessibleName('%s, %s' % (hit.mod.name, line))
            card.set_selected(key == self.current)
            card.clicked.connect(lambda key=key: self.open_mod(key))
            self.cards[key] = card
            self.card_order.append(card)
        self.built = end
        self.arrange()

    def show_more(self):
        self.build_cards(PAGE_SIZE)
        self.more.setVisible(self.built < len(self.hits))

    # ---- the sheet ----------------------------------------------------------------

    def hit_of(self, key):
        return next((h for h in self.hits if (h.repository.source.id, h.mod.id) == key), None)

    def selected(self):
        return self.shown_hit

    def open_mod(self, key):
        hit = self.hit_of(key)
        if hit is None:
            return
        self.current, self.shown_hit = key, hit
        for k, card in self.cards.items():
            card.set_selected(k == key)
        self.set_result()
        self.pictures_on = False
        self.pictures_button.setText(tr('Show pictures'))
        self.clear_pictures()
        mod, repository = hit.mod, hit.repository
        self.sheet.title.setText(breakable(mod.name))
        self.d_by.setText(breakable(tr('by {0}').format(mod.author or tr('unknown author')) + ' · ' + (mod.license or tr('licence not stated'))))
        while self.d_badges.count():
            item = self.d_badges.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.d_badges.addWidget(Badge(repository.name, 'neutral'))
        self.d_badges.addWidget(Badge(trust_words(repository.trust), TRUST_VARIANT[repository.trust]))
        self.d_badges.addStretch(1)
        self.trust_notice.title.setText(trust_words(repository.trust))
        self.trust_notice.text.setText(breakable(repository.trust_note or ''))
        self.trust_notice.text.setVisible(bool(repository.trust_note))
        self.trust_notice.setVisible(repository.trust is not Trust.OFFICIAL)
        self.d_summary.setText(breakable(mod.summary or ''))
        self.d_summary.setVisible(bool(mod.summary))
        self.d_description.setText(breakable(mod.description or tr('The author gave no description.')))
        self.version.blockSignals(True)
        self.version.clear()
        for v in mod.versions:
            flags = [tr('withdrawn')] if v.yanked else ([tr('pre-release')] if v.prerelease else [])
            if v.unsupported_reason:
                flags.append(tr('unsupported'))
            self.version.addItem(v.version.text + (' · ' + ', '.join(flags) if flags else ''), v.version.text)
        latest = hit.latest
        self.version.setCurrentIndex(max(0, self.version.findData(latest.version.text)) if latest else 0)
        self.version.blockSignals(False)
        self.open_button.setEnabled(bool(mod.source_url or mod.homepage))
        self.pictures_button.setVisible(bool(mod.screenshots))
        self.refresh_version()
        self.sheet.open_sheet()

    def sheet_closed(self):
        self._token += 1
        self.current, self.shown_hit = None, None
        for card in self.cards.values():
            card.set_selected(False)

    def close_sheet(self):
        self.sheet.close_sheet()

    def current_version(self):
        hit = self.shown_hit
        if hit is None or self.version.currentData() is None:
            return None
        return hit.mod.find(self.version.currentData())

    def version_changed(self, *_):
        self.refresh_version()

    def refresh_version(self):
        """The facts of the chosen version: dates, size, checksum, fit with the game, what it needs, its changelog."""
        self.facts.clear()
        v = self.current_version()
        if v is not None:
            pkg = v.package
            self.facts.add(tr('Published'), ltr(day_text_of(v.published)))
            self.facts.add(tr('Download'), ltr(size_text(pkg.size)) if pkg and pkg.size else tr('unknown size'))
            self.facts.add(tr('File check'), tr('SHA-256 published') if pkg and pkg.sha256 else tr('no SHA-256 published'))
            build = self.service.game_build()
            words, variant = FIT_WORDS[fit(v.game, build)]
            badge_row = QWidget()
            row = QHBoxLayout(badge_row)
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(Badge(words(), variant), 0, Qt.AlignVCenter)
            row.addStretch(1)
            self.facts.add(tr('Your game'), badge_row)
            if v.dependencies:
                self.facts.add(tr('Needs'), breakable(', '.join('%s %s' % (d.id, d.range) for d in v.dependencies)))
            if v.conflicts:
                self.facts.add(tr('Conflicts with'), breakable(', '.join(d.id for d in v.conflicts)))
            self.d_changelog.setText(breakable(v.changelog or tr('No changelog.')))
        self.d_changelog_title.setVisible(v is not None)
        self.d_changelog.setVisible(v is not None)
        self.sync_install()

    def sync_install(self, *_):
        hit, v = self.shown_hit, self.current_version()
        self.install_block.setVisible(hit is not None)
        if hit is None:
            return
        busy = self.service.busy
        linked = self.service.ready()
        have = self.installed_map().get(self.current)
        if v is None:
            self.install_button.setEnabled(False)
            self.remove_button.setVisible(False)
            self.d_status.setText(tr('This mod has no stable version yet.'))
            self.d_status.setVisible(True)
            self.game_notice.setVisible(not linked)
            return
        self.install_button.setText(tr('Reinstall {0}').format(v.version) if have and have.version == v.version.text
                                    else (tr('Update to {0}').format(v.version) if have else tr('Install {0}').format(v.version)))
        self.install_button.setEnabled(not busy and v.installable and linked)
        self.remove_button.setVisible(have is not None)
        self.remove_button.setEnabled(not busy and have is not None)
        reason = v.unsupported_reason or (tr('This version was withdrawn by its author.') if v.yanked else '')
        status = reason or (tr('Installed: {0}.').format(have.version) if have else '')
        self.d_status.setText(breakable(status))
        self.d_status.setVisible(bool(status))
        self.game_notice.setVisible(not linked)

    # ---- installing -----------------------------------------------------------------

    def set_result(self, variant='', title='', text=''):
        if self.result is not None:
            self.result.setParent(None)
            self.result.deleteLater()
            self.result = None
        if variant:
            self.result = Banner(breakable(title), breakable(text), variant)
            self.result_box.addWidget(self.result)

    def result_text(self):
        return '' if self.result is None else (self.result.title.text() + '\n' + self.result.text.text()).strip()

    def install(self):
        hit, v = self.shown_hit, self.current_version()
        if hit is None or v is None or self.service.busy:
            return
        if not self.service.ready():
            self.set_result('warning', tr('Link your Deadlock folder on the Home page first.'))
            return
        self.set_result()
        self.act_text.setText(tr('Downloading and checking {0} {1}… nothing is installed yet.').format(hit.mod.name, v.version))
        self.install_bar.set_unknown()
        self.install_cancel.show()
        self.activity.show()
        self.service.prepare(hit.repository.source.id, hit.mod.id, v.version.text, self.prepared, self.install_failed)
        self.sync_install()

    def prepared(self, plan):
        self.activity.hide()
        dialog = InstallReview(plan, self)
        if dialog.exec() != InstallReview.Accepted:
            self.service.discard(plan)
            self.set_result('info', tr('Cancelled. Nothing was changed.'))
            return
        self.act_text.setText(tr('Installing {0} {1}…').format(plan.mod_name, plan.version))
        self.install_bar.set_unknown()
        self.install_cancel.hide()
        self.activity.show()
        self.service.commit(plan, dialog.acknowledged, self.installed, self.install_failed)

    def installed(self, mod):
        self.activity.hide()
        self.set_result('success', tr('Installed {0} {1}.').format(mod.name, mod.version), tr('Every file was re-checked after copying: {0}.').format(', '.join(mod.file_names())))
        Toast(self, tr('Installed {0}.').format(mod.name))
        self.reload()

    def install_failed(self, message, code):
        self.activity.hide()
        lead, _, detail = failure_text(code, message).partition('\n')
        self.set_result('danger', lead, detail or tr('Nothing was changed.'))
        self.sync_install()

    def show_install_progress(self, done, total):
        if not self.activity.isVisibleTo(self) or not total:
            return
        self.install_bar.set_known(int(done * 1000 / total), 1000)
        self.act_text.setText(tr('Downloading… {0} of {1}').format(size_text(done), size_text(total)))

    def ask(self, title, text, action):
        return confirm(self, title, text, action, danger=True)

    def uninstall(self):
        hit = self.shown_hit
        if hit is None or self.service.busy:
            return
        have = self.installed_map().get(self.current)
        if have is None:
            return
        if not self.ask(tr('Remove {0}?').format(have.name), tr('Its files are moved to the Toolbox recovery folder, not deleted.'), tr('Remove')):
            return
        self.service.operate('uninstall', (have.repository_id, have.mod_id),
                             lambda _: (self.set_result('success', tr('Removed {0}.').format(have.name)), self.reload()), self.install_failed)

    def open_source(self):
        hit = self.shown_hit
        if hit:
            url = hit.mod.source_url or hit.mod.homepage
            if url:
                QDesktopServices.openUrl(QUrl(url))

    # ---- pictures (only when asked) -----------------------------------------------------

    def clear_pictures(self):
        self._token += 1
        while self.pictures_box.count():
            item = self.pictures_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.picture_count = 0

    def toggle_pictures(self):
        hit = self.shown_hit
        if hit is None:
            return
        self.pictures_on = not self.pictures_on
        self.pictures_button.setText(tr('Hide pictures') if self.pictures_on else tr('Show pictures'))
        self.clear_pictures()
        if self.pictures_on:
            token = self._token
            for url in hit.mod.screenshots[:IMAGES_SHOWN]:
                job = Job(lambda url=url: self.service.transport.get(url, max_bytes=MAX_IMAGE_BYTES).body)
                job.signals.result.connect(lambda data, token=token, url=url: self.picture_loaded(token, url, data))
                QThreadPool.globalInstance().start(job)

    def picture_loaded(self, token, url, data):
        if token != self._token or not data:
            return
        image = QImage.fromData(data)
        if image.isNull() or image.width() > MAX_IMAGE_SIDE or image.height() > MAX_IMAGE_SIDE:
            return
        label = mark(QLabel(), 'ModPicture')
        label.setAlignment(Qt.AlignCenter)
        label.setPixmap(QPixmap.fromImage(image).scaledToWidth(180, Qt.SmoothTransformation))
        label.setToolTip(url)
        self.pictures_box.addWidget(label, self.picture_count // 2, self.picture_count % 2)
        self.picture_count += 1


def day_text_of(published):
    """The date part of an ISO time such as '2026-11-10T09:00:00Z', or a dash."""
    return (published or '')[:10] or '—'
