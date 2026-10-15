from pathlib import Path
import copy, difflib, json, platform, sys
from PySide6.QtCore import Qt, QUrl, QStandardPaths, QTimer, QSize
from PySide6.QtGui import QDesktopServices, QFont, QIcon, QFontDatabase
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QLabel,QPushButton,QLineEdit,QFileDialog,QComboBox,QSlider,QCheckBox,QSpinBox,QScrollArea,QStackedWidget,QFrame,QMessageBox,QDialog,QPlainTextEdit,QDialogButtonBox)
from .core import Studio, detect_games, video_files, ASSETS
from .settings import Settings, PRESETS, MODS, TEXTURE_LABELS, level_info, MAX_LEVEL
from .mods import ModLibrary
from .server_ui import ServerPage
from .design import STYLE, ArtworkHero, BrandMark, nav_icon
from . import __version__


def label(text,style=None):
    l=QLabel(text);l.setWordWrap(True)
    if style:l.setObjectName(style)
    return l

def card(title,description=None):
    f=QFrame();f.setObjectName('card');v=QVBoxLayout(f);v.setContentsMargins(20,16,20,16);v.setSpacing(10)
    v.addWidget(label(title,'cardtitle'))
    if description:v.addWidget(label(description,'subtitle'))
    return f,v

class Window(QMainWindow):
    def __init__(self):
        super().__init__();self.setWindowIcon(QIcon(str(ASSETS/'app.png')));self.setWindowTitle('Deadlock Toolbox');self.resize(1280,900);self.setMinimumSize(940,680)
        self.controls={};self.mod_checks={};self.mod_labels={}
        legacy=Path(QStandardPaths.writableLocation(QStandardPaths.GenericDataLocation))/'exelight7/DeadlockFPSStudio/mods'
        self.library=ModLibrary(legacy if legacy.exists() else Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))/'mods')
        root=QWidget();self.setCentralWidget(root);layout=QHBoxLayout(root);layout.setContentsMargins(0,0,0,0)
        sidebar=QFrame();sidebar.setObjectName('sidebar');sidebar.setFixedWidth(218);side=QVBoxLayout(sidebar);side.setContentsMargins(18,26,18,22);side.setSpacing(10)
        brandrow=QHBoxLayout();brandrow.setSpacing(10);brandrow.addWidget(BrandMark())
        brandcopy=QVBoxLayout();brandcopy.setSpacing(0)
        brand=label('Toolbox','brand');brand.setLayoutDirection(Qt.LeftToRight);brand.setAlignment(Qt.AlignRight);brandcopy.addWidget(brand)
        eyebrow=label('DEADLOCK','eyebrow');eyebrow.setLayoutDirection(Qt.LeftToRight);eyebrow.setAlignment(Qt.AlignRight);brandcopy.addWidget(eyebrow)
        brandrow.addLayout(brandcopy,1);side.addLayout(brandrow)
        side.addSpacing(30);side.addWidget(label('مساحة التحكم','sectionLabel'))
        self.stack=QStackedWidget();self.nav=[];self.guard_signature=None;self.guard_retries=0;self.guard_attempts={}
        for index,text in enumerate(['لوحة التحكم','تخصيص الرسوم','المودات','النسخ والاسترجاع','السيرفرات']):
            b=QPushButton(text);b.setObjectName('nav');b.setIcon(nav_icon(index));b.setIconSize(QSize(21,21));b.setCheckable(True);b.clicked.connect(lambda _,i=index:self.navigate(i));side.addWidget(b);self.nav.append(b)
        side.addStretch();side.addWidget(label('أدواتك. إعداداتك. اختيارك.','subtitle'));side.addSpacing(6);version=label(__version__,'badge');version.setLayoutDirection(Qt.LeftToRight);side.addWidget(version,0,Qt.AlignRight);side.addWidget(label('مفتوح المصدر • Windows + Linux','sectionLabel'))
        git=QPushButton('GitHub ↗');git.clicked.connect(lambda:QDesktopServices.openUrl(QUrl('https://github.com/exelight7/deadlock-fps-')));side.addWidget(git)
        layout.addWidget(sidebar)
        content=QWidget();v=QVBoxLayout(content);v.setContentsMargins(26,20,26,20);v.setSpacing(14)
        top=QHBoxLayout();self.heading=label('مساحة العمل / لوحة التحكم','crumb');top.addWidget(self.heading,1)
        top.addWidget(label('مفتوح المصدر','badge'));v.addLayout(top)
        self.hero=ArtworkHero();v.addWidget(self.hero);v.addWidget(self.stack,1)
        self.status=label('جاهز • اختر إعدادًا، ثم راجع التغييرات.','subtitle');v.addWidget(self.status)
        actionbar=QFrame();self.actionbar=actionbar;actionbar.setObjectName('actionbar');footer=QHBoxLayout(actionbar);footer.setContentsMargins(16,10,16,10);self.summary=label('دقة اللعبة محفوظة • خامات بسيطة','subtitle');footer.addWidget(self.summary,1)
        apply=QPushButton('معاينة وتطبيق الإعدادات ←');apply.setObjectName('primary');apply.clicked.connect(self.primary_action);self.apply_button=apply;footer.addWidget(apply);v.addWidget(actionbar)
        layout.addWidget(content,1)
        self.dashboard();self.graphics();self.mods();self.backups();self.servers=ServerPage(self);server_scroll=QScrollArea();server_scroll.setWidgetResizable(True);server_scroll.setWidget(self.servers);self.stack.addWidget(server_scroll);self.servers.layout().removeWidget(self.servers.actions_panel);v.addWidget(self.servers.actions_panel);self.navigate(0);self.load_preset('performance')
        games=detect_games()
        if games:self.path.setText(str(games[0]));self.refresh_accounts()
        try:
            candidates=self.library.discover()
            if candidates:self.library.import_sources(candidates)
        except Exception:pass
        self.refresh_mod_library()
        self.guard_timer=QTimer(self);self.guard_timer.setInterval(5000);self.guard_timer.timeout.connect(self.guard_tick);self.guard_timer.start()
    def closeEvent(self,event):
        if self.servers.busy:
            self.status.setText('انتظر اكتمال عملية السيرفرات قبل إغلاق البرنامج.');self.servers.status.setText(self.status.text());event.ignore()
        else:super().closeEvent(event)
    def page(self):
        page=QWidget();v=QVBoxLayout(page);v.setContentsMargins(0,0,10,0);v.setSpacing(16)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(page);self.stack.addWidget(scroll)
        return v
    def primary_action(self):
        if self.stack.currentIndex()==4:self.servers.block_selected()
        elif self.stack.currentIndex()==2:self.install_mods()
        else:self.preview()
    def navigate(self,i):
        self.stack.setCurrentIndex(i)
        self.hero.set_page(i)
        self.status.setVisible(i!=4)
        self.actionbar.setVisible(i!=4);self.servers.actions_panel.setVisible(i==4)
        self.heading.setText('مساحة العمل / '+self.nav[i].text())
        if hasattr(self,'apply_button'):self.apply_button.setText('حظر السيرفرات المحددة' if i==4 else ('تركيب / تحديث المودات المختارة' if i==2 else 'معاينة وتطبيق الإعدادات ←'))
        for j,b in enumerate(self.nav):b.setChecked(j==i)
        if i==4:self.summary.setText('اختيار مناطق اتصال Steam • يحتاج صلاحية المدير عند التطبيق')
        else:self.changed()
    def dashboard(self):
        v=self.page();f,c=card('اللعبة المرتبطة','يُكتشف مسار Steam تلقائيًا. يمكنك اختيار مجلد اللعبة يدويًا.');v.addWidget(f)
        row=QHBoxLayout();self.path=QLineEdit();self.path.setLayoutDirection(Qt.LeftToRight);self.path.setPlaceholderText('…/steamapps/common/Deadlock');row.addWidget(self.path,1)
        b=QPushButton('تصفح');b.clicked.connect(self.browse_game);row.addWidget(b);c.addLayout(row)
        self.path.editingFinished.connect(self.refresh_accounts)
        self.accounts=QComboBox();self.accounts.setLayoutDirection(Qt.LeftToRight);c.addWidget(label('حساب Steam / ملف إعدادات الفيديو','subtitle'));c.addWidget(self.accounts)
        f,c=card('مستوى التخفيف','ارفع التخفيف لتضعف الرسوم تدريجيًا. الرقم الأعلى يعني رسومًا أبسط وحملًا أقل، وليس قياسًا لقوة جهازك.');v.insertWidget(0,f)
        self.presets={}
        self.level=QSlider(Qt.Horizontal);self.level.setLayoutDirection(Qt.LeftToRight);self.level.setRange(0,MAX_LEVEL);self.level.setTickInterval(25);self.level.setTickPosition(QSlider.TicksBelow);self.level.valueChanged.connect(self.level_changed)
        ends=QWidget();ends.setStyleSheet('background:transparent;');ends.setLayoutDirection(Qt.LeftToRight);row=QHBoxLayout(ends);row.setContentsMargins(0,0,0,0);row.addWidget(label('0 • جودة أعلى / جهاز قوي'));row.addStretch();row.addWidget(label(f'{MAX_LEVEL} • أقصى تخفيف تجريبي'));c.addWidget(ends);c.addWidget(self.level)
        self.level_title=label('','cardtitle');self.level_description=label('','subtitle');c.addWidget(self.level_title);c.addWidget(self.level_description)
        self.level_effects=label('','subtitle');c.addWidget(self.level_effects)
        f,c=card('تحكم مدروس، حتى في أقصى تخفيف','إغلاق اللعبة مطلوب قبل التطبيق. الإعدادات تحفظ الأصل تلقائيًا، وبعض الخيارات المرفقة تجريبية وقد تتجاهلها تحديثات اللعبة. جرّب الوضوح في التدريب بعد كل تغيير.');v.addWidget(f)
        c.addWidget(label(f'النظام: {platform.system()}  •  المعالج: {platform.machine()}','subtitle'));v.addStretch()
    def slider(self,layout,key,title,lo,hi,unit=''):
        row=QHBoxLayout();row.addWidget(label(title),1);out=label('');row.addWidget(out);layout.addLayout(row)
        s=QSlider(Qt.Horizontal);s.setRange(lo,hi);s.valueChanged.connect(lambda value:out.setText(str(value)+unit));s.valueChanged.connect(self.changed);layout.addWidget(s);self.controls[key]=s
    def check(self,layout,key,title):
        b=QCheckBox(title);b.stateChanged.connect(self.changed);layout.addWidget(b);self.controls[key]=b
    def graphics(self):
        v=self.page()
        f,c=card('عرض الرؤية • View width','نسبة الأبعاد مستقلة عن التخفيف. الأساسي 1.78 (16:9)، وارفعها حتى 3.50 لعرض أعرض. لا تتغير دقة الشاشة أو دقة العرض الداخلية.');v.addWidget(f)
        row=QHBoxLayout();row.addWidget(label('Aspect ratio'),1);self.aspect_value=label('1.78','cardtitle');self.aspect_value.setLayoutDirection(Qt.LeftToRight);row.addWidget(self.aspect_value);c.addLayout(row)
        self.aspect=QSlider(Qt.Horizontal);self.aspect.setLayoutDirection(Qt.LeftToRight);self.aspect.setRange(178,350);self.aspect.setSingleStep(1);self.aspect.setPageStep(10);self.aspect.setValue(178);self.aspect.valueChanged.connect(self.aspect_changed);c.addWidget(self.aspect)
        ends=QWidget();ends.setStyleSheet('background:transparent;');ends.setLayoutDirection(Qt.LeftToRight);row=QHBoxLayout(ends);row.setContentsMargins(0,0,0,0);row.addWidget(label('1.78 • Default 16:9'));row.addStretch();row.addWidget(label('3.50 • Ultra wide'));c.addWidget(ends)
        button=QPushButton('الرجوع للأساسي 1.78');button.clicked.connect(lambda:self.aspect.setValue(178));c.addWidget(button)
        c.addWidget(label('حرّك السحاب ثم اضغط معاينة وتطبيق. يتطلب إعادة تشغيل اللعبة؛ قد تختلف النتيجة حسب دعم إصدار اللعبة.','subtitle'))
        f,c=card('كل الرسوم في شريط واحد','استخدم مستوى التخفيف في لوحة التحكم. الوضع الأساسي 80/200 عنيف ويستند إلى إعداداتك المرفقة. جميع المستويات تحافظ على دقة الشاشة والعرض الداخلي وFSR/DLSS.');v.addWidget(f)
        button=QPushButton('تعديل مستوى التخفيف');button.clicked.connect(lambda:self.navigate(0));c.addWidget(button)
        f,c=card('كيف تختار؟','0–20: جهاز قوي وجودة أعلى. 40: جهاز ضعيف. 60: ضعيف جدًا. 80: تخفيف عنيف. 100: شديد. 150: فائق. 175: يخفف حسابات الصوت أيضًا. 200: تجريبي وقد تختفي بعض المؤثرات. ابدأ بالأساسي، وخفّض المستوى إذا أردت تفاصيل أكثر.');v.addWidget(f)
        f,c=card('حد الإطارات','مستقل عن مستوى التخفيف ونسبة الأبعاد.');v.addWidget(f)
        self.slider(c,'fps','حد الإطارات • 0 بدون حد (مستقل عن مستوى التخفيف)',0,500,' FPS')
        f,c=card('إصلاح رجوع الإعدادات','يفحص البرنامج قيم التعديلات بدل الاعتماد على شكل الملف. إذا رجعت القيم، يدمج التخفيف مع الملفات الحالية ويحفظ نسخة قبل الإصلاح.');v.addWidget(f)
        self.guard=QCheckBox('إعادة تطبيق المستوى المحفوظ تلقائيًا بعد إغلاق اللعبة • أبقِ البرنامج مفتوحًا');self.guard.setChecked(True);c.addWidget(self.guard)
        self.guard_status=label('الحماية جاهزة • لا يكتب البرنامج ملفات أثناء تشغيل اللعبة.','subtitle');c.addWidget(self.guard_status)
        button=QPushButton('فحص وإصلاح رجوع الإعدادات الآن');button.clicked.connect(self.repair_settings);c.addWidget(button);v.addStretch()
    def aspect_changed(self,value):
        self.aspect_value.setText(f'{value/100:.2f}');self.changed()
    def level_changed(self,value):
        name,desc=level_info(value);s=Settings.at_level(value)
        self.level_title.setText(f'{value}/{MAX_LEVEL} • {name}');self.level_description.setText(desc)
        self.level_effects.setText(f'تبسيط الخامات {s.textures}/4 • '+('ظلال مفعلة' if s.shadows else 'بدون ظلال')+' • '+('ضباب مفعل' if s.fog else 'بدون ضباب')+' • تفاصيل الجزيئات '+str(s.particles)+'/2')
        self.changed()
    def repair_settings(self):
        try:
            self.guard_status.setText(self.studio().repair(self.library.cache));self.guard_signature=None;self.guard_retries=0;self.refresh_mod_library()
        except Exception as e:self.error(e)
    def guard_tick(self):
        if QApplication.activeModalWidget() or not self.guard.isChecked() or not self.path.text():return
        try:
            from .core import ensure_closed
            ensure_closed();studio=self.studio()
            changed=studio.drift()
            if not changed:
                self.guard_signature=None;self.guard_retries=0;self.guard_status.setText('قيم التعديلات محفوظة • اختلاف تنسيق الأرقام لا يُعتبر رجوعًا.');return
            state=studio.state();from .core import digest
            signature=tuple((name,digest(Path(name).read_bytes()) if Path(name).exists() else None) for name in state['files'])
            if signature!=self.guard_signature:
                self.guard_signature=signature;self.guard_retries=0;self.guard_status.setText('اكتشفت رجوعًا في: '+', '.join(changed)+' • أنتظر استقرار الملفات.');return
            if self.guard_retries>=1:return
            if self.guard_attempts.get(signature,0)>=2:
                self.guard_status.setText('تتكرر إعادة ضبط نفس القيم؛ أوقفت الإصلاح التلقائي. استخدم الإصلاح اليدوي بعد مراجعة اللعبة.');return
            self.guard_attempts[signature]=self.guard_attempts.get(signature,0)+1
            self.guard_retries+=1;self.guard_status.setText(studio.repair(self.library.cache));self.guard_signature=None
        except Exception as e:self.guard_status.setText(str(e))
    def mods(self):
        v=self.page();f,c=card('مكتبة المودات الذكية','استورد الحزمة المضغوطة أو ملفات VPK أو مجلد MODS مرة واحدة. البرنامج يتعرف عليها حتى لو تغيرت أسماؤها ويحفظها للمرة القادمة.');v.addWidget(f)
        row=QHBoxLayout()
        for title,fn in [('بحث تلقائي',self.discover_mods),('استيراد ZIP أو VPK',self.import_mod_files),('استيراد مجلد',self.browse_mods)]:
            button=QPushButton(title);button.clicked.connect(fn);row.addWidget(button)
        c.addLayout(row)
        self.mod_status=label('','subtitle');c.addWidget(self.mod_status)
        for key,(_,title,desc) in MODS.items():
            f,c=card(title,desc);v.addWidget(f);b=QCheckBox('تركيب هذا المود');self.mod_checks[key]=b;c.addWidget(b)
            info=label('','subtitle');c.addWidget(info);self.mod_labels[key]=info
            b.toggled.connect(lambda checked,k=key:self.mod_selected(k,checked))
        button=QPushButton('تركيب / تحديث المودات المختارة');button.setObjectName('primary');button.clicked.connect(self.install_mods);v.addWidget(button)
        v.addWidget(label('التركيب يتم تلقائيًا في مجلد خاص داخل اللعبة، مع تفعيل مسار التحميل والنسخ الاحتياطي. اختيار إزالة الأسماء يلغي شريط الصحة القديم والعكس لتجنب التعارض.','subtitle'));v.addStretch()
        self.refresh_mod_library()
    def refresh_mod_library(self):
        available=self.library.available()
        for key,info in self.mod_labels.items():
            installed=False
            if self.path.text():
                installed=(Path(self.path.text())/'game/citadel/fps_studio'/MODS[key][0].split(' - ')[0]).is_file()
            info.setText('مركّب في اللعبة' if installed else ('جاهز للتركيب' if key in available else 'يحتاج استيراد الحزمة'))
        self.mod_status.setText('المودات الجاهزة: '+('، '.join(MODS[k][1] for k in MODS if k in available) or 'اضغط بحث تلقائي أو استورد الحزمة'))
    def mod_selected(self,key,checked):
        other={'names':'health','health':'names'}.get(key)
        if checked and other:self.mod_checks[other].setChecked(False)
    def import_mod_sources(self,paths):
        imported=self.library.import_sources(paths);self.refresh_mod_library()
        self.status.setText(f'تم تجهيز {len(imported)} مودات. اختر المطلوب ثم اضغط تركيب.')
    def discover_mods(self):
        try:
            candidates=self.library.discover()
            if not candidates:raise ValueError('ضع حزمة MODS بجانب البرنامج أو في التنزيلات، أو استخدم زر الاستيراد.')
            self.import_mod_sources(candidates)
        except Exception as e:self.error(e)
    def import_mod_files(self):
        paths,_=QFileDialog.getOpenFileNames(self,'استيراد المودات','','Mod files (*.zip *.vpk);;All files (*)')
        if paths:
            try:self.import_mod_sources(paths)
            except Exception as e:self.error(e)
    def install_mods(self):
        try:
            studio=self.studio();settings=Settings.from_dict(studio.state().get('settings',{}))
            settings.mods=tuple(k for k,b in self.mod_checks.items() if b.isChecked());settings.validate()
            plan=studio.plan_mods(settings.mods,self.library.cache)
            if not plan:self.status.setText('المودات المختارة مركبة بالفعل.');return
            names='، '.join(MODS[k][1] for k in settings.mods) or 'إزالة مودات البرنامج'
            if QMessageBox.question(self,'تركيب المودات',names+'\nسيحفظ البرنامج الأصل ويطبق تغييرات المودات فقط. متابعة؟')==QMessageBox.Yes:
                fresh=studio.plan_mods(settings.mods,self.library.cache)
                if fresh!=plan:raise ValueError('تغيرت الملفات. أعد المحاولة.')
                self.status.setText(studio.apply(plan,settings,mod_only=True));self.refresh_mod_library();QMessageBox.information(self,'تم تركيب المودات',self.status.text())
        except Exception as e:self.error(e)
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
        if hasattr(self,'level') and 'fps' in self.controls:
            self.summary.setText(f'الدقة محفوظة • تخفيف {self.level.value()}/{MAX_LEVEL} • عرض الرؤية {self.aspect.value()/100:.2f}')
    def load_settings(self,s):
        self.level.setValue(s.level);self.level_changed(s.level)
        self.controls['fps'].setValue(s.fps)
        self.aspect.setValue(round((s.aspect_ratio if s.aspect_ratio is not None else 1.78)*100));self.aspect_changed(self.aspect.value())
        for key,b in self.mod_checks.items():b.setChecked(key in s.mods)
    def load_preset(self,key):
        s=copy.deepcopy(PRESETS[key]);s.aspect_ratio=self.aspect.value()/100;self.load_settings(s)
    def settings(self):
        s=Settings.at_level(self.level.value(),aspect_ratio=self.aspect.value()/100,fps=self.controls['fps'].value(),preset='custom',mods=tuple(k for k,b in self.mod_checks.items() if b.isChecked()));s.validate();return s
    def browse_game(self):
        p=QFileDialog.getExistingDirectory(self,'اختر مجلد Deadlock')
        if p:self.path.setText(p);self.refresh_accounts()
    def browse_mods(self):
        p=QFileDialog.getExistingDirectory(self,'اختر مجلد MODS')
        if p:
            try:self.import_mod_sources([p])
            except Exception as e:self.error(e)
    def refresh_accounts(self):
        self.accounts.clear()
        try:
            from .core import game_root
            root=game_root(self.path.text())
            for f in video_files(root):self.accounts.addItem(str(f),str(f))
            self.status.setText('تم العثور على اللعبة • الدقة محفوظة دائمًا.')
            saved=Studio(root,self.accounts.currentData()).state().get('settings')
            if saved:self.load_settings(Settings.from_dict(saved))
        except Exception as e:self.status.setText(str(e))
    def studio(self):return Studio(self.path.text(),self.accounts.currentData())
    def error(self,e):QMessageBox.warning(self,'تعذر إكمال العملية',str(e));self.status.setText(str(e))
    def preview(self):
        try:
            studio=self.studio();s=self.settings();plan=studio.plan(s,self.library.cache)
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
                fresh=studio.plan(s,self.library.cache)
                if fresh!=plan:raise ValueError('تغيرت الملفات أثناء المعاينة. أعد المعاينة.')
                self.status.setText(studio.apply(plan,s));self.refresh_mod_library();QMessageBox.information(self,'تم التطبيق',self.status.text())
        except Exception as e:self.error(e)
    def restore(self):
        try:
            studio=self.studio()
            if QMessageBox.question(self,'استرجاع الأصل','سيتم حفظ الحالة الحالية ثم استرجاع النسخ الأصلية. متابعة؟')==QMessageBox.Yes:self.guard.setChecked(False);self.status.setText(studio.restore(self.preserve.isChecked()))
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
                s=Settings.from_dict(json.loads(Path(p).read_text()));s.validate();self.load_settings(s);self.status.setText('تم الاستيراد • راجع ثم طبّق.')
        except Exception as e:self.error(e)

def main():
    app=QApplication(sys.argv);app.setApplicationName('DeadlockToolbox');app.setApplicationDisplayName('Deadlock Toolbox');app.setOrganizationName('exelight7');app.setLayoutDirection(Qt.RightToLeft);app.setStyle('Fusion');QFontDatabase.addApplicationFont(str(ASSETS/'fonts/NotoSansArabic.ttf'));app.setStyleSheet(STYLE)
    window=Window();window.show();sys.exit(app.exec())
