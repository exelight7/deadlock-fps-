"""Update Center: explicit release state, portable downloads and installation help."""
from datetime import datetime
import sys
from pathlib import Path
from PySide6.QtCore import Qt, QStandardPaths, QUrl, Signal, QThreadPool, QProcess
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWidget,QFrame,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QScrollArea,QPlainTextEdit,QCheckBox,QProgressBar
from . import __version__
from .design import nav_icon,UtilityHeader
from .updates import UpdateStore,Version,RELEASES_URL,platform_key
from .update_client import UpdateClient


def text(value,style='subtitle'):
    label=QLabel(value);label.setTextFormat(Qt.PlainText);label.setWordWrap(True);label.setObjectName(style);return label


def panel():
    frame=QFrame();frame.setObjectName('card');layout=QVBoxLayout(frame);layout.setContentsMargins(20,16,20,16);layout.setSpacing(10);return frame,layout


def checked_time(value):
    try:return datetime.fromtimestamp(value).astimezone().strftime('%Y-%m-%d %H:%M') if value else 'غير معروف'
    except (ValueError,OSError,OverflowError):return 'غير معروف'


class UpdatePage(QWidget):
    updateAvailable=Signal(bool)
    def __init__(self,parent=None,store=None,current=__version__,manager=None,download_folder=None):
        super().__init__(parent);self.current=Version.parse(current);self.release=None;self.fresh=False;self.saved_path=None;self.installing=False;self.installed_binary=None;self.saved_version=None;self.saved_hash=''
        self.store=store or UpdateStore(Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))/'updates')
        self.download_folder=Path(download_folder or (Path(QStandardPaths.writableLocation(QStandardPaths.DownloadLocation) or str(Path.home()/'Downloads'))/'Deadlock Toolbox'))
        self.client=UpdateClient(self.store,self,manager)
        root=QVBoxLayout(self);root.setContentsMargins(0,0,0,0);root.setSpacing(12)
        scroll=QScrollArea();scroll.setWidgetResizable(True);body=QWidget();v=QVBoxLayout(body);v.setContentsMargins(0,0,10,0);v.setSpacing(12);scroll.setWidget(body);root.addWidget(scroll,1)
        v.addWidget(UtilityHeader(6,'التحديث والتثبيت','افحص، نزّل، ثم ثبّت بضغطة. بدون نقل ملفات يدويًا.','UPDATE / INSTALL'))
        frame,c=panel();v.addWidget(frame)
        self.channel=text('نسخة تجريبية محلية' if self.current.pre else 'إصدارات مستقرة','badge');c.addWidget(self.channel,0,Qt.AlignRight)
        row=QHBoxLayout();self.check_button=QPushButton('التحقق من التحديثات');self.check_button.setObjectName('positive');self.check_button.clicked.connect(self.check);row.addWidget(self.check_button)
        self.release_button=QPushButton('صفحة الإصدارات ↗');self.release_button.clicked.connect(self.open_release);row.addWidget(self.release_button);row.addStretch();c.addLayout(row)
        row=QHBoxLayout();v.addLayout(row)
        frame,c=panel();c.addWidget(text('إصدارك الحالي','sectionLabel'));self.current_label=text(current,'cardtitle');self.current_label.setLayoutDirection(Qt.LeftToRight);c.addWidget(self.current_label);c.addWidget(text('Windows / Linux • x64' if platform_key() else 'هذا النظام لا يملك حزمة تنزيل متوافقة.','sectionLabel'));row.addWidget(frame,1)
        frame,c=panel();c.addWidget(text('آخر إصدار عام','sectionLabel'));self.latest=text('—','cardtitle');self.latest.setLayoutDirection(Qt.LeftToRight);c.addWidget(self.latest);self.published=text('المصدر: GitHub · exelight7/deadlock-fps-','sectionLabel');c.addWidget(self.published);row.addWidget(frame,1)
        frame,c=panel();v.addWidget(frame);self.state=text('ابدأ بفحص الإصدارات.','cardtitle');c.addWidget(self.state);self.detail=text('الفحص والتنزيل يعملان في الخلفية.');c.addWidget(self.detail)
        self.checked=text('لم يتم الفحص بعد.','sectionLabel');c.addWidget(self.checked)
        self.progress=QProgressBar();self.progress.setRange(0,100);self.progress.setLayoutDirection(Qt.LeftToRight);self.progress.setTextVisible(False)
        self.progress.setStyleSheet('QProgressBar {border:0;border-radius:4px;background:#363b3d;min-height:8px;max-height:8px;} QProgressBar::chunk {background:#e7c08a;border-radius:4px;}');c.addWidget(self.progress);self.progress.hide()
        self.progress_text=text('','sectionLabel');self.progress_text.setLayoutDirection(Qt.LeftToRight);c.addWidget(self.progress_text);self.progress_text.hide()
        frame,c=panel();v.addWidget(frame);c.addWidget(text('ما الجديد؟','cardtitle'));self.notes=QPlainTextEdit();self.notes.setReadOnly(True);self.notes.setMinimumHeight(145);self.notes.setMaximumHeight(220);self.notes.setLayoutDirection(Qt.LeftToRight);self.notes.setPlainText('ستظهر ملاحظات الإصدار هنا بعد الفحص.');c.addWidget(self.notes)
        frame,c=panel();v.addWidget(frame);c.addWidget(text('تركيب النسخة الجديدة','cardtitle'))
        c.addWidget(text('1. اضغط التحقق من التحديثات ثم تنزيل التحديث.\n2. بعد التحقق، اضغط تثبيت النسخة المنزّلة.\n3. افتح النسخة الجديدة من الزر أو قائمة التطبيقات.'))
        c.addWidget(text('التثبيت لحسابك فقط، دون صلاحية مدير. تُحفظ النسخة السابقة، وإعدادات اللعبة والنسخ الاحتياطية تبقى في مكانها.','sectionLabel'))
        self.install_current_button=QPushButton('تثبيت هذه النسخة في قائمة التطبيقات');self.install_current_button.clicked.connect(self.install_current);self.install_current_button.setVisible(bool(getattr(sys,'frozen',False)));c.addWidget(self.install_current_button)
        self.auto_check=QCheckBox('فحص عند تشغيل البرنامج • بحد أقصى مرة يوميًا');self.auto_check.setChecked(self.store.auto_check);self.auto_check.toggled.connect(self.save_preference);c.addWidget(self.auto_check)
        v.addStretch()
        footer,c=panel();root.addWidget(footer);row=QHBoxLayout();self.download_button=QPushButton('تنزيل حزمة نظامك');self.download_button.setObjectName('primary');self.download_button.clicked.connect(self.download);row.addWidget(self.download_button,1)
        self.cancel_button=QPushButton('إلغاء');self.cancel_button.clicked.connect(self.client.cancel);row.addWidget(self.cancel_button)
        self.folder_button=QPushButton('فتح مجلد التنزيل ↗');self.folder_button.clicked.connect(self.open_folder);row.addWidget(self.folder_button);c.addLayout(row)
        row=QHBoxLayout();self.install_button=QPushButton('تثبيت النسخة المنزّلة');self.install_button.setObjectName('positive');self.install_button.clicked.connect(self.install_download);row.addWidget(self.install_button,1)
        self.launch_button=QPushButton('فتح النسخة الجديدة');self.launch_button.clicked.connect(self.launch_installed);row.addWidget(self.launch_button);c.addLayout(row)
        self.client.busyChanged.connect(self.refresh_buttons);self.client.phaseChanged.connect(self.phase_changed)
        self.client.found.connect(self.show_release);self.client.failed.connect(self.failed);self.client.cancelled.connect(self.cancelled);self.client.progress.connect(self.show_progress);self.client.downloaded.connect(self.downloaded)
        if self.store.release:self.show_release(self.store.release,True)
        if self.store.warning:self.detail.setText(self.store.warning)
        self.refresh_buttons()

    def save_preference(self,value):
        old=self.store.auto_check;self.store.auto_check=value
        try:self.store.save_preferences()
        except OSError as e:
            self.store.auto_check=old;self.auto_check.blockSignals(True);self.auto_check.setChecked(old);self.auto_check.blockSignals(False);self.detail.setText('تعذر حفظ تفضيل الفحص: '+str(e))

    def check(self):
        if self.client.busy or self.installing:return
        self.fresh=False;self.client.check();self.refresh_buttons()

    def automatic_check(self):
        if self.store.due():self.check()

    def show_release(self,release,cached=False):
        self.progress.hide();self.progress_text.hide()
        self.release=release;self.fresh=not cached;self.latest.setText(release.tag)
        date=release.published_at[:10] or 'غير متوفر';self.published.setText('تاريخ النشر: '+date+' • GitHub')
        self.notes.setPlainText(release.notes or 'لم يرفق هذا الإصدار ملاحظات.');newer=release.version>self.current
        if cached:self.state.setText('نتيجة فحص محفوظة');self.detail.setText('اضغط التحقق من التحديثات لتأكيد آخر إصدار وتفعيل التنزيل.')
        elif newer:self.state.setText('تحديث جديد متاح');self.detail.setText('يمكنك تنزيل الحزمة المتوافقة مع نظامك ومراجعة ما تغيّر أدناه.')
        elif release.version==self.current:self.state.setText('أنت على آخر إصدار عام');self.detail.setText('يمكنك تنزيل الحزمة مرة أخرى إذا احتجتها.')
        else:self.state.setText('نسختك أحدث من الإصدار العام');self.detail.setText('أنت تختبر نسخة أحدث. تنزيل الإصدار العام أدناه اختياري وهو أقدم من نسختك.')
        stamp=checked_time(self.store.checked_at)
        self.checked.setText(('آخر فحص ناجح محفوظ: ' if cached else 'تم التحقق الآن: ')+stamp)
        self.download_button.setText('تنزيل الإصدار العام (أقدم)' if release.version<self.current else ('تنزيل التحديث' if newer else 'تنزيل حزمة نظامك'))
        if not release.package():self.detail.setText(self.detail.text()+' لا تتوفر حزمة متوافقة مع نظامك لهذا الإصدار.')
        elif not release.asset('SHA256SUMS.txt'):self.detail.setText(self.detail.text()+' ملف التحقق غير موجود؛ التنزيل معطّل.')
        self.updateAvailable.emit(newer);self.refresh_buttons()

    def refresh_buttons(self,*_):
        busy=self.client.busy or self.installing;self.check_button.setEnabled(not busy);self.cancel_button.setVisible(self.client.busy)
        self.download_button.setEnabled(bool(not busy and self.fresh and self.release and self.release.package() and self.release.asset('SHA256SUMS.txt')))
        self.folder_button.setEnabled(self.saved_path is not None)
        self.install_button.setEnabled(bool(not busy and self.saved_path and self.saved_hash and not self.installed_binary))
        self.launch_button.setVisible(self.installed_binary is not None)
        self.launch_button.setEnabled(not busy)
        self.install_current_button.setEnabled(not busy)

    def phase_changed(self,phase):
        title={'check':'جارٍ التحقق من الإصدارات…','checksum':'جارٍ قراءة بصمات الحزمة…','download':'جارٍ تنزيل الحزمة…'}
        self.state.setText(title[phase]);self.detail.setText('يمكنك متابعة استخدام التطبيق أو إلغاء العملية في أي وقت.');self.progress.show();self.progress.setRange(0,0);self.progress_text.hide()

    def failed(self,message):
        self.fresh=False
        self.state.setText('تعذر إكمال العملية');self.detail.setText(message)
        if self.release:
            stamp=checked_time(self.store.checked_at)
            self.checked.setText('آخر فحص ناجح: '+stamp+' • النتيجة المعروضة محفوظة')
        self.progress.hide();self.progress_text.hide();self.updateAvailable.emit(False);self.refresh_buttons()

    def cancelled(self):
        self.state.setText('تم الإلغاء');self.detail.setText('توقفت العملية. أُزيلت أي أجزاء تنزيل غير مكتملة؛ يمكنك إعادة المحاولة.');self.progress.hide();self.progress_text.hide();self.refresh_buttons()

    def show_progress(self,received,total):
        self.progress.setRange(0,100);self.progress.setValue(int(received*100/total));self.progress_text.show();self.progress_text.setText(f'{received/1048576:.1f} / {total/1048576:.1f} MB · {int(received*100/total)}%')

    def download(self):
        if self.download_button.isEnabled():self.client.download(self.release,self.download_folder)

    def downloaded(self,path):
        self.saved_path=path;self.saved_hash=self.client.downloaded_hash;self.saved_version=self.client.release.tag;self.installed_binary=None;self.progress.setRange(0,100);self.progress.setValue(100);self.state.setText('تم التحقق من التنزيل ✓');self.detail.setText('جاهز. اضغط «تثبيت النسخة المنزّلة»؛ لا تحتاج تفك الملفات أو تنقلها.');self.progress_text.setText(str(path));self.refresh_buttons()

    def install_download(self):
        if not self.install_button.isEnabled():return
        from .installation import install_archive
        from .server_ui import Job
        self.begin_install(lambda:install_archive(self.saved_path,self.saved_version,self.saved_hash))

    def install_current(self):
        if self.installing or self.client.busy or not getattr(sys,'frozen',False):return
        from .installation import install_folder
        self.begin_install(lambda:install_folder(Path(sys.executable).parent))

    def begin_install(self,operation):
        from .server_ui import Job
        self.installing=True;self.state.setText('جارٍ تثبيت النسخة الجديدة…');self.progress.show();self.progress.setRange(0,0);self.refresh_buttons()
        self.install_job=Job(operation)
        self.install_job.signals.result.connect(self.install_complete)
        self.install_job.signals.failure.connect(self.install_failed)
        QThreadPool.globalInstance().start(self.install_job)

    def install_complete(self,result):
        self.installing=False;self.installed_binary,warning=result;self.progress.hide();self.state.setText('تم التثبيت ✓');self.detail.setText(warning or 'النسخة الجديدة جاهزة في قائمة التطبيقات. افتحها، ثم أغلق هذه النسخة.');self.refresh_buttons()

    def install_failed(self,message):
        self.installing=False;self.progress.hide();self.state.setText('تعذر التثبيت');self.detail.setText(message+' يمكنك إعادة المحاولة أو فك الحزمة يدويًا.');self.refresh_buttons()

    def launch_installed(self):
        if not self.installed_binary:return
        ok,_=QProcess.startDetached(str(self.installed_binary),[],str(self.installed_binary.parent))
        if not ok:self.detail.setText('تعذر فتح النسخة. افتح الملف من: '+str(self.installed_binary))

    def open_release(self):QDesktopServices.openUrl(QUrl(self.release.url if self.release else RELEASES_URL))
    def open_folder(self):
        if self.saved_path:QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.saved_path.parent)))
