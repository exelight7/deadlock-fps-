"""Settings › App update: check for a new Toolbox, download it (checked against the published checksums), install it for this user only.

The logic is the Update Center's (`UpdateStore`, `UpdateClient`, `installation`); this page draws it with the new components.
Nothing is downloaded or installed until a button is pressed. The older words of the Update Center are kept (they are already translated).
"""
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QProcess, QStandardPaths, QThreadPool, QUrl, Signal, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QHBoxLayout, QPlainTextEdit, QScrollArea, QVBoxLayout, QWidget, QFrame

from .. import __version__
from ..i18n import tr
from ..shell import theme
from ..shell.components import Badge, Banner, Button, Card, List, ListRow, ProgressBar, Switch, mark, set_props, text_label
from ..ui_common import Job
from ..update_client import UpdateClient
from ..updates import RELEASES_URL, UpdateStore, Version, platform_key


def checked_time(value):
    try:
        return datetime.fromtimestamp(value).astimezone().strftime('%Y-%m-%d %H:%M') if value else tr('غير معروف')
    except (ValueError, OSError, OverflowError):
        return tr('غير معروف')


class UpdatePage(QWidget):
    updateAvailable = Signal(bool)
    TONES = (('danger', (tr('تعذر'),)), ('success', ('✓', tr('أنت على آخر إصدار'))), ('info', (tr('تحديث جديد'),)))

    def __init__(self, parent=None, store=None, current=__version__, manager=None, download_folder=None):
        super().__init__(parent)
        mark(self, 'UpdatePage')
        self.current = Version.parse(current)
        self.release = None
        self.fresh = False
        self.saved_path = None
        self.installing = False
        self.installed_binary = None
        self.saved_version = None
        self.saved_hash = ''
        self.store = store or UpdateStore(Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / 'updates')
        self.download_folder = Path(download_folder or (Path(QStandardPaths.writableLocation(QStandardPaths.DownloadLocation) or str(Path.home() / 'Downloads')) / 'Deadlock Toolbox'))
        self.client = UpdateClient(self.store, self, manager)
        t = theme.current()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)
        inner = QWidget()
        inner.setMaximumWidth(760)
        v = QVBoxLayout(inner)
        v.setContentsMargins(0, 0, 12, 0)
        v.setSpacing(t.px('space.4'))
        scroll.setWidget(inner)

        self.error_banner = Banner('', '', 'danger')
        self.error_banner.hide()
        v.addWidget(self.error_banner)
        card = Card()
        head = QHBoxLayout()
        self.state = text_label(tr('ابدأ بفحص الإصدارات.'), 'CardTitle')
        head.addWidget(self.state, 1)
        self.channel = Badge(tr('نسخة تجريبية محلية') if self.current.pre else tr('إصدارات مستقرة'), 'neutral')
        head.addWidget(self.channel, 0, Qt.AlignTop)
        card.body.addLayout(head)
        self.detail = text_label(tr('الفحص والتنزيل يعملان في الخلفية.'), 'CardText')
        card.body.addWidget(self.detail)
        self.checked = text_label(tr('لم يتم الفحص بعد.'), 'Muted')
        card.body.addWidget(self.checked)
        self.progress = ProgressBar()
        self.progress.setLayoutDirection(Qt.LeftToRight)
        self.progress.hide()
        card.body.addWidget(self.progress)
        self.progress_text = text_label('', 'Muted')
        self.progress_text.setLayoutDirection(Qt.LeftToRight)
        self.progress_text.hide()
        card.body.addWidget(self.progress_text)
        row = QHBoxLayout()
        row.setSpacing(t.px('space.2'))
        self.check_button = Button(tr('التحقق من التحديثات'), 'secondary', icon='refresh')
        self.check_button.clicked.connect(self.check)
        self.download_button = Button(tr('تنزيل حزمة نظامك'), 'primary', icon='download')
        self.download_button.clicked.connect(self.download)
        self.install_button = Button(tr('تثبيت النسخة المنزّلة'), 'primary', icon='check')
        self.install_button.clicked.connect(self.install_download)
        self.launch_button = Button(tr('فتح النسخة الجديدة'), 'secondary')
        self.launch_button.clicked.connect(self.launch_installed)
        self.cancel_button = Button(tr('إلغاء'), 'secondary')
        self.cancel_button.clicked.connect(self.client.cancel)
        for button in (self.check_button, self.download_button, self.install_button, self.launch_button, self.cancel_button):
            row.addWidget(button)
        row.addStretch(1)
        card.body.addLayout(row)
        row = QHBoxLayout()
        self.release_button = Button(tr('صفحة الإصدارات'), 'ghost', 'sm', icon='ext')
        self.release_button.clicked.connect(self.open_release)
        self.folder_button = Button(tr('فتح مجلد التنزيل'), 'ghost', 'sm', icon='folder')
        self.folder_button.clicked.connect(self.open_folder)
        row.addWidget(self.release_button)
        row.addWidget(self.folder_button)
        row.addStretch(1)
        card.body.addLayout(row)
        v.addWidget(card)

        rows = Card(variant='flat')
        lst = List(variant='flat')
        self.current_label = text_label(str(current), 'RowTitle', wrap=False)
        self.current_label.setLayoutDirection(Qt.LeftToRight)
        lst.add(ListRow(tr('إصدارك الحالي'), 'Windows / Linux • x64' if platform_key() else tr('هذا النظام لا يملك حزمة تنزيل متوافقة.'), control=self.current_label))
        self.latest = text_label('—', 'RowTitle', wrap=False)
        self.latest.setLayoutDirection(Qt.LeftToRight)
        self.published_row = ListRow(tr('آخر إصدار عام'), tr('المصدر: GitHub · exelight7/deadlock-fps-'), control=self.latest)
        self.published = self.published_row.line
        lst.add(self.published_row)
        self.auto_check = Switch()
        self.auto_check.setAccessibleName(tr('فحص عند تشغيل البرنامج • بحد أقصى مرة يوميًا'))
        self.auto_check.setChecked(self.store.auto_check)
        self.auto_check.toggled.connect(self.save_preference)
        lst.add(ListRow(tr('فحص عند تشغيل البرنامج • بحد أقصى مرة يوميًا'), tr('الفحص يقرأ صفحة الإصدارات العامة فقط.'), control=self.auto_check))
        self.install_current_button = Button(tr('تثبيت هذه النسخة في قائمة التطبيقات'), 'secondary', 'sm')
        self.install_current_button.clicked.connect(self.install_current)
        if not getattr(sys, 'frozen', False):
            self.install_current_button.hide()                  # nothing to install when running from source
        else:
            lst.add(ListRow(tr('تثبيت النسخة الجديدة'), tr('التثبيت لحسابك فقط، دون صلاحية مدير. تُحفظ النسخة السابقة، وإعدادات اللعبة والنسخ الاحتياطية تبقى في مكانها.'), control=self.install_current_button))
        rows.body.addWidget(lst)
        v.addWidget(rows)

        notes = Card(tr('ما الجديد؟'))
        self.notes = QPlainTextEdit()
        self.notes.setReadOnly(True)
        self.notes.setMinimumHeight(145)
        self.notes.setMaximumHeight(240)
        self.notes.setLayoutDirection(Qt.LeftToRight)
        self.notes.setPlainText(tr('ستظهر ملاحظات الإصدار هنا بعد الفحص.'))
        notes.body.addWidget(self.notes)
        v.addWidget(notes)
        v.addStretch(1)

        self.client.busyChanged.connect(self.refresh_buttons)
        self.client.phaseChanged.connect(self.phase_changed)
        self.client.found.connect(self.show_release)
        self.client.failed.connect(self.failed)
        self.client.cancelled.connect(self.cancelled)
        self.client.progress.connect(self.show_progress)
        self.client.downloaded.connect(self.downloaded)
        if self.store.release:
            self.show_release(self.store.release, True)
        if self.store.warning:
            self.detail.setText(self.store.warning)
        self.refresh_buttons()

    # ---- the words of the state ----------------------------------------------------------

    def say(self, state, detail=None):
        """Set the headline (its tone follows the outcome the words report) and, if given, the sentence under it."""
        self.state.setText(state)
        tone = next((name for name, words in self.TONES if any(word in state for word in words)), None)
        set_props(self.state, tone=tone)
        if detail is not None:
            self.detail.setText(detail)
        if tone == 'danger':
            self.error_banner.title.setText(state)
            self.error_banner.text.setText(self.detail.text())
            self.error_banner.text.setVisible(bool(self.detail.text()))
            self.error_banner.show()
        else:
            self.error_banner.hide()

    def save_preference(self, value):
        old = self.store.auto_check
        self.store.auto_check = value
        try:
            self.store.save_preferences()
        except OSError as error:
            self.store.auto_check = old
            self.auto_check.blockSignals(True)
            self.auto_check.setChecked(old)
            self.auto_check.blockSignals(False)
            self.detail.setText(tr('تعذر حفظ تفضيل الفحص: ') + str(error))

    def check(self):
        if self.client.busy or self.installing:
            return
        self.fresh = False
        self.client.check()
        self.refresh_buttons()

    def automatic_check(self):
        if self.store.due():
            self.check()

    def show_release(self, release, cached=False):
        self.progress.hide()
        self.progress_text.hide()
        self.release = release
        self.fresh = not cached
        self.latest.setText(release.tag)
        date = release.published_at[:10] or tr('غير متوفر')
        self.published.setText(tr('تاريخ النشر: ') + date + ' • GitHub')
        self.notes.setPlainText(release.notes or tr('لم يرفق هذا الإصدار ملاحظات.'))
        newer = release.version > self.current
        if cached:
            self.say(tr('نتيجة فحص محفوظة'), tr('اضغط التحقق من التحديثات لتأكيد آخر إصدار وتفعيل التنزيل.'))
        elif newer:
            self.say(tr('تحديث جديد متاح'), tr('يمكنك تنزيل الحزمة المتوافقة مع نظامك ومراجعة ما تغيّر أدناه.'))
        elif release.version == self.current:
            self.say(tr('أنت على آخر إصدار عام'), tr('يمكنك تنزيل الحزمة مرة أخرى إذا احتجتها.'))
        else:
            self.say(tr('نسختك أحدث من الإصدار العام'), tr('أنت تختبر نسخة أحدث. تنزيل الإصدار العام أدناه اختياري وهو أقدم من نسختك.'))
        stamp = checked_time(self.store.checked_at)
        self.checked.setText((tr('آخر فحص ناجح محفوظ: ') if cached else tr('تم التحقق الآن: ')) + stamp)
        self.download_button.setText(tr('تنزيل الإصدار العام (أقدم)') if release.version < self.current else (tr('تنزيل التحديث') if newer else tr('تنزيل حزمة نظامك')))
        if not release.package():
            self.detail.setText(self.detail.text() + tr(' لا تتوفر حزمة متوافقة مع نظامك لهذا الإصدار.'))
        elif not release.asset('SHA256SUMS.txt'):
            self.detail.setText(self.detail.text() + tr(' ملف التحقق غير موجود؛ التنزيل معطّل.'))
        self.updateAvailable.emit(newer)
        self.refresh_buttons()

    def refresh_buttons(self, *_):
        busy = self.client.busy or self.installing
        self.check_button.setEnabled(not busy)
        self.cancel_button.setVisible(self.client.busy)
        self.download_button.setEnabled(bool(not busy and self.fresh and self.release and self.release.package() and self.release.asset('SHA256SUMS.txt')))
        self.folder_button.setEnabled(self.saved_path is not None)
        self.install_button.setEnabled(bool(not busy and self.saved_path and self.saved_hash and not self.installed_binary))
        self.launch_button.setVisible(self.installed_binary is not None)
        self.launch_button.setEnabled(not busy)
        self.install_current_button.setEnabled(not busy)

    def phase_changed(self, phase):
        title = {'check': tr('جارٍ التحقق من الإصدارات…'), 'checksum': tr('جارٍ قراءة بصمات الحزمة…'), 'download': tr('جارٍ تنزيل الحزمة…')}
        self.say(title[phase], tr('يمكنك متابعة استخدام التطبيق أو إلغاء العملية في أي وقت.'))
        self.progress.show()
        self.progress.set_unknown()
        self.progress_text.hide()

    def failed(self, message):
        self.fresh = False
        self.say(tr('تعذر إكمال العملية'), message)
        if self.release:
            stamp = checked_time(self.store.checked_at)
            self.checked.setText(tr('آخر فحص ناجح: ') + stamp + tr(' • النتيجة المعروضة محفوظة'))
        self.progress.hide()
        self.progress_text.hide()
        self.updateAvailable.emit(False)
        self.refresh_buttons()

    def cancelled(self):
        self.say(tr('تم الإلغاء'), tr('توقفت العملية. أُزيلت أي أجزاء تنزيل غير مكتملة؛ يمكنك إعادة المحاولة.'))
        self.progress.hide()

    def show_progress(self, received, total):
        self.progress.set_known(int(received * 100 / total), 100)
        self.progress_text.show()
        self.progress_text.setText(f'{received / 1048576:.1f} / {total / 1048576:.1f} MB · {int(received * 100 / total)}%')

    def download(self):
        if self.download_button.isEnabled():
            self.client.download(self.release, self.download_folder)

    def downloaded(self, path):
        self.saved_path = path
        self.saved_hash = self.client.downloaded_hash
        self.saved_version = self.client.release.tag
        self.installed_binary = None
        self.progress.set_known(100, 100)
        self.say(tr('تم التحقق من التنزيل ✓'), tr('جاهز. اضغط «تثبيت النسخة المنزّلة»؛ لا تحتاج تفك الملفات أو تنقلها.'))
        self.progress_text.setText(str(path))
        self.refresh_buttons()

    def install_download(self):
        if not self.install_button.isEnabled():
            return
        from ..installation import install_archive
        self.begin_install(lambda: install_archive(self.saved_path, self.saved_version, self.saved_hash))

    def install_current(self):
        if self.installing or self.client.busy or not getattr(sys, 'frozen', False):
            return
        from ..installation import install_folder
        self.begin_install(lambda: install_folder(Path(sys.executable).parent))

    def begin_install(self, operation):
        self.installing = True
        self.say(tr('جارٍ تثبيت النسخة الجديدة…'))
        self.progress.show()
        self.progress.set_unknown()
        self.refresh_buttons()
        self.install_job = Job(operation)
        self.install_job.signals.result.connect(self.install_complete)
        self.install_job.signals.failure.connect(self.install_failed)
        QThreadPool.globalInstance().start(self.install_job)

    def install_complete(self, result):
        self.installing = False
        self.installed_binary, warning = result
        self.progress.hide()
        self.say(tr('تم التثبيت ✓'), warning or tr('النسخة الجديدة جاهزة في قائمة التطبيقات. افتحها، ثم أغلق هذه النسخة.'))
        self.refresh_buttons()

    def install_failed(self, message):
        self.installing = False
        self.progress.hide()
        self.say(tr('تعذر التثبيت'), message + tr(' يمكنك إعادة المحاولة أو فك الحزمة يدويًا.'))
        self.refresh_buttons()

    def launch_installed(self):
        if not self.installed_binary:
            return
        ok, _ = QProcess.startDetached(str(self.installed_binary), [], str(self.installed_binary.parent))
        if not ok:
            self.detail.setText(tr('تعذر فتح النسخة. افتح الملف من: ') + str(self.installed_binary))

    def open_release(self):
        QDesktopServices.openUrl(QUrl(self.release.url if self.release else RELEASES_URL))

    def open_folder(self):
        if self.saved_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.saved_path.parent)))
