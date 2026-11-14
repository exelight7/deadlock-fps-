"""Backups: go back to the original game files, undo one tool only, move your settings to a file, and see the saved copies.

`BackupsPage` draws and reports; `BackupsMixin` is what the window does (restore through `Studio`, settings files, the shortcuts into the other tools).
Nothing here writes to the game without a confirmation; the current state is always saved before a restore (`Studio.restore`).
"""
import json
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QFrame, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from ..i18n import tr
from ..settings import Settings
from ..shell import theme
from ..shell.components import Banner, Button, Card, Checkbox, EmptyState, List, ListRow, Toast, confirm, mark, text_label


class BackupsPage(QWidget):
    restoreRequested = Signal(bool)         # keep the changes made outside Toolbox?
    folderRequested = Signal()
    undoRequested = Signal(str)             # 'crosshair', 'mods' or 'servers'
    exportRequested = Signal()
    importRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        mark(self, 'BackupsPage')
        t = theme.current()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)
        inner = QWidget()
        inner.setMaximumWidth(1080)
        v = QVBoxLayout(inner)
        v.setContentsMargins(0, 0, 12, 0)
        v.setSpacing(t.px('space.4'))
        scroll.setWidget(inner)

        self.notice_box = QVBoxLayout()
        v.addLayout(self.notice_box)

        card = Card(tr('Go back to the original game files'), tr('The first time Toolbox changes a file, it keeps the original. Restoring puts the originals back and saves the current state first, so even a restore can be undone.'))
        self.keep = Checkbox(tr('Keep changes made outside Toolbox'))
        self.keep.setToolTip(tr('Use this after a game update changed the files: Toolbox saves what is there now, then restores.'))
        card.body.addWidget(self.keep)
        row = QHBoxLayout()
        self.restore_button = Button(tr('Restore the originals'), 'danger-quiet', icon='history')
        self.restore_button.clicked.connect(lambda: self.restoreRequested.emit(self.keep.isChecked()))
        self.folder_button = Button(tr('Open the backups folder'), 'secondary', icon='folder')
        self.folder_button.clicked.connect(self.folderRequested.emit)
        row.addWidget(self.restore_button)
        row.addWidget(self.folder_button)
        row.addStretch(1)
        card.body.addLayout(row)
        v.addWidget(card)

        undo = Card(tr('Undo one tool only'), tr('Each tool keeps its own way back. These are shortcuts, and each one shows a review before it does anything.'))
        lst = List(variant='flat')
        undo.body.addWidget(lst)
        self.undo_buttons = {}
        for key, title, line in (('crosshair', tr('الكروس هير'), tr('استرجاع آخر كروس هير كان في اللعبة قبل التطبيق.')),
                                 ('mods', tr('المودات'), tr('إزالة مودات الأداة واسترجاع ملفات اللعبة الأصلية.')),
                                 ('servers', tr('السيرفرات'), tr('فك كل حظر أنشأته الأداة.'))):
            button = Button(tr('مراجعة التراجع'), 'secondary', 'sm')
            button.clicked.connect(lambda _=False, k=key: self.undoRequested.emit(k))
            self.undo_buttons[key] = button
            lst.add(ListRow(title, line, control=button))
        v.addWidget(undo)

        row = QHBoxLayout()
        row.setSpacing(t.px('space.4'))
        move = Card(tr('Move your settings'), tr('Save the graphics choices to a file, or load a file you saved. It holds no game files and nothing about your accounts.'))
        buttons = QHBoxLayout()
        self.export_button = Button(tr('Save to a file'), 'secondary', icon='download')
        self.export_button.clicked.connect(self.exportRequested.emit)
        self.import_button = Button(tr('Load from a file'), 'secondary', icon='folder')
        self.import_button.clicked.connect(self.importRequested.emit)
        buttons.addWidget(self.export_button)
        buttons.addWidget(self.import_button)
        buttons.addStretch(1)
        move.body.addLayout(buttons)
        move.body.addStretch(1)
        row.addWidget(move, 1)
        self.copies = Card(tr('Saved copies'), tr('The state Toolbox saved just before each restore.'))
        self.copy_list = List(variant='flat')
        self.copies.body.addWidget(self.copy_list)
        self.copies_empty = EmptyState('history', tr('Nothing to restore yet'), tr('Copies appear here after the first restore.'))
        self.copies.body.addWidget(self.copies_empty)
        row.addWidget(self.copies, 1)
        v.addLayout(row)
        v.addStretch(1)
        self.set_copies([])

    def say(self, title, text='', variant='info'):
        """One notice at the top, in the colour of what happened (`''` clears it)."""
        while self.notice_box.count():
            old = self.notice_box.takeAt(0).widget()
            if old is not None:
                old.hide()
                old.setParent(None)
                old.deleteLater()
        if title:
            self.notice = Banner(title, text, variant)
            self.notice_box.addWidget(self.notice)

    def set_copies(self, copies):
        """`copies` is a list of (when, number of files), newest first."""
        self.copy_list.clear()
        for when, files in copies[:8]:
            self.copy_list.add(ListRow(when, tr('{0} files').format(files) if files != 1 else tr('1 file')))
        self.copy_list.setVisible(bool(copies))
        self.copies_empty.setVisible(not copies)

    def set_busy(self, busy):
        for button in (self.restore_button, self.export_button, self.import_button, *self.undo_buttons.values()):
            button.setEnabled(not busy)


def history_rows(studio):
    """What was saved just before earlier restores, newest first: (a readable time, how many files)."""
    folder = studio.store / 'history'
    rows = []
    if folder.is_dir():
        for entry in sorted((p for p in folder.iterdir() if p.is_dir()), reverse=True):
            try:
                when = datetime.strptime(entry.name[:15], '%Y%m%dT%H%M%S').strftime('%Y-%m-%d %H:%M')
            except ValueError:
                when = entry.name
            rows.append((when, max(0, len([p for p in entry.glob('*.bin')]))))
    return rows


class BackupsMixin:
    """What the window does with `self.backups_page`."""

    def build_backups(self):
        page = self.backups_page = BackupsPage()
        page.restoreRequested.connect(self.restore)
        page.folderRequested.connect(self.open_backups)
        page.undoRequested.connect(self.undo_tool)
        page.exportRequested.connect(self.export_settings)
        page.importRequested.connect(self.import_settings)
        self.add_slot('recovery', page)

    def refresh_backups(self):
        try:
            self.backups_page.set_copies(history_rows(self.studio()) if self.path.text().strip() else [])
        except Exception:
            self.backups_page.set_copies([])

    def undo_tool(self, key):
        {'crosshair': self.undo_crosshair, 'mods': self.undo_mods, 'servers': self.undo_servers}[key]()

    def undo_crosshair(self):
        self.crosshair.review(True)

    def undo_mods(self):
        for check in self.mod_checks.values():
            check.setChecked(False)
        self.navigate('mods.installed')
        self.installed.show_classic()
        self.install_mods()

    def undo_servers(self):
        self.servers.apply_action('clear')

    def restore(self, preserve=False):
        page = self.backups_page
        page.say('')
        if self.mod_task_busy():
            page.say(tr('A mod task is running'), tr('Wait for it to finish, then try again. Nothing was changed.'), 'warning')
            return
        if not self.path.text().strip():
            self.focus_game()
            return
        try:
            studio = self.studio()
            if not confirm(self, tr('Restore the original files?'), tr('The current state is saved first. Then the original files are put back.'), tr('Restore the originals'), danger=True):
                return
            self.guard.setChecked(False)
            message = studio.restore(preserve)
            self.guard_signature = None
            self.refresh_mod_library()
            self.refresh_backups()
            Toast(self.centralWidget(), message)
        except Exception as error:
            text = str(error)
            if 'خارج البرنامج' in text or 'outside' in text:
                page.say(tr('The game files changed outside Toolbox'), tr('Tick “Keep changes made outside Toolbox” above, then restore again. Nothing was changed.'), 'danger')
            else:
                page.say(tr('Nothing was changed'), text, 'danger')

    def open_backups(self):
        try:
            studio = self.studio()
            studio.store.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(studio.store)))
        except Exception as error:
            self.backups_page.say(tr('Could not open the folder'), str(error), 'danger')

    def export_settings(self):
        try:
            s = self.settings()
            name, _ = QFileDialog.getSaveFileName(self, tr('تصدير'), 'deadlock-profile.json', 'JSON (*.json)')
            if name:
                Path(name).write_text(json.dumps(s.to_dict(), indent=2))
                Toast(self.centralWidget(), tr('تم تصدير الإعدادات.'))
        except Exception as error:
            self.backups_page.say(tr('Could not save the file'), str(error), 'danger')

    def import_settings(self):
        try:
            name, _ = QFileDialog.getOpenFileName(self, tr('استيراد'), '', 'JSON (*.json)')
            if name:
                s = Settings.from_dict(json.loads(Path(name).read_text()))
                s.validate()
                self.load_settings(s)
                self.navigate('performance.level')
                Toast(self.centralWidget(), tr('تم الاستيراد • راجع ثم طبّق.'))
        except Exception as error:
            self.backups_page.say(tr('That file could not be used'), str(error), 'danger')
