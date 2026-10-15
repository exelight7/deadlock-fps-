"""Native, read-only mod diagnostics workspace."""
from datetime import datetime
from pathlib import Path
import json,threading
from PySide6.QtCore import QThreadPool
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QPlainTextEdit,QFileDialog,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView
from .update_ui import text
from .server_ui import Job
from .mod_inspector import inspect_mods
from .core import atomic
from .design import UtilityHeader


class InspectorPage(QWidget):
    def __init__(self,window):
        super().__init__(window);self.window=window;self.busy=False;self.result=None;self.cancel_event=None;self._job=None;root=QVBoxLayout(self);root.setContentsMargins(0,0,0,0);root.setSpacing(12)
        root.addWidget(UtilityHeader(7,'Mod Inspector','اعرف ما ينقص مكتبتك، وما يمنع التركيب، قبل أن تغيّر أي ملف.','CHECK / VERIFY / INSTALL'))
        row=QHBoxLayout();self.scan_button=QPushButton('فحص المودات');self.scan_button.setObjectName('primary');self.scan_button.clicked.connect(self.scan);row.addWidget(self.scan_button);self.cancel_button=QPushButton('إلغاء الفحص');self.cancel_button.clicked.connect(self.cancel);row.addWidget(self.cancel_button);self.cancel_button.hide()
        library=QPushButton('فتح مكتبة المودات');library.clicked.connect(lambda:window.navigate(2));row.addWidget(library);export=QPushButton('تصدير التقرير');export.clicked.connect(self.export);row.addWidget(export);root.addLayout(row)
        self.table=QTableWidget(0,4);self.table.setHorizontalHeaderLabels(['المود','مختار','المكتبة','المركب في اللعبة']);self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);self.table.verticalHeader().hide();self.table.setEditTriggers(QAbstractItemView.NoEditTriggers);self.table.setMinimumHeight(150);self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.setAlternatingRowColors(True);self.table.setShowGrid(False);self.table.verticalHeader().setDefaultSectionSize(44);root.addWidget(self.table,1)
        self.details=QPlainTextEdit();self.details.setReadOnly(True);self.details.setMinimumHeight(100);self.details.setMaximumHeight(200);root.addWidget(self.details);self.status=text('جاهز للفحص.');root.addWidget(self.status);root.addWidget(text('يفحص الملفات المدعومة وبنيتها والتداخل بينها. توافق المود مع آخر تحديث للعبة يحتاج تجربة داخل التدريب.','sectionLabel'))
    def showEvent(self,event):
        super().showEvent(event)
        if self.result is None and not self.busy:self.scan()
    def scan(self):
        if self.busy:return
        self.busy=True;self.scan_button.setEnabled(False);self.cancel_button.show();self.status.setText('جارٍ الفحص في الخلفية…');self.cancel_event=threading.Event()
        root=self.window.path.text().strip() or None;selected=tuple(k for k,b in self.window.mod_checks.items() if b.isChecked());event=self.cancel_event;library=self.window.library
        self._job=Job(lambda:inspect_mods(library,root,selected,event));self._job.signals.result.connect(self.render);self._job.signals.failure.connect(self.failed);self._job.signals.done.connect(self.finished);QThreadPool.globalInstance().start(self._job)
    def cancel(self):
        if self.cancel_event:self.cancel_event.set();self.status.setText('أُلغي الفحص. تبقى نتيجة الفحص السابق إن وجدت.')
    def invalidate(self):
        if self.busy:self.cancel()
        self.result=None;self.table.setRowCount(0);self.details.clear();self.status.setText('تغيّر الاختيار أو الملفات؛ أعد الفحص لتحديث النتيجة.')
    def render(self,result):
        if result is None or self.cancel_event and self.cancel_event.is_set():return
        self.result=result;self.table.setRowCount(len(result.rows))
        for row,value in enumerate(result.rows):
            for col,key in enumerate(('name','selected','library','installed')):
                item=QTableWidgetItem(('نعم' if value[key] else 'لا') if key=='selected' else value[key])
                if key in ('library','installed'):item.setForeground(QColor('#9dd7b2' if value[key].startswith('سليم') else '#efad91' if value[key]=='تالف أو معدل' else '#9aa7ad'))
                self.table.setItem(row,col,item)
        findings=['['+('خطأ يمنع التطبيق' if f.severity=='error' else 'تنبيه')+'] '+f.title+'\n'+f.detail for f in result.findings]
        self.details.setPlainText('\n\n'.join(findings) or 'لم يُكتشف تلف أو تعارض في الاختيار الحالي. راجع حالة كل مود في الجدول؛ الملفات غير المختارة قد تكون غير موجودة.');self.status.setText(datetime.now().strftime('%H:%M:%S')+f' • {len(result.errors)} أخطاء تمنع التطبيق • {len(result.findings)-len(result.errors)} تنبيهات')
    def failed(self,message):self.result=None;self.table.setRowCount(0);self.details.clear();self.status.setText('تعذر الفحص: '+message)
    def finished(self):self.busy=False;self._job=None;self.scan_button.setEnabled(True);self.cancel_button.hide()
    def export(self):
        if not self.result:self.status.setText('نفّذ فحصًا أولًا.');return
        name,_=QFileDialog.getSaveFileName(self,'تصدير تقرير المودات','deadlock-mod-inspection.json','JSON (*.json)')
        if name:
            try:atomic(Path(name),json.dumps(self.result.to_dict(),ensure_ascii=False,indent=2).encode('utf-8'));self.status.setText('تم تصدير التقرير.')
            except Exception as e:self.status.setText(str(e))
