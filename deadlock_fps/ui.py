from pathlib import Path
import copy, difflib, json, platform, sys
from PySide6.QtCore import Qt, QUrl, QStandardPaths, QTimer, QSize
from PySide6.QtGui import QDesktopServices, QFont, QIcon, QFontDatabase
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QLabel,QPushButton,QLineEdit,QFileDialog,QComboBox,QSlider,QCheckBox,QSpinBox,QScrollArea,QStackedWidget,QFrame,QMessageBox,QDialog,QPlainTextEdit,QDialogButtonBox)
from .core import Studio, detect_games, video_files, ASSETS
from .settings import Settings, PRESETS, MODS, TEXTURE_LABELS, level_info, MAX_LEVEL
from .mods import ModLibrary
from .server_ui import ServerPage
from .crosshair_ui import CrosshairPage
from .update_ui import UpdatePage
from .inspector_ui import InspectorPage
from .mod_inspector import require_mods
from .mod_ui import ModPage
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
        super().__init__();self.setWindowIcon(QIcon(str(ASSETS/'app.png')));self.setWindowTitle('Deadlock Toolbox');self.resize(1200,820);self.setMinimumSize(940,680)
        self.preferences_file=Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))/'workspace.json'
        self.preferred_account=None;self.saved_game=''
        try:
            saved=json.loads(self.preferences_file.read_text(encoding='utf-8'))
            if isinstance(saved,dict):
                self.saved_game=saved.get('game','') if isinstance(saved.get('game'),str) else ''
                self.preferred_account=saved.get('account') if isinstance(saved.get('account'),str) else None
        except (OSError,ValueError):pass
        self.controls={};self.mod_checks={};self.mod_labels={}
        legacy=Path(QStandardPaths.writableLocation(QStandardPaths.GenericDataLocation))/'exelight7/DeadlockFPSStudio/mods'
        self.library=ModLibrary(legacy if legacy.exists() else Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))/'mods')
        root=QWidget();self.setCentralWidget(root);layout=QHBoxLayout(root);layout.setContentsMargins(0,0,0,0)
        sidebar=QFrame();sidebar.setObjectName('sidebar');sidebar.setFixedWidth(218);side=QVBoxLayout(sidebar);side.setContentsMargins(16,18,16,16);side.setSpacing(6)
        brandrow=QHBoxLayout();brandrow.setSpacing(10);brandrow.addWidget(BrandMark())
        brandcopy=QVBoxLayout();brandcopy.setSpacing(0)
        brand=label('Toolbox','brand');brand.setLayoutDirection(Qt.LeftToRight);brand.setAlignment(Qt.AlignRight);brandcopy.addWidget(brand)
        eyebrow=label('DEADLOCK','eyebrow');eyebrow.setLayoutDirection(Qt.LeftToRight);eyebrow.setAlignment(Qt.AlignRight);brandcopy.addWidget(eyebrow)
        brandrow.addLayout(brandcopy,1);side.addLayout(brandrow)
        side.addSpacing(14);side.addWidget(label('مساحة التحكم','sectionLabel'))
        nav_body=QWidget();nav_body.setObjectName('navContent');nav_body.setStyleSheet('QWidget#navContent {background:#101a22;}');nav_layout=QVBoxLayout(nav_body);nav_layout.setContentsMargins(0,0,0,0);nav_layout.setSpacing(6)
        self.nav_scroll=QScrollArea();self.nav_scroll.setWidgetResizable(True);self.nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);self.nav_scroll.setWidget(nav_body);side.addWidget(self.nav_scroll,1)
        self.stack=QStackedWidget();self.nav=[];self.guard_signature=None;self.guard_retries=0;self.guard_attempts={}
        for index,text in enumerate(['ابدأ هنا','الرسوم والأداء','المودات','النسخ والاسترجاع','السيرفرات','الكروس هير','التحديث والتثبيت','فحص المودات']):
            b=QPushButton(text);b.setObjectName('nav');b.setIcon(nav_icon(index));b.setIconSize(QSize(21,21));b.setCheckable(True);b.clicked.connect(lambda _,i=index:self.navigate(i));nav_layout.addWidget(b);self.nav.append(b)
        nav_layout.addStretch();side.addWidget(label('أدواتك. إعداداتك. اختيارك.','subtitle'));side.addSpacing(6);version=label(__version__,'badge');version.setLayoutDirection(Qt.LeftToRight);side.addWidget(version,0,Qt.AlignRight);side.addWidget(label('مفتوح المصدر • Windows + Linux','sectionLabel'))
        git=QPushButton('GitHub ↗');git.clicked.connect(lambda:QDesktopServices.openUrl(QUrl('https://github.com/exelight7/deadlock-fps-')));side.addWidget(git)
        layout.addWidget(sidebar)
        content=QWidget();v=QVBoxLayout(content);v.setContentsMargins(24,18,24,18);v.setSpacing(12)
        top=QHBoxLayout();self.heading=label('مساحة العمل / لوحة التحكم','crumb');top.addWidget(self.heading,1)
        self.game_chip=QPushButton('ربط اللعبة');self.game_chip.setObjectName('quiet');self.game_chip.clicked.connect(self.focus_game);top.addWidget(self.game_chip)
        self.private_badge=label('مفتوح المصدر','badge');top.addWidget(self.private_badge);v.addLayout(top)
        self.hero=ArtworkHero();v.addWidget(self.hero);self.page_hint=label('','stepPill');v.addWidget(self.page_hint);v.addWidget(self.stack,1)
        self.status=label('جاهز • اختر إعدادًا، ثم راجع التغييرات.','subtitle');v.addWidget(self.status)
        actionbar=QFrame();self.actionbar=actionbar;actionbar.setObjectName('actionbar');footer=QHBoxLayout(actionbar);footer.setContentsMargins(16,10,16,10);self.summary=label('دقة اللعبة محفوظة • خامات بسيطة','subtitle');footer.addWidget(self.summary,1)
        apply=QPushButton('معاينة وتطبيق الإعدادات ←');apply.setObjectName('primary');apply.clicked.connect(self.primary_action);self.apply_button=apply;footer.addWidget(apply);v.addWidget(actionbar)
        layout.addWidget(content,1)
        self.dashboard();self.graphics();self.mods();self.backups();self.servers=ServerPage(self);server_scroll=QScrollArea();server_scroll.setWidgetResizable(True);server_scroll.setWidget(self.servers);self.stack.addWidget(server_scroll);self.servers.layout().removeWidget(self.servers.actions_panel);v.addWidget(self.servers.actions_panel);self.crosshair=CrosshairPage(lambda:(self.path.text(),self.accounts.currentData()),self);self.stack.addWidget(self.crosshair);self.crosshair.layout().removeWidget(self.crosshair.actions_panel);v.addWidget(self.crosshair.actions_panel)
        self.updates=UpdatePage(self);self.stack.addWidget(self.updates);self.updates.updateAvailable.connect(lambda available:self.nav[6].setText('التحديث والتثبيت •' if available else 'التحديث والتثبيت'))
        if self.updates.release and self.updates.release.version>self.updates.current:self.nav[6].setText('التحديث والتثبيت •')
        self.inspector=InspectorPage(self);self.stack.addWidget(self.inspector)
        self.path.editingFinished.connect(self.inspector.invalidate)
        self.update_startup_timer=QTimer(self);self.update_startup_timer.setSingleShot(True);self.update_startup_timer.timeout.connect(self.updates.automatic_check)
        self.navigate(0);self.load_preset('balanced')
        games=detect_games()
        if self.saved_game and (Path(self.saved_game)/'game/citadel/gameinfo.gi').is_file():self.path.setText(self.saved_game);self.refresh_accounts()
        elif games:self.path.setText(str(games[0]));self.refresh_accounts()
        try:
            candidates=self.library.discover()
            if candidates:self.library.import_sources(candidates)
        except Exception:pass
        self.refresh_mod_library()
        self.guard_timer=QTimer(self);self.guard_timer.setInterval(5000);self.guard_timer.timeout.connect(self.guard_tick);self.guard_timer.start()
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'hero') and hasattr(self,'stack'):self.hero.setVisible(self.stack.currentIndex() in (2,3,4) and self.height()>=800)
    def closeEvent(self,event):
        if self.updates.installing:
            self.updates.detail.setText('انتظر اكتمال التثبيت قبل إغلاق البرنامج.');event.ignore();return
        if self.mods_page.applying:
            self.mods_page.status.setText('أكمل حفظ الملفات أولًا؛ ينتهي التركيب بعد لحظات.');event.ignore();return
        if self.servers.busy:
            self.status.setText('انتظر اكتمال عملية السيرفرات قبل إغلاق البرنامج.');self.servers.status.setText(self.status.text());event.ignore()
        else:
            if hasattr(self,'guard_timer'):self.guard_timer.stop()
            self.update_startup_timer.stop();self.updates.client.cancel()
            self.inspector.cancel();self.mods_page.cancel()
            super().closeEvent(event)
    def page(self):
        page=QWidget();v=QVBoxLayout(page);v.setContentsMargins(0,0,10,0);v.setSpacing(16)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(page);self.stack.addWidget(scroll)
        return v
    def primary_action(self):
        if self.stack.currentIndex()==7:self.inspector.scan()
        elif self.stack.currentIndex()==6:self.updates.check()
        elif self.stack.currentIndex()==5:self.crosshair.review()
        elif self.stack.currentIndex()==4:self.servers.block_selected()
        elif self.stack.currentIndex()==2:self.install_mods()
        else:self.preview()
    def navigate(self,i):
        self.stack.setCurrentIndex(i)
        self.page_hint.setText([
            'ابدأ من هنا: اربط اللعبة ← اختر الأداء ← راجع وطبّق.',
            'اختر مستوى التخفيف. نسبة الأبعاد وحد الإطارات اختيارات إضافية.',
            'أضف ZIP أو VPK ← اختر المودات ← راجع التركيب. الفحص يتم قبل الحفظ.',
            'تبي ترجع؟ استرجع الأصل. تبي تنقل خياراتك؟ صدّر إعداداتك.',
            'انتظر القياس ← حدد المناطق ← اختر السماح بها فقط أو الحظر. فك كل الحظر متاح دائمًا.',
            'اختر تصميمًا جاهزًا، جرّب المعاينة، ثم راجع تطبيقه على حسابك.',
            'تحقق من التحديثات ← نزّل ← ثبّت ← افتح النسخة الجديدة.',
            'الفحص يوضح الملفات الناقصة والتالفة. عالج الأخطاء ثم ارجع للمودات للتركيب.'
        ][i])
        self.hero.setVisible(i in (2,3,4) and self.height()>=800)
        self.hero.set_page(i)
        self.status.setVisible(i in (0,1,3))
        self.actionbar.setVisible(i in (0,1));self.servers.actions_panel.setVisible(i==4);self.crosshair.actions_panel.setVisible(i==5)
        self.heading.setText(('Workspace / ' if i==5 else 'مساحة العمل / ')+self.nav[i].text().removesuffix(' •'));self.private_badge.setText('Open source' if i==5 else 'مفتوح المصدر')
        linked=self.game_chip.text() in ('اللعبة مرتبطة','Game connected');self.game_chip.setText(('Game connected' if linked else 'Connect game') if i==5 else ('اللعبة مرتبطة' if linked else 'ربط اللعبة'))
        if hasattr(self,'apply_button'):self.apply_button.setText('حظر السيرفرات المحددة' if i==4 else ('تركيب / تحديث المودات المختارة' if i==2 else 'معاينة وتطبيق الإعدادات ←'))
        for j,b in enumerate(self.nav):b.setChecked(j==i)
        self.nav_scroll.ensureWidgetVisible(self.nav[i])
        if i==4:self.summary.setText('اختيار مناطق اتصال Steam • يحتاج صلاحية المدير عند التطبيق')
        else:self.changed()
    def dashboard(self):
        v=self.page();shortcuts=QHBoxLayout()
        for title,index in [('المودات',2),('فحص المودات',7),('السيرفرات',4)]:
            button=QPushButton(title);button.setIcon(nav_icon(index));button.setIconSize(QSize(24,24));button.setObjectName('shortcut');button.clicked.connect(lambda _,i=index:self.navigate(i));shortcuts.addWidget(button,1)
        v.addLayout(shortcuts);f,c=card('1 · اربط اللعبة مرة واحدة','نكتشف Steam تلقائيًا ونحفظ اختيارك. اختر مجلد Deadlock أو مجلد game بداخله.');v.addWidget(f)
        self.connection_note=label('اختر مجلد اللعبة للبدء. تقدر تستخدم التحديث والمكتبة بدون ربط.','stepPill');c.addWidget(self.connection_note)
        row=QHBoxLayout();self.path=QLineEdit();self.path.setLayoutDirection(Qt.LeftToRight);self.path.setPlaceholderText('…/steamapps/common/Deadlock');row.addWidget(self.path,1)
        b=QPushButton('اختيار المجلد');b.clicked.connect(self.browse_game);row.addWidget(b)
        b=QPushButton('بحث تلقائي');b.clicked.connect(self.detect_game);row.addWidget(b);c.addLayout(row)
        self.path.editingFinished.connect(self.refresh_accounts)
        self.accounts=QComboBox();self.accounts.setLayoutDirection(Qt.LeftToRight);self.accounts.currentIndexChanged.connect(self.remember_account);self.account_label=label('حساب Steam · اختر الحساب الذي تلعب عليه','subtitle');c.addWidget(self.account_label);c.addWidget(self.accounts);self.account_label.hide();self.accounts.hide()
        f,c=card('2 · اختر الأداء المناسب','ابدأ بمتوازن. ارفع التخفيف إذا احتجت أداء أعلى؛ دقة اللعبة محفوظة.');v.addWidget(f)
        row=QHBoxLayout()
        for title,key in [('متوازن','balanced'),('أداء أعلى','performance'),('تخفيف شديد','ultra')]:
            b=QPushButton(title);b.clicked.connect(lambda _,k=key:self.load_preset(k));row.addWidget(b)
        c.addLayout(row)
        self.presets={}
        self.level=QSlider(Qt.Horizontal);self.level.setLayoutDirection(Qt.LeftToRight);self.level.setRange(0,MAX_LEVEL);self.level.setTickInterval(25);self.level.setTickPosition(QSlider.TicksBelow);self.level.valueChanged.connect(self.level_changed)
        ends=QWidget();ends.setStyleSheet('background:transparent;');ends.setLayoutDirection(Qt.LeftToRight);row=QHBoxLayout(ends);row.setContentsMargins(0,0,0,0);row.addWidget(label('0 • جودة أعلى / جهاز قوي'));row.addStretch();row.addWidget(label(f'{MAX_LEVEL} • أقصى تخفيف تجريبي'));c.addWidget(ends);c.addWidget(self.level)
        self.level_title=label('','cardtitle');self.level_description=label('','subtitle');c.addWidget(self.level_title);c.addWidget(self.level_description)
        self.level_effects=label('','subtitle');c.addWidget(self.level_effects)
        customize=QPushButton('تخصيص المستوى يدويًا');customize.setCheckable(True);c.addWidget(customize)
        for widget in (ends,self.level,self.level_effects):widget.hide();customize.toggled.connect(widget.setVisible)
        f,c=card('3 · راجع وطبّق','أغلق اللعبة ثم اضغط معاينة وتطبيق أسفل الشاشة. نحفظ الأصل تلقائيًا؛ تقدر تتراجع من النسخ والاسترجاع. جرّب الوضوح في التدريب.');v.addWidget(f)
        c.addWidget(label(f'النظام: {platform.system()}  •  المعالج: {platform.machine()}','subtitle'));v.addStretch()
    def slider(self,layout,key,title,lo,hi,unit=''):
        row=QHBoxLayout();row.addWidget(label(title),1);out=label('');row.addWidget(out);layout.addLayout(row)
        s=QSlider(Qt.Horizontal);s.setRange(lo,hi);s.valueChanged.connect(lambda value:out.setText(str(value)+unit));s.valueChanged.connect(self.changed);layout.addWidget(s);self.controls[key]=s
    def check(self,layout,key,title):
        b=QCheckBox(title);b.stateChanged.connect(self.changed);layout.addWidget(b);self.controls[key]=b
    def graphics(self):
        v=self.page()
        f,c=card('تخفيف الرسوم','تحكم مباشر في كل الرسوم. الدقة وFSR/DLSS تبقى كما هي.');v.addWidget(f)
        self.graphics_level_title=label('','cardtitle');c.addWidget(self.graphics_level_title);self.graphics_level=QSlider(Qt.Horizontal);self.graphics_level.setLayoutDirection(Qt.LeftToRight);self.graphics_level.setRange(0,MAX_LEVEL);self.graphics_level.valueChanged.connect(self.level.setValue);self.level.valueChanged.connect(self.graphics_level.setValue);c.addWidget(self.graphics_level)
        self.graphics_level_description=label('','subtitle');c.addWidget(self.graphics_level_description);c.addWidget(label('0 للجودة الأعلى • 80 تخفيف عنيف • 200 أقصى تخفيف تجريبي','sectionLabel'))
        f,c=card('عرض الرؤية • View width','نسبة الأبعاد مستقلة عن التخفيف. الأساسي 1.78 (16:9)، وارفعها حتى 3.50 لعرض أعرض. لا تتغير دقة الشاشة أو دقة العرض الداخلية.');v.addWidget(f)
        row=QHBoxLayout();row.addWidget(label('Aspect ratio'),1);self.aspect_value=label('1.78','cardtitle');self.aspect_value.setLayoutDirection(Qt.LeftToRight);row.addWidget(self.aspect_value);c.addLayout(row)
        self.aspect=QSlider(Qt.Horizontal);self.aspect.setLayoutDirection(Qt.LeftToRight);self.aspect.setRange(178,350);self.aspect.setSingleStep(1);self.aspect.setPageStep(10);self.aspect.setValue(178);self.aspect.valueChanged.connect(self.aspect_changed);c.addWidget(self.aspect)
        ends=QWidget();ends.setStyleSheet('background:transparent;');ends.setLayoutDirection(Qt.LeftToRight);row=QHBoxLayout(ends);row.setContentsMargins(0,0,0,0);row.addWidget(label('1.78 • Default 16:9'));row.addStretch();row.addWidget(label('3.50 • Ultra wide'));c.addWidget(ends)
        button=QPushButton('الرجوع للأساسي 1.78');button.clicked.connect(lambda:self.aspect.setValue(178));c.addWidget(button)
        c.addWidget(label('حرّك السحاب ثم اضغط معاينة وتطبيق. يتطلب إعادة تشغيل اللعبة؛ قد تختلف النتيجة حسب دعم إصدار اللعبة.','subtitle'))
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
        if hasattr(self,'graphics_level_title'):self.graphics_level_title.setText(self.level_title.text());self.graphics_level_description.setText(desc)
        self.level_effects.setText(f'تبسيط الخامات {s.textures}/4 • '+('ظلال مفعلة' if s.shadows else 'بدون ظلال')+' • '+('ضباب مفعل' if s.fog else 'بدون ضباب')+' • تفاصيل الجزيئات '+str(s.particles)+'/2')
        self.changed()
    def repair_settings(self):
        if self.mod_task_busy():return
        try:
            self.guard_status.setText(self.studio().repair(self.library.cache));self.guard_signature=None;self.guard_retries=0;self.refresh_mod_library()
        except Exception as e:self.error(e)
    def guard_tick(self):
        if self.mods_page.busy:return
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
        self.mods_page=ModPage(self);self.stack.addWidget(self.mods_page);self.mod_checks=self.mods_page.checks;self.mod_labels=self.mods_page.labels;self.mod_status=self.mods_page.status
    def refresh_mod_library(self):self.mods_page.refresh()
    def mod_selected(self,key,checked):
        other={'names':'health','health':'names'}.get(key)
        if checked and other:self.mod_checks[other].setChecked(False)
        if hasattr(self,'inspector'):self.inspector.invalidate()
        self.mods_page.refresh()
    def import_mod_sources(self,paths):self.mods_page.import_paths(paths)
    def discover_mods(self):self.mods_page.discover()
    def import_mod_files(self):self.mods_page.browse_files()
    def install_mods(self):self.mods_page.install()
    def backups(self):
        v=self.page();f,c=card('ارجع للأصل بثقة','تُحفظ الملفات قبل أول تعديل. الاسترجاع يحتفظ بنسخة من وضعك الحالي أيضًا.');v.addWidget(f)
        b=QPushButton('فتح مجلد النسخ الاحتياطية ↗');b.clicked.connect(self.open_backups);c.addWidget(b)
        self.preserve=QCheckBox('حفظ التغييرات الخارجية الحالية ثم استرجاع الأصل (بعد تحديث اللعبة مثلًا)');c.addWidget(self.preserve)
        b=QPushButton('استرجاع الإعدادات الأصلية');b.setObjectName('danger');b.clicked.connect(self.restore);c.addWidget(b)
        f,c=card('احتفظ بنسخة من إعداداتك','تصدير واستيراد خيارات الرسوم بصيغة JSON، دون ملفات اللعبة أو بيانات الحساب.');v.addWidget(f)
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
        if self.mods_page.applying:return
        p=QFileDialog.getExistingDirectory(self,'اختر مجلد Deadlock')
        if p:self.path.setText(p);self.refresh_accounts()
    def browse_mods(self):self.mods_page.browse_folder()
    def focus_game(self):
        self.navigate(0)
        self.path.setFocus()
        QTimer.singleShot(0,lambda:self.stack.widget(0).ensureWidgetVisible(self.path))
    def mod_task_busy(self):
        if self.mods_page.busy:self.status.setText('انتظر اكتمال عملية المودات الحالية، ثم أعد المحاولة.');return True
        return False
    def detect_game(self):
        if self.mods_page.applying:return
        games=detect_games()
        if games:self.path.setText(str(games[0]));self.refresh_accounts()
        else:self.connection_note.setText('ما لقينا اللعبة تلقائيًا. من Steam: إدارة اللعبة ← استعراض الملفات المحلية، ثم اختر المجلد هنا.')
    def remember_account(self,*_):
        self.preferred_account=self.accounts.currentData();self.save_workspace()
    def save_workspace(self):
        from .core import atomic
        try:atomic(self.preferences_file,json.dumps({'game':self.path.text(),'account':self.preferred_account},ensure_ascii=False).encode('utf-8'))
        except OSError:self.status.setText('اللعبة مرتبطة، لكن تعذر حفظ اختيار المجلد للجلسة القادمة.')
    def refresh_accounts(self):
        self.accounts.blockSignals(True);self.accounts.clear()
        try:
            from .core import game_root
            root=game_root(self.path.text())
            self.path.setText(str(root))
            for f in video_files(root):
                account=next((p.name for p in f.parents if p.parent.name=='userdata'),None)
                self.accounts.addItem('Steam '+account if account else 'إعدادات محلية للعبة',str(f));self.accounts.setItemData(self.accounts.count()-1,str(f),Qt.ToolTipRole)
            index=self.accounts.findData(self.preferred_account)
            if index>=0:self.accounts.setCurrentIndex(index)
            self.preferred_account=self.accounts.currentData()
            self.connection_note.setText('✓ اللعبة مرتبطة · اختر الأداء بالأسفل، ثم راجع وطبّق.');self.save_workspace()
            if not self.accounts.count():self.connection_note.setText('✓ اللعبة مرتبطة · شغّل اللعبة مرة واحدة إذا احتجت إعدادات الفيديو والكروس هير.')
            self.status.setText('اللعبة مرتبطة • جاهز للتخصيص.');self.game_chip.setText('اللعبة مرتبطة')
            saved=Studio(root,self.accounts.currentData()).state().get('settings')
            if saved:self.load_settings(Settings.from_dict(saved))
        except Exception as e:self.status.setText(str(e));self.connection_note.setText('اختر مجلد Deadlock الصحيح أو استخدم البحث التلقائي.');self.game_chip.setText('ربط اللعبة')
        finally:
            self.accounts.blockSignals(False);self.accounts.setVisible(self.accounts.count()>1);self.account_label.setVisible(self.accounts.count()>1)
        self.refresh_mod_library()
        if hasattr(self,'inspector'):self.inspector.invalidate()
    def studio(self):return Studio(self.path.text(),self.accounts.currentData())
    def error(self,e):QMessageBox.warning(self,'تعذر إكمال العملية',str(e));self.status.setText(str(e))
    def preview(self):
        if self.mod_task_busy():return
        if not self.path.text().strip():self.focus_game();self.connection_note.setText('باقي خطوة واحدة: اختر مجلد اللعبة أولًا.');return
        try:
            studio=self.studio();s=self.settings();plan=studio.plan(s,self.library.cache)
            require_mods(self.library,studio.root,s.mods)
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
            name,description=level_info(s.level)
            v.addWidget(label(f'الأداء: {name} · المستوى {s.level}/{MAX_LEVEL}\nحد الإطارات: '+(str(s.fps)+' FPS' if s.fps else 'بدون حد')+'\nدقة اللعبة محفوظة. تستطيع التراجع من النسخ والاسترجاع.','subtitle'))
            out.setPlainText('\n\n'.join(parts));out.hide();more=QPushButton('إظهار تفاصيل الملفات');more.setCheckable(True);more.toggled.connect(out.setVisible);v.addWidget(more);v.addWidget(out,1)
            buttons=QDialogButtonBox();ok=buttons.addButton('تطبيق وحفظ نسخة احتياطية',QDialogButtonBox.AcceptRole);buttons.addButton('إلغاء',QDialogButtonBox.RejectRole);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);v.addWidget(buttons)
            if dialog.exec()==QDialog.Accepted:
                # Regenerate after preview to detect file changes before committing.
                fresh=studio.plan(s,self.library.cache)
                if fresh!=plan:raise ValueError('تغيرت الملفات أثناء المعاينة. أعد المعاينة.')
                self.status.setText(studio.apply(plan,s));self.refresh_mod_library();QMessageBox.information(self,'تم التطبيق',self.status.text())
        except Exception as e:self.error(e)
    def restore(self):
        if self.mod_task_busy():return
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
    window=Window()
    if '--crosshair' in sys.argv:window.navigate(5)
    if '--updates' in sys.argv:window.navigate(6)
    if '--inspector' in sys.argv:window.navigate(7)
    if '--mods' in sys.argv:window.navigate(2)
    if '--install' in sys.argv:
        window.navigate(6);QTimer.singleShot(100,window.updates.install_current)
    window.show();window.update_startup_timer.start(3000);sys.exit(app.exec())
