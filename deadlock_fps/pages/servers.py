"""Servers: measure the Steam relay answer time of every region and choose which regions the game may use (a firewall rule Toolbox owns).

The engines are `deadlock_fps.servers` (catalogue, ping, saved choices) and `deadlock_fps.firewall` (the one elevated step). This page draws them.
Selecting a row never changes anything; only the buttons at the bottom do, after a review. The ping is the relay answer time, not the ping in a match.
Rows are rebuilt in the wanted order (name or lowest ping) instead of sorting the table, so the checkboxes always stay with their rows.
"""
import time
from pathlib import Path

from PySide6.QtCore import QEvent, QSize, QStandardPaths, Qt, QThreadPool, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QHeaderView, QInputDialog, QTableWidgetItem, QVBoxLayout, QWidget)

from ..core import ensure_closed
from ..firewall import apply_elevated
from ..i18n import tr
from ..region_info import flag_icon, region_info
from ..servers import PingResult, ServerStore, ping_regions
from ..shell import theme
from ..shell.components import (ActionBar, Badge, Banner, Button, Checkbox, DataTable, Dialog, EmptyState, IconButton, Menu, ProgressBar, SearchField, Select,
                                confirm, mark, text_label)
from ..ui_common import Job

FAST, SLOW = 60, 120                      # ms: green up to FAST, amber up to SLOW, red above
COMPACT_WIDTH = 700                       # below this the server count column is hidden


def ping_tone(latency):
    """Which colour a measured ping gets."""
    if latency is None:
        return None
    return 'color.success.text' if latency <= FAST else ('color.warning.text' if latency <= SLOW else 'color.danger.text')


class PingCell(QTableWidgetItem):
    """The ping text; sorts (and `numeric` reads) by the number, with unmeasured rows last."""

    def __init__(self, text, numeric=None):
        super().__init__(text)
        self.numeric = numeric
        self.setTextAlignment(Qt.AlignTrailing | Qt.AlignVCenter)

    def __lt__(self, other):
        mine = self.numeric if self.numeric is not None else 1e9
        theirs = getattr(other, 'numeric', None)
        return mine < (theirs if theirs is not None else 1e9)


class ServerPage(QWidget):
    def __init__(self, parent=None, store=None):
        super().__init__(parent)
        mark(self, 'ServerPage')
        self.busy = False
        self.regions = []
        self.measurements = {}
        self._job = None
        self.last_measure = 0
        self.pending = set()
        self.measure_total = 0
        self.selection_locked = False
        self.ping_sorted = False
        self.last_action = ''
        self.boxes = {}                                 # region code → its checkbox
        self.store = store or ServerStore(Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / 'servers')
        t = theme.current()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 12, 0)
        layout.setSpacing(t.px('space.3'))

        self.notice_box = QVBoxLayout()
        layout.addLayout(self.notice_box)
        row = QHBoxLayout()
        row.setSpacing(t.px('space.3'))
        self.search_field = SearchField(tr('ابحث بالعربي أو الإنجليزي: دبي، Frankfurt، ae، dxb'))
        self.search = self.search_field.edit
        self.search.setAccessibleName(tr('بحث'))
        self.search.textChanged.connect(self.filter_rows)
        row.addWidget(self.search_field, 1)
        self.view_filter = Select()
        for caption in (tr('كل المناطق'), tr('الحظر المحفوظ'), tr('المحددة فقط')):
            self.view_filter.addItem(caption)
        self.view_filter.currentIndexChanged.connect(self.filter_rows)
        row.addWidget(self.view_filter)
        self.ping_button = Button(tr('قياس البنق'), 'secondary', icon='refresh')
        self.ping_button.setToolTip(tr('يقيس المناطق المحددة، أو كل المناطق الظاهرة إذا لم تحدد شيئًا.'))
        self.ping_button.clicked.connect(self.measure)
        row.addWidget(self.ping_button)
        self.refresh_button = Button(tr('تحديث القائمة'), 'ghost', icon='download')
        self.refresh_button.clicked.connect(self.refresh)
        row.addWidget(self.refresh_button)
        self.help_button = IconButton('info', tr('شرح'), 'ghost')
        self.help_button.clicked.connect(self.explain)
        row.addWidget(self.help_button)
        layout.addLayout(row)

        row = QHBoxLayout()
        row.setSpacing(t.px('space.2'))
        self.selection_note = text_label('', 'CardText')
        row.addWidget(self.selection_note, 1)
        self.select_visible_button = Button(tr('تحديد الظاهر'), 'ghost', 'sm')
        self.select_visible_button.clicked.connect(self.select_visible)
        self.clear_selection_button = Button(tr('مسح التحديد'), 'ghost', 'sm')
        self.clear_selection_button.clicked.connect(self.clear_selection)
        self.sort_button = Button(tr('الأقل بنقًا'), 'ghost', 'sm')
        self.sort_button.clicked.connect(self.sort_ping)
        self.saved_button = Button(tr('اختياراتي'), 'ghost', 'sm')
        self.saved_menu = Menu(self.saved_button)
        self.saved_button.setMenu(self.saved_menu)
        self.selection_buttons = [self.select_visible_button, self.clear_selection_button, self.sort_button, self.saved_button, self.help_button]
        for button in self.selection_buttons[:4]:
            row.addWidget(button)
        layout.addLayout(row)

        self.progress_row = QWidget()
        pr = QHBoxLayout(self.progress_row)
        pr.setContentsMargins(0, 0, 0, 0)
        self.progress = ProgressBar()
        pr.addWidget(self.progress, 1)
        self.progress_text = text_label('', 'Muted', wrap=False)
        pr.addWidget(self.progress_text)
        self.progress_row.hide()
        layout.addWidget(self.progress_row)

        self.table = DataTable([tr('تحديد'), tr('المنطقة / الدولة'), tr('العدد'), tr('البنق (ms)'), tr('الحظر المحفوظ')], numeric=(2, 3))
        self.table.setIconSize(QSize(32, 24))
        self.table.setWordWrap(False)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setAlternatingRowColors(False)
        self.table.cellClicked.connect(self.toggle_row)
        self.table.installEventFilter(self)
        self.table.viewport().installEventFilter(self)
        self.table.verticalHeader().setDefaultSectionSize(52)
        self.table.setMinimumHeight(250)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for col, width in ((0, 64), (2, 80), (3, 120), (4, 120)):
            header.setSectionResizeMode(col, QHeaderView.Fixed)
            self.table.setColumnWidth(col, width)
        self.table.viewport().setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.table, 1)
        self.empty = EmptyState('globe', tr('لا توجد مناطق مطابقة'), tr('غيّر البحث أو اختر «كل المناطق» من القائمة.'))
        self.empty.hide()
        layout.addWidget(self.empty)
        self.note = text_label(tr('هذا زمن رد الخوادم الوسيطة، وليس البنق داخل المباراة.'), 'Muted')
        layout.addWidget(self.note)

        self.status = text_label(tr('جاهز • اختر المناطق، ثم اختر إجراءً.'), 'CardText')
        self.status.setToolTip(tr('حالة الحظر تمثل الاختيار المحفوظ، وليست فحصًا حيًا لجدار الحماية. Toolbox لا يحذف قواعد البرامج الأخرى.'))
        layout.addWidget(self.status)
        self.actions_panel = ActionBar()
        self.block_button = Button(tr('حظر المحدد'), 'danger-quiet', icon='block')
        self.block_button.clicked.connect(self.block_selected)
        self.only_button = Button(tr('اسمح بالمحدد فقط'), 'secondary', icon='check')
        self.only_button.setToolTip(tr('يسمح بالمحدد ويحظر بقية المناطق. راجع التأكيد قبل التطبيق.'))
        self.only_button.clicked.connect(lambda: self.apply_action('only'))
        self.unblock_button = Button(tr('فك حظر المحدد'), 'secondary')
        self.unblock_button.clicked.connect(lambda: self.apply_action('unblock'))
        self.clear_block_button = Button(tr('فك كل الحظر'), 'ghost')
        self.clear_block_button.setToolTip(tr('يزيل حظر Toolbox كله، حتى بدون تحديد مناطق. لا يحذف قواعد البرامج الأخرى.'))
        self.clear_block_button.clicked.connect(lambda: self.apply_action('clear'))
        for button in (self.block_button, self.only_button, self.unblock_button, self.clear_block_button):
            self.actions_panel.add(button)
        layout.addWidget(self.actions_panel)
        self.buttons = [self.ping_button, self.refresh_button, self.block_button, self.only_button, self.unblock_button, self.clear_block_button, *self.selection_buttons[:4]]
        self.reload_presets()
        try:
            self.set_catalog(self.store.load_catalog())
        except Exception as error:
            self.say(tr('تعذر إكمال العملية: ') + str(error)[:2000], '', 'danger')

    # ---- words ---------------------------------------------------------------------------

    def say(self, title, text='', variant='info'):
        """One notice at the top, in the colour of what happened (an empty title clears it)."""
        while self.notice_box.count():
            old = self.notice_box.takeAt(0).widget()
            if old is not None:
                old.hide()
                old.setParent(None)
                old.deleteLater()
        if title:
            self.notice = Banner(title, text, variant)
            self.notice_box.addWidget(self.notice)

    def explain(self):
        dialog = Dialog(tr('البنق واختيار السيرفرات'), '', 'review', '', tr('إغلاق'), False, self)
        text = tr('البنق قياس ICMP إلى خوادم Steam الوسيطة، وليس بنق المباراة الفعلي.\n\n'
                  'لا رد: قد تكون ردود ICMP محجوبة؛ لا يعني أن سيرفر اللعبة متوقف. تعذر القياس: راجع توضيح الخطأ بالمرور على الخانة.\n\n'
                  'العلامة ✓ تحدد المنطقة للعملية فقط. لإجراء تغيير، اختر الحظر أو السماح بالأزرار أسفل القائمة وراجع التأكيد.\n\n'
                  'آخر اختيار محفوظ لا يمثل فحصًا لجدار الحماية. على Linux أعد تطبيق الحظر بعد إعادة التشغيل. الحظر قد يؤثر على ألعاب Steam الأخرى.\n\n'
                  'إذا استعملت ServerPickerX سابقًا، فك قواعده من البرنامج الأصلي؛ Toolbox يعدل قواعده الخاصة فقط.')
        dialog.body.addWidget(text_label(text, 'CardText'))
        dialog.exec()

    # ---- the table -----------------------------------------------------------------------

    def selected_codes(self):
        return {code for code, box in self.boxes.items() if box.isChecked()}

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(300, self.activate)

    def activate(self):
        if self.isVisible() and not self.busy and time.monotonic() - self.last_measure > 60:
            self.measure()

    def set_catalog(self, result):
        selected = self.selected_codes()
        before = {r.code: r.relays for r in self.regions}
        regions, _revision = result
        self.regions = sorted(regions, key=lambda r: (0 if r.code == 'dxb' else 1 if r.code == 'dfjr' else 2, r.name.casefold()))
        for r in self.regions:
            if before.get(r.code) != r.relays:
                self.measurements.pop(r.code, None)
        self.render(selected)
        self.status.setText(tr('{0} منطقة اتصال • سيبدأ البنق تلقائيًا عند فتح الصفحة، أو اضغط إعادة القياس.').format(len(self.regions)))

    def ordered(self):
        if not self.ping_sorted:
            return self.regions
        def key(region):
            result = self.measurements.get(region.code)
            return (result.latency if result is not None and result.status == 'ok' else 1e9)
        return sorted(self.regions, key=key)

    def render(self, selected=None):
        selected = self.selected_codes() if selected is None else selected
        blocked = set(self.store.state().get('blocked', []))
        self.table.setRowCount(0)
        self.boxes = {}
        regions = self.ordered()
        self.table.setRowCount(len(regions))
        for row, region in enumerate(regions):
            box = Checkbox()
            box.setChecked(region.code in selected)
            box.setToolTip(tr('محدد للعملية فقط، وليس حظرًا. اضغط مرة لتبديل التحديد.'))
            box.setAccessibleName(region.name)
            box.toggled.connect(lambda _on: self.selection_changed())
            holder = QWidget()
            lay = QHBoxLayout(holder)
            lay.setContentsMargins(20, 0, 0, 0)
            lay.addWidget(box)
            self.table.setCellWidget(row, 0, holder)
            self.boxes[region.code] = box
            info = region_info(region)
            name = QTableWidgetItem(info.text(region))
            name.setIcon(flag_icon(info.country))
            name.setData(Qt.UserRole, region.code)
            name.setData(Qt.UserRole + 1, info.search(region))
            name.setToolTip(region.name + ' [' + region.code + ']\n' + info.country_name + '\n' + '\n'.join(f'{r.ip}:{r.first}–{r.last}' for r in region.relays))
            self.table.setItem(row, 1, name)
            count = QTableWidgetItem(str(len(region.relays)))
            count.setTextAlignment(Qt.AlignTrailing | Qt.AlignVCenter)
            self.table.setItem(row, 2, count)
            self.render_measurement(row, region.code)
            holder = QWidget()
            lay = QHBoxLayout(holder)
            lay.setContentsMargins(8, 0, 8, 0)
            if region.code in blocked:
                badge = Badge(tr('حظر محفوظ'), 'danger')
            else:
                badge = Badge(tr('غير محظور'), 'neutral')
            badge.setToolTip(tr('الاختيار المحفوظ؛ لا يمثل فحصًا حيًا لجدار الحماية.'))
            lay.addWidget(badge, 0, Qt.AlignLeading | Qt.AlignVCenter)
            lay.addStretch(1)
            self.table.setCellWidget(row, 4, holder)
            self.table.setRowHeight(row, 52)
        self.filter_rows()

    def find_row(self, code):
        return next((r for r in range(self.table.rowCount()) if self.table.item(r, 1) is not None and self.table.item(r, 1).data(Qt.UserRole) == code), None)

    def render_measurement(self, row, code):
        result = self.measurements.get(code)
        numeric = None
        if code in self.pending:
            ping, detail, tone = tr('جارٍ القياس…'), tr('انتظر وصول الردود.'), None
        elif result is None:
            ping, detail, tone = tr('لم يُقَس'), tr('لم يبدأ القياس لهذه المنطقة بعد.'), None
        elif result.status == 'ok':
            ping = f'{result.latency:.1f}'
            detail = result.detail + tr('\nفقد الردود: ') + str(result.loss) + tr('%\nالعنوان: ') + result.address
            numeric, tone = result.latency, ping_tone(result.latency)
        else:
            ping = tr('لا رد') if result.status == 'no_reply' else (tr('انتهت المهلة') if result.status == 'timeout' else tr('تعذر القياس'))
            detail = result.detail + (tr('\nالعنوان: ') + result.address if result.address else '')
            tone = None
        item = PingCell(ping, numeric)
        item.setToolTip(detail)
        if tone:
            item.setForeground(theme.color(tone))
            font = QFont(self.table.font())
            font.setBold(True)
            item.setFont(font)
        self.table.setItem(row, 3, item)

    def filter_rows(self, *_):
        text = self.search.text().strip().casefold()
        mode = self.view_filter.currentIndex()
        blocked = set(self.store.state().get('blocked', []))
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1)
            if item is None:
                continue
            code = item.data(Qt.UserRole)
            visible = text in (item.data(Qt.UserRole + 1) or item.text().casefold()) and (mode != 1 or code in blocked) and (mode != 2 or self.boxes[code].isChecked())
            self.table.setRowHidden(row, not visible)
        self.update_selection_note()

    def selection_changed(self):
        self.filter_rows()

    def update_selection_note(self):
        count = len(self.selected_codes())
        visible = sum(not self.table.isRowHidden(row) for row in range(self.table.rowCount()))
        hidden = sum(1 for row in range(self.table.rowCount()) if self.table.isRowHidden(row) and self.boxes[self.table.item(row, 1).data(Qt.UserRole)].isChecked())
        self.selection_note.setText((tr('✓ تم تحديد {0} مناطق').format(count) if count else tr('لم تحدد أي منطقة')) + tr(' • الظاهر: {0}').format(visible)
                                    + (tr(' • {0} محدد خارج البحث').format(hidden) if hidden else ''))
        self.selection_note.setProperty('hasSelection', bool(count))
        self.actions_panel.summary.setText(tr('✓ تم تحديد {0} مناطق').format(count) if count else tr('لم تحدد أي منطقة'))
        self.empty.setVisible(not visible and bool(self.regions))
        self.table.setVisible(bool(visible) or not self.regions)
        for button in (self.block_button, self.unblock_button, self.only_button):
            button.setEnabled(bool(count) and not self.busy)

    def toggle_row(self, row, col):
        if col == 0 or self.selection_locked:
            return
        item = self.table.item(row, 1)
        if item is not None:
            box = self.boxes[item.data(Qt.UserRole)]
            box.setChecked(not box.isChecked())

    def eventFilter(self, watched, event):
        if watched is self.table.viewport() and event.type() == QEvent.Resize:
            compact = self.table.viewport().width() < COMPACT_WIDTH
            if compact != getattr(self, '_compact', None):
                self._compact = compact
                self.table.setColumnHidden(2, compact)
        if watched is self.table and event.type() == QEvent.KeyPress and event.key() == Qt.Key_Space and self.table.currentRow() >= 0 and self.table.currentColumn() != 0:
            self.toggle_row(self.table.currentRow(), self.table.currentColumn())
            return True
        return super().eventFilter(watched, event)

    def clear_selection(self):
        for box in self.boxes.values():
            box.blockSignals(True)
            box.setChecked(False)
            box.blockSignals(False)
        self.filter_rows()

    def select_visible(self):
        for row in range(self.table.rowCount()):
            if not self.table.isRowHidden(row):
                box = self.boxes[self.table.item(row, 1).data(Qt.UserRole)]
                box.blockSignals(True)
                box.setChecked(True)
                box.blockSignals(False)
        self.filter_rows()

    def sort_ping(self):
        self.ping_sorted = True
        self.render()

    # ---- background work -----------------------------------------------------------------

    def start(self, fn, success, message, progress=False):
        if self.busy:
            return
        self.busy = True
        self.selection_locked = not progress
        self.status.setText(message)
        self.table.setEnabled(progress)
        self.search.setEnabled(progress)
        self.view_filter.setEnabled(progress)
        for button in self.buttons:
            button.setEnabled(False)
        if progress:
            for button in self.selection_buttons[:4]:
                button.setEnabled(True)
            self.progress_row.show()
            self.progress.setRange(0, max(1, self.measure_total))
            self.progress.setValue(0)
        self._job = Job(fn, progress)
        self._job.signals.progress.connect(self.ping_progress)
        self._job.signals.result.connect(success)
        self._job.signals.failure.connect(self.failed)
        self._job.signals.done.connect(self.finished)
        QThreadPool.globalInstance().start(self._job)

    def finished(self):
        self.busy = False
        for button in self.buttons:
            button.setEnabled(True)
        self._job = None
        self.selection_locked = False
        self.table.setEnabled(True)
        self.search.setEnabled(True)
        self.view_filter.setEnabled(True)
        self.progress_row.hide()
        self.update_selection_note()

    def failed(self, message):
        for code in list(self.pending):
            self.measurements[code] = PingResult(None, None, 'error', message)
        self.pending.clear()
        self.render(self.selected_codes())
        self.say(tr('تعذر إكمال العملية'), message[:2000], 'danger')
        self.status.setText(tr('لم يتغير شيء.'))

    def refresh(self):
        self.say('')
        self.start(self.store.refresh, self.set_catalog, tr('أجلب أحدث مناطق الاتصال من Steam…'))

    def measure(self):
        if self.busy:
            return
        selected = self.selected_codes()
        visible = {self.table.item(row, 1).data(Qt.UserRole) for row in range(self.table.rowCount()) if not self.table.isRowHidden(row)}
        regions = [r for r in self.regions if r.code in (selected or visible)]
        if not regions:
            self.status.setText(tr('لا توجد مناطق ظاهرة للقياس.'))
            return
        self.say('')
        self.pending = {r.code for r in regions}
        self.measure_total = len(regions)
        self.render(self.selected_codes())
        self.start(lambda emit: ping_regions(regions, lambda code, result: emit((code, result))), self.measured,
                   tr('أقيس البنق • 0/{0} • النتائج ستظهر فور وصولها.').format(self.measure_total), progress=True)

    def ping_progress(self, payload):
        code, result = payload
        self.measurements[code] = result
        self.pending.discard(code)
        if self.ping_sorted:
            self.render(self.selected_codes())
        else:
            row = self.find_row(code)
            if row is not None:
                self.render_measurement(row, code)
        done = self.measure_total - len(self.pending)
        self.progress.setValue(done)
        self.progress_text.setText(tr('{0} من {1}').format(done, self.measure_total))
        self.status.setText(tr('أقيس البنق • اكتمل {0}/{1} • هذا اتصال وسيط وليس بنق المباراة.').format(done, self.measure_total))

    def measured(self, result):
        self.pending.clear()
        self.last_measure = time.monotonic()
        selected = self.selected_codes()
        self.measurements.update(result)
        self.render(selected)
        ok = sum(r.status == 'ok' for r in result.values())
        errors = sum(r.status == 'error' for r in result.values())
        self.status.setText(tr('اكتمل القياس: {0}/{1} مناطق ردّت').format(ok, len(result)) + (tr(' • {0} أخطاء أداة القياس').format(errors) if errors else '')
                            + tr(' • لا رد يعني أن ICMP لم يستجب، وليس أن السيرفر متوقف.'))

    # ---- my choices ----------------------------------------------------------------------

    def reload_presets(self):
        names = sorted(self.store.state().get('presets', {}))
        self.saved_menu.clear()
        self.saved_menu.add(tr('حفظ التحديد الحالي'), self.save_preset)
        for name in names:
            self.saved_menu.add(tr('تحميل: ') + name, lambda _=False, n=name: self.load_preset(n))
        if names:
            self.saved_menu.addSeparator()
            self.saved_menu.add(tr('حذف اختيار محفوظ…'), self.choose_delete_preset)

    def choose_delete_preset(self):
        names = sorted(self.store.state().get('presets', {}))
        if not names:
            self.status.setText(tr('لا توجد اختيارات محفوظة لحذفها.'))
            return
        name, ok = QInputDialog.getItem(self, tr('حذف اختيار محفوظ'), tr('اختر الاسم:'), names, editable=False)
        if ok:
            self.delete_preset(name)

    def save_preset(self):
        codes = self.selected_codes()
        if not codes:
            self.status.setText(tr('حدد مناطق قبل الحفظ.'))
            return
        name, ok = QInputDialog.getText(self, tr('حفظ اختيار السيرفرات'), tr('اسم الاختيار:'))
        if ok:
            try:
                self.store.save_preset(name, codes)
                self.reload_presets()
                self.status.setText(tr('حُفظ الاختيار؛ لم يتغير الحظر.'))
            except Exception as error:
                self.failed(str(error))

    def load_preset(self, name):
        codes = set(self.store.state().get('presets', {}).get(name, []))
        self.search.clear()
        self.view_filter.setCurrentIndex(0)
        self.render(codes)
        self.status.setText(tr('تم تحميل الاختيار. اختر إجراء الحظر لتطبيقه.'))

    def delete_preset(self, name):
        self.store.delete_preset(name)
        self.reload_presets()

    # ---- the firewall --------------------------------------------------------------------

    def block_selected(self):
        self.apply_action('block')

    def apply_action(self, action):
        if self.busy:
            return
        try:
            ensure_closed()
            selected = self.selected_codes()
            if action in {'block', 'unblock', 'only'} and not selected:
                raise ValueError(tr('حدد منطقة واحدة على الأقل.'))
            plan, blocked = self.store.plan(self.regions, selected, action)
            plan['reset'] = action == 'clear'
            names = [region_info(r).city + ' [' + r.code + ']' for r in self.regions if r.code in selected]
            if action == 'clear':
                description = tr('إزالة كل قواعد الحظر التي أنشأها Toolbox. لا تحتاج تحديد مناطق، ولا تُحذف قواعد البرامج الأخرى.')
            elif action == 'unblock':
                description = tr('فك الحظر المحفوظ عن:\n') + '\n'.join(names)
            elif action == 'only':
                description = tr('السماح بالمناطق المحددة فقط:\n') + '\n'.join(names) + tr('\n\nسيُحظر باقي المناطق في القائمة.')
            else:
                description = tr('حظر المناطق المحددة:\n') + '\n'.join(names)
            description += tr('\n\nإجمالي المناطق المحظورة بعد العملية: ') + str(len(blocked))
            description += tr('\n\nعدد قواعد UDP: {0}.\nستظهر نافذة صلاحية المدير. قد تتأثر ألعاب Steam أخرى بنفس الخوادم الوسيطة.').format(len(plan['new']))
            if not confirm(self, tr('مراجعة اختيار السيرفرات'), description, tr('تطبيق'), danger=action in ('block', 'only')):
                return

            def apply():
                ensure_closed()
                apply_elevated(plan)
                self.store.record(blocked, plan['new'])
                return blocked
            self.last_action = action
            self.say('')
            self.start(apply, self.applied, tr('أطبّق القواعد • أكمل نافذة صلاحية المدير إن ظهرت…'))
        except Exception as error:
            self.failed(str(error))

    def applied(self, result):
        self.render(self.selected_codes())
        self.reload_presets()
        self.say('')
        done = (tr('تم فك كل حظر Toolbox.') if self.last_action == 'clear' else tr('تم فك حظر المناطق المحددة.') if self.last_action == 'unblock' else tr('تم تطبيق الاختيار.'))
        self.status.setText(done + tr(' الحظر المحفوظ: {0} مناطق.').format(len(result)))
