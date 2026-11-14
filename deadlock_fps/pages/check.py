"""Mods > Check: are the installed mods intact, loaded, and not fighting each other, and do they fit the game version.

Read-only: nothing here changes a file except the one *Repair* button, which re-registers `citadel/addons` in
`gameinfo.gi` (the same operation as the Installed page used to offer and Home's attention list still does). The page draws what
`Installer.analyze()` and `ModService.statuses()` say; problems come first, each with a plain title, one sentence and at most one action.
"""
import json
import threading
import time
from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool, QTimer, Signal
from PySide6.QtWidgets import QFileDialog, QFrame, QHBoxLayout, QHeaderView, QScrollArea, QVBoxLayout, QWidget

from ..core import atomic
from ..hub_ui import failure_text
from ..i18n import tr
from ..installer import InstallError
from ..mod_inspector import inspect_mods
from ..repos.compat import fit
from ..repos.model import GameFit
from ..ui_common import Job
from ..shell import theme
from ..shell.components import Badge, Banner, Button, Card, DataTable, EmptyState, List, ListRow, Toast, breakable, mark, text_label
from ..ui_common import ltr
from .browse import ago_text, plural

SEVERITY = {'error': 'danger', 'warning': 'warning', 'info': 'info'}
ORDER = {'error': 0, 'warning': 1, 'info': 2}


def finding_words(issue):
    """(plain title, one sentence, icon) for an engine finding. The sentence is the engine's own text where it has the detail."""
    code, subject, detail = issue.code, issue.subject, issue.detail
    if code == 'inactive':
        return tr('Your mods are switched off in the game'), tr('Steam restored a game file, so the game no longer loads the mod folder.'), 'warn'
    if code == 'missing':
        return tr('{0} has a missing file').format(subject), detail, 'warn'
    if code == 'modified':
        return tr('{0} was changed after it was installed').format(subject), detail, 'warn'
    if code == 'damaged':
        return tr('{0} has a damaged file').format(subject), detail, 'warn'
    if code == 'overlap':
        return tr('Two mods change the same files'), '%s: %s' % (subject, detail), 'warn'
    if code == 'dependency':
        return tr('{0} needs another mod').format(subject), detail, 'warn'
    if code == 'unreadable':
        return tr('A file could not be read'), '%s: %s' % (subject, detail), 'warn'
    return subject, detail, 'info'


def fit_badge(version, build):
    """(words, Badge variant) for how a mod's newest version fits the linked game's build."""
    if version is None:
        return tr('Unknown'), 'neutral'
    kind = fit(version.game, build)
    return {GameFit.COMPATIBLE: (tr('Fits'), 'success'), GameFit.UNTESTED: (tr('Not tested on this version'), 'warning'),
            GameFit.INCOMPATIBLE: (tr('Other game version'), 'danger'), GameFit.UNKNOWN: (tr('Unknown'), 'neutral')}[kind]


def made_for(version):
    """The game builds a mod says it was made for, in plain words."""
    if version is None:
        return tr('not stated')
    low, high = version.game.min_build, version.game.max_build
    if low is not None and high is not None:
        return tr('{0} to {1}').format(ltr(low), ltr(high))
    if low is not None:
        return tr('{0} and newer').format(ltr(low))
    if high is not None:
        return tr('up to {0}').format(ltr(high))
    if version.game.tested_build is not None:
        return tr('tested on {0}').format(ltr(version.game.tested_build))
    return tr('not stated')


class CheckPage(QWidget):
    openRequested = Signal(str)
    gameRequired = Signal()

    def __init__(self, service, scan_inputs=None, parent=None):
        """`scan_inputs()` returns (library, game folder or None, chosen classic mods) for the classic-pack scan; without it that section is left out."""
        super().__init__(parent)
        mark(self, 'CheckPage')
        self.service = service
        self.scan_inputs = scan_inputs
        self.result = None                  # the last classic-pack scan (mod_inspector.Inspection)
        self.scanning = False
        self.cancel_event = None
        self.checked_at = 0
        self.issues = []
        self.failed = False
        self.banner = None
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
        top = QHBoxLayout()
        top.setSpacing(t.px('space.2'))
        self.summary = text_label('', 'CardText')
        top.addWidget(self.summary, 1)
        self.check_button = Button(tr('Check again'), 'secondary', icon='refresh')
        self.check_button.clicked.connect(self.reload)
        top.addWidget(self.check_button)
        self.column.addLayout(top)
        self.note = text_label(tr('Reads your installed files and the addons folder. Nothing is changed.'), 'Muted')
        self.column.addWidget(self.note)

        self.findings = Card(variant='flat')
        self.list = List(variant='flat')
        self.findings.body.addWidget(self.list)
        self.column.addWidget(self.findings)
        self.again_button = Button(tr('Check again'), 'secondary')
        self.again_button.clicked.connect(self.reload)
        self.clear = EmptyState('check', tr('Everything looks fine'), tr('Your mod files are in place and match what was installed.'), self.again_button)
        self.clear.hide()
        self.column.addWidget(self.clear)
        self.try_button = Button(tr('Try again'), 'secondary')
        self.try_button.clicked.connect(self.reload)
        self.broken = EmptyState('warn', tr('The check could not finish'), tr('Nothing was changed. Your mods and the game are as they were.'), self.try_button, variant='danger')
        self.broken.hide()
        self.column.addWidget(self.broken)

        self.classic_card = Card(variant='flat')
        head = QHBoxLayout()
        head.setContentsMargins(t.px('space.4'), t.px('space.4'), t.px('space.4'), t.px('space.2'))
        head.addWidget(text_label(tr('Classic pack'), 'CardTitle'), 1)
        self.scan_text = text_label('', 'Muted')
        head.addWidget(self.scan_text)
        self.export_button = Button(tr('Save the report'), 'ghost', 'sm', icon='download')
        self.export_button.clicked.connect(self.export)
        head.addWidget(self.export_button)
        self.classic_card.body.addLayout(head)
        self.classic_list = List(variant='flat')
        self.classic_card.body.addWidget(self.classic_list)
        self.classic_card.hide()
        self.column.addWidget(self.classic_card)

        self.fits_card = Card(tr('Do they fit your game version?'))
        self.fits = DataTable([tr('Mod'), tr('Made for'), tr('Fit')])
        header = self.fits.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setStretchLastSection(False)
        self.fits.setColumnWidth(2, theme.current().px('space.8') * 7)
        self.fits_card.body.addWidget(self.fits)
        self.column.addWidget(self.fits_card)
        self.column.addStretch(1)
        service.changed.connect(self.reload)
        service.busyChanged.connect(lambda _: self.sync())
        self.reload()

    def showEvent(self, event):
        super().showEvent(event)
        self.reload()
        if self.result is None and not self.scanning:
            self.scan()

    def installer(self):
        try:
            return self.service.installer()
        except InstallError:
            return None

    def sync(self):
        self.check_button.setEnabled(self.installer() is not None and not self.service.busy)

    def reload(self, *_):
        installer = self.installer()
        self.game_notice.setVisible(installer is None)
        self.list.clear()
        self.fits.setRowCount(0)
        self.failed = False
        if installer is None:
            self.issues = []
            self.summary.setText(tr('No game linked.'))
            for widget in (self.findings, self.clear, self.broken, self.fits_card, self.note):
                widget.setVisible(False)
            self.sync()
            return
        try:
            issues = installer.analyze()
            mods = installer.installed()
            statuses = self.service.statuses()
        except (InstallError, OSError, ValueError):
            self.failed = True
            self.issues = []
            self.summary.setText(tr('The check could not finish.'))
            for widget in (self.findings, self.clear, self.fits_card):
                widget.setVisible(False)
            self.broken.setVisible(True)
            self.note.setVisible(True)
            self.sync()
            return
        self.broken.setVisible(False)
        self.note.setVisible(True)
        self.checked_at = time.time()
        self.issues = [i for i in issues if i.severity != 'info' or i.code not in ('unmanaged',)]
        problems = sorted((i for i in self.issues), key=lambda i: (ORDER[i.severity], i.subject))
        for issue in problems:
            title, line, icon = finding_words(issue)
            control = None
            if issue.code == 'inactive':
                control = Button(tr('Repair'), 'primary', 'sm')
                control.clicked.connect(self.repair)
            self.list.add(ListRow(breakable(title), breakable(line), icon, control, tone=SEVERITY[issue.severity]))
        named = {i.subject for i in problems if i.severity in ('error', 'warning')}
        bad = sum(1 for m in mods if any(m.name in subject for subject in named))
        fine = len(mods) - bad
        if mods and fine > 0:
            self.list.add(ListRow(plural(fine, tr('{0} mod is fine'), tr('{0} mods are fine')) if problems else plural(len(mods), tr('{0} mod is fine'), tr('All {0} mods are fine')),
                                  tr('Files are in place and match what was installed.'), 'check', tone='success'))
        self.findings.setVisible(bool(problems))
        self.clear.setVisible(not problems)
        build = self.service.game_build()
        errors = sum(1 for i in problems if i.severity == 'error')
        self.summary.setText(' · '.join([tr('Checked {0}').format(ago_text(self.checked_at)), tr('game build {0}').format(build) if build else tr('game build unknown')]))
        self.fits_card.setVisible(bool(statuses))
        for s in statuses:
            words, variant = fit_badge(s.version, build)
            row = self.fits.add_row([s.mod.name, made_for(s.version), ''])
            holder = QWidget()
            box = QHBoxLayout(holder)
            box.setContentsMargins(0, 0, 0, 0)
            badge = Badge(words, variant)
            box.addWidget(badge, 0, Qt.AlignVCenter)
            box.addStretch(1)
            self.fits.setCellWidget(row, 2, holder)
        self.fits.fit_height()
        self.sync()
        self.errors = errors

    def repair(self):
        self.summary.setText(tr('Repairing…'))
        self.service.operate('repair', (), lambda _: self.reload(), self.repair_failed)

    def repair_failed(self, message, code):
        if self.banner is not None:
            self.banner.setParent(None)
            self.banner.deleteLater()
        lead, _, detail = failure_text(code, message).partition('\n')
        self.banner = Banner(breakable(lead), breakable(detail or tr('Nothing was changed.')), 'danger')
        self.column.insertWidget(1, self.banner)
        self.reload()

    # ---- the classic pack (the old "Inspector") ------------------------------------------

    def scan(self):
        """Read the four classic mods, in the library and in the game, in the background. Nothing is written."""
        if self.scanning or self.scan_inputs is None:
            return
        library, root, selected = self.scan_inputs()
        self.scanning = True
        self.cancel_event = event = threading.Event()
        self.scan_text.setText(tr('Checking in the background…'))
        job = Job(lambda: inspect_mods(library, root, selected, event))
        job.signals.result.connect(self.render_scan)
        job.signals.failure.connect(self.scan_failed)
        job.signals.done.connect(self.scan_done)
        QThreadPool.globalInstance().start(job)

    def cancel(self):
        if self.cancel_event:
            self.cancel_event.set()

    def invalidate(self):
        """The choice or the game files changed: the last scan is out of date. It runs again when the page is on screen."""
        if self.scanning:
            self.cancel()
        self.result = None
        self.classic_list.clear()
        self.classic_card.hide()
        if self.isVisible():
            QTimer.singleShot(0, self.scan)

    def render_scan(self, result):
        if result is None or (self.cancel_event and self.cancel_event.is_set()):
            return
        self.result = result
        self.classic_list.clear()
        absent = tr('غير موجود')
        relevant = any(r['selected'] or r['library'] != absent or r['installed'] != absent for r in result.rows)
        for f in result.findings:
            self.classic_list.add(ListRow(breakable(f.title), breakable(f.detail.split('\n')[0]), 'warn', tone='danger' if f.severity == 'error' else 'warning'))
        good = tr('سليم')
        for r in result.rows:
            words = tr('In the library: {0} · In the game: {1}').format(r['library'], r['installed'])
            damaged = tr('تالف أو معدل') in (r['library'], r['installed'])
            tone = 'danger' if damaged else ('success' if r['library'].startswith(good) or r['installed'].startswith(good) else None)
            badge = Badge(tr('Chosen'), 'info') if r['selected'] else None
            self.classic_list.add(ListRow(r['name'], words, 'check' if tone == 'success' else ('warn' if tone == 'danger' else 'box'), badge, tone=tone))
        self.classic_card.setVisible(relevant or bool(result.findings))
        errors = len(result.errors)
        self.scan_text.setText(tr('{0} problems that stop the install · {1} warnings').format(errors, len(result.findings) - errors))

    def scan_failed(self, message):
        self.result = None
        self.classic_list.clear()
        self.classic_card.show()
        self.classic_list.add(ListRow(tr('The check could not run'), breakable(message), 'warn', tone='danger'))
        self.scan_text.setText('')

    def scan_done(self):
        self.scanning = False
        self.cancel_event = None

    def export(self):
        if not self.result:
            return
        name, _ = QFileDialog.getSaveFileName(self, tr('Save the report'), 'deadlock-mod-inspection.json', 'JSON (*.json)')
        if name:
            try:
                atomic(Path(name), json.dumps(self.result.to_dict(), ensure_ascii=False, indent=2).encode('utf-8'))
                Toast(self, tr('The report was saved.'))
            except Exception as error:
                self.scan_text.setText(breakable(str(error)))
