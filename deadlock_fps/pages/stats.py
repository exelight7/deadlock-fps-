"""Stats › Heroes, Ranks and My stats: which heroes are strong right now, how players are spread over the ranks, and your own record.

The numbers come from the public Deadlock API (api.deadlock-api.com). Nothing is requested until the user presses a button; what is
already saved on this computer is shown at once. Heroes and Ranks send only the period, the mode and the rank that were chosen
(they share one filter, kept in step on both tabs). My stats sends one Steam account number, only when its button is pressed, and
nothing about a player is saved. Every word from the server is shown as plain text.

`StatsPage` holds the logic and the three views (`heroes_view`, `ranks_view`, `me_view`); the window puts one view in each tab.
"""
from PySide6.QtCore import QObject, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QHBoxLayout, QStyle, QStyledItemDelegate, QStyleOptionViewItem, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from ..i18n import tr
from ..shell import theme
from ..shell.components import (Bar, Badge, Banner, Button, Card, DataTable, EmptyState, SearchField, SegmentedControl, Select, StatTile, TextField,
                                mark, set_props, text_label)
from ..stats.steam import SteamIdError, account_id as parse_account
from ..ui_common import ltr, time_text
from .performance import scrolling

TIER_COUNT = 11
DEFAULT_WINDOW, DEFAULT_MODE = 14, 'ranked'
SORT_ROLE = Qt.UserRole
LOW_ROLE, HIGH_ROLE = Qt.UserRole + 1, Qt.UserRole + 2


def failure_text(code, message):
    """One plain sentence for an engine failure, with the engine's own detail after it."""
    lead = {
        'rate-limited': tr('The statistics server asked us to slow down. Try again in a minute.'),
        'network': tr('Could not reach the statistics server.'),
        'bad-response': tr('The statistics server sent something this version does not understand.'),
        'not-found': tr('The statistics server has nothing for this request.'),
        'too-large': tr('The statistics server sent more data than expected, so it was ignored.'),
    }.get(code, tr('Something went wrong.'))
    return lead if code == 'rate-limited' else lead + '\n' + message


def account_problem(code):
    return {
        'empty': tr('Enter a Steam account number first.'),
        'vanity': tr('A profile name (steamcommunity.com/id/name) has no number in it. Use the button to read your number from the Steam folder, or paste a steamcommunity.com/profiles/… link.'),
        'range': tr('That number is outside the range Steam uses.'),
    }.get(code, tr('That is not an account number. Use the number from your Steam userdata folder, a 17-digit Steam ID, or a steamcommunity.com/profiles/… link.'))


def percent(fraction, digits=1):
    return '%.*f %%' % (digits, 100 * fraction)


def count(value):
    return ltr('{:,}'.format(value))


class NumberItem(QTableWidgetItem):
    """A cell that shows text and sorts by a number."""

    def __init__(self, shown, number):
        super().__init__(shown)
        self.setData(SORT_ROLE, number)
        self.setTextAlignment(Qt.AlignTrailing | Qt.AlignVCenter)

    def __lt__(self, other):
        mine = self.data(SORT_ROLE)
        theirs = other.data(SORT_ROLE) if isinstance(other, QTableWidgetItem) else None
        if isinstance(mine, (int, float)) and isinstance(theirs, (int, float)):
            return mine < theirs
        return super().__lt__(other)


def verdict_color(low, high):
    """Green when the whole 95 % range is above one half, red when it is all below, otherwise no colour."""
    if low > 0.5:
        return theme.color('color.success.text')
    if high < 0.5:
        return theme.color('color.danger.text')
    return None


def fill(empty, title, text=''):
    empty.set_text(title, text)


class RangeDelegate(QStyledItemDelegate):
    """The "How sure" cell: a 0 to 100 % track with the 95 % range drawn on it and a mark at 50 %. The cell's own text stays for reading and sorting."""

    def paint(self, painter, option, index):
        low, high = index.data(LOW_ROLE), index.data(HIGH_ROLE)
        shown = QStyleOptionViewItem(option)
        self.initStyleOption(shown, index)
        text = shown.text
        shown.text = ''
        style = option.widget.style() if option.widget else QApplication.style()
        style.drawControl(QStyle.CE_ItemViewItem, shown, painter, option.widget)
        if low is None or high is None:
            return
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(option.rect).adjusted(12, 0, -12, 0)
        font = QFont(option.font)
        font.setPointSizeF(max(7., font.pointSizeF() - 1))
        painter.setFont(font)
        painter.setPen(theme.color('color.text.muted'))
        painter.drawText(QRectF(rect.left(), rect.top() + 4, rect.width(), rect.height() / 2 - 2), Qt.AlignLeft | Qt.AlignVCenter, text)
        track = QRectF(rect.left(), rect.bottom() - 14, rect.width(), 6)
        painter.setPen(Qt.NoPen)
        painter.setBrush(theme.color('color.bg.sunken'))
        painter.drawRoundedRect(track, 3, 3)
        colour = verdict_color(low, high)
        painter.setBrush(colour if colour is not None else theme.color('color.text.muted'))
        rtl = option.direction == Qt.RightToLeft
        a, b = (1 - high, 1 - low) if rtl else (low, high)
        painter.drawRoundedRect(QRectF(track.left() + a * track.width(), track.top(), max(2., (b - a) * track.width()), track.height()), 3, 3)
        painter.setBrush(theme.color('color.text.primary'))
        painter.drawRect(QRectF(track.center().x() - .5, track.top() - 2, 1, track.height() + 4))
        painter.restore()


class PeriodControl(SegmentedControl):
    """A SegmentedControl of days with the small API of a combo box (`findData`, `setCurrentIndex`, `currentData`, `currentText`), so the page treats it like one."""

    def __init__(self, options, parent=None):
        super().__init__([(str(v), short) for v, short, _ in options], parent)
        self.options = list(options)                        # (value, short caption, sentence caption)
        self.changed.connect(lambda _key: self.choice.emit(self.currentData()))

    from PySide6.QtCore import Signal as _Signal
    choice = _Signal(object)

    def currentData(self):
        return int(self.value())

    def currentText(self):
        return next(long for v, _, long in self.options if str(v) == self.value())

    def findData(self, data):
        return next((i for i, (v, _, _) in enumerate(self.options) if v == data), -1)

    def count(self):
        return len(self.options)

    def setCurrentIndex(self, index):
        self.set_value(str(self.options[index][0]))
        self.choice.emit(self.currentData())


def modes():
    return ((tr('All modes'), ''), (tr('Ranked'), 'ranked'), (tr('Unranked'), 'unranked'))


class FilterRow(QWidget):
    """Period, mode and rank, a badge for the age of what is shown, and the button that asks the server. One per tab, kept the same by the page."""

    def __init__(self, parent=None):
        super().__init__(parent)
        t = theme.current()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(t.px('space.3'))
        self.window_box = PeriodControl(((7, tr('7 days'), tr('Last 7 days')), (14, tr('14 days'), tr('Last 14 days')), (30, tr('30 days'), tr('Last 30 days'))))
        self.window_box.set_value(str(DEFAULT_WINDOW))
        self.mode_box, self.tier_box = Select(), Select()
        for caption, value in modes():
            self.mode_box.addItem(caption, value)
        self.mode_box.setCurrentIndex(self.mode_box.findData(DEFAULT_MODE))
        for box, name in ((self.window_box, tr('Period')), (self.mode_box, tr('Game mode')), (self.tier_box, tr('Rank'))):
            box.setAccessibleName(name)
        self.mode_box.setMinimumWidth(130)
        self.tier_box.setMinimumWidth(130)
        row.addWidget(self.window_box)
        row.addWidget(self.mode_box)
        row.addWidget(self.tier_box)
        row.addStretch(1)
        self.badge = Badge('', 'neutral')
        self.badge.hide()
        row.addWidget(self.badge)
        self.load_button = Button('', 'primary', icon='refresh')
        row.addWidget(self.load_button)

    def values(self):
        return self.window_box.currentData(), self.mode_box.currentData(), self.tier_box.currentData() or 0

    def set_values(self, window, mode, tier):
        self.window_box.set_value(str(window))
        self.mode_box.setCurrentIndex(self.mode_box.findData(mode))
        self.tier_box.setCurrentIndex(max(0, self.tier_box.findData(tier)))


class StatsPage(QObject):
    def __init__(self, window, service, account=None):
        super().__init__(window)
        self.window = window
        self.service = service
        self.account = account or (lambda: None)       # the account number found in the user's Steam folder, or None
        self.overview = None                           # what the Heroes and Ranks tabs show
        self.view = None                               # what My stats shows
        self.tiers = {}
        self._seq = 0                                  # answers to an older question are dropped
        self._building = True
        self.rows = [FilterRow(), FilterRow()]
        self.heroes_view = self._heroes_view(self.rows[0])
        self.ranks_view = self._ranks_view(self.rows[1])
        self.me_view = self._me_view()
        first = self.rows[0]
        self.window_box, self.mode_box, self.tier_box, self.load_button = first.window_box, first.mode_box, first.tier_box, first.load_button
        for row in self.rows:
            row.window_box.choice.connect(lambda _v, r=row: self.filter_changed(r))
            row.mode_box.currentIndexChanged.connect(lambda _i, r=row: self.filter_changed(r))
            row.tier_box.currentIndexChanged.connect(lambda _i, r=row: self.filter_changed(r))
            row.load_button.clicked.connect(self.load)
        service.busyChanged.connect(self.refresh_buttons)
        self._building = False
        self.refresh_tiers({})
        self.show_choice()

    # ---- construction ---------------------------------------------------------------

    def _column(self):
        """A scrolling page with one column; returns (the widget to show, the layout to fill)."""
        t = theme.current()
        inner = QWidget()
        column = QVBoxLayout(inner)
        column.setContentsMargins(0, 0, 12, 0)
        column.setSpacing(t.px('space.3'))
        return scrolling(inner), column

    def _status_line(self):
        label = text_label('', 'StatusText')
        return label

    def _heroes_view(self, row):
        widget, c = self._column()
        c.addWidget(row)
        self.status = self._status_line()
        c.addWidget(self.status)
        self.note = text_label(tr('The numbers come from api.deadlock-api.com, a community service. Loading Heroes and Ranks sends only the period, mode and rank chosen here: nothing about you.'), 'Muted')
        c.addWidget(self.note)
        line = QHBoxLayout()
        self.search_field = SearchField(tr('Search a hero'))
        self.search = self.search_field.edit
        self.search.setAccessibleName(tr('Search a hero'))
        self.search.textChanged.connect(self.fill_heroes)
        line.addWidget(self.search_field, 1)
        c.addLayout(line)
        self.summary = text_label('', 'Muted')
        c.addWidget(self.summary)
        self.hero_table = DataTable([tr('Hero'), tr('Matches'), tr('Pick rate'), tr('Win rate'), tr('How sure (95 %)'), tr('KDA'), tr('Net worth')], numeric=(1, 2, 3, 5, 6))
        self.hero_table.setSortingEnabled(True)
        self.hero_table.horizontalHeader().setSortIndicator(1, Qt.DescendingOrder)
        self.hero_table.horizontalHeader().setToolTip(tr('Click a heading to sort. Sorting the 95 % range puts the heroes whose strength is best established first.'))
        self.hero_table.setItemDelegateForColumn(4, RangeDelegate(self.hero_table))
        for column, width in enumerate((170, 100, 100, 100, 240, 90)):
            self.hero_table.setColumnWidth(column, width)
        self.hero_table.setMinimumHeight(360)
        c.addWidget(self.hero_table)
        self.hero_empty = EmptyState('chart', tr('Nothing loaded yet'), '', Button(tr('Load statistics'), 'primary'))
        self.hero_empty.button.clicked.connect(self.load)
        c.addWidget(self.hero_empty)
        c.addWidget(text_label(tr('Win rate is shown with its 95 % range: a hero played few times can look strong by luck, and the range says how far the real number could be. Green or red appears only when the whole range is on one side of 50 %. KDA is kills plus assists per death. Pick rate is the share of matches the hero was played in.'), 'Muted'))
        c.addStretch(1)
        return widget

    def _ranks_view(self, row):
        widget, c = self._column()
        c.addWidget(row)
        self.rank_status = self._status_line()
        c.addWidget(self.rank_status)
        self.rank_summary = text_label('', 'Muted')
        c.addWidget(self.rank_summary)
        self.rank_table = DataTable([tr('Rank'), tr('Players'), tr('Share of players'), tr('Matches')], numeric=(1, 3))
        self.rank_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.rank_table.setMinimumHeight(360)
        c.addWidget(self.rank_table)
        self.rank_empty = EmptyState('chart', tr('Nothing loaded yet'), '', Button(tr('Load statistics'), 'primary'))
        self.rank_empty.button.clicked.connect(self.load)
        c.addWidget(self.rank_empty)
        c.addWidget(text_label(tr('A player is counted in the rank they had in each match, so someone who climbed during the period appears in more than one row.'), 'Muted'))
        c.addStretch(1)
        return widget

    def _me_view(self):
        widget, c = self._column()
        c.addWidget(Banner(tr('This sends a Steam account number'),
                           tr('Looking someone up sends their Steam account number to api.deadlock-api.com, a community service that publishes Deadlock statistics. Nothing is sent until you press Look up, and nothing is saved on this computer.'), 'info'))
        row = QHBoxLayout()
        row.setSpacing(theme.current().px('space.3'))
        self.account_input = TextField(placeholder=tr('Steam account number, 17-digit Steam ID or profile link'))
        self.account_field = self.account_input.edit
        self.account_field.setMaxLength(200)
        self.account_field.setAccessibleName(tr('Steam account'))
        self.account_field.returnPressed.connect(self.look_up)
        row.addWidget(self.account_input, 1)
        self.own_button = Button(tr('Use my Steam account'), 'secondary', icon='user')
        self.own_button.setToolTip(tr('Reads the number from the folder name Steam keeps your game settings in. Nothing is sent.'))
        self.own_button.clicked.connect(self.use_own_account)
        row.addWidget(self.own_button, 0, Qt.AlignTop)
        self.look_button = Button(tr('Look up'), 'primary', icon='search')
        self.look_button.clicked.connect(self.look_up)
        row.addWidget(self.look_button, 0, Qt.AlignTop)
        c.addLayout(row)
        row = QHBoxLayout()
        row.setSpacing(theme.current().px('space.3'))
        self.me_window = PeriodControl(((0, tr('All time'), tr('All time')), (30, tr('30 days'), tr('Last 30 days')), (14, tr('14 days'), tr('Last 14 days')), (7, tr('7 days'), tr('Last 7 days'))))
        self.me_mode = Select()
        for caption, value in modes():
            self.me_mode.addItem(caption, value)
        for box, name in ((self.me_window, tr('Period')), (self.me_mode, tr('Game mode'))):
            box.setAccessibleName(name)
        self.me_mode.setMinimumWidth(130)
        row.addWidget(self.me_window)
        row.addWidget(self.me_mode)
        row.addStretch(1)
        c.addLayout(row)
        self.me_status = self._status_line()
        c.addWidget(self.me_status)
        tiles = QHBoxLayout()
        tiles.setSpacing(theme.current().px('space.3'))
        self.tile_rank, self.tile_matches = StatTile('—', tr('Rank')), StatTile('—', tr('Matches'))
        self.tile_wins, self.tile_rate = StatTile('—', tr('Wins')), StatTile('—', tr('Win rate'))
        for tile in (self.tile_rank, self.tile_matches, self.tile_wins, self.tile_rate):
            tiles.addWidget(tile, 1)
        self.tiles = QWidget()
        self.tiles.setLayout(tiles)
        tiles.setContentsMargins(0, 0, 0, 0)
        self.tiles.hide()
        c.addWidget(self.tiles)
        self.me_table = DataTable([tr('Hero'), tr('Matches'), tr('Wins'), tr('Win rate'), tr('Everyone'), tr('Difference'), tr('KDA')], numeric=(1, 2, 3, 4, 5, 6))
        self.me_table.setSortingEnabled(True)
        self.me_table.horizontalHeader().setSortIndicator(1, Qt.DescendingOrder)
        for column, width in enumerate((170, 100, 90, 100, 100, 110)):
            self.me_table.setColumnWidth(column, width)
        self.me_table.setMinimumHeight(300)
        self.me_table.hide()
        c.addWidget(self.me_table)
        self.me_empty = EmptyState('user', tr('Whose stats?'), tr('Enter an account number above and press Look up.'))
        c.addWidget(self.me_empty)
        c.addWidget(text_label(tr('"Everyone" is the win rate of all players on that hero over the last 7, 14 or 30 days (30 when you choose All time), in the same game mode. A difference from only a few matches is mostly luck: look at heroes you have played a lot.'), 'Muted'))
        c.addStretch(1)
        return widget

    # ---- the choice at the top -------------------------------------------------------

    def choice(self):
        return self.rows[0].values()

    def filter_changed(self, source):
        """One tab's filter moved: the other follows, then the page shows the saved copy for it (no request)."""
        if self._building:
            return
        self._building = True
        for row in self.rows:
            if row is not source:
                row.set_values(*source.values())
        self._building = False
        self.show_choice()

    def refresh_tiers(self, names):
        """Names for the rank filter: the real ones once the server has told us, numbered placeholders until then."""
        self.tiers = dict(names)
        current = self.rows[0].tier_box.currentData() or 0
        for row in self.rows:
            box = row.tier_box
            box.blockSignals(True)
            box.clear()
            box.addItem(tr('All ranks'), 0)
            for tier in range(1, TIER_COUNT + 1):
                box.addItem(self.tiers.get(tier) or tr('Rank {0}').format(tier), tier)
            box.setCurrentIndex(max(0, box.findData(current)))
            box.blockSignals(False)

    def set_status(self, text, tone=None):
        for label in (self.status, self.rank_status):
            label.setText(text)
            set_props(label, tone=tone)

    def show_badge(self, text='', variant='neutral'):
        for row in self.rows:
            row.badge.setText(text)
            row.badge.set_variant(variant)
            row.badge.setVisible(bool(text))

    def show_choice(self, *_):
        """The choice changed: show the saved copy for it when there is one, otherwise say that nothing is loaded. No request is made."""
        if self._building:
            return
        self._seq += 1
        saved = self.service.cached_overview(*self.choice())
        if saved is not None:
            self.show_overview(saved)
        else:
            self.overview = None
            self.fill_heroes()
            self.fill_ranks()
            self.show_badge()
            self.set_status(tr('Nothing is loaded for this choice yet. Press the button to ask the statistics server.'))
        self.refresh_buttons()

    def refresh_buttons(self, *_):
        busy = self.service.busy
        caption = tr('Refresh') if self.overview is not None else tr('Load statistics')
        for row in self.rows:
            row.load_button.setText(caption)
            row.load_button.set_variant('secondary' if self.overview is not None else 'primary')
            row.load_button.set_busy(busy and self._loading_overview)
            row.load_button.setEnabled(not busy)
        self.look_button.setEnabled(not busy)
        self.own_button.setEnabled(self.account() is not None)

    _loading_overview = False

    # ---- Heroes and Ranks ------------------------------------------------------------

    def load(self):
        if self.service.busy:
            return
        window, mode, tier = self.choice()
        self._seq += 1
        seq = self._seq
        self.set_status(tr('Loading…'))
        self._loading_overview = True
        started = self.service.load_overview(window, mode, tier, self.overview is not None,
                                             lambda overview, s=seq: self.loaded(s, overview), lambda message, code, s=seq: self.load_failed(s, message, code))
        if not started:
            self._loading_overview = False
            self.set_status('')
        self.refresh_buttons()

    def loaded(self, seq, overview):
        self._loading_overview = False
        if seq == self._seq:
            self.show_overview(overview)
        self.refresh_buttons()

    def load_failed(self, seq, message, code):
        self._loading_overview = False
        if seq == self._seq:
            self.set_status(failure_text(code, message), 'danger')
        self.refresh_buttons()

    def show_overview(self, overview):
        self.overview = overview
        if overview.tiers:
            self.refresh_tiers(overview.tiers)
        self.fill_heroes()
        self.fill_ranks()
        meta = overview.meta.value
        row = self.rows[0]
        window, mode, tier = row.window_box.currentText(), row.mode_box.currentText(), row.tier_box.currentText()
        lead = tr('{0} · {1} · {2}: {3} matches. Updated {4}.').format(window, mode, tier, count(meta.total_matches), ltr(time_text(meta.fetched_at)))
        tone = None
        if overview.meta.stale:
            lead += '\n' + tr('Could not reach the statistics server, so this is the copy saved earlier.') + '\n' + failure_text(overview.meta.error.code, overview.meta.error.message)
            tone = 'warning'
            self.show_badge(tr('Old copy'), 'warning')
        elif overview.meta.cached:
            lead += ' ' + tr('(saved copy)')
            self.show_badge(tr('Saved copy · {0}').format(ltr(time_text(meta.fetched_at))), 'neutral')
        else:
            self.show_badge()
        self.set_status(lead, tone)

    def fill_heroes(self, *_):
        table = self.hero_table
        sort_column, sort_order = table.horizontalHeader().sortIndicatorSection(), table.horizontalHeader().sortIndicatorOrder()
        table.setSortingEnabled(False)
        table.setRowCount(0)
        if self.overview is None:
            self.summary.setText('')
            fill(self.hero_empty, tr('Nothing loaded yet'), tr('Press “Load statistics”. Only the period, mode and rank you chose are sent.'))
            self.hero_empty.button.show()
            self.hero_empty.show()
            table.hide()
            table.setSortingEnabled(True)
            return
        meta = self.overview.meta.value
        needle = self.search.text().strip().casefold()
        heroes = [h for h in meta.heroes if needle in h.name.casefold()]
        table.setRowCount(len(heroes))
        bold = QFont(table.font())
        bold.setBold(True)
        for row, hero in enumerate(heroes):
            low, high = hero.interval
            cells = [QTableWidgetItem(hero.name),
                     NumberItem(count(hero.matches), hero.matches),
                     NumberItem(ltr(percent(meta.pick_rate(hero))), meta.pick_rate(hero)),
                     NumberItem(ltr(percent(hero.win_rate)), hero.win_rate),
                     NumberItem(ltr('%.1f – %.1f %%' % (100 * low, 100 * high)), low),
                     NumberItem(ltr('%.2f' % hero.kda), hero.kda),
                     NumberItem(count(round(hero.average_net_worth)), hero.average_net_worth)]
            cells[0].setData(SORT_ROLE, hero.hero_id)
            cells[3].setFont(bold)
            cells[4].setData(LOW_ROLE, low)
            cells[4].setData(HIGH_ROLE, high)
            color = verdict_color(low, high)
            if color is not None:
                cells[3].setForeground(color)
            for column, item in enumerate(cells):
                table.setItem(row, column, item)
        table.setSortingEnabled(True)
        table.sortByColumn(sort_column, sort_order)
        minutes = round(meta.average_duration_s / 60)
        self.summary.setText(tr('{0} matches · average length {1} min · abandon rate {2}').format(count(meta.total_matches), ltr(minutes), ltr(percent(meta.abandon_rate))))
        if heroes:
            self.hero_empty.hide()
            table.show()
        else:
            fill(self.hero_empty, tr('No hero matches your search') if meta.heroes else tr('The server returned no heroes for this choice'))
            self.hero_empty.button.hide()
            self.hero_empty.show()
            table.hide()

    def fill_ranks(self):
        table = self.rank_table
        table.setRowCount(0)
        distribution = self.overview.distribution.value if self.overview is not None and self.overview.distribution is not None else None
        if distribution is None or not distribution.shares:
            self.rank_summary.setText('')
            if self.overview is None:
                fill(self.rank_empty, tr('Nothing loaded yet'), tr('Press “Load statistics”. Only the period, mode and rank you chose are sent.'))
                self.rank_empty.button.show()
            else:
                fill(self.rank_empty, tr('No rank numbers'), self.overview.distribution_error or tr('The server returned no rank numbers for this choice.'))
                self.rank_empty.button.hide()
            self.rank_empty.show()
            table.hide()
            return
        self.rank_empty.hide()
        table.show()
        total = distribution.total_players or 1
        biggest = max(s.players for s in distribution.shares) or 1
        table.setRowCount(len(distribution.shares))
        for row, share in enumerate(distribution.shares):
            table.setItem(row, 0, QTableWidgetItem(share.name))
            table.setItem(row, 1, NumberItem(count(share.players), share.players))
            table.setItem(row, 3, NumberItem(count(share.matches), share.matches))
            table.setCellWidget(row, 2, self.share_cell(share.players / total, share.players / biggest))
        table.setColumnWidth(0, 180)
        table.setColumnWidth(1, 120)
        table.setColumnWidth(2, 320)
        self.rank_summary.setText(tr('{0} players · {1}').format(count(distribution.total_players), self.rows[1].window_box.currentText()))

    @staticmethod
    def share_cell(fraction, relative):
        """The percentage and, beside it, a bar as long as `relative` (1 for the biggest rank) so the rows can be compared at a glance."""
        cell = QWidget()
        row = QHBoxLayout(cell)
        row.setContentsMargins(8, 0, 12, 0)
        row.setSpacing(10)
        label = text_label(ltr(percent(fraction)), 'KeyValueValue', wrap=False)
        label.setMinimumWidth(64)
        bar = Bar(relative)
        row.addWidget(label)
        row.addWidget(bar, 1)
        return cell

    # ---- My stats --------------------------------------------------------------------

    def use_own_account(self):
        own = self.account()
        if own is not None:
            self.account_field.setText(str(own))
            self.account_input.set_error('')

    def look_up(self):
        if self.service.busy:
            return
        try:
            number = parse_account(self.account_field.text())
        except SteamIdError as error:
            self.me_status.setText(account_problem(error.code))
            set_props(self.me_status, tone='danger')
            self.account_input.set_error(account_problem(error.code))
            return
        self.account_input.set_error('')
        window, mode = self.me_window.currentData(), self.me_mode.currentData()
        scope = '%s · %s' % (self.me_window.currentText(), self.me_mode.currentText())      # what the answer is about, even if the choice changes meanwhile
        self.me_status.setText(tr('Looking up…'))
        set_props(self.me_status, tone=None)
        started = self.service.load_player(number, window, mode, lambda view, s=scope: self.looked_up(s, view), self.look_up_failed)
        if not started:
            self.me_status.setText('')
        self.look_button.set_busy(started)
        self.refresh_buttons()

    def looked_up(self, scope, view):
        self.look_button.set_busy(False)
        self.show_player(view, scope)
        self.refresh_buttons()

    def look_up_failed(self, message, code):
        self.look_button.set_busy(False)
        self.me_status.setText(failure_text(code, message))
        set_props(self.me_status, tone='danger')
        self.refresh_buttons()

    def show_player(self, view, scope=''):
        self.view = view
        player = view.player
        table = self.me_table
        sort_column, sort_order = table.horizontalHeader().sortIndicatorSection(), table.horizontalHeader().sortIndicatorOrder()
        table.setSortingEnabled(False)
        table.setRowCount(0)
        everyone = {h.hero_id: h for h in view.meta.value.heroes} if view.meta is not None else {}
        header = table.horizontalHeaderItem(4)
        header.setToolTip(tr('Win rate of all players on that hero over the last {0} days, in the same game mode.').format(view.meta.value.window_days) if view.meta is not None else tr('The comparison could not be loaded.'))
        table.setRowCount(len(player.heroes))
        for row, hero in enumerate(player.heroes):
            other = everyone.get(hero.hero_id)
            difference = hero.win_rate - other.win_rate if other is not None else None
            cells = [QTableWidgetItem(hero.name),
                     NumberItem(count(hero.matches), hero.matches),
                     NumberItem(count(hero.wins), hero.wins),
                     NumberItem(ltr(percent(hero.win_rate)), hero.win_rate),
                     NumberItem(ltr(percent(other.win_rate)) if other is not None else '—', other.win_rate if other is not None else -1.0),
                     NumberItem(ltr('%+.1f' % (100 * difference)) if difference is not None else '—', difference if difference is not None else -9.0),
                     NumberItem(ltr('%.2f' % hero.kda), hero.kda)]
            cells[0].setData(SORT_ROLE, hero.hero_id)
            if difference is not None and abs(difference) >= 0.005:
                cells[5].setForeground(theme.color('color.success.text' if difference > 0 else 'color.danger.text'))
            for column, item in enumerate(cells):
                table.setItem(row, column, item)
        table.setSortingEnabled(True)
        table.sortByColumn(sort_column, sort_order)
        matches, wins = sum(h.matches for h in player.heroes), sum(h.wins for h in player.heroes)
        if player.rank is not None:
            names = self.tiers or (self.overview.tiers if self.overview is not None else {})
            name = names.get(player.rank.tier) or tr('Rank {0}').format(player.rank.tier)
            rank = tr('Rank: {0} {1}').format(name, ltr(player.rank.subrank))
            self.tile_rank.set_value('%s %s' % (name, ltr(player.rank.subrank)))
        else:
            rank = tr('No rank on record')
            self.tile_rank.set_value('—')
        lead = (scope + ' · ' if scope else '') + rank
        set_props(self.me_status, tone=None)
        if matches:
            self.me_empty.hide()
            table.show()
            self.tiles.show()
            self.tile_matches.set_value(count(matches))
            self.tile_wins.set_value(count(wins))
            self.tile_rate.set_value(ltr(percent(wins / matches)))
            self.me_status.setText(lead + ' · ' + tr('{0} matches · {1} wins · {2} win rate').format(count(matches), count(wins), ltr(percent(wins / matches))))
        else:
            self.tiles.hide()
            fill(self.me_empty, tr('No matches found'), tr('This account has no matches in this period and mode, or its match history is private, or the number is wrong. Try All time and All modes.'))
            self.me_empty.show()
            table.hide()
            self.me_status.setText(lead)
