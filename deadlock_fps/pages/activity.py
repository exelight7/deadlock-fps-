"""Mods > Activity: what Toolbox downloaded and changed in the game folder, newest first, and a download that is running now.

Reads `Installer.history()`; the page draws only. A failed item is the first thing you see in its row (danger look) with the reason.
"""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from ..i18n import tr
from ..installer import InstallError
from ..shell import theme
from ..shell.components import Banner, Button, Card, EmptyState, List, ListRow, ProgressBar, breakable, mark, text_label
from ..ui_common import size_text, iso_text
from .installed import action_word


class ActivityPage(QWidget):
    openRequested = Signal(str)
    gameRequired = Signal()

    def __init__(self, service, parent=None):
        super().__init__(parent)
        mark(self, 'ActivityPage')
        self.service = service
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
        self.game_notice = Banner(tr('Link your game first'), tr('These pages work on a Deadlock folder. Link it on the Home page, or let Toolbox find it.'), 'warning')
        link = Button(tr('Link the game'), 'secondary', 'sm')
        link.clicked.connect(self.gameRequired.emit)
        self.game_notice.add_action(link)
        self.game_notice.hide()
        self.column.addWidget(self.game_notice)
        self.now = text_label(tr('Nothing is downloading right now.'), 'CardText')
        self.column.addWidget(self.now)
        self.running = Card()
        self.running_title = text_label(tr('Downloading'), 'CardTitle')
        self.running.body.addWidget(self.running_title)
        self.running_text = text_label('', 'CardText')
        self.running.body.addWidget(self.running_text)
        line = QHBoxLayout()
        self.bar = ProgressBar()
        self.bar.set_unknown()
        line.addWidget(self.bar, 1)
        self.cancel_button = Button(tr('Cancel'), 'secondary', 'sm')
        self.cancel_button.clicked.connect(service.cancel)
        line.addWidget(self.cancel_button)
        self.running.body.addLayout(line)
        self.running.hide()
        self.column.addWidget(self.running)
        self.history = Card(variant='flat')
        head = QHBoxLayout()
        head.setContentsMargins(t.px('space.4'), t.px('space.4'), t.px('space.4'), t.px('space.2'))
        head.addWidget(text_label(tr('History'), 'CardTitle'), 1)
        self.history.body.addLayout(head)
        self.list = List(variant='flat')
        self.history.body.addWidget(self.list)
        self.column.addWidget(self.history)
        self.empty = EmptyState('clock', tr('Nothing has happened yet'), tr('Installs, updates, removals and restores are listed here.'))
        self.empty.hide()
        self.column.addWidget(self.empty)
        self.column.addStretch(1)
        service.changed.connect(self.reload)
        service.progress.connect(self.show_progress)
        service.busyChanged.connect(self.busy)
        self.reload()

    def showEvent(self, event):
        super().showEvent(event)
        self.reload()

    def busy(self, value):
        self.running.setVisible(bool(value))
        self.now.setVisible(not value)
        if value:
            self.running_text.setText(tr('Working…'))
            self.bar.set_unknown()

    def show_progress(self, done, total):
        self.running.setVisible(True)
        self.now.setVisible(False)
        if total:
            self.bar.set_known(min(1000, int(done * 1000 / total)), 1000)
        else:
            self.bar.set_unknown()
        self.running_text.setText(tr('Downloading · {0} of {1}').format(size_text(done), size_text(total) if total else '?'))

    def reload(self, *_):
        try:
            installer = self.service.installer()
        except InstallError:
            installer = None
        self.game_notice.setVisible(installer is None)
        entries = list(installer.history()) if installer else []
        self.list.clear()
        for entry in entries:
            self.list.add(self.make_row(entry))
        self.history.setVisible(bool(entries))
        self.empty.setVisible(installer is not None and not entries)

    @staticmethod
    def make_row(entry):
        ok = entry.get('result') == 'ok'
        name, version = entry.get('name', ''), entry.get('version', '')
        title = ' '.join(part for part in (action_word(entry.get('action', '')), name, version) if part)
        when = iso_text(entry.get('at', ''))
        bits = [when, entry.get('note', '')] if ok else [when, entry.get('result', ''), entry.get('note', '')]
        line = ' · '.join(bit for bit in bits if bit)
        return ListRow(breakable(title), breakable(line), 'check' if ok else 'warn', tone='success' if ok else 'danger')
