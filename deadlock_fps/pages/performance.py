"""Performance › Level and Performance › Every setting, and the review before anything is written.

`LevelPage` holds the three choices (level, view width, frame limit) and the "leave out" list; it only draws and reports.
`AllSettingsPage` lists every setting the level writes (Valve's data, `perf.explain`) with a checkbox to leave one out.
`PerformanceMixin` is what the window does with them: build the settings, show the review Dialog, apply through `Studio`.
"""
import copy
import difflib
from dataclasses import replace

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QPlainTextEdit, QScrollArea, QVBoxLayout, QWidget

from ..core import ensure_closed
from ..i18n import tr
from ..mod_inspector import require_mods
from ..perf import CATEGORIES, CHECKED_ON, CONVAR_BUILD, STATUS_LABELS, STATUS_TEXT, explain, ignored_names
from ..perf.knowledge import ACTIVE, BLOCKED, REMOVED
from ..settings import MAX_LEVEL, PRESETS, Settings, level_info
from ..shell import theme
from ..shell.components import (ActionBar, Badge, Banner, Button, Card, Checkbox, DataTable, Dialog, EmptyState, KeyValue, LinkButton,
                                SegmentedControl, Select, Slider, StatTile, Switch, Toast, mark, text_label)
from ..ui_common import ltr
from .browse import mono

PRESET_KEYS = ('balanced', 'performance', 'ultra')
STATUS_VARIANT = {ACTIVE: 'success', BLOCKED: 'danger', REMOVED: 'danger'}      # cheat-only and unverified are amber


def preset_names():
    return {'balanced': tr('Balanced'), 'performance': tr('Performance'), 'ultra': tr('Maximum')}


def aspect_text(value):
    return '%.2f' % (value / 100)


def fps_text(value):
    return '%d FPS' % value if value else tr('No limit')


def level_badges(level):
    """What a level does, in four short facts (textures, shadows, fog, effects), as (text, variant) pairs."""
    s = Settings.at_level(level)
    return [(tr('Textures {0}/4').format(s.textures), 'neutral'),
            (tr('Shadows on') if s.shadows else tr('No shadows'), 'neutral'),
            (tr('Fog on') if s.fog else tr('No fog'), 'neutral'),
            (tr('Effects {0}/2').format(s.particles), 'neutral')]


def scrolling(inner):
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setWidget(inner)
    return scroll


class LevelPage(QWidget):
    """The level, the view width and the frame limit, with the action bar that starts the review."""
    changed = Signal()
    reviewRequested = Signal()
    detailsRequested = Signal()
    gameRequired = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        mark(self, 'LevelPage')
        self.linked = False
        self.skip = ()
        t = theme.current()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(t.px('space.3'))
        inner = QWidget()
        column = QVBoxLayout(inner)
        column.setContentsMargins(0, 0, 12, 0)
        column.setSpacing(t.px('space.4'))
        outer.addWidget(scrolling(inner), 1)

        self.game_notice = Banner(tr('Link the game to apply'), tr('The controls work, but nothing can be written until a Deadlock folder is linked.'), 'warning')
        link = Button(tr('Link the game'), 'secondary', 'sm')
        link.clicked.connect(self.gameRequired.emit)
        self.game_notice.add_action(link)
        column.addWidget(self.game_notice)
        self.error = Banner('', '', 'danger')
        self.error.hide()
        column.addWidget(self.error)

        card = Card(tr('How much to lighten the game'), tr('Screen resolution and FSR/DLSS are never changed.'))
        names = preset_names()
        self.presets = SegmentedControl([(key, names[key]) for key in PRESET_KEYS])
        self.presets.changed.connect(self.load_preset)
        card.body.addWidget(self.presets, 0, Qt.AlignLeading)
        head = QHBoxLayout()
        self.level_number = text_label('', 'StatValue', wrap=False)
        self.level_number.setLayoutDirection(Qt.LeftToRight)
        head.addWidget(self.level_number)
        self.level_name = text_label('', 'RowTitle', wrap=False)
        head.addWidget(self.level_name, 1)
        card.body.addLayout(head)
        self.level_text = text_label('', 'CardText')
        card.body.addWidget(self.level_text)
        self.level = Slider(0, MAX_LEVEL, 0)
        self.level.setLayoutDirection(Qt.LeftToRight)
        self.level.valueChanged.connect(self.level_changed)
        card.body.addWidget(self.level)
        ends = QHBoxLayout()
        ends.addWidget(text_label(tr('Best looks'), 'Muted', wrap=False))
        ends.addStretch()
        ends.addWidget(text_label(tr('Most frames'), 'Muted', wrap=False))
        holder = QWidget()
        holder.setLayoutDirection(Qt.LeftToRight)
        holder.setLayout(ends)
        ends.setContentsMargins(0, 0, 0, 0)
        card.body.addWidget(holder)
        self.badges = QHBoxLayout()
        self.badges.setSpacing(t.px('space.2'))
        card.body.addLayout(self.badges)
        self.details = LinkButton(tr('What does this level change?'))
        self.details.clicked.connect(self.detailsRequested.emit)
        card.body.addWidget(self.details, 0, Qt.AlignLeading)
        column.addWidget(card)

        card = Card(tr('View width'), tr('Wider than 16:9 shows more at the sides. It needs a restart of the game and does not change your screen resolution.'))
        row = QHBoxLayout()
        row.addWidget(text_label(tr('Aspect ratio'), 'RowTitle', wrap=False), 1)
        self.aspect_value = text_label('1.78', 'StatValue', wrap=False)
        self.aspect_value.setLayoutDirection(Qt.LeftToRight)
        row.addWidget(self.aspect_value)
        card.body.addLayout(row)
        self.aspect = Slider(178, 350, 178)
        self.aspect.setLayoutDirection(Qt.LeftToRight)
        self.aspect.valueChanged.connect(self.aspect_changed)
        card.body.addWidget(self.aspect)
        ends = QHBoxLayout()
        ends.setContentsMargins(0, 0, 0, 0)
        ends.addWidget(text_label('1.78 · 16:9', 'Muted', wrap=False))
        ends.addStretch()
        ends.addWidget(text_label('3.50', 'Muted', wrap=False))
        holder = QWidget()
        holder.setLayoutDirection(Qt.LeftToRight)
        holder.setLayout(ends)
        card.body.addWidget(holder)
        reset = Button(tr('Back to 1.78'), 'ghost', 'sm', icon='refresh')
        reset.clicked.connect(lambda: self.aspect.setValue(178))
        card.body.addWidget(reset, 0, Qt.AlignLeading)
        column.addWidget(card)

        card = Card(tr('Frame limit'), tr('Separate from the level and the view width. 0 means no limit.'))
        row = QHBoxLayout()
        row.addWidget(text_label(tr('Highest frames per second'), 'RowTitle', wrap=False), 1)
        self.fps_value = text_label(fps_text(0), 'StatValue', wrap=False)
        self.fps_value.setLayoutDirection(Qt.LeftToRight)
        row.addWidget(self.fps_value)
        card.body.addLayout(row)
        self.fps = Slider(0, 500, 0)
        self.fps.setLayoutDirection(Qt.LeftToRight)
        self.fps.valueChanged.connect(self.fps_changed)
        card.body.addWidget(self.fps)
        column.addWidget(card)
        column.addStretch(1)

        self.bar = ActionBar()
        self.review_button = Button(tr('Review and apply'), 'primary', icon='check')
        self.review_button.clicked.connect(self.reviewRequested.emit)
        self.bar.add(self.review_button)
        outer.addWidget(self.bar)
        self.level_changed(0)
        self.aspect_changed(178)
        self.set_linked(False)

    # ---- what the user chose -------------------------------------------------------------

    def values(self):
        return dict(level=self.level.value(), aspect_ratio=self.aspect.value() / 100, fps=self.fps.value(), skip=tuple(self.skip))

    def set_values(self, level, aspect_ratio, fps, skip):
        """Put a whole choice on the page (a preset, a saved profile). One `changed` at the end."""
        for slider in (self.level, self.aspect, self.fps):
            slider.blockSignals(True)
        self.level.setValue(level)
        self.aspect.setValue(round((aspect_ratio if aspect_ratio is not None else 1.78) * 100))
        self.fps.setValue(fps)
        for slider in (self.level, self.aspect, self.fps):
            slider.blockSignals(False)
        self.skip = tuple(skip)
        self.level_changed(self.level.value(), emit=False)
        self.aspect_changed(self.aspect.value(), emit=False)
        self.fps_changed(self.fps.value(), emit=False)
        self.changed.emit()

    def load_preset(self, key):
        preset = copy.deepcopy(PRESETS[key])
        self.set_values(preset.level, self.aspect.value() / 100, self.fps.value(), ())

    def level_changed(self, value, emit=True):
        name, text = level_info(value)
        self.level_number.setText('%d / %d' % (value, MAX_LEVEL))
        self.level_name.setText(name)
        self.level_text.setText(text)
        match = next((k for k in PRESET_KEYS if PRESETS[k].level == value), None)
        self.presets.set_value(match)
        while self.badges.count():
            item = self.badges.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        for text, variant in level_badges(value):
            self.badges.addWidget(Badge(text, variant))
        self.badges.addStretch(1)
        if emit:
            self.skip = ()           # the list belongs to the level it was made for
            self.changed.emit()
        self.refresh_details()

    def aspect_changed(self, value, emit=True):
        self.aspect_value.setText(aspect_text(value))
        if emit:
            self.changed.emit()

    def fps_changed(self, value, emit=True):
        self.fps_value.setText(fps_text(value))
        if emit:
            self.changed.emit()

    def set_skip(self, skip):
        self.skip = tuple(skip)
        self.refresh_details()
        self.changed.emit()

    def refresh_details(self):
        self.details.setText(tr('What does this level change?') + (tr(' · {0} left out').format(len(self.skip)) if self.skip else ''))

    def summary(self):
        return tr('Level {0}/{1} · view width {2} · {3}').format(self.level.value(), MAX_LEVEL, aspect_text(self.aspect.value()), fps_text(self.fps.value()))

    # ---- states --------------------------------------------------------------------------

    def set_linked(self, linked):
        self.linked = bool(linked)
        self.game_notice.setVisible(not self.linked)
        self.review_button.setEnabled(self.linked)
        self.review_button.setToolTip('' if self.linked else tr('Link the game to apply'))
        self.bar.summary.setText(self.summary())

    def show_error(self, title, text=''):
        self.error.title.setText(title)
        self.error.text.setText(text)
        self.error.text.setVisible(bool(text))
        self.error.setVisible(bool(title))

    def set_busy(self, busy, text=''):
        self.review_button.set_busy(busy)
        self.bar.summary.setText(text if busy and text else self.summary())

    def refresh_summary(self):
        if not self.review_button.busy:
            self.bar.summary.setText(self.summary())


class AllSettingsPage(QWidget):
    """Every setting a level writes, in plain words, with what Valve's data says; a Checkbox leaves any of them out."""
    skipChanged = Signal(tuple)

    def __init__(self, settings_provider, parent=None):
        super().__init__(parent)
        mark(self, 'AllSettingsPage')
        self.settings_provider = settings_provider
        self.items = []
        self.boxes = []
        self._building = False
        t = theme.current()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(t.px('space.3'))
        self.intro = text_label(tr("These are the settings the chosen level writes. The status comes from Valve's own data for game build {0} (checked {1}), not from a test in the game; a game update can change it.").format(CONVAR_BUILD, CHECKED_ON), 'CardText')
        outer.addWidget(self.intro)
        self.sight = Banner('', '', 'info')
        self.sight.hide()
        outer.addWidget(self.sight)
        tiles = QHBoxLayout()
        tiles.setSpacing(t.px('space.3'))
        self.tile_written = StatTile('0', tr('will be written'))
        self.tile_confirmed = StatTile('0', tr('confirmed by Valve'))
        self.tile_ignored = StatTile('0', tr('the game ignores'))
        self.tile_unsure = StatTile('0', tr('not sure'))
        for tile in (self.tile_written, self.tile_confirmed, self.tile_ignored, self.tile_unsure):
            tiles.addWidget(tile, 1)
        outer.addLayout(tiles)
        row = QHBoxLayout()
        row.setSpacing(t.px('space.3'))
        self.category = Select()
        self.category.addItem(tr('All groups'), '')
        for key, label in CATEGORIES.items():
            self.category.addItem(label, key)
        self.category.currentIndexChanged.connect(self.filter)
        row.addWidget(self.category)
        self.only_ignored = Switch(tr('Only what the game ignores'))
        self.only_ignored.toggled.connect(self.filter)
        row.addWidget(self.only_ignored)
        row.addStretch(1)
        self.leave_button = Button(tr('Leave out the ignored ones'), 'secondary', 'sm')
        self.leave_button.clicked.connect(self.leave_out_ignored)
        row.addWidget(self.leave_button)
        self.write_button = Button(tr('Write everything'), 'secondary', 'sm')
        self.write_button.clicked.connect(self.write_everything)
        row.addWidget(self.write_button)
        outer.addLayout(row)
        self.table = DataTable([tr('Write'), tr('Setting'), tr("Valve's value"), tr('Written'), tr('Does the game apply it?')], numeric=(2, 3))
        self.empty = EmptyState('search', tr('No setting matches'), tr('Change the group or switch the filter off.'), Button(tr('Clear the filter'), 'secondary'))
        self.empty.button.clicked.connect(self.clear_filter)
        self.empty.hide()
        outer.addWidget(self.table, 1)
        outer.addWidget(self.empty)

    def showEvent(self, event):
        super().showEvent(event)
        self.reload()

    def reload(self):
        """Read the window's current settings again (the level may have changed since this page was last seen)."""
        settings = self.settings_provider()
        self.base = replace(settings, skip=())
        self.current_skip = tuple(settings.skip)
        self.build()

    def build(self):
        self._building = True
        report = explain(self.base)
        self.items = report.items
        self.boxes = []
        self.table.setRowCount(0)
        for item in self.items:
            row = self.table.rowCount()
            self.table.insertRow(row)
            box = Checkbox()
            box.setChecked(item.name not in self.current_skip)
            if item.entry.protected:
                box.setChecked(True)
                box.setEnabled(False)
                box.setToolTip(tr('This one has its own control, so it cannot be left out here.'))
            box.toggled.connect(self.changed)
            holder = QWidget()
            lay = QHBoxLayout(holder)
            lay.setContentsMargins(12, 0, 0, 0)
            lay.addWidget(box)
            self.table.setCellWidget(row, 0, holder)
            self.boxes.append(box)
            cell = QWidget()
            cell_box = QVBoxLayout(cell)
            cell_box.setContentsMargins(8, 4, 8, 4)
            cell_box.setSpacing(0)
            name = mono(text_label(item.name, 'KeyValueValue', wrap=False))
            cell_box.addWidget(name)
            effect = item.entry.effect + ((' · ' + tr('can change what you see')) if item.entry.sight else '')
            cell_box.addWidget(text_label(effect, 'Muted', wrap=False))
            cell.setToolTip('%s\n%s' % (CATEGORIES[item.entry.category], tr('Written to {0}').format(item.where)))
            self.table.setCellWidget(row, 1, cell)
            self.table.setItem(row, 1, self.plain(item.name))
            self.table.setItem(row, 2, self.plain(ltr(item.entry.default or '—'), True))
            self.table.setItem(row, 3, self.plain(ltr(item.value), True))
            status = Badge(STATUS_LABELS[item.entry.status] + (' · ' + tr('build {0}').format(item.entry.since) if item.entry.since else ''), STATUS_VARIANT.get(item.entry.status, 'warning'))
            status.setToolTip(STATUS_TEXT[item.entry.status])
            holder = QWidget()
            lay = QHBoxLayout(holder)
            lay.setContentsMargins(8, 0, 8, 0)
            lay.addWidget(status, 0, Qt.AlignLeading | Qt.AlignVCenter)
            lay.addStretch(1)
            self.table.setCellWidget(row, 4, holder)
            self.table.setRowHeight(row, 52)
        self.table.setColumnWidth(0, 72)
        self.table.setColumnWidth(1, 300)
        self.table.setColumnWidth(2, 110)
        self.table.setColumnWidth(3, 110)
        self._building = False
        self.refresh()
        self.filter()

    @staticmethod
    def plain(text, numeric=False):
        from PySide6.QtWidgets import QTableWidgetItem
        item = QTableWidgetItem(text)
        item.setTextAlignment((Qt.AlignTrailing if numeric else Qt.AlignLeading) | Qt.AlignVCenter)
        if not numeric:
            item.setForeground(Qt.transparent)          # the name is drawn by the cell widget; the item only carries it for reading by tests and tools
        return item

    # ---- what the user chose -------------------------------------------------------------

    def skip(self):
        """The names left out, sorted. Settings with their own controls are never in it."""
        return tuple(sorted(item.name for item, box in zip(self.items, self.boxes) if not item.entry.protected and not box.isChecked()))

    def refresh(self):
        report = explain(replace(self.base, skip=self.skip()))
        self.tile_written.set_value(str(report.written))
        self.tile_confirmed.set_value(str(report.confirmed))
        self.tile_ignored.set_value(str(report.ignored))
        self.tile_unsure.set_value(str(report.uncertain))
        self.summary_text = tr('{0} settings would be written: {1} confirmed by Valve\'s data, {2} the game should ignore, {3} that cannot be confirmed. {4} left out.').format(report.written, report.confirmed, report.ignored, report.uncertain, report.left_out)
        if report.sight:
            self.sight.title.setText(tr('{0} of them can change how much of the world you can see (fog, grass, clutter, view width).').format(report.sight))
            self.sight.text.setText(tr('Some players treat that as an advantage; check the rules of the game you play.'))
            self.sight.text.show()
            self.sight.show()
        else:
            self.sight.hide()

    def changed(self, *_):
        if self._building:
            return
        self.refresh()
        self.filter()
        self.current_skip = self.skip()
        self.skipChanged.emit(self.current_skip)

    def set_all(self, names):
        self._building = True
        for item, box in zip(self.items, self.boxes):
            if not item.entry.protected:
                box.setChecked(item.name not in names)
        self._building = False
        self.changed()

    def leave_out_ignored(self):
        self.set_all(set(ignored_names(self.base)))

    def write_everything(self):
        self.set_all(set())

    def clear_filter(self):
        self.category.setCurrentIndex(0)
        self.only_ignored.setChecked(False)

    def filter(self, *_):
        wanted, only = self.category.currentData() or '', self.only_ignored.isChecked()
        shown = 0
        for number, item in enumerate(self.items):
            hidden = (bool(wanted) and item.entry.category != wanted) or (only and item.entry.status not in ('removed', 'blocked'))
            self.table.setRowHidden(number, hidden)
            shown += not hidden
        self.table.setVisible(bool(shown))
        self.empty.setVisible(not shown and bool(self.items))


class ApplyReview(Dialog):
    """The review before anything is written: what changes and in which files, with every line on request."""

    def __init__(self, plan, settings, parent=None):
        name, _ = level_info(settings.level)
        super().__init__(tr('Review the changes'), '', 'review', tr('Apply'), tr('Cancel'), False, parent)
        self.setMinimumWidth(theme.current().px('size.dialog.md') + 120)
        safe = Banner(tr('The originals are saved first'), tr('You can go back from Backups at any time.'), 'success')
        self.body.addWidget(safe)
        facts = KeyValue([(tr('Level'), '%d / %d · %s' % (settings.level, MAX_LEVEL, name)),
                          (tr('View width'), aspect_text(round((settings.aspect_ratio or 1.78) * 100))),
                          (tr('Frame limit'), fps_text(settings.fps)),
                          (tr('Left out'), str(len(settings.skip)))])
        self.body.addWidget(facts)
        self.table = DataTable([tr('File'), tr('What changes')])
        lines = {}
        for path, data in plan.items():
            if data is None:
                what = tr('Removed (a file Toolbox added)')
            elif path.suffix in {'.gi', '.txt'}:
                old = path.read_text(errors='replace') if path.exists() else ''
                diff = list(difflib.unified_diff(old.splitlines(True), data.decode().splitlines(True), fromfile='current', tofile='proposed'))
                changed = sum(1 for l in diff if l[:1] in '+-' and l[:3] not in ('+++', '---'))
                what = tr('{0} lines change').format(changed)
                lines[str(path)] = ''.join(diff)
            else:
                what = tr('Installs a VPK: {0:,} bytes').format(len(data))
            self.table.add_row([str(path), what])
        self.table.setColumnWidth(0, 360)
        self.table.setMinimumHeight(min(260, 44 * (len(plan) + 1) + 8))
        self.body.addWidget(self.table)
        self.every = Button(tr('Show every line'), 'ghost', 'sm')
        self.every.setCheckable(True)
        self.body.addWidget(self.every, 0, Qt.AlignLeading)
        self.diff = QPlainTextEdit()
        self.diff.setReadOnly(True)
        self.diff.setLayoutDirection(Qt.LeftToRight)
        self.diff.setPlainText('\n\n'.join('%s\n%s' % (p, d) for p, d in lines.items()) or tr('Nothing to show.'))
        self.diff.setMinimumHeight(180)
        self.diff.hide()
        self.every.toggled.connect(self.diff.setVisible)
        self.body.addWidget(self.diff)
        self.setMinimumHeight(0)


class PerformanceMixin:
    """What the window does with the two Performance pages (`self.level_page`, `self.all_page`)."""
    skip = ()

    @property
    def level(self):
        return self.level_page.level

    @property
    def aspect(self):
        return self.level_page.aspect

    def build_performance(self):
        self.level_page = LevelPage()
        self.level_page.changed.connect(self.performance_changed)
        self.level_page.reviewRequested.connect(self.preview)
        self.level_page.detailsRequested.connect(lambda: self.navigate('performance.all'))
        self.level_page.gameRequired.connect(self.focus_game)
        self.add_slot('graphics', self.level_page)
        self.all_page = AllSettingsPage(self.settings)
        self.all_page.skipChanged.connect(self.set_skip)
        self.add_slot('perf_all', self.all_page)

    def performance_changed(self):
        self.skip = tuple(self.level_page.skip)
        self.level_page.refresh_summary()
        if hasattr(self, 'home'):
            self.refresh_home()

    def set_skip(self, skip):
        self.level_page.set_skip(skip)
        self.skip = tuple(skip)

    def load_settings(self, s):
        self.level_page.set_values(s.level, s.aspect_ratio, s.fps, s.skip)
        for key, b in self.mod_checks.items():
            b.setChecked(key in s.mods)
        self.skip = tuple(s.skip)

    def load_preset(self, key):
        s = copy.deepcopy(PRESETS[key])
        s.aspect_ratio = self.level_page.aspect.value() / 100
        s.fps = self.level_page.fps.value()
        self.load_settings(s)

    def settings(self):
        page = self.level_page.values()
        s = Settings.at_level(page['level'], aspect_ratio=page['aspect_ratio'], fps=page['fps'], preset='custom',
                              mods=tuple(k for k, b in self.mod_checks.items() if b.isChecked()), skip=page['skip'])
        s.validate()
        return s

    def preview(self):
        """Review, then apply. Errors stay on the page as a banner and nothing is written."""
        page = self.level_page
        page.show_error('')
        if self.mod_task_busy():
            page.show_error(tr('A mod task is running'), tr('Wait for it to finish, then try again. Nothing was changed.'))
            return
        if not self.path.text().strip():
            self.focus_game()
            self.connection_note.setText(tr('باقي خطوة واحدة: اختر مجلد اللعبة أولًا.'))
            return
        try:
            studio = self.studio()
            s = self.settings()
            plan = studio.plan(s, self.library.cache)
            require_mods(self.library, studio.root, s.mods)
            if not plan:
                Toast(self.centralWidget(), tr('Already applied. Nothing to change.'))
                return
            dialog = ApplyReview(plan, s, self)
            if dialog.exec() != QDialog.Accepted:
                return
            fresh = studio.plan(s, self.library.cache)
            if fresh != plan:
                raise ValueError(tr('The files changed during the review. Review again.'))
            page.set_busy(True, tr('Saving the originals, then writing {0} files…').format(len(plan)))
            try:
                ensure_closed()
                message = studio.apply(plan, s)
            finally:
                page.set_busy(False)
            self.refresh_mod_library()
            self.applied_message = message
            Toast(self.centralWidget(), tr('Applied. Start the game to see it.'), self.undo_apply, tr('Undo'))
        except Exception as error:
            page.set_busy(False)
            page.show_error(tr('Nothing was changed'), str(error))

    def undo_apply(self):
        try:
            self.studio().restore()
            self.refresh_mod_library()
        except Exception as error:
            self.level_page.show_error(tr('Could not undo'), str(error))
