"""Mods > Browse: every Deadlock mod on GameBanana, from a searchable copy kept on this computer.

Built from the redesign components (`deadlock_fps/shell/components.py`) to the spec in
vault/Design/New Design/05 Screens.md. Browsing never changes the game. The catalogue is downloaded only when the user
asks (the cost is stated first), a mod's own page is fetched only when its card is pressed, and every word that came from
GameBanana is shown as plain text. Installing goes through the same engine as the Mod Hub: the file is downloaded to a
private folder, checked and inspected, a review shows what would change, and only the user's confirmation copies anything
into the game. The page only draws; the engines (`store/`, `store_service.py`, `mod_service.py`, `installer/`) are unchanged.
"""
import time
from datetime import datetime

from PySide6.QtCore import QEvent, Qt, QThreadPool, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QFont, QImage, QPixmap
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from ..hub_ui import failure_text as install_failure_text
from ..i18n import tr
from ..installer import InstallError
from ..repos import Trust
from ..ui_common import Job
from ..shell import theme
from ..shell.components import (breakable, Badge, Banner, Button, Card, Checkbox, Chip, Dialog, EmptyState, KeyValue, List, ListRow, ModCard, ProgressBar,
                                SearchField, Select, Sheet, Skeleton, Toast, mark, text_label)
from ..store.install import STORE_ID, file_format, mod_id_of
from ..ui_common import ltr, size_text

ROW_LIMIT = 300                 # most cards the page will ever build; narrower filters reach the rest
PAGE_SIZE = 48                  # cards built at first and with every "Show more"
CARD_MIN = 160                  # a card is never narrower; the grid has as many columns as fit (three at the smallest window)
GAP = 16
SEARCH_MIN = 180                 # the narrowest the search box is allowed to get before the three choices move to a row of their own
MAX_IMAGE_BYTES = 3 * 1024 * 1024
MAX_IMAGE_SIDE = 4096
PROFILE_CACHE = 60
IMAGES_SHOWN = 4


def failure_text(code, message):
    """One plain sentence for an engine failure, with the engine's own detail after it."""
    lead = {
        'rate-limited': tr('GameBanana asked us to slow down. Your progress is saved; try again in a few minutes.'),
        'network': tr('Could not reach GameBanana.'),
        'bad-response': tr('GameBanana sent something this version does not understand.'),
        'store': tr('The local catalogue could not be read or written.'),
        'not-found': tr('GameBanana has no such page any more.'),
        'too-large': tr('GameBanana sent more data than expected, so it was ignored.'),
    }.get(code, tr('Something went wrong.'))
    return lead if code == 'rate-limited' else lead + '\n' + message


def day_text(stamp):
    try:
        return datetime.fromtimestamp(stamp).strftime('%Y-%m-%d') if stamp else '—'
    except (ValueError, OSError, OverflowError):
        return '—'


def ago_text(stamp, now=None):
    """'just now', '5 minutes ago', '2 hours ago', '3 days ago'. No direction marks: a sentence that starts with one is laid out left to right, even in Arabic."""
    if not stamp:
        return tr('never')
    seconds = (time.time() if now is None else now) - stamp
    if seconds < 90:
        return tr('just now')
    minutes = seconds / 60
    if minutes < 90:
        return tr('{0} minutes ago').format(round(minutes))
    hours = minutes / 60
    if hours < 36:
        return tr('{0} hours ago').format(round(hours))
    return tr('{0} days ago').format(round(hours / 24))


def plural(n, one, many):
    """'1 mod' or '5 mods': the caller passes both sentences through tr(), each with {0} for the number."""
    return (one if n == 1 else many).format(n)


def mono(label):
    """Technical text (paths, checksums): the monospace face, always left to right."""
    font = QFont()
    font.setFamilies(theme.current().families('font.family.mono'))
    label.setFont(font)
    label.setLayoutDirection(Qt.LeftToRight)
    return label


def trust_badge(trust):
    """The label a source carries. Only the project's own source is ever reviewed (vault: Trust System)."""
    if trust in (Trust.OFFICIAL, Trust.VERIFIED):
        return Badge(tr('Official') if trust == Trust.OFFICIAL else tr('Verified'), 'success')
    if trust == Trust.COMMUNITY:
        return Badge(tr('Community'), 'neutral')
    return Badge(tr('Not reviewed'), 'warning')


class InstallReview(Dialog):
    """What would change, and from whom. The Install button stays off until every required acknowledgement is given."""

    def __init__(self, plan, parent=None):
        update = plan.action == 'update'
        super().__init__(tr('Review before updating') if update else tr('Review before installing'), variant='review',
                         action=tr('Update') if update else tr('Install'), cancel=tr('Cancel'), parent=parent)
        self.plan = plan
        t = theme.current()
        facts = KeyValue()
        facts.form.setVerticalSpacing(t.px('space.2'))
        facts.add(tr('Mod'), (tr('{0}, from {1} to {2}').format(plan.mod_name, plan.replaces, plan.version) if update else '%s %s' % (plan.mod_name, plan.version)).strip())
        source = QWidget()
        row = QHBoxLayout(source)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(t.px('space.2'))
        row.addWidget(text_label(plan.repository_name, 'KeyValueValue', wrap=False))
        self.trust = trust_badge(Trust(plan.trust))
        row.addWidget(self.trust)
        row.addStretch(1)
        facts.add(tr('From'), source)
        if plan.verified:
            check = Badge(tr('Matches the published SHA-256'), 'success')
        elif plan.md5_verified:
            check = Badge(tr('Matches the published checksum (MD5)'), 'warning')
        else:
            check = Badge(tr('No checksum was published'), 'warning')
        self.check = check
        holder = QWidget()
        holder_row = QHBoxLayout(holder)
        holder_row.setContentsMargins(0, 0, 0, 0)
        holder_row.addWidget(check)
        holder_row.addStretch(1)
        facts.add(tr('File check'), holder)
        self.body.addWidget(facts)
        if not plan.verified:
            self.body.addWidget(text_label(tr('This catches a damaged download, but not one that was deliberately changed.') if plan.md5_verified
                                           else tr('No SHA-256 was published, so the file could not be checked against the publisher.'), 'Muted'))
        digest = mono(text_label('SHA-256 ' + plan.actual_sha256, 'Muted', wrap=False))
        digest.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.body.addWidget(digest)

        self.body.addSpacing(t.px('space.2'))
        self.body.addWidget(text_label(tr('What will be added to the game'), 'RowTitle'))
        files = List()
        for f in plan.files:
            size = text_label(ltr(size_text(f.size)), 'Muted', wrap=False)
            item = ListRow('game/citadel/addons/' + f.name, f.source or tr('(the download itself)'), control=size)
            mono(item.title)
            files.add(item)
        if len(plan.files) > 4:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setFixedHeight(4 * 62)
            scroll.setWidget(files)
            self.body.addWidget(scroll)
        else:
            self.body.addWidget(files)
        self.body.addWidget(text_label(tr('Goes to game/citadel/addons. Lower pak numbers win when two mods provide the same file.'), 'Muted'))
        if plan.removed:
            self.body.addWidget(text_label(tr('No longer provided by this version (moved to the backup): ') + ', '.join(plan.removed), 'Muted'))
        for blocker in plan.blockers:
            self.body.addWidget(Banner(blocker, '', 'danger'))
        for warning in plan.warnings:
            self.body.addWidget(Banner(warning, '', 'warning'))
        self.ack = Checkbox(tr('I understand these warnings and want to install anyway'))
        self.ack.setVisible(plan.requires_ack and plan.can_install)
        self.ack.toggled.connect(self.refresh)
        self.body.addWidget(self.ack)
        self.body.addWidget(text_label(tr('Nothing has been changed yet. The game must be closed. A backup of anything replaced is kept, and the installation is undone automatically if verification fails.'), 'Muted'))
        self.install_button = self.action_button
        self.refresh()

    def refresh(self, *_):
        self.install_button.setEnabled(self.plan.can_install and (not self.plan.requires_ack or self.ack.isChecked()))

    @property
    def acknowledged(self):
        return self.ack.isChecked() or not self.plan.requires_ack


class BrowsePage(QWidget):
    openRequested = Signal(str)             # an address such as 'mods.installed'
    gameRequired = Signal()                 # the user asked to link the game (the window brings up Home's link card)

    def __init__(self, service, mods=None, parent=None):
        super().__init__(parent)
        mark(self, 'BrowsePage')
        self.service = service
        self.auto_pictures = False          # Settings > Advanced > Show mod pictures: show them when a sheet opens (off by default: each one is a request to GameBanana)
        self.mods = mods                    # the ModService that installs; without it the page only browses
        self.current = None                 # id of the mod whose sheet is open
        self.subject = None                 # its listing
        self.profile = None                 # its page, once it has arrived
        self.rows = ()                      # what the filters found (at most ROW_LIMIT)
        self.total = 0                      # how many the filters match in all
        self.cards = {}                     # mod id → ModCard
        self.card_order = []
        self.built = 0
        self.columns = 0
        self.message = ''                   # the last thing a download of the list said, for the record
        self.banner = None
        self.result = None                  # the banner in the sheet that says what an install did
        self.pictures_on = False
        self._building = True               # filters fire signals while the page is still being assembled
        self._token = 0                     # screenshots
        self._profiles = {}                 # session cache, so going back to a mod costs nothing
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
        self.column.addWidget(self.build_progress())
        self.column.addWidget(self.build_partial())
        self.column.addWidget(self.build_first_run())
        self.unavailable = EmptyState('warn', tr('The local catalogue is unavailable.'), '', variant='danger')
        self.column.addWidget(self.unavailable)
        self.skeletons = QWidget()
        skeleton_row = QHBoxLayout(self.skeletons)
        skeleton_row.setContentsMargins(0, 0, 0, 0)
        skeleton_row.setSpacing(GAP)
        for _ in range(3):
            skeleton_row.addWidget(Skeleton(height=150))
        self.column.addWidget(self.skeletons)
        self.column.addWidget(self.build_filters())
        self.empty_filter = EmptyState('search', tr('No mods match your search'), tr('Try fewer words or another filter.'), Button(tr('Clear the filter'), 'secondary'))
        self.empty_filter.button.clicked.connect(self.clear_filters)
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
        service.progress.connect(self.show_progress)
        service.busyChanged.connect(lambda _: self.show_state())
        if mods is not None:
            mods.progress.connect(self.show_install_progress)
            mods.busyChanged.connect(self.sync_install)
            mods.changed.connect(self.sync_install)
            mods.changed.connect(self.reload)          # the "Installed" marks on the cards
        self._building = False
        self.reload()

    # ---- construction ---------------------------------------------------------

    def build_progress(self):
        """Work the user started: how far it is, and a way to stop it."""
        self.progress_card = Card()
        head = QHBoxLayout()
        self.progress_title = text_label(tr('Getting the mod list…'), 'CardTitle')
        head.addWidget(self.progress_title, 1)
        self.stop_button = Button(tr('Stop'), 'secondary', 'sm')
        self.stop_button.clicked.connect(self.service.cancel)
        head.addWidget(self.stop_button)
        self.progress_card.body.addLayout(head)
        self.progress_text = text_label('', 'CardText')
        self.progress_card.body.addWidget(self.progress_text)
        self.progress_bar = ProgressBar()
        self.progress_bar.set_unknown()
        self.progress_card.body.addWidget(self.progress_bar)
        self.progress_note = text_label('', 'Muted')
        self.progress_card.body.addWidget(self.progress_note)
        self.progress_card.hide()
        return self.progress_card

    def build_partial(self):
        """An interrupted first download: what is saved, and a way to continue."""
        self.partial = Banner('', '', 'info')
        self.continue_button = Button(tr('Continue the download'), 'primary', 'sm')
        self.continue_button.clicked.connect(self.start_sync)
        self.partial.add_action(self.continue_button)
        self.partial.hide()
        return self.partial

    def build_first_run(self):
        self.first_button = Button(tr('Get the mod list'), 'primary', 'lg', icon='download')
        self.first_button.clicked.connect(self.start_sync)
        self.first_run = EmptyState('box', tr('Get the mod list first'), tr('Downloads the list of every Deadlock mod on GameBanana, once: about 2 minutes and 26 MB. After that only new and changed mods are fetched. Nothing is installed.'),
                                    self.first_button)
        self.first_run.layout().setContentsMargins(0, theme.current().px('space.8'), 0, 0)
        self.first_run.hide()
        return self.first_run

    def build_filters(self):
        t = theme.current()
        self.filters = QWidget()
        box = QVBoxLayout(self.filters)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(t.px('space.3'))
        self.top = QGridLayout()                                  # the search box, then the three choices: one row, or two when the window is narrow
        self.top.setHorizontalSpacing(t.px('space.2'))
        self.top.setVerticalSpacing(t.px('space.2'))
        self.search = SearchField(tr('Search mods, heroes, authors'))
        self.query = self.search.edit
        self.query.setAccessibleName(tr('Search the store'))
        self.query.textChanged.connect(self.filter_changed)
        self.category = Select()
        self.category.setAccessibleName(tr('Type'))
        self.subcategory = Select()
        self.subcategory.setAccessibleName(tr('Hero'))
        self.sort = Select()
        self.sort.setAccessibleName(tr('Order'))
        for caption, value in ((tr('Recently updated'), 'updated'), (tr('Newest'), 'newest'), (tr('Name'), 'name')):
            self.sort.addItem(caption, value)
        self.choices = QWidget()
        choices = QHBoxLayout(self.choices)
        choices.setContentsMargins(0, 0, 0, 0)
        choices.setSpacing(t.px('space.2'))
        for select in (self.category, self.subcategory, self.sort):
            select.setMinimumWidth(130)
            select.currentIndexChanged.connect(self.filter_changed)
            choices.addWidget(select)
        self.top_wide = None
        self.place_top(True)
        box.addLayout(self.top)
        self.line = QGridLayout()                                 # chips at the leading side; the count and the check button share the row when there is room, else take a row of their own
        self.line.setHorizontalSpacing(t.px('space.2'))
        self.line.setVerticalSpacing(t.px('space.2'))
        self.chips = QWidget()
        chips = QHBoxLayout(self.chips)
        chips.setContentsMargins(0, 0, 0, 0)
        chips.setSpacing(t.px('space.2'))
        self.hide_outdated = Chip(tr('Hide outdated'))
        self.hide_outdated.setChecked(True)
        self.adult = Chip(tr('Show adult content'))
        for chip in (self.hide_outdated, self.adult):
            chip.toggled.connect(self.filter_changed)
            chips.addWidget(chip)
        chips.addStretch(1)
        self.meta = QWidget()
        meta = QHBoxLayout(self.meta)
        meta.setContentsMargins(0, 0, 0, 0)
        meta.setSpacing(t.px('space.2'))
        self.count_label = text_label('', 'Muted')
        meta.addWidget(self.count_label, 1)
        self.check_button = Button(tr('Check for new mods'), 'ghost', 'sm', icon='refresh')
        self.check_button.clicked.connect(self.start_sync)
        meta.addWidget(self.check_button)
        self.meta_wide = None
        self.place_meta(True)
        box.addLayout(self.line)
        return self.filters

    def build_sheet(self):
        """The mod's sheet: the file and the Install button first, then what to know before pressing it."""
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
        self.file_label = text_label(tr('File'), 'FieldLabel')
        block.addWidget(self.file_label)
        self.file_pick = Select()
        self.file_pick.setAccessibleName(tr('File to install'))
        self.file_pick.currentIndexChanged.connect(self.file_changed)
        block.addWidget(self.file_pick)
        self.install_button = Button(tr('Install'), 'primary', 'lg', icon='download')
        self.install_button.clicked.connect(self.install)
        block.addWidget(self.install_button)
        self.d_status = text_label('', 'Muted')
        block.addWidget(self.d_status)
        self.game_notice = Banner(tr('Link your game to install mods'), tr('Toolbox needs to know where Deadlock is installed.'), 'warning')
        self.game_notice.add_action(self.link_button())
        block.addWidget(self.game_notice)
        self.activity = QWidget()
        act = QVBoxLayout(self.activity)
        act.setContentsMargins(0, 0, 0, 0)
        act.setSpacing(t.px('space.1'))
        self.act_text = text_label('', 'CardText')
        act.addWidget(self.act_text)
        line = QHBoxLayout()
        self.install_bar = ProgressBar()
        self.install_bar.set_unknown()
        line.addWidget(self.install_bar, 1)
        self.install_cancel = Button(tr('Cancel'), 'ghost', 'sm')
        self.install_cancel.clicked.connect(self.cancel_install)
        line.addWidget(self.install_cancel)
        act.addLayout(line)
        self.activity.hide()
        block.addWidget(self.activity)
        self.result_box = QVBoxLayout()
        block.addLayout(self.result_box)
        body.addWidget(self.install_block)
        self.trust_notice = Banner(tr('Not reviewed'), tr('From GameBanana. Made by the community; Toolbox has not reviewed it.'), 'warning')
        body.addWidget(self.trust_notice)
        self.facts = KeyValue()
        self.facts.form.setVerticalSpacing(t.px('space.2'))
        body.addWidget(self.facts)
        self.d_description = text_label('', 'CardText')
        self.d_description.setTextInteractionFlags(Qt.TextSelectableByMouse)
        body.addWidget(self.d_description)
        self.pictures_box = QGridLayout()
        self.pictures_box.setSpacing(t.px('space.2'))
        body.addLayout(self.pictures_box)
        actions = QVBoxLayout()                                   # one under the other: side by side they would not fit a narrow sheet at a large text size
        actions.setSpacing(t.px('space.2'))
        self.open_button = Button(tr('Open on GameBanana'), 'secondary', 'sm', icon='ext')
        self.open_button.clicked.connect(self.open_page)
        actions.addWidget(self.open_button, 0, Qt.AlignLeading)
        self.pictures_button = Button(tr('Show pictures'), 'ghost', 'sm', icon='eye')
        self.pictures_button.clicked.connect(self.toggle_pictures)
        actions.addWidget(self.pictures_button, 0, Qt.AlignLeading)
        body.addLayout(actions)
        self.installed_button = Button(tr('Show in Installed'), 'ghost')
        self.installed_button.clicked.connect(lambda: self.openRequested.emit('mods.installed'))
        self.installed_button.hide()
        body.addWidget(self.installed_button, 0, Qt.AlignLeading)
        self.d_note = text_label(tr('Files are downloaded to a private folder and inspected first. Nothing in your game changes until you confirm. GameBanana publishes MD5 only, which catches a damaged download but not a deliberately changed one.'), 'Muted')
        body.addWidget(self.d_note)
        body.addStretch(1)

    def link_button(self):
        button = Button(tr('Link the game'), 'secondary', 'sm')
        button.clicked.connect(self.gameRequired.emit)
        return button

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
        self.show_state()
        self.arrange()
        QTimer.singleShot(0, self.arrange)               # once the widgets are polished their real minimum sizes are known

    def place_top(self, wide):
        """The search box and the three choices: side by side (wide) or the choices on a row below (narrow)."""
        if wide == self.top_wide:
            return
        self.top_wide = wide
        for widget in (self.search, self.choices):
            self.top.removeWidget(widget)
        if wide:
            self.top.addWidget(self.search, 0, 0)
            self.top.addWidget(self.choices, 0, 1)
            self.top.setColumnStretch(0, 1)
            self.top.setColumnStretch(1, 0)
        else:
            self.top.addWidget(self.search, 0, 0, 1, 2)
            self.top.addWidget(self.choices, 1, 0, 1, 2)
            self.top.setColumnStretch(0, 1)
            self.top.setColumnStretch(1, 0)

    def place_meta(self, wide):
        """The count and the check button: in the chips' row (wide) or on a row below (narrow)."""
        if wide == self.meta_wide:
            return
        self.meta_wide = wide
        for widget in (self.chips, self.meta):
            self.line.removeWidget(widget)
        self.line.addWidget(self.chips, 0, 0)
        if wide:
            self.line.addWidget(self.meta, 0, 1)
            self.line.setColumnStretch(0, 0)
            self.line.setColumnStretch(1, 1)
            self.count_label.setAlignment(Qt.AlignTrailing | Qt.AlignVCenter)
        else:
            self.line.addWidget(self.meta, 1, 0, 1, 2)
            self.line.setColumnStretch(0, 1)
            self.line.setColumnStretch(1, 0)
            self.count_label.setAlignment(Qt.AlignLeading | Qt.AlignVCenter)

    def arrange(self):
        """As many columns as fit; cards keep their order and are only re-seated."""
        width = self.scroll.viewport().width() - self.column.contentsMargins().right()
        need = self.chips.minimumSizeHint().width() + self.meta.minimumSizeHint().width() + self.line.horizontalSpacing()
        self.place_meta(width >= need)
        search = max(round(SEARCH_MIN * theme.current().scale / 100), self.search.minimumSizeHint().width())
        self.place_top(width >= search + self.choices.minimumSizeHint().width() + self.top.horizontalSpacing())
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

    # ---- what is on screen ----------------------------------------------------------

    def info(self):
        return self.service.summary()

    def show_state(self):
        ready = self.service.ready
        count = self.service.catalog.count() if ready else 0
        syncing = self.service.busy
        info = self.info()
        has_list = ready and count > 0
        self.unavailable.setVisible(not ready)
        if not ready:
            self.unavailable.text.setText(self.service.error)
            self.unavailable.text.setVisible(bool(self.service.error))
        resumable = info['resumable']
        self.first_run.setVisible(ready and count == 0 and not syncing)
        self.first_button.setText(tr('Continue the download') if resumable else tr('Get the mod list'))
        self.skeletons.setVisible(ready and count == 0 and syncing)
        self.progress_card.setVisible(syncing)
        self.progress_title.setText(tr('Getting the mod list…') if info['first_download'] else tr('Checking for new mods…'))
        self.progress_note.setText(tr('You can keep using Toolbox. Stop keeps everything fetched so far, and the download continues where it stopped next time.') if info['first_download']
                                   else tr('You can keep using Toolbox. Stop keeps everything fetched so far.'))
        interrupted = has_list and info['first_download'] and not syncing
        self.partial.setVisible(interrupted)
        if interrupted:
            self.partial.title.setText(tr('The first download was interrupted. {0} mods are saved; continue where it stopped.').format(count))
        self.filters.setVisible(has_list)
        self.check_button.setVisible(has_list and not info['first_download'] and not syncing)
        self.check_button.setEnabled(not syncing)
        found = bool(self.rows)
        self.empty_filter.setVisible(has_list and not found)
        self.grid_host.setVisible(has_list and found)
        self.more.setVisible(has_list and self.built < len(self.rows))
        trailing = thousands(self.total)
        stamp = info['last']
        self.count_label.setText(tr('{0} mods · list checked {1}').format(trailing, ago_text(stamp)) if stamp else tr('{0} mods').format(trailing))
        capped = has_list and self.total > len(self.rows) and self.built >= len(self.rows)
        self.note.setText(tr('Showing the first {0} of {1}. Narrow the search to see the rest.').format(ltr(len(self.rows)), ltr(self.total)) if capped else '')
        self.note.setVisible(bool(self.note.text()))

    def set_notice(self, variant='', title='', text='', retry=False):
        """One banner at the top about the list; an empty `variant` clears it."""
        if self.banner is not None:
            self.banner.setParent(None)
            self.banner.deleteLater()
            self.banner = None
        if variant:
            self.banner = Banner(breakable(title), breakable(text), variant)
            if retry:
                again = Button(tr('Try again'), 'secondary', 'sm')
                again.clicked.connect(self.start_sync)
                self.banner.add_action(again)
            self.notice.addWidget(self.banner)

    def notice_text(self):
        return '' if self.banner is None else (self.banner.title.text() + '\n' + self.banner.text.text()).strip()

    # ---- the catalogue and its download -------------------------------------------

    def start_sync(self):
        if self.service.busy or not self.service.ready:
            return
        self.message = ''
        self.set_notice()
        self.progress_bar.set_unknown()
        self.progress_text.setText(tr('Starting…'))
        if self.service.start_sync(self.synced, self.sync_failed):
            self.show_state()

    def show_progress(self, done, total):
        self.progress_bar.set_known(min(done, max(total, 1)), max(total, 1))
        self.progress_text.setText(tr('Page {0} of about {1}.').format(ltr(done), ltr(total)))

    def synced(self, report):
        if report.stopped == 'rate-limited':
            self.message = failure_text('rate-limited', '')
            self.set_notice('warning', self.message)
        elif report.stopped == 'cancelled':
            self.message = tr('Stopped. Everything fetched so far is saved.')
            self.set_notice('info', self.message)
        elif report.stopped == 'page-limit':
            self.message = tr('Stopped at the page limit; the catalogue is only partly downloaded.')
            self.set_notice('warning', self.message)
        elif report.mode == 'crawl':
            self.message = tr('Catalogue downloaded: {0} listings.').format(report.fetched) + (tr(' {0} malformed entries were skipped.').format(report.skipped) if report.skipped else '')
            Toast(self, self.message)
        else:
            self.message = tr('Checked {0} recent listings.').format(report.fetched)
            Toast(self, self.message)
        self.reload()

    def sync_failed(self, message, code):
        text = failure_text(code, message)
        lead, _, detail = text.partition('\n')
        self.message = text
        self.set_notice('danger', lead, detail, retry=True)
        self.reload()

    # ---- the list ------------------------------------------------------------------

    def fill_facets(self):
        catalog = self.service.catalog
        flags = {'include_nsfw': self.adult.isChecked(), 'include_obsolete': not self.hide_outdated.isChecked()}
        current = self.category.currentData()
        self.category.blockSignals(True)
        self.category.clear()
        self.category.addItem(tr('All types'), '')
        for name, count in catalog.categories(**flags):
            self.category.addItem('%s (%s)' % (name, ltr(count)), name)
        self.category.setCurrentIndex(max(0, self.category.findData(current)))
        self.category.blockSignals(False)
        chosen = self.category.currentData() or ''
        current = self.subcategory.currentData()
        self.subcategory.blockSignals(True)
        self.subcategory.clear()
        self.subcategory.addItem(tr('All heroes'), '')
        if chosen:
            for name, count in catalog.subcategories(chosen, **flags):
                self.subcategory.addItem('%s (%s)' % (name, ltr(count)), name)
        self.subcategory.setCurrentIndex(max(0, self.subcategory.findData(current)))
        self.subcategory.setEnabled(self.subcategory.count() > 1)
        self.subcategory.blockSignals(False)

    def filter_changed(self, *_):
        self.reload()

    def clear_filters(self):
        for box in (self.query, self.category, self.subcategory, self.adult, self.hide_outdated):
            box.blockSignals(True)
        self.query.clear()
        self.category.setCurrentIndex(0)
        self.subcategory.setCurrentIndex(0)
        self.adult.setChecked(False)
        self.hide_outdated.setChecked(True)
        for box in (self.query, self.category, self.subcategory, self.adult, self.hide_outdated):
            box.blockSignals(False)
        self.reload()

    def reload(self, *_):
        if self._building:
            return
        if not self.service.ready:
            self.rows, self.total = (), 0
            self.clear_cards()
            self.show_state()
            return
        self.fill_facets()
        result = self.service.catalog.query(text=self.query.text(), category=self.category.currentData() or '', subcategory=self.subcategory.currentData() or '',
                                            include_nsfw=self.adult.isChecked(), include_obsolete=not self.hide_outdated.isChecked(),
                                            sort=self.sort.currentData() or 'updated', limit=ROW_LIMIT)
        self.rows, self.total = result.rows, result.total
        self.clear_cards()
        self.build_cards(PAGE_SIZE)
        self.show_state()
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
        installer = self.installer_or_none()
        end = min(len(self.rows), self.built + count)
        for s in self.rows[self.built:end]:
            have = installer is not None and installer.get(STORE_ID, mod_id_of(s.id)) is not None
            line = ' · '.join(part for part in (s.subcategory or s.category, s.author) if part)      # a skin is "for" a hero; HUDs and maps have no hero
            name = s.name + (tr(' (18+)') if s.nsfw else '')
            card = ModCard(name, line, have)
            card.setAccessibleName('%s, %s' % (name, line))
            card.set_selected(s.id == self.current)
            card.clicked.connect(lambda ident=s.id: self.open_mod(ident))
            self.cards[s.id] = card
            self.card_order.append(card)
        self.built = end
        self.arrange()

    def show_more(self):
        self.build_cards(PAGE_SIZE)
        self.show_state()

    # ---- the sheet -------------------------------------------------------------------

    def selected(self):
        return self.subject

    def open_mod(self, ident):
        s = next((r for r in self.rows if r.id == ident), None) or self.service.catalog.get(ident)
        if s is None:
            return
        self.current, self.subject, self.profile = s.id, s, None
        for key, card in self.cards.items():
            card.set_selected(key == s.id)
        self.set_result()
        self.pictures_on = False
        self.pictures_button.setText(tr('Show pictures'))
        self.clear_pictures()
        self.sheet.title.setText(breakable(s.name + (tr(' (18+)') if s.nsfw else '')))
        self.d_by.setText(breakable(tr('by {0}').format(s.author or tr('unknown author'))))
        while self.d_badges.count():
            item = self.d_badges.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for label in (s.category, s.subcategory):
            if label:
                self.d_badges.addWidget(Badge(label, 'neutral'))
        if s.nsfw:
            self.d_badges.addWidget(Badge(tr('18+'), 'warning'))
        self.d_badges.addStretch(1)
        self.open_button.setEnabled(True)
        self.pictures_button.setVisible(bool(s.images))
        cached = self._profiles.get(s.id)
        self.file_pick.blockSignals(True)
        self.file_pick.clear()
        self.file_pick.blockSignals(False)
        if cached:
            self.fill_profile(cached)
        else:
            self.d_description.setText(tr('Loading the mod page…'))
            self.refresh_facts()
            self.sync_install()
            self.service.fetch_profile(s.id, lambda profile, ident=s.id: self.profile_arrived(ident, profile),
                                       lambda message, code, ident=s.id: self.profile_failed(ident, message, code))
        self.sheet.open_sheet()
        if self.auto_pictures and s.images and not self.pictures_on:      # Settings > Advanced: the user chose to see pictures without pressing the button
            self.toggle_pictures()

    def sheet_closed(self):
        self._token += 1                              # pictures still arriving are dropped
        self.current, self.subject, self.profile = None, None, None
        for card in self.cards.values():
            card.set_selected(False)

    def close_sheet(self):
        self.sheet.close_sheet()

    def profile_arrived(self, ident, profile):
        if len(self._profiles) >= PROFILE_CACHE:
            self._profiles.pop(next(iter(self._profiles)))
        self._profiles[ident] = profile
        if ident == self.current:
            self.fill_profile(profile)

    def profile_failed(self, ident, message, code):
        if ident == self.current:
            self.d_description.setText(tr('The mod page could not be loaded.'))
            self.profile = None
            self.refresh_facts()
            self.sync_install()
            lead, _, detail = failure_text(code, message).partition('\n')
            self.set_result('danger', lead, detail)

    def fill_profile(self, profile):
        self.profile = profile
        self.d_description.setText(breakable(profile.text) if profile.text else tr('The author gave no description.'))
        keep = self.file_pick.currentData()
        self.file_pick.blockSignals(True)
        self.file_pick.clear()
        for f in profile.files:
            self.file_pick.addItem('%s · %s' % (f.name, size_text(f.size)) + ('' if file_format(f)[0] else ' · ' + tr('not supported')), f.id)
        first_supported = next((i for i, f in enumerate(profile.files) if file_format(f)[0]), 0)
        self.file_pick.setCurrentIndex(self.file_pick.findData(keep) if self.file_pick.findData(keep) >= 0 else first_supported)
        self.file_pick.blockSignals(False)
        self.refresh_facts()
        self.sync_install()

    def file_changed(self, *_):
        self.refresh_facts()
        self.sync_install()

    def refresh_facts(self):
        """The facts of the open mod: its dates and counts, and what GameBanana says about the chosen file."""
        self.facts.clear()
        s = self.subject
        if s is None:
            return
        if s.version:
            self.facts.add(tr('Version'), ltr(s.version))
        self.facts.add(tr('Updated'), ltr(day_text(s.modified)))
        file = self.selected_file()
        if file is not None:
            self.facts.add(tr('File check'), tr('Checksum published') if file.md5 else tr('No checksum published'))
            if file.md5:
                self.facts.add(tr('MD5'), mono(text_label(file.md5, 'KeyValueValue', wrap=False)))
            self.facts.add(tr('Virus scan'), tr('Clean, says GameBanana') if file.av_clean else (tr('Flagged, says GameBanana') if file.av_clean is False else tr('Not scanned')))
        if self.profile is not None:
            p = self.profile.submission
            self.facts.add(tr('Likes'), ltr('{:,}'.format(p.likes)))
            self.facts.add(tr('Downloads'), ltr('{:,}'.format(p.downloads)))
            self.facts.add(tr('Licence'), self.profile.license or tr('not stated'))

    # ---- installing -----------------------------------------------------------------

    @staticmethod
    def unsupported_text(code):
        return {'rar': tr('This file is a .rar archive. Toolbox can only unpack .zip archives and .vpk files so far.'),
                '7z': tr('This file is a .7z archive. Toolbox can only unpack .zip archives and .vpk files so far.')}.get(code, tr('Toolbox can only install .zip archives and .vpk files so far.'))

    def selected_file(self):
        if self.profile is None:
            return None
        ident = self.file_pick.currentData()
        return next((f for f in self.profile.files if f.id == ident), None)

    def installer_or_none(self):
        """The installer of the linked game, or None (no game linked, or a recovery problem the Installed page reports)."""
        if self.mods is None:
            return None
        try:
            return self.mods.installer()
        except InstallError:
            return None

    def installed_record(self):
        installer = self.installer_or_none()
        if installer is None or self.current is None:
            return None
        return installer.get(STORE_ID, mod_id_of(self.current))

    def sync_install(self, *_):
        shown = self.mods is not None and self.current is not None
        self.install_block.setVisible(shown)
        self.installed_button.setVisible(False)
        if not shown:
            return
        file = self.selected_file()
        have = self.installed_record()
        linked = self.mods.ready()
        status, can = '', False
        if self.profile is not None:
            if file is None:
                status = tr('This mod has no downloadable files.')
            else:
                kind, code = file_format(file)
                can = bool(kind) and not self.mods.busy and linked
                status = '' if kind else self.unsupported_text(code)
        if have:
            status = (status + '\n' if status else '') + tr('Installed: {0}.').format(have.version)
        self.install_button.setText(tr('Reinstall') if have else tr('Install'))
        self.install_button.setEnabled(can)
        self.game_notice.setVisible(not linked)
        self.installed_button.setVisible(have is not None)
        self.d_status.setText(status)
        self.d_status.setVisible(bool(status))
        self.file_pick.setVisible(self.profile is not None and self.file_pick.count() > 0)
        self.file_label.setVisible(self.file_pick.isVisibleTo(self.install_block))

    def set_result(self, variant='', title='', text=''):
        """What an install did, as a banner under the Install button. An empty `variant` clears it."""
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
        s, file = self.selected(), self.selected_file()
        if self.mods is None or s is None or file is None or self.mods.busy or not file_format(file)[0]:
            return
        if not self.mods.ready():
            self.set_result('warning', tr('Link your Deadlock folder on the Home page first.'))
            return
        self.set_result()
        self.act_text.setText(tr('Downloading and checking {0}… nothing is installed yet.').format(file.name))
        self.install_bar.set_unknown()
        self.install_cancel.show()
        self.activity.show()
        self.mods.prepare_store(self.profile, file.id, self.prepared, self.install_failed)
        self.sync_install()

    def prepared(self, plan):
        self.activity.hide()
        dialog = InstallReview(plan, self)
        if dialog.exec() != Dialog.Accepted:
            self.mods.discard(plan)
            self.set_result('info', tr('Cancelled. Nothing was changed.'))
            return
        self.act_text.setText(tr('Installing {0} {1}…').format(plan.mod_name, plan.version))
        self.install_bar.set_unknown()
        self.install_cancel.hide()
        self.activity.show()
        self.mods.commit(plan, dialog.acknowledged, self.installed, self.install_failed)

    def installed(self, mod):
        self.activity.hide()
        self.set_result('success', tr('Installed {0} {1}.').format(mod.name, mod.version), tr('Every file was re-checked after copying: {0}.').format(', '.join(mod.file_names())))
        Toast(self, tr('Installed {0}.').format(mod.name))
        self.sync_install()

    def install_failed(self, message, code):
        self.activity.hide()
        lead, _, detail = install_failure_text(code, message).partition('\n')
        self.set_result('danger', lead, detail or tr('Nothing was changed.'))
        self.sync_install()

    def cancel_install(self):
        if self.mods is not None:
            self.mods.cancel()

    def show_install_progress(self, done, total):
        if not self.activity.isVisibleTo(self) or not total:
            return
        self.install_bar.set_known(int(done * 1000 / total), 1000)
        self.act_text.setText(tr('Downloading… {0} of {1}').format(size_text(done), size_text(total)))

    # ---- pictures (only when the user asks, so browsing makes no picture requests) ------------

    def clear_pictures(self):
        self._token += 1
        while self.pictures_box.count():
            item = self.pictures_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.picture_count = 0

    def toggle_pictures(self):
        s = self.subject
        if s is None:
            return
        self.pictures_on = not self.pictures_on
        self.pictures_button.setText(tr('Hide pictures') if self.pictures_on else tr('Show pictures'))
        self.clear_pictures()
        if self.pictures_on:
            token = self._token
            for url in s.images[:IMAGES_SHOWN]:
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

    # ---- actions --------------------------------------------------------------------

    def open_page(self):
        s = self.subject
        if s:
            QDesktopServices.openUrl(QUrl(s.url))


def thousands(total):
    """The number shown in the count line, with thousands separators ('6,104')."""
    return '{:,}'.format(total)
