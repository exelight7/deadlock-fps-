"""Home: the game link, three doors (Mods, Performance, Stats), what needs attention, three small cards.

Built from the redesign components (`deadlock_fps/shell/components.py`) to the spec in
vault/Design/New Design/05 Screens.md. The page only draws what it is given: the window
(`deadlock_fps/game_link.py`) owns the game link, reads the engines and feeds `set_*` methods.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ..i18n import tr
from ..shell import theme
from ..shell.components import Badge, Banner, Button, Card, DoorCard, ListRow, PathField, ProgressBar, Select, mark, text_label

NEEDS_GAME = ('mods', 'performance')


def door_list():
    """(key, icon, name, what it is, the way in, address). A function, so the words follow the language chosen at start-up."""
    return (('mods', 'box', tr('Mods'), tr('Skins, HUDs, sounds and more from the community.'), tr('Browse mods'), 'mods.browse'),
            ('performance', 'gauge', tr('Performance'), tr('One slider for more frames per second.'), tr('Tune the game'), 'performance'),
            ('stats', 'chart', tr('Stats'), tr('Which heroes win now, the rank spread, and your own record.'), tr('Open stats'), 'stats'))


def small_cards():
    return (('crosshair', 'crosshair', tr('Crosshair'), 'crosshair'), ('servers', 'globe', tr('Servers'), 'servers'), ('backups', 'history', tr('Backups'), 'backups'))


class HomePage(QWidget):
    openRequested = Signal(str)             # an address such as 'mods.browse'
    gameRequired = Signal()                 # a door that needs the game was pressed before the game is linked

    def __init__(self, parent=None):
        super().__init__(parent)
        mark(self, 'HomePage')
        t = theme.current()
        self.linked = False
        self.show_card = False
        self.banner = None
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(t.px('space.4'))
        self.notice = QVBoxLayout()
        box.addLayout(self.notice)
        box.addWidget(self.build_link_card())
        self.search = QWidget()
        search_row = QVBoxLayout(self.search)
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.setSpacing(t.px('space.1'))
        search_row.addWidget(text_label(tr('Looking for Deadlock…'), 'CardText'))
        self.search_bar = ProgressBar()
        self.search_bar.set_unknown()
        search_row.addWidget(self.search_bar)
        self.search.hide()
        box.addWidget(self.search)

        doors = QHBoxLayout()
        doors.setSpacing(t.px('space.4'))
        self.doors = {}
        self.mods_text = tr('Skins, HUDs, sounds and more from the community.')
        for key, icon, title, text, action, address in door_list():
            door = DoorCard(icon, title, text, action)
            door.clicked.connect(lambda key=key, address=address: self.open_door(key, address))
            self.doors[key] = door
            doors.addWidget(door, 1)
        box.addLayout(doors)
        self.hint = text_label(tr('Mods and Performance open after the game is linked. Stats works without it.'), 'Muted')
        box.addWidget(self.hint)

        self.attention = Card(variant='flat')
        head = QHBoxLayout()
        head.setContentsMargins(t.px('space.4'), t.px('space.4'), t.px('space.4'), t.px('space.2'))
        head.addWidget(text_label(tr('Needs your attention'), 'CardTitle'), 1)
        self.count = Badge('0', 'count')
        head.addWidget(self.count)
        self.attention.body.addLayout(head)
        self.rows = []
        self.attention.hide()
        box.addWidget(self.attention)

        small = QHBoxLayout()
        small.setSpacing(t.px('space.4'))
        self.small = {}
        for key, icon, title, address in small_cards():
            card = Card(variant='clickable')
            title_row = QHBoxLayout()
            glyph = QLabel()
            glyph.setPixmap(theme.icon(icon, 'color.text.secondary', 20).pixmap(20, 20))
            title_row.addWidget(glyph)
            title_row.addWidget(text_label(title, 'CardTitle'), 1)
            card.body.addLayout(title_row)
            card.status = text_label('', 'CardText')
            card.body.addWidget(card.status)
            card.body.addStretch(1)
            card.clicked.connect(lambda address=address: self.openRequested.emit(address))
            self.small[key] = card
            small.addWidget(card, 1)
        box.addLayout(small)
        box.addStretch(1)
        self.set_linked(False)

    # --- the game link card ---------------------------------------------------------------------------

    def build_link_card(self):
        t = theme.current()
        self.link_card = Card()
        head = QHBoxLayout()
        head.setSpacing(t.px('space.3'))
        plate = mark(QLabel(), 'DoorIcon')
        plate.setAlignment(Qt.AlignCenter)
        plate.setPixmap(theme.icon('folder', 'color.accent.text', 20).pixmap(20, 20))
        head.addWidget(plate, 0, Qt.AlignTop)
        copy = QVBoxLayout()
        copy.setSpacing(2)
        self.link_title = text_label(tr('First, link your game'), 'CardTitle')
        copy.addWidget(self.link_title)
        self.link_text = text_label(tr('Toolbox needs to know where Deadlock is installed. It only looks; nothing is changed until you apply something.'), 'CardText')
        copy.addWidget(self.link_text)
        head.addLayout(copy, 1)
        self.link_card.body.addLayout(head)
        self.path_field = PathField('…/steamapps/common/Deadlock')
        self.path = self.path_field.edit
        self.link_card.body.addWidget(self.path_field)
        self.account_field = QWidget()
        account = QVBoxLayout(self.account_field)
        account.setContentsMargins(0, 0, 0, 0)
        account.setSpacing(4)
        account.addWidget(text_label(tr('Steam account: pick the one you play on'), 'FieldLabel'))
        self.accounts = Select()
        self.accounts.setLayoutDirection(Qt.LeftToRight)
        account.addWidget(self.accounts)
        self.account_field.hide()
        self.link_card.body.addWidget(self.account_field)
        row = QHBoxLayout()
        row.setSpacing(t.px('space.2'))
        self.find_button = Button(tr('Find it automatically'), 'primary', icon='search')
        self.choose_button = Button(tr('Choose the folder'), icon='folder')
        self.install_button = Button(tr('Install Deadlock from Steam'), icon='ext')
        self.install_button.hide()
        for button in (self.find_button, self.choose_button):
            row.addWidget(button)
        row.addStretch()
        self.link_card.body.addLayout(row)
        install = QHBoxLayout()                    # its own row: three buttons side by side do not fit the minimum window at 130 % text
        install.addWidget(self.install_button)
        install.addStretch()
        self.link_card.body.addLayout(install)
        self.note = text_label('', 'Muted')
        self.note.hide()
        self.link_card.body.addWidget(self.note)
        return self.link_card

    def set_note(self, text):
        self.note.setText(text)
        self.note.setVisible(bool(text))

    def set_linked(self, linked):
        """Linked: the card goes away (Settings, then the game pill, bring it back) and every door opens."""
        self.linked = bool(linked)
        self.refresh_visibility()
        for key in NEEDS_GAME:
            self.doors[key].set_available(self.linked)
        self.hint.setVisible(not self.linked)

    def show_link_card(self, shown=True):
        self.show_card = bool(shown)
        self.refresh_visibility()

    def refresh_visibility(self):
        self.link_card.setVisible(not self.linked or self.show_card)
        self.link_title.setText(tr('Where Deadlock is installed') if self.linked else tr('First, link your game'))

    def set_searching(self, searching):
        self.search.setVisible(bool(searching))
        self.find_button.set_busy(searching)

    def open_door(self, key, address):
        if key in NEEDS_GAME and not self.linked:
            self.gameRequired.emit()
            return
        self.openRequested.emit(address)

    # --- messages about the game ------------------------------------------------------------------------

    def set_notice(self, variant='', title='', text=''):
        """One banner at the top: what is going on with the game. An empty `variant` clears it."""
        if self.banner is not None:
            self.banner.setParent(None)
            self.banner.deleteLater()
            self.banner = None
        if variant:
            self.banner = Banner(title, text, variant)
            self.notice.addWidget(self.banner)

    def show_status(self, status, linked):
        """Turn a `detection.GameStatus` into the banner and the card's buttons (read-only; nothing is changed)."""
        self.set_notice()
        if status.running and linked:
            self.set_notice('warning', tr('Deadlock is running'), tr('Close it before applying any change.'))
        elif status.found and status.state == 'installed':
            if not linked:
                parts = [tr('Game version {0}').format(status.build) if status.build else '', '%.1f GB' % (status.size / 1073741824) if status.size else '']
                self.set_notice('info', tr('Deadlock was found on this PC'), ' · '.join(part for part in parts if part))
        elif status.state == 'updating':
            self.set_notice('info', tr('Steam is still downloading or updating Deadlock'),
                            tr('Wait for Steam to finish, then press Find it automatically. Toolbox looks again every few seconds.'))
        elif status.state == 'no_steam':
            self.set_notice('warning', tr('Steam was not found on this PC'),
                            tr('Install Steam and Deadlock, or choose the game folder yourself if it is somewhere unusual.'))
        else:
            self.set_notice('danger', tr('Deadlock was not found on this PC'),
                            tr('Looked in {0} Steam libraries and on every drive. Install it from Steam or choose its folder.').format(status.libraries))
        self.install_button.setVisible(not linked and status.state in ('missing', 'updating'))

    # --- what the doors and cards say ----------------------------------------------------------------------

    def set_mods(self, installed, updates):
        if installed:
            text = tr('{0} installed · {1} updates').format(installed, updates) if updates else tr('{0} installed').format(installed)
        else:
            text = self.mods_text
        self.doors['mods'].status.setText(text)

    def set_performance(self, level, name):
        self.doors['performance'].status.setText(tr('Level {0} · {1}').format(level, name))

    def set_small(self, key, text):
        self.small[key].status.setText(text)

    def set_attention(self, items):
        """`items`: dicts with tone, icon, title, line, action, callback. An empty list hides the card."""
        for row in self.rows:
            row.setParent(None)
            row.deleteLater()
        self.rows = []
        for item in items:
            button = Button(item['action'], 'primary' if item['tone'] == 'danger' else 'secondary', 'sm')
            button.clicked.connect(item['callback'])
            row = ListRow(item['title'], item.get('line', ''), item['icon'], button, tone=item['tone'])
            self.attention.body.addWidget(row)
            self.rows.append(row)
        self.count.setText(str(len(items)))
        self.attention.setVisible(bool(items))
