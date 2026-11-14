"""Mods > Browse as a whole: GameBanana, and (when you have added sources of your own) "My sources" beside it.

A thin host: the switch and the two views. The switch is hidden until at least one extra source exists, so most people never see it.
"""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget

from ..i18n import tr
from ..shell import theme
from ..shell.components import SegmentedControl, mark


class BrowseHost(QWidget):
    openRequested = Signal(str)
    gameRequired = Signal()

    def __init__(self, browse, sources, service, parent=None):
        """`browse` is the GameBanana page, `sources` the page of extra sources, `service` the ModService (its manager knows the sources)."""
        super().__init__(parent)
        mark(self, 'BrowseHost')
        self.browse, self.sources, self.service = browse, sources, service
        t = theme.current()
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(t.px('space.3'))
        self.switch_row = QWidget()
        row = QHBoxLayout(self.switch_row)
        row.setContentsMargins(0, 0, 0, 0)
        self.switch = SegmentedControl([('gamebanana', tr('GameBanana')), ('sources', tr('My sources'))])
        self.switch.changed.connect(self.show_view)
        row.addWidget(self.switch)
        row.addStretch(1)
        box.addWidget(self.switch_row)
        self.stack = QStackedWidget()
        self.stack.addWidget(browse)
        self.stack.addWidget(sources)
        box.addWidget(self.stack, 1)
        for page in (browse, sources):
            page.openRequested.connect(self.openRequested)
            page.gameRequired.connect(self.gameRequired)
        service.changed.connect(self.refresh_switch)
        self.refresh_switch()

    def has_sources(self):
        try:
            return bool(self.service.manager.list())
        except Exception:
            return False

    def refresh_switch(self, *_):
        have = self.has_sources()
        self.switch_row.setVisible(have)
        if not have and self.stack.currentWidget() is self.sources:
            self.show_view('gamebanana')

    def show_view(self, key):
        """'gamebanana' or 'sources'. An open sheet is closed first; it belongs to the view it was opened in."""
        for page in (self.browse, self.sources):
            if not page.sheet.isHidden():
                page.close_sheet()
        self.stack.setCurrentWidget(self.sources if key == 'sources' and self.has_sources() else self.browse)
        self.switch.set_value('sources' if self.stack.currentWidget() is self.sources else 'gamebanana')

    def current(self):
        return 'sources' if self.stack.currentWidget() is self.sources else 'gamebanana'
