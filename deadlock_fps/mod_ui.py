"""Three-step mod library: drop a bundle, choose cards, review one safe install."""
from pathlib import Path
import threading
from PySide6.QtCore import Qt,QThreadPool,QSize,Signal
from PySide6.QtWidgets import QWidget,QFrame,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QPushButton,QCheckBox,QScrollArea,QFileDialog,QMenu,QProgressBar,QDialog,QPlainTextEdit
from .settings import MODS
from .core import Studio,game_root
from .mods import ImportCancelled
from .mod_install import prepare_mods,commit_mods
from .server_ui import Job
from .update_ui import text,panel
from .design import nav_icon,mod_icon

class DropArea(QFrame):
    dropped=Signal(object)
    def __init__(self):
        super().__init__();self.setObjectName('dropArea');self.setAcceptDrops(True);self.setMinimumHeight(100)
        layout=QHBoxLayout(self);layout.setContentsMargins(22,16,22,16);icon=QLabel();icon.setPixmap(nav_icon(2).pixmap(42,42));layout.addWidget(icon)
        copy=QVBoxLayout();copy.setSpacing(2);copy.addWidget(text('اسحب الحزمة هنا. واترك الباقي للأداة.','cardtitle'));copy.addWidget(text('ZIP أو VPK أو مجلد MODS • يتعرف على المودات حتى لو تغيّر اسم الملف.','subtitle'));layout.addLayout(copy,1)
    @staticmethod
    def paths(mime):return [Path(url.toLocalFile()) for url in mime.urls()] if mime.hasUrls() and all(url.isLocalFile() for url in mime.urls()) else []
    def highlight(self,value):self.setProperty('dragging',value);self.style().unpolish(self);self.style().polish(self)
    def dragEnterEvent(self,event):
        if self.isEnabled() and self.paths(event.mimeData()):event.acceptProposedAction();self.highlight(True)
        else:event.ignore()
    def dragLeaveEvent(self,event):self.highlight(False);event.accept()
    def dropEvent(self,event):
        self.highlight(False);paths=self.paths(event.mimeData())
        if self.isEnabled() and paths:event.acceptProposedAction();self.dropped.emit(paths)
        else:event.ignore()

class ModCard(QFrame):
    def __init__(self,key):
        super().__init__();self.key=key;self.setObjectName('modCard');self.setMinimumHeight(148)
        v=QVBoxLayout(self);v.setContentsMargins(18,15,18,15);v.setSpacing(8);row=QHBoxLayout();icon=QLabel();icon.setPixmap(mod_icon(key).pixmap(28,28));row.addWidget(icon)
        title=text(MODS[key][1],'modTitle');title.setLayoutDirection(Qt.LeftToRight);row.addWidget(title,1);self.state=text('أضف الحزمة','statusPill');row.addWidget(self.state);v.addLayout(row)
        descriptions={'daylock':'إضاءة نهارية للخريطة. جرّب الوضوح في التدريب.','names':'إخفاء أسماء اللاعبين. يتعارض مع شريط الصحة القديم.','health':'شكل شريط الصحة القديم. اختره أو إخفاء الأسماء.','sinner':'تعديل Sinner المرجعي. افحص النتيجة داخل اللعبة.'}
        v.addWidget(text(descriptions[key]));self.check=QCheckBox('أريده في اللعبة');v.addWidget(self.check);self.check.toggled.connect(self.mark)
    def mark(self,value):self.setProperty('selected',value);self.style().unpolish(self);self.style().polish(self)
    def mouseReleaseEvent(self,event):
        if event.button()==Qt.LeftButton and self.check.isEnabled():self.check.toggle();event.accept()
        else:super().mouseReleaseEvent(event)

class ModReview(QDialog):
    def __init__(self,prepared,parent=None):
        super().__init__(parent);self.setWindowTitle('تأكيد المودات');self.resize(600,450);self.setMinimumWidth(490);v=QVBoxLayout(self);v.setContentsMargins(24,22,24,22);v.setSpacing(14)
        v.addWidget(text('كل شيء جاهز. راجع اختيارك.','heroTitle'));v.addWidget(text('تتغير المودات فقط. الدقة والرسوم محفوظة، والأصل يُحفظ تلقائيًا.'))
        installed=[];removed=[]
        for path,data in prepared.plan.items():
            if path.suffix!='.vpk':continue
            key=next((key for key,(filename,_,_) in MODS.items() if filename.split(' - ')[0]==path.name),None);title=MODS[key][1] if key else path.name
            (installed if key in prepared.settings.mods else removed).append(title)
        frame,c=panel();v.addWidget(frame);c.addWidget(text('في اللعبة بعد التطبيق','sectionLabel'));c.addWidget(text(' • '.join(MODS[k][1] for k in prepared.settings.mods) or 'بدون مودات مختارة','cardtitle'))
        if installed:c.addWidget(text('تركيب / تحديث: '+', '.join(installed)))
        if removed:c.addWidget(text('إلغاء المود واسترجاع الأصل: '+', '.join(removed)))
        warnings=[f.title+' — '+f.detail for f in prepared.report.findings if f.severity=='warning']
        if warnings:warning=text('\n'.join(warnings),'noticeWarning');v.addWidget(warning)
        self.details=QPlainTextEdit();self.details.setReadOnly(True);self.details.setLayoutDirection(Qt.LeftToRight);self.details.setPlainText('\n'.join(str(p)+('  → remove' if b is None else f'  → {len(b):,} bytes') for p,b in prepared.plan.items()));self.details.hide();v.addWidget(self.details,1)
        more=QPushButton('تفاصيل الملفات');more.setObjectName('quiet');more.setCheckable(True);more.toggled.connect(self.details.setVisible);v.addWidget(more);v.addStretch()
        row=QHBoxLayout();cancel=QPushButton('رجوع');cancel.clicked.connect(self.reject);row.addWidget(cancel);ok=QPushButton('تأكيد التركيب' if prepared.settings.mods else 'تأكيد الإزالة');ok.setObjectName('primary');ok.clicked.connect(self.accept);row.addWidget(ok,1);v.addLayout(row)

class ModPage(QWidget):
    def __init__(self,window):
        super().__init__(window);self.window=window;self.stage='';self._job=None;self.sequence=0;self.cancel_event=None;self.cards={};self.checks={};self.labels={};self._columns=0;self._can_install=False
        root=QVBoxLayout(self);root.setContentsMargins(0,0,0,0);root.setSpacing(12)
        steps=QHBoxLayout()
        for number,title in [('01','أضف الحزمة'),('02','اختر المودات'),('03','ركّب بأمان')]:
            label=text(number+'  /  '+title,'stepPill');steps.addWidget(label,1)
        root.addLayout(steps)
        scroll=QScrollArea();scroll.setWidgetResizable(True);body=QWidget();v=QVBoxLayout(body);v.setContentsMargins(0,0,8,0);v.setSpacing(12);scroll.setWidget(body);root.addWidget(scroll,1)
        self.drop=DropArea();self.drop.dropped.connect(self.import_paths);v.addWidget(self.drop)
        row=QHBoxLayout();self.add_button=QPushButton('إضافة حزمة');self.add_button.setIcon(nav_icon(2));self.add_button.setObjectName('primary');self.add_button.clicked.connect(self.browse_files);row.addWidget(self.add_button)
        self.more_button=QPushButton('خيارات الإضافة ▾');menu=QMenu(self.more_button);menu.addAction('اختيار مجلد',self.browse_folder);menu.addAction('العثور على الحزمة تلقائيًا',self.discover);self.more_button.setMenu(menu);row.addWidget(self.more_button)
        self.link_button=QPushButton('ربط اللعبة');self.link_button.clicked.connect(window.focus_game);row.addWidget(self.link_button);row.addStretch();v.addLayout(row)
        self.import_note=text('أضف الحزمة مرة واحدة. تبقى المودات محفوظة للجلسات القادمة.','subtitle');v.addWidget(self.import_note)
        self.grid=QGridLayout();self.grid.setContentsMargins(0,0,0,0);self.grid.setSpacing(12);v.addLayout(self.grid)
        for key in MODS:
            card=ModCard(key);self.cards[key]=card;self.checks[key]=card.check;self.labels[key]=card.state;card.check.toggled.connect(lambda checked,k=key:window.mod_selected(k,checked))
        self.arrange(2);v.addWidget(text('المودات المدعومة هي الملفات المرجعية المرفقة. إضافة الحزمة لا تغيّر اللعبة.','sectionLabel'));v.addStretch()
        self.actions_panel=QFrame();self.actions_panel.setObjectName('actionbar');actions=QVBoxLayout(self.actions_panel);actions.setContentsMargins(18,12,18,12);actions.setSpacing(8)
        self.status=text('اختر ما تريده في اللعبة، ثم اضغط التركيب.');actions.addWidget(self.status)
        self.progress=QProgressBar();self.progress.setTextVisible(False);self.progress.setRange(0,0);self.progress.setFixedHeight(5);self.progress.hide();actions.addWidget(self.progress)
        row=QHBoxLayout();self.install_button=QPushButton('فحص وتركيب الاختيار');self.install_button.setObjectName('primary');self.install_button.clicked.connect(self.install);row.addWidget(self.install_button,1)
        self.inspect_button=QPushButton('تفاصيل الفحص');self.inspect_button.setIcon(nav_icon(7));self.inspect_button.clicked.connect(lambda:window.navigate(7));row.addWidget(self.inspect_button)
        self.cancel_button=QPushButton('إلغاء');self.cancel_button.clicked.connect(self.cancel);self.cancel_button.hide();row.addWidget(self.cancel_button);actions.addLayout(row);root.addWidget(self.actions_panel)
    @property
    def busy(self):return bool(self.stage)
    @property
    def applying(self):return self.stage=='apply'
    def selected(self):return tuple(k for k,c in self.checks.items() if c.isChecked())
    def arrange(self,columns):
        if self._columns==columns:return
        self._columns=columns
        for card in self.cards.values():self.grid.removeWidget(card)
        for i,card in enumerate(self.cards.values()):self.grid.addWidget(card,i//columns,i%columns)
    def resizeEvent(self,event):super().resizeEvent(event);self.arrange(2 if self.width()>=620 else 1)
    def refresh(self):
        available=self.window.library.available();installed=self.window.library.installed(self.window.path.text().strip())
        try:managed=Studio(self.window.path.text()).state().get('files',{})
        except Exception:managed={}
        for key,card in self.cards.items():
            target=Path(self.window.path.text())/'game/citadel/fps_studio'/MODS[key][0].split(' - ')[0]
            if key in installed:message='مركّب' if str(target.resolve()) in managed else 'موجود من قبل';state='success'
            elif key in available:message='جاهز';state='ready'
            else:message='أضف الحزمة';state='muted'
            card.state.setText(message);card.state.setProperty('tone',state);card.state.style().unpolish(card.state);card.state.style().polish(card.state)
        self.link_button.setText('اللعبة مرتبطة' if (Path(self.window.path.text())/'game/citadel/gameinfo.gi').is_file() else 'ربط اللعبة')
        count=len(self.selected())
        owned=any(str((Path(self.window.path.text())/'game/citadel/fps_studio'/name.split(' - ')[0]).resolve()) in managed for name,_,_ in MODS.values());self._can_install=bool(count or owned)
        if not self.busy:self.status.setText(f'{count} مودات مختارة • '+('جاهز للفحص والتركيب' if count else 'تُسترجع مودات الأداة المركبة عند التأكيد.' if owned else 'أضف الحزمة أو اختر مودًا للبدء.'))
        self.install_button.setText('فحص وتركيب الاختيار' if count else 'مراجعة إزالة مودات الأداة' if owned else 'اختر مودًا للبدء');self.install_button.setEnabled(not self.busy and self._can_install)
    def browse_files(self):
        paths,_=QFileDialog.getOpenFileNames(self,'أضف حزمة المودات','','Mod bundles (*.zip *.vpk*);;All files (*)')
        if paths:self.import_paths(paths)
    def browse_folder(self):
        folder=QFileDialog.getExistingDirectory(self,'اختر مجلد المودات')
        if folder:self.import_paths([folder])
    def discover(self):
        paths=self.window.library.discover()
        if paths:self.import_paths(paths)
        else:self.status.setText('لم أعثر على حزمة. اسحب ZIP هنا أو اختر مجلد MODS من خيارات الإضافة.')
    def import_paths(self,paths):
        if self.busy:return
        library=self.window.library;paths=tuple(paths);self.cancel_event=threading.Event();event=self.cancel_event
        self.start('import',lambda emit:library.import_report(paths,event,emit),self.imported,True)
    def imported(self,report):
        self.idle();matched=report.matched
        for key in matched-{'names','health'}:self.checks[key].setChecked(True)
        pair=matched&{'names','health'}
        if len(pair)==1:self.checks[next(iter(pair))].setChecked(True)
        note=f'تعرّفت على {len(matched)} مودات وحفظتها. راجع البطاقات ثم ركّب.'
        if len(pair)==2 and not any(self.checks[k].isChecked() for k in pair):note+=' اختر إخفاء الأسماء أو شريط الصحة؛ لا يعملان معًا.'
        if report.ignored:note+=f' تجاهلت {len(report.ignored)} ملفات غير مدعومة.'
        self.import_note.setText(note);self.window.refresh_mod_library();self.window.inspector.invalidate();self.status.setText(note)
    def install(self):
        if self.busy:return
        root=self.window.path.text().strip();selected=self.selected();library=self.window.library;self.cancel_event=threading.Event();event=self.cancel_event
        self.start('prepare',lambda:prepare_mods(root,library,selected,event),self.prepared)
    def prepared(self,prepared):
        if self.cancel_event and self.cancel_event.is_set():self.idle();self.status.setText('أُلغي الفحص؛ لم تتغير ملفات اللعبة.');return
        try:
            if game_root(self.window.path.text())!=prepared.root or self.selected()!=prepared.settings.mods:raise ValueError('تغيّر مسار اللعبة أو الاختيار أثناء الفحص. أعد المحاولة.')
        except Exception as e:self.idle();self.status.setText(str(e));return
        self.stage='review';self.busy_ui()
        if prepared.plan:
            dialog=ModReview(prepared,self);accepted=dialog.exec()==QDialog.Accepted;dialog.deleteLater()
            if not accepted:self.idle();self.status.setText('أُلغي التركيب. لم تتغير ملفات اللعبة.');return
        library=self.window.library;self.idle();self.start('apply',lambda:commit_mods(prepared,library),self.applied)
    def applied(self,message):
        self.idle();self.window.refresh_mod_library();self.window.inspector.invalidate();self.status.setText('تم • '+message+' الدقة والرسوم محفوظة.');self.import_note.setText('اختيارك محفوظ. يمكنك تعديل المودات في أي وقت وإعادة التطبيق.')
    def start(self,stage,fn,success,progress=False):
        self.sequence+=1;generation=self.sequence;self.stage=stage;self.busy_ui();self.status.setText({'import':'أقرأ الحزمة وأتعرف على المودات…','prepare':'أفحص الاختيار وأجهّز التركيب…','apply':'أركّب المودات وأحفظ الأصل…'}[stage])
        job=Job(fn,progress);self._job=job;job.signals.result.connect(lambda value:self.got(generation,success,value));job.signals.failure.connect(lambda message:self.failed(generation,message));job.signals.done.connect(lambda:self.finished(generation));job.signals.progress.connect(lambda value:self.import_progress(generation,value));QThreadPool.globalInstance().start(job)
    def got(self,generation,success,value):
        if generation==self.sequence:success(value)
    def failed(self,generation,message):
        if generation!=self.sequence:return
        self.idle();self.status.setText(message);self.import_note.setText('راجع الرسالة أو افتح تفاصيل الفحص. يمكنك إعادة الاستيراد من الحزمة الأصلية.')
    def finished(self,generation):
        if generation==self.sequence and self.stage!='review':self.idle()
    def idle(self):self.stage='';self._job=None;self.busy_ui()
    def busy_ui(self):
        busy=self.busy
        for widget in (self.drop,self.add_button,self.more_button,self.install_button,self.link_button):widget.setEnabled(not busy)
        self.install_button.setEnabled(not busy and self._can_install)
        for check in self.checks.values():check.setEnabled(not busy)
        self.inspect_button.setEnabled(not self.applying);self.cancel_button.setVisible(self.stage in ('import','prepare'));self.progress.setVisible(busy and self.stage!='review')
        self.window.path.setEnabled(not self.applying);self.window.accounts.setEnabled(not self.applying)
    def cancel(self):
        if self.stage in ('import','prepare') and self.cancel_event:self.cancel_event.set();self.status.setText('أوقف العملية بأمان…')
    def import_progress(self,generation,value):
        if generation!=self.sequence:return
        kind,name=value
        if kind=='commit':self.cancel_button.hide();self.status.setText('أحفظ المودات في المكتبة…')
        elif name:self.status.setText('أقرأ: '+name)
