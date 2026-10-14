from pathlib import Path
import copy, difflib, json, platform, sys
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QIcon
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QLabel,QPushButton,QLineEdit,QFileDialog,QComboBox,QSlider,QCheckBox,QSpinBox,QScrollArea,QStackedWidget,QFrame,QMessageBox,QDialog,QPlainTextEdit,QDialogButtonBox)
from .core import Studio, detect_games, video_files, ASSETS
from .settings import Settings, PRESETS, MODS
STYLE='''
QWidget { background:#101419; color:#e7e9eb; font-family:"Noto Sans Arabic","Segoe UI",sans-serif; font-size:14px; }
QMainWindow {background:#101419;} QFrame#sidebar {background:#171d24;border-left:1px solid #2a333e;}
QFrame#sidebar QLabel {background:transparent;}
QLabel#brand {color:#cff47b;font-size:23px;font-weight:800;} QLabel#eyebrow {color:#a8c868;font-size:12px;}
QLabel#title {font-size:32px;font-weight:800;} QLabel#subtitle {color:#94a2b2;font-size:14px;}
QFrame#card {background:#192129;border:1px solid #303c47;border-radius:14px;}
QFrame#card QLabel {background:transparent;} QLabel#cardtitle {font-size:18px;font-weight:700;}
QPushButton {background:#242f39;border:1px solid #364452;border-radius:9px;padding:11px 18px;font-weight:600;}
QPushButton:hover {background:#344452;border-color:#a4c66c;} QPushButton:checked {color:#d8fa9e;background:#35432c;border-color:#98b866;}
QPushButton#primary {background:#c6ee7b;color:#17210e;border:0;font-size:16px;padding:14px 22px;}
QPushButton#primary:hover {background:#ddffa4;} QPushButton:disabled {color:#65717c;background:#252b31;}
QLineEdit,QComboBox,QSpinBox,QPlainTextEdit {background:#111820;border:1px solid #354350;border-radius:7px;padding:8px;selection-background-color:#637f3e;}
QComboBox QAbstractItemView {background:#192129;selection-background-color:#35432c;}
QCheckBox {spacing:12px;padding:9px;} QCheckBox::indicator {width:19px;height:19px;border:1px solid #506171;border-radius:5px;background:#111820;}
QCheckBox::indicator:checked {background:#c6ee7b;border-color:#c6ee7b;}
QSlider::groove:horizontal {height:6px;background:#354350;border-radius:3px;} QSlider::sub-page:horizontal {background:#b9df73;border-radius:3px;}
QSlider::handle:horizontal {width:18px;margin:-6px 0;background:#d5f49c;border-radius:9px;}
QScrollArea {border:0;} QScrollBar:vertical {background:#131a21;width:8px;} QScrollBar::handle:vertical {background:#465345;border-radius:4px;min-height:25px;}
QDialog {background:#101419;}
'''

def label(text,style=None):
    l=QLabel(text);l.setWordWrap(True)
    if style:l.setObjectName(style)
    return l

def card(title,description=None):
    f=QFrame();f.setObjectName('card');v=QVBoxLayout(f);v.setContentsMargins(22,18,22,18);v.setSpacing(12)
    v.addWidget(label(title,'cardtitle'))
    if description:v.addWidget(label(description,'subtitle'))
    return f,v

class Window(QMainWindow):
    def __init__(self):
        super().__init__();self.setWindowIcon(QIcon(str(ASSETS/'app.png')));self.setWindowTitle('Deadlock FPS Studio');self.resize(1180,850);self.setMinimumSize(940,680)
        self.controls={};self.mod_checks={}
        root=QWidget();self.setCentralWidget(root);layout=QHBoxLayout(root);layout.setContentsMargins(0,0,0,0)
        sidebar=QFrame();sidebar.setObjectName('sidebar');sidebar.setFixedWidth(225);side=QVBoxLayout(sidebar);side.setContentsMargins(22,32,22,28);side.setSpacing(14)
        side.addWidget(label('◈  DEADLOCK','brand'));side.addWidget(label('FPS STUDIO / 1.0','eyebrow'));side.addSpacing(40)
        self.stack=QStackedWidget();self.nav=[]
        for index,text in enumerate(['لوحة التحكم','تخصيص الرسوم','المودات','النسخ والاسترجاع']):
            b=QPushButton(text);b.setCheckable(True);b.clicked.connect(lambda _,i=index:self.navigate(i));side.addWidget(b);self.nav.append(b)
        side.addStretch();side.addWidget(label('مفتوح المصدر\nWindows + Linux','subtitle'))
        git=QPushButton('GitHub ↗');git.clicked.connect(lambda:QDesktopServices.openUrl(QUrl('https://github.com/exelight7/deadlock-fps-')));side.addWidget(git)
        layout.addWidget(sidebar)
        content=QWidget();v=QVBoxLayout(content);v.setContentsMargins(30,28,30,22);v.setSpacing(18)
        self.heading=label('أداء أعلى. تحكم كامل.','title');v.addWidget(self.heading)
        v.addWidget(label('خفّف الرسوم، خصّص تجربتك، وارجع لإعداداتك في أي وقت.','subtitle'));v.addWidget(self.stack,1)
        self.status=label('جاهز • اختر إعدادًا، ثم راجع التغييرات.','subtitle');v.addWidget(self.status)
        footer=QHBoxLayout();self.summary=label('67% دقة العرض  /  120 FPS حد الإطارات','subtitle');footer.addWidget(self.summary,1)
        apply=QPushButton('معاينة وتطبيق الإعدادات ←');apply.setObjectName('primary');apply.clicked.connect(self.preview);footer.addWidget(apply);v.addLayout(footer)
        layout.addWidget(content,1)
        self.dashboard();self.graphics();self.mods();self.backups();self.navigate(0);self.load_preset('performance')
        games=detect_games()
        if games:self.path.setText(str(games[0]));self.refresh_accounts()
    def page(self):
        page=QWidget();v=QVBoxLayout(page);v.setContentsMargins(0,0,10,0);v.setSpacing(16)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(page);self.stack.addWidget(scroll)
        return v
    def navigate(self,i):
        self.stack.setCurrentIndex(i)
        for j,b in enumerate(self.nav):b.setChecked(j==i)
    def dashboard(self):
        v=self.page();f,c=card('01  /  اربط لعبتك','يُكتشف مسار Steam تلقائيًا. يمكنك اختيار مجلد اللعبة يدويًا.');v.addWidget(f)
        row=QHBoxLayout();self.path=QLineEdit();self.path.setLayoutDirection(Qt.LeftToRight);self.path.setPlaceholderText('…/steamapps/common/Deadlock');row.addWidget(self.path,1)
        b=QPushButton('تصفح');b.clicked.connect(self.browse_game);row.addWidget(b);c.addLayout(row)
        self.path.editingFinished.connect(self.refresh_accounts)
        self.accounts=QComboBox();self.accounts.setLayoutDirection(Qt.LeftToRight);c.addWidget(label('حساب Steam / ملف إعدادات الفيديو','subtitle'));c.addWidget(self.accounts)
        f,c=card('02  /  اختر نقطة البداية','كل وضع قابل للتعديل. لا توجد أرقام زيادة FPS مضمونة.');v.addWidget(f)
        row=QHBoxLayout();self.presets={}
        for key,name,desc in [('balanced','متوازن','وضوح أفضل · 85%'),('performance','أداء قوي','أجهزة ضعيفة · 67%'),('ultra','أقصى تخفيف','720p · 50% · خامات مبسطة')]:
            b=QPushButton(name+'\n'+desc);b.setMinimumHeight(90);b.setCheckable(True);b.clicked.connect(lambda _,k=key:self.load_preset(k));row.addWidget(b,1);self.presets[key]=b
        c.addLayout(row)
        f,c=card('تحكم مدروس، حتى في أقصى تخفيف','إغلاق اللعبة مطلوب قبل التطبيق. الإعدادات تحفظ الأصل تلقائيًا، وبعض الخيارات المرفقة تجريبية وقد تتجاهلها تحديثات اللعبة. جرّب الوضوح في التدريب بعد كل تغيير.');v.addWidget(f)
        c.addWidget(label(f'النظام: {platform.system()}  •  المعالج: {platform.machine()}','subtitle'));v.addStretch()
    def slider(self,layout,key,title,lo,hi,unit=''):
        row=QHBoxLayout();row.addWidget(label(title),1);out=label('');row.addWidget(out);layout.addLayout(row)
        s=QSlider(Qt.Horizontal);s.setRange(lo,hi);s.valueChanged.connect(lambda value:out.setText(str(value)+unit));s.valueChanged.connect(self.changed);layout.addWidget(s);self.controls[key]=s
    def check(self,layout,key,title):
        b=QCheckBox(title);b.stateChanged.connect(self.changed);layout.addWidget(b);self.controls[key]=b
    def graphics(self):
        v=self.page();f,c=card('الدقة والخامات','خفض دقة العرض والخامات يركز على تقليل حمل كرت الشاشة.');v.addWidget(f)
        self.slider(c,'scale','دقة العرض الداخلية',25,100,'%');self.slider(c,'textures','تبسيط الخامات • 0 أعلى جودة / 4 أقل جودة',0,4)
        row=QHBoxLayout();row.addWidget(label('دقة الشاشة'),1);self.resolution=QComboBox();self.resolution.addItems(['الحفاظ على الحالية','1280 × 720','1600 × 900','1920 × 1080','مخصصة']);self.resolution.currentIndexChanged.connect(self.changed);row.addWidget(self.resolution);c.addLayout(row)
        row=QHBoxLayout();self.width=QSpinBox();self.width.setRange(640,7680);self.width.setValue(1280);self.height=QSpinBox();self.height.setRange(480,4320);self.height.setValue(720);row.addWidget(label('العرض / الارتفاع المخصص'));row.addWidget(self.width);row.addWidget(self.height);c.addLayout(row)
        self.width.valueChanged.connect(self.changed);self.height.valueChanged.connect(self.changed)
        self.slider(c,'fps','حد الإطارات • 0 بدون حد',0,500,' FPS')
        f,c=card('الإضاءة والمؤثرات','التعطيل يقلل التفاصيل. خيارات الظلال والضباب تشمل تعديلات ملف المحرك عند تفعيله.');v.addWidget(f)
        for k,t in [('shadows','الظلال'),('fog','الضباب'),('bloom','وهج الإضاءة'),('ao','التظليل المحيطي')]: self.check(c,k,t)
        self.slider(c,'particles','تفاصيل الجزيئات • 0 أقل / 2 أعلى',0,2)
        f,c=card('تخفيف إضافي من ملفاتك','تعديلات المحرك مشتقة من الحزمة المرفقة، وتُدمج في gameinfo الحالي. لا تُغيّر جدولة النظام أو إعدادات الشبكة.');v.addWidget(f)
        self.check(c,'cpu','تقليل الحطام والجثث وحركة القوائم (يتطلب تعديل المحرك)');self.check(c,'engine','تفعيل تعديلات المحرك التجريبية');v.addStretch()
    def mods(self):
        v=self.page();f,c=card('موداتك، باختيارك','اختر مجلد MODS من الحزمة الأصلية. تُنسخ المودات المحددة إلى مجلد مستقل، دون المساس بموداتك الأخرى.');v.addWidget(f)
        row=QHBoxLayout();self.modpath=QLineEdit();self.modpath.setLayoutDirection(Qt.LeftToRight)
        default=Path(__file__).resolve().parents[2]/'MODS'
        if default.exists(): self.modpath.setText(str(default))
        row.addWidget(self.modpath,1);b=QPushButton('مجلد المودات');b.clicked.connect(self.browse_mods);row.addWidget(b);c.addLayout(row)
        for key,(_,title,desc) in MODS.items():
            f,c=card(title,desc);v.addWidget(f);b=QCheckBox('تفعيل المود');self.mod_checks[key]=b;c.addWidget(b)
        v.addWidget(label('إزالة الأسماء وشريط الصحة القديم يتعارضان. لا يُسمح بتفعيلهما معًا. تأثير المودات على الأداء غير مقاس، وقد تتوقف بعد تحديثات اللعبة.','subtitle'));v.addStretch()
    def backups(self):
        v=self.page();f,c=card('الأصل محفوظ','يحفظ البرنامج النسخ الأصلية قبل أول تعديل. إعادة التطبيق لا تستبدلها. الاسترجاع يحفظ أيضًا الحالة الحالية داخل مجلد النسخ.');v.addWidget(f)
        b=QPushButton('فتح مجلد النسخ الاحتياطية ↗');b.clicked.connect(self.open_backups);c.addWidget(b)
        self.preserve=QCheckBox('حفظ التغييرات الخارجية الحالية ثم استرجاع الأصل (بعد تحديث اللعبة مثلًا)');c.addWidget(self.preserve)
        b=QPushButton('استرجاع الإعدادات الأصلية');b.clicked.connect(self.restore);c.addWidget(b)
        f,c=card('ملفات إعدادات قابلة للمشاركة','صدّر إعدادات الواجهة أو استوردها بصيغة JSON. لا يتضمن التصدير ملفات اللعبة أو حساب Steam.');v.addWidget(f)
        row=QHBoxLayout()
        for title,fn in [('تصدير الإعدادات',self.export_settings),('استيراد الإعدادات',self.import_settings)]:
            b=QPushButton(title);b.clicked.connect(fn);row.addWidget(b)
        c.addLayout(row);v.addStretch()
    def changed(self,*_):
        if not getattr(self,'loading',False):
            for b in getattr(self,'presets',{}).values():b.setChecked(False)
        if 'fps' in self.controls:
            self.summary.setText(f"{self.controls['scale'].value()}% دقة العرض  /  {self.controls['fps'].value()} FPS حد الإطارات")
    def load_settings(self,s):
        self.loading=True
        for key,w in self.controls.items():
            if isinstance(w,QCheckBox):w.setChecked(getattr(s,key))
            else:w.setValue(getattr(s,key))
        pairs=[(0,0),(1280,720),(1600,900),(1920,1080)]
        self.resolution.setCurrentIndex(pairs.index((s.width,s.height)) if (s.width,s.height) in pairs else 4)
        if s.width:self.width.setValue(s.width);self.height.setValue(s.height)
        for key,b in self.mod_checks.items():b.setChecked(key in s.mods)
        for key,b in self.presets.items():b.setChecked(key==s.preset)
        self.loading=False
    def load_preset(self,key):self.load_settings(copy.deepcopy(PRESETS[key]))
    def settings(self):
        data={k:(w.isChecked() if isinstance(w,QCheckBox) else w.value()) for k,w in self.controls.items()}
        pair=[(0,0),(1280,720),(1600,900),(1920,1080),(self.width.value(),self.height.value())][self.resolution.currentIndex()]
        s=Settings(**data,width=pair[0],height=pair[1],preset='custom',mods=tuple(k for k,b in self.mod_checks.items() if b.isChecked()));s.validate();return s
    def browse_game(self):
        p=QFileDialog.getExistingDirectory(self,'اختر مجلد Deadlock')
        if p:self.path.setText(p);self.refresh_accounts()
    def browse_mods(self):
        p=QFileDialog.getExistingDirectory(self,'اختر مجلد MODS')
        if p:self.modpath.setText(p)
    def refresh_accounts(self):
        self.accounts.clear()
        try:
            from .core import game_root
            root=game_root(self.path.text())
            for f in video_files(root):self.accounts.addItem(str(f),str(f))
            self.status.setText('تم العثور على اللعبة • اختر حساب Steam المطلوب.')
        except Exception as e:self.status.setText(str(e))
    def studio(self):return Studio(self.path.text(),self.accounts.currentData())
    def error(self,e):QMessageBox.warning(self,'تعذر إكمال العملية',str(e));self.status.setText(str(e))
    def preview(self):
        try:
            studio=self.studio();s=self.settings();plan=studio.plan(s,self.modpath.text())
            if not plan:self.status.setText('الإعدادات مطبقة بالفعل.');return
            dialog=QDialog(self);dialog.setWindowTitle('مراجعة التغييرات');dialog.resize(880,650);v=QVBoxLayout(dialog)
            v.addWidget(label(f'سيتم تعديل {len(plan)} ملفات مع حفظ الأصل. أغلق اللعبة قبل المتابعة.','cardtitle'))
            out=QPlainTextEdit();out.setReadOnly(True);out.setLayoutDirection(Qt.LeftToRight);out.setFont(QFont('monospace',10));parts=[]
            for p,b in plan.items():
                parts.append(str(p))
                if p.suffix in {'.gi','.txt'} and b is not None:
                    old=p.read_text(errors='replace') if p.exists() else ''
                    parts.append(''.join(difflib.unified_diff(old.splitlines(True),b.decode().splitlines(True),fromfile='current',tofile='proposed')))
                else:parts.append('Remove managed file' if b is None else f'Install VPK: {len(b):,} bytes')
            out.setPlainText('\n\n'.join(parts));v.addWidget(out,1)
            buttons=QDialogButtonBox();ok=buttons.addButton('تطبيق وحفظ نسخة احتياطية',QDialogButtonBox.AcceptRole);buttons.addButton('إلغاء',QDialogButtonBox.RejectRole);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);v.addWidget(buttons)
            if dialog.exec()==QDialog.Accepted:
                # Regenerate after preview to detect file changes before committing.
                fresh=studio.plan(s,self.modpath.text())
                if fresh!=plan:raise ValueError('تغيرت الملفات أثناء المعاينة. أعد المعاينة.')
                self.status.setText(studio.apply(plan,s));QMessageBox.information(self,'تم التطبيق',self.status.text())
        except Exception as e:self.error(e)
    def restore(self):
        try:
            studio=self.studio()
            if QMessageBox.question(self,'استرجاع الأصل','سيتم حفظ الحالة الحالية ثم استرجاع النسخ الأصلية. متابعة؟')==QMessageBox.Yes:self.status.setText(studio.restore(self.preserve.isChecked()))
        except Exception as e:self.error(e)
    def open_backups(self):
        try:
            studio=self.studio();studio.store.mkdir(parents=True,exist_ok=True);QDesktopServices.openUrl(QUrl.fromLocalFile(str(studio.store)))
        except Exception as e:self.error(e)
    def export_settings(self):
        try:
            s=self.settings();p,_=QFileDialog.getSaveFileName(self,'تصدير','deadlock-profile.json','JSON (*.json)')
            if p:Path(p).write_text(json.dumps(s.to_dict(),indent=2));self.status.setText('تم تصدير الإعدادات.')
        except Exception as e:self.error(e)
    def import_settings(self):
        try:
            p,_=QFileDialog.getOpenFileName(self,'استيراد','','JSON (*.json)')
            if p:
                s=Settings(**json.loads(Path(p).read_text()));s.validate();self.load_settings(s);self.status.setText('تم الاستيراد • راجع ثم طبّق.')
        except Exception as e:self.error(e)

def main():
    app=QApplication(sys.argv);app.setLayoutDirection(Qt.RightToLeft);app.setStyle('Fusion');app.setStyleSheet(STYLE)
    window=Window();window.show();sys.exit(app.exec())
