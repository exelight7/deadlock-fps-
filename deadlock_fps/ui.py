from .i18n import tr
from pathlib import Path
import copy, difflib, json, platform, sys
from PySide6.QtCore import Qt, QUrl, QStandardPaths, QTimer, QSize
from PySide6.QtGui import QDesktopServices, QFont, QIcon, QFontDatabase
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QLabel,QPushButton,QLineEdit,QFileDialog,QComboBox,QSlider,QCheckBox,QSpinBox,QScrollArea,QStackedWidget,QFrame,QMessageBox,QGridLayout,QDialog,QPlainTextEdit,QDialogButtonBox)
from .core import Studio, detect_games, video_files, ASSETS
from .settings import Settings, PRESETS, MODS, TEXTURE_LABELS, level_info, MAX_LEVEL
from .mods import ModLibrary
from .server_ui import ServerPage
from .crosshair_ui import CrosshairPage
from .update_ui import UpdatePage
from .inspector_ui import InspectorPage
from .mod_inspector import require_mods
from .mod_ui import ModPage
from .design import (STYLE, ArtworkHero, BrandMark, nav_icon, brand_logo, icon, label, card, Rail, Rule, Kicker, HintLine, ActionBar, Combo, Plate, Panel,
                     load_fonts, dark_palette)
from . import theme as T
from . import i18n
from .detection import scan,INSTALL_URL
from .update_ui import StateTitle
from .motion import PageTransition, NavButton, NavIndicator, StatusChip, LevelMeter, Intro, enliven
from . import __version__


class Window(QMainWindow):
    def __init__(self):
        super().__init__();load_fonts();self.setWindowTitle('Deadlock Toolbox');self.resize(1200,820);self.setMinimumSize(940,680)
        window_icon=QIcon(str(ASSETS/'app.png'))
        for size in (16,24,32,48,64,128,256):window_icon.addFile(str(ASSETS/f'brand/icon-{size}.png'),QSize(size,size))
        self.setWindowIcon(window_icon)
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
        root=QWidget();self.setCentralWidget(root);layout=QHBoxLayout(root);layout.setContentsMargins(0,0,0,0);layout.setSpacing(0)

        # Directory rail: emblem, destinations, footer.
        sidebar=Rail();side=QVBoxLayout(sidebar);side.setContentsMargins(16,20,16,16);side.setSpacing(6)
        brandrow=QHBoxLayout();brandrow.setSpacing(12);brandrow.addWidget(BrandMark())
        brandcopy=QVBoxLayout();brandcopy.setSpacing(0)
        brand=label('Toolbox','brand',False);brandcopy.addWidget(brand)
        eyebrow=Kicker('COMMUNITY TOOL');eyebrow.setAlignment(Qt.AlignLeading|Qt.AlignVCenter);brandcopy.addWidget(eyebrow)
        brandrow.addLayout(brandcopy,1);side.addLayout(brandrow)
        side.addSpacing(10);side.addWidget(Rule())
        nav_body=QWidget();nav_body.setObjectName('navContent');nav_layout=QVBoxLayout(nav_body);nav_layout.setContentsMargins(0,2,0,0);nav_layout.setSpacing(4)
        self.nav_scroll=QScrollArea();self.nav_scroll.setWidgetResizable(True);self.nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);self.nav_scroll.setWidget(nav_body);side.addWidget(self.nav_scroll,1)
        self.nav_indicator=NavIndicator(nav_body);self.intro_played=False
        self.stack=QStackedWidget();self.nav=[];self.guard_signature=None;self.guard_retries=0;self.guard_attempts={}
        for index,text in enumerate([tr('الرئيسية'),tr('الرسوم والأداء'),tr('المودات'),tr('النسخ والاسترجاع'),tr('السيرفرات'),tr('الكروس هير'),tr('التحديث والتثبيت'),tr('فحص المودات'),tr('الإعدادات')]):
            b=NavButton(text,nav_icon(index));b.clicked.connect(lambda _,i=index:self.navigate(i));b.setParent(nav_body);self.nav.append(b)
        # Stack indexes stay as they always were; only the order and grouping on the rail change.
        nav_layout.addWidget(self.nav[0])
        for title,members in [(tr('اللعب'),(1,5,2,4)),(tr('النظام'),(3,8))]:
            heading=label(title,'sectionLabel',False);heading.setContentsMargins(4,8,4,0);nav_layout.addWidget(heading)
            for index in members:nav_layout.addWidget(self.nav[index])
        self.nav[7].hide();nav_layout.addStretch();nav_layout.addWidget(self.nav[6])
        side.addWidget(Rule());side.addWidget(label(tr('أدواتك. إعداداتك. اختيارك.'),'subtitle'))
        meta=QHBoxLayout();meta.setSpacing(8);version=label(__version__,'badge',False);version.setLayoutDirection(Qt.LeftToRight);meta.addWidget(version);meta.addWidget(label('Windows + Linux','sectionLabel',False));meta.addStretch();side.addLayout(meta)
        side.addWidget(label(tr('مفتوح المصدر • مشروع مستقل، غير تابع لـ Valve.'),'sectionLabel'))
        git=QPushButton('GitHub');git.setObjectName('quiet');git.setIcon(icon('external',T.TEXT_SOFT));git.setIconSize(QSize(16,16));git.setToolTip('github.com/exelight7/deadlock-fps-');git.clicked.connect(lambda:QDesktopServices.openUrl(QUrl('https://github.com/exelight7/deadlock-fps-')));side.addSpacing(4);side.addWidget(git)
        layout.addWidget(sidebar)

        # Page column: header, optional banner, guidance, the page itself, then the pinned action bar.
        content=QWidget();v=QVBoxLayout(content);v.setContentsMargins(T.GUTTER,16,T.GUTTER,16);v.setSpacing(12)
        top=QHBoxLayout();top.setSpacing(10);titles=QVBoxLayout();titles.setSpacing(0)
        self.heading=label(tr('مساحة العمل / لوحة التحكم'),'crumb',False);titles.addWidget(self.heading)
        self.page_title=label('','pageTitle',False);titles.addWidget(self.page_title);top.addLayout(titles,1)
        self.mods_switch=QWidget();switch=QHBoxLayout(self.mods_switch);switch.setContentsMargins(0,0,0,0);switch.setSpacing(0);self.switch_buttons={}
        for title,target in [(tr('المكتبة والتركيب'),2),(tr('الفحص'),7)]:
            b=QPushButton(title);b.setCheckable(True);b.setObjectName('quiet');b.clicked.connect(lambda _,i=target:self.navigate(i));switch.addWidget(b);self.switch_buttons[target]=b
        top.addWidget(self.mods_switch,0,Qt.AlignVCenter);self.mods_switch.hide()
        self.game_chip=StatusChip(tr('ربط اللعبة'));self.game_chip.setToolTip('Deadlock');self.game_chip.clicked.connect(self.focus_game);top.addWidget(self.game_chip,0,Qt.AlignVCenter)
        self.private_badge=label(tr('مفتوح المصدر'),'badge',False);top.addWidget(self.private_badge,0,Qt.AlignVCenter);v.addLayout(top)
        self.hero=ArtworkHero();v.addWidget(self.hero);self.page_hint=HintLine();v.addWidget(self.page_hint);v.addWidget(self.stack,1)
        self.status=label(tr('جاهز • اختر إعدادًا، ثم راجع التغييرات.'),'subtitle');v.addWidget(self.status)
        actionbar=ActionBar();self.actionbar=actionbar;footer=QHBoxLayout();footer.setSpacing(16);actionbar.body.addLayout(footer);self.summary=label(tr('دقة اللعبة محفوظة • خامات بسيطة'),'subtitle');footer.addWidget(self.summary,1)
        apply=QPushButton(tr('معاينة وتطبيق الإعدادات ←'));apply.setObjectName('primary');apply.clicked.connect(self.primary_action);self.apply_button=apply;footer.addWidget(apply);v.addWidget(actionbar)
        layout.addWidget(content,1)
        self.transition=PageTransition(content,lambda:top.geometry().bottom()+1,lambda:self.stack.geometry().bottom()+1)
        self.graphics();self.stack.insertWidget(0,self.dashboard_scroll());self.mods();self.backups();self.servers=ServerPage(self);server_scroll=QScrollArea();server_scroll.setWidgetResizable(True);server_scroll.setWidget(self.servers);self.stack.addWidget(server_scroll);self.servers.layout().removeWidget(self.servers.actions_panel);v.addWidget(self.servers.actions_panel);self.crosshair=CrosshairPage(lambda:(self.path.text(),self.accounts.currentData()),self);self.stack.addWidget(self.crosshair);self.crosshair.layout().removeWidget(self.crosshair.actions_panel);v.addWidget(self.crosshair.actions_panel)
        self.updates=UpdatePage(self);self.stack.addWidget(self.updates);self.updates.updateAvailable.connect(lambda available:self.nav[6].setText(tr('التحديث والتثبيت •') if available else tr('التحديث والتثبيت')))
        if self.updates.release and self.updates.release.version>self.updates.current:self.nav[6].setText(tr('التحديث والتثبيت •'))
        self.inspector=InspectorPage(self);self.stack.addWidget(self.inspector)
        self.settings_page()
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
        self.detect_timer=QTimer(self);self.detect_timer.setInterval(20000);self.detect_timer.timeout.connect(self.auto_detect);self.detect_timer.start()
        self.update_game_status();self.refresh_home()
        enliven(self)
    def showEvent(self,event):
        super().showEvent(event)
        if not self.intro_played:
            self.intro_played=True;Intro(self.centralWidget(),brand_logo(264),'Deadlock Toolbox','VERSION '+__version__)
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'hero') and hasattr(self,'stack'):self.hero.setVisible(self.stack.currentIndex() in (2,3,4) and self.height()>=800)
    def closeEvent(self,event):
        if self.updates.installing:
            self.updates.detail.setText(tr('انتظر اكتمال التثبيت قبل إغلاق البرنامج.'));event.ignore();return
        if self.mods_page.applying:
            self.mods_page.status.setText(tr('أكمل حفظ الملفات أولًا؛ ينتهي التركيب بعد لحظات.'));event.ignore();return
        if self.servers.busy:
            self.status.setText(tr('انتظر اكتمال عملية السيرفرات قبل إغلاق البرنامج.'));self.servers.status.setText(self.status.text());event.ignore()
        else:
            if hasattr(self,'guard_timer'):self.guard_timer.stop()
            if hasattr(self,'detect_timer'):self.detect_timer.stop()
            self.update_startup_timer.stop();self.updates.client.cancel()
            self.inspector.cancel();self.mods_page.cancel()
            super().closeEvent(event)
    def page(self):
        # Form pages keep one readable column, centred once the window is wider than it.
        page=QWidget();outer=QHBoxLayout(page);outer.setContentsMargins(0,0,12,0);outer.setSpacing(0)
        column=QWidget();column.setMaximumWidth(1080);v=QVBoxLayout(column);v.setContentsMargins(0,0,0,0);v.setSpacing(16);outer.addStretch(1);outer.addWidget(column,1000);outer.addStretch(1)
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
        moving=i!=self.stack.currentIndex()
        if moving:self.transition.capture(1 if i>self.stack.currentIndex() else -1)
        self.stack.setCurrentIndex(i)
        self.page_hint.setText([
            tr('حالة اللعبة وأدواتك في نظرة واحدة. اختر بطاقة للانتقال إليها.'),
            tr('اختر مستوى التخفيف. نسبة الأبعاد وحد الإطارات اختيارات إضافية.'),
            tr('أضف ZIP أو VPK ← اختر المودات ← راجع التركيب. الفحص يتم قبل الحفظ.'),
            tr('تبي ترجع؟ استرجع الأصل. تبي تنقل خياراتك؟ صدّر إعداداتك.'),
            tr('انتظر القياس ← حدد المناطق ← اختر السماح بها فقط أو الحظر. فك كل الحظر متاح دائمًا.'),
            tr('اختر تصميمًا جاهزًا، جرّب المعاينة، ثم راجع تطبيقه على حسابك.'),
            tr('تحقق من التحديثات ← نزّل ← ثبّت ← افتح النسخة الجديدة.'),
            tr('الفحص يوضح الملفات الناقصة والتالفة. عالج الأخطاء ثم ارجع للمودات للتركيب.'),
            tr('اللغة، الحماية التلقائية والتحديث. تغيير اللغة يُطبّق بعد إعادة التشغيل.')
        ][i])
        self.hero.setVisible(i in (2,3,4) and self.height()>=800)
        self.hero.set_page(i,animate=not moving)
        self.page_title.setText('Crosshair Designer' if i==5 and i18n.LANGUAGE=='source' else self.nav[i].text().removesuffix(' •'))
        self.status.setVisible(i in (0,1,3,8));self.mods_switch.setVisible(i in (2,7))
        for target,b in self.switch_buttons.items():b.setChecked(target==i)
        self.actionbar.setVisible(i==1);self.servers.actions_panel.setVisible(i==4);self.crosshair.actions_panel.setVisible(i==5)
        english=i==5 and i18n.LANGUAGE=='source';self.heading.setText(('Workspace / ' if english else tr('مساحة العمل / '))+self.nav[i].text().removesuffix(' •'));self.private_badge.setText('Open source' if english else tr('مفتوح المصدر'))
        linked=self.game_chip.text() in (tr('اللعبة مرتبطة'),'Game connected');self.game_chip.setText(('Game connected' if linked else 'Connect game') if english else (tr('اللعبة مرتبطة') if linked else tr('ربط اللعبة')))
        if hasattr(self,'apply_button'):self.apply_button.setText(tr('حظر السيرفرات المحددة') if i==4 else (tr('تركيب / تحديث المودات المختارة') if i==2 else tr('معاينة وتطبيق الإعدادات ←')))
        rail=2 if i==7 else i
        for j,b in enumerate(self.nav):b.setChecked(j==rail)
        self.nav_indicator.move_to(self.nav[rail])
        self.nav_scroll.ensureWidgetVisible(self.nav[rail])
        if i==0:self.update_game_status();self.refresh_home()
        if i==4:self.summary.setText(tr('اختيار مناطق اتصال Steam • يحتاج صلاحية المدير عند التطبيق'))
        else:self.changed()
    def dashboard_scroll(self):
        self.dashboard();scroll=self.stack.widget(self.stack.count()-1);self.stack.removeWidget(scroll);return scroll
    def dashboard(self):
        v=self.page()
        f,c=card(tr('اللعبة على هذا الجهاز'),tr('تبحث الأداة في مكتبات Steam وكل الأقراص وفي اللعبة إن كانت تعمل، وتحفظ اختيارك.'),icon_name='link');v.addWidget(f)
        self.game_state=StateTitle('');c.addWidget(self.game_state);self.game_detail=label('','subtitle');c.addWidget(self.game_detail)
        self.connection_note=label(tr('اختر مجلد اللعبة للبدء. تقدر تستخدم التحديث والمكتبة بدون ربط.'),'stepPill');c.addWidget(self.connection_note)
        row=QHBoxLayout();row.setSpacing(8);self.path=QLineEdit();self.path.setLayoutDirection(Qt.LeftToRight);self.path.setPlaceholderText('…/steamapps/common/Deadlock');row.addWidget(self.path,1)
        b=QPushButton(tr('اختيار المجلد'));b.setIcon(icon('folder',T.TEXT));b.clicked.connect(self.browse_game);row.addWidget(b)
        b=QPushButton(tr('بحث تلقائي'));b.setIcon(icon('search',T.TEXT));b.clicked.connect(self.detect_game);row.addWidget(b);c.addLayout(row)
        row=QHBoxLayout();self.install_game=QPushButton(tr('تثبيت Deadlock من Steam'));self.install_game.setObjectName('positive');self.install_game.setIcon(icon('external',T.VERDIGRIS));self.install_game.clicked.connect(lambda:QDesktopServices.openUrl(QUrl(INSTALL_URL)));row.addWidget(self.install_game);row.addStretch();c.addLayout(row);self.install_game.hide()
        self.path.editingFinished.connect(self.refresh_accounts)
        self.accounts=Combo();self.accounts.setLayoutDirection(Qt.LeftToRight);self.accounts.currentIndexChanged.connect(self.remember_account);self.account_label=label(tr('حساب Steam · اختر الحساب الذي تلعب عليه'),'sectionLabel');c.addWidget(self.account_label);c.addWidget(self.accounts);self.account_label.hide();self.accounts.hide()
        # One tile per tool: what it is set to now, and the way in.
        grid=QGridLayout();grid.setSpacing(16);self.tiles={}
        for position,(index,title,glyph) in enumerate([(1,tr('الرسوم والأداء'),'gauge'),(2,tr('المودات'),'mods'),(5,tr('الكروس هير'),'crosshair'),(4,tr('السيرفرات'),'servers'),(3,tr('النسخ والاسترجاع'),'backups'),(6,tr('التحديث والتثبيت'),'updates')]):
            tile=Panel(margins=(16,14,16,14),spacing=6);row=QHBoxLayout();row.setSpacing(12);row.addWidget(Plate(icon_name=glyph,size=40),0,Qt.AlignTop)
            copy=QVBoxLayout();copy.setSpacing(2);copy.addWidget(label(title,'cardtitle',False));value=label('','subtitle');copy.addWidget(value);row.addLayout(copy,1)
            go=QPushButton(tr('فتح'));go.setObjectName('quiet');go.setCursor(Qt.PointingHandCursor);go.clicked.connect(lambda _,i=index:self.navigate(i));row.addWidget(go,0,Qt.AlignVCenter);tile.body.addLayout(row)
            self.tiles[index]=value;grid.addWidget(tile,position//2,position%2)
        v.addLayout(grid);v.addStretch()
    def update_game_status(self):
        """Say plainly whether the game is here: linked, downloading, missing, or no Steam at all."""
        if not hasattr(self,'game_state'):return
        linked=self.game_chip.text() in StatusChip.CONNECTED
        try:status=scan([Path(self.path.text())] if linked else detect_games())
        except Exception:status=scan([])
        if status.found and status.state=='installed':
            self.game_state.setText(tr('اللعبة مرتبطة ✓') if linked else tr('وجدت Deadlock على هذا الجهاز'))
            parts=[(tr('الإصدار ')+status.build) if status.build else '',f'{status.size/1073741824:.1f} GB' if status.size else '']
            self.game_detail.setText(' • '.join(part for part in parts if part) or tr('مجلد اللعبة جاهز.'))
        elif status.state=='updating':
            self.game_state.setText(tr('Steam ما زال ينزّل Deadlock أو يحدّثها'));self.game_detail.setText(tr('انتظر اكتمال التنزيل في Steam ثم اضغط بحث تلقائي. الأداة تعيد البحث كل بضع ثوانٍ.'))
        elif status.state=='no_steam':
            self.game_state.setText(tr('تعذر العثور على Steam في هذا الجهاز'));self.game_detail.setText(tr('ثبّت Steam و Deadlock، أو اختر مجلد اللعبة يدويًا إن كانت في مكان غير معتاد.'))
        else:
            self.game_state.setText(tr('تعذر العثور على Deadlock في هذا الجهاز'));self.game_detail.setText(tr('بحثت في {0} من مكتبات Steam وفي كل الأقراص. ثبّتها من Steam أو اختر مجلدها يدويًا.').format(status.libraries))
        if status.running:self.game_detail.setText(self.game_detail.text()+tr(' • اللعبة تعمل الآن؛ أغلقها قبل تطبيق أي تغيير.'))
        self.install_game.setVisible(not linked and status.state in ('missing','updating'))
    def auto_detect(self):
        """While nothing is linked, keep looking quietly and link the game the moment it appears."""
        if not self.isVisible() or self.mods_page.busy or QApplication.activeModalWidget() or self.game_chip.text() in StatusChip.CONNECTED or self.path.hasFocus():return
        games=detect_games()
        if games:self.path.setText(str(games[0]));self.refresh_accounts()
        elif self.stack.currentIndex()==0:self.update_game_status()
    def refresh_home(self):
        if not hasattr(self,'tiles') or not hasattr(self,'updates'):return
        name,_=level_info(self.level.value());self.tiles[1].setText(f'{self.level.value()}/{MAX_LEVEL} • {name}')
        chosen=sum(b.isChecked() for b in self.mod_checks.values());self.tiles[2].setText(tr('{0} مودات مختارة').format(chosen) if chosen else tr('لا مودات مختارة'))
        self.tiles[5].setText(self.crosshair.design_name.text())
        try:blocked=len(self.servers.store.state().get('blocked',[]))
        except Exception:blocked=0
        self.tiles[4].setText(tr('{0} مناطق محظورة').format(blocked) if blocked else tr('لا مناطق محظورة'))
        self.tiles[3].setText(tr('الأصل محفوظ قبل أول تعديل'))
        self.tiles[6].setText(self.updates.state.text())
    def slider(self,layout,key,title,lo,hi,unit=''):
        row=QHBoxLayout();row.addWidget(label(title),1);out=label('','value',False);out.setLayoutDirection(Qt.LeftToRight);row.addWidget(out);layout.addLayout(row)
        s=QSlider(Qt.Horizontal);s.setRange(lo,hi);s.valueChanged.connect(lambda value:out.setText(str(value)+unit));s.valueChanged.connect(self.changed);layout.addWidget(s);self.controls[key]=s
    def check(self,layout,key,title):
        b=QCheckBox(title);b.stateChanged.connect(self.changed);layout.addWidget(b);self.controls[key]=b
    def graphics(self):
        v=self.page()
        f,c=card(tr('مستوى التخفيف'),tr('ابدأ بمتوازن. ارفع التخفيف إذا احتجت أداء أعلى؛ الدقة وFSR/DLSS تبقى كما هي.'),icon_name='gauge');v.addWidget(f)
        row=QHBoxLayout();row.setSpacing(8);self.preset_buttons={}
        for title,key in [(tr('متوازن'),'balanced'),(tr('أداء أعلى'),'performance'),(tr('تخفيف شديد'),'ultra')]:
            b=QPushButton(title);b.clicked.connect(lambda _,k=key:self.load_preset(k));row.addWidget(b,1);self.preset_buttons[key]=b
        c.addLayout(row);self.presets={}
        # `level` is the value every handler reads; the visible slider below is wired to it both ways.
        self.level=QSlider(Qt.Horizontal,f);self.level.setRange(0,MAX_LEVEL);self.level.hide();self.level.valueChanged.connect(self.level_changed)
        self.level_title=label('','value');c.addWidget(self.level_title);self.graphics_level_title=self.level_title
        self.level_meter=LevelMeter(MAX_LEVEL,[preset.level for preset in PRESETS.values()]);self.level.valueChanged.connect(self.level_meter.set_value);self.level.valueChanged.connect(self.mark_preset);c.addWidget(self.level_meter)
        self.graphics_level=QSlider(Qt.Horizontal);self.graphics_level.setLayoutDirection(Qt.LeftToRight);self.graphics_level.setRange(0,MAX_LEVEL);self.graphics_level.valueChanged.connect(self.level.setValue);self.level.valueChanged.connect(self.graphics_level.setValue);c.addWidget(self.graphics_level)
        ends=QWidget();ends.setLayoutDirection(Qt.LeftToRight);row=QHBoxLayout(ends);row.setContentsMargins(0,0,0,0);row.addWidget(label(tr('0 • جودة أعلى / جهاز قوي'),'sectionLabel',False));row.addStretch();row.addWidget(label(tr('{0} • أقصى تخفيف تجريبي').format(MAX_LEVEL),'sectionLabel',False));c.addWidget(ends)
        self.level_description=label('','subtitle');c.addWidget(self.level_description);self.graphics_level_description=self.level_description
        self.level_effects=label('','sectionLabel');c.addWidget(self.level_effects)

        f,c=card(tr('عرض الرؤية • View width'),tr('نسبة الأبعاد مستقلة عن التخفيف. الأساسي 1.78 (16:9)، وارفعها حتى 3.50 لعرض أعرض. لا تتغير دقة الشاشة أو دقة العرض الداخلية.'),icon_name='aspect');v.addWidget(f)
        row=QHBoxLayout();row.addWidget(label('Aspect ratio'),1);self.aspect_value=label('1.78','value',False);self.aspect_value.setLayoutDirection(Qt.LeftToRight);row.addWidget(self.aspect_value);c.addLayout(row)
        self.aspect=QSlider(Qt.Horizontal);self.aspect.setLayoutDirection(Qt.LeftToRight);self.aspect.setRange(178,350);self.aspect.setSingleStep(1);self.aspect.setPageStep(10);self.aspect.setValue(178);self.aspect.valueChanged.connect(self.aspect_changed);c.addWidget(self.aspect)
        ends=QWidget();ends.setLayoutDirection(Qt.LeftToRight);row=QHBoxLayout(ends);row.setContentsMargins(0,0,0,0);row.addWidget(label('1.78 • Default 16:9','sectionLabel',False));row.addStretch();row.addWidget(label('3.50 • Ultra wide','sectionLabel',False));c.addWidget(ends)
        row=QHBoxLayout();button=QPushButton(tr('الرجوع للأساسي 1.78'));button.setObjectName('quiet');button.setIcon(icon('undo',T.TEXT_SOFT));button.clicked.connect(lambda:self.aspect.setValue(178));row.addWidget(button);row.addStretch();c.addLayout(row)
        c.addWidget(label(tr('حرّك السحاب ثم اضغط معاينة وتطبيق. يتطلب إعادة تشغيل اللعبة؛ قد تختلف النتيجة حسب دعم إصدار اللعبة.'),'sectionLabel'))

        f,c=card(tr('حد الإطارات'),tr('مستقل عن مستوى التخفيف ونسبة الأبعاد.'),icon_name='clock');v.addWidget(f)
        self.slider(c,'fps',tr('حد الإطارات • 0 بدون حد (مستقل عن مستوى التخفيف)'),0,500,' FPS')
        v.addWidget(label(tr('أغلق اللعبة ثم اضغط معاينة وتطبيق. نحفظ الأصل تلقائيًا؛ تقدر تتراجع من النسخ والاسترجاع.  •  {0} {1}').format(platform.system(),platform.machine()),'sectionLabel'));v.addStretch()
    def mark_preset(self,value):
        for key,button in self.preset_buttons.items():
            active=PRESETS[key].level==value
            if bool(button.property('active'))!=active:button.setProperty('active',active);button.style().unpolish(button);button.style().polish(button)
    def aspect_changed(self,value):
        self.aspect_value.setText(f'{value/100:.2f}');self.changed()
    def level_changed(self,value):
        name,desc=level_info(value);s=Settings.at_level(value)
        self.level_title.setText(f'{value}/{MAX_LEVEL} • {name}');self.level_description.setText(desc)
        if hasattr(self,'graphics_level_title'):self.graphics_level_title.setText(self.level_title.text());self.graphics_level_description.setText(desc)
        self.level_effects.setText(tr('تبسيط الخامات {0}/4 • ').format(s.textures)+(tr('ظلال مفعلة') if s.shadows else tr('بدون ظلال'))+' • '+(tr('ضباب مفعل') if s.fog else tr('بدون ضباب'))+tr(' • تفاصيل الجزيئات ')+str(s.particles)+'/2')
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
                self.guard_signature=None;self.guard_retries=0;self.guard_status.setText(tr('قيم التعديلات محفوظة • اختلاف تنسيق الأرقام لا يُعتبر رجوعًا.'));return
            state=studio.state();from .core import digest
            signature=tuple((name,digest(Path(name).read_bytes()) if Path(name).exists() else None) for name in state['files'])
            if signature!=self.guard_signature:
                self.guard_signature=signature;self.guard_retries=0;self.guard_status.setText(tr('اكتشفت رجوعًا في: ')+', '.join(changed)+tr(' • أنتظر استقرار الملفات.'));return
            if self.guard_retries>=1:return
            if self.guard_attempts.get(signature,0)>=2:
                self.guard_status.setText(tr('تتكرر إعادة ضبط نفس القيم؛ أوقفت الإصلاح التلقائي. استخدم الإصلاح اليدوي بعد مراجعة اللعبة.'));return
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
        v=self.page();f,c=card(tr('ارجع للأصل بثقة'),tr('تُحفظ الملفات قبل أول تعديل. الاسترجاع يحتفظ بنسخة من وضعك الحالي أيضًا.'),icon_name='backups');v.addWidget(f)
        self.preserve=QCheckBox(tr('حفظ التغييرات الخارجية الحالية ثم استرجاع الأصل (بعد تحديث اللعبة مثلًا)'));c.addWidget(self.preserve)
        row=QHBoxLayout();row.setSpacing(8)
        b=QPushButton(tr('استرجاع الإعدادات الأصلية'));b.setObjectName('danger');b.setIcon(icon('undo',T.CRIMSON_TEXT));b.clicked.connect(self.restore);row.addWidget(b)
        b=QPushButton(tr('فتح مجلد النسخ الاحتياطية'));b.setIcon(icon('external',T.TEXT));b.clicked.connect(self.open_backups);row.addWidget(b);row.addStretch();c.addLayout(row)
        f,c=card(tr('تراجع عن بقية الأدوات'),tr('كل أداة تحتفظ بطريق رجوعها. هذه اختصارات لها، وكل واحد يعرض مراجعة قبل التنفيذ.'),icon_name='undo');v.addWidget(f)
        for title,detail,fn in [(tr('الكروس هير'),tr('استرجاع آخر كروس هير كان في اللعبة قبل التطبيق.'),self.undo_crosshair),(tr('المودات'),tr('إزالة مودات الأداة واسترجاع ملفات اللعبة الأصلية.'),self.undo_mods),(tr('السيرفرات'),tr('فك كل حظر أنشأته الأداة.'),self.undo_servers)]:
            row=QHBoxLayout();row.setSpacing(12);copy=QVBoxLayout();copy.setSpacing(0);copy.addWidget(label(title,'lead',False));copy.addWidget(label(detail,'sectionLabel'));row.addLayout(copy,1)
            b=QPushButton(tr('مراجعة التراجع'));b.setObjectName('quiet');b.clicked.connect(fn);row.addWidget(b,0,Qt.AlignVCenter);c.addLayout(row)
        f,c=card(tr('احتفظ بنسخة من إعداداتك'),tr('تصدير واستيراد خيارات الرسوم بصيغة JSON، دون ملفات اللعبة أو بيانات الحساب.'),icon_name='save');v.addWidget(f)
        row=QHBoxLayout();row.setSpacing(8)
        for title,fn,glyph in [(tr('تصدير الإعدادات'),self.export_settings,'share'),(tr('استيراد الإعدادات'),self.import_settings,'updates')]:
            b=QPushButton(title);b.setIcon(icon(glyph,T.TEXT));b.clicked.connect(fn);row.addWidget(b)
        row.addStretch();c.addLayout(row);v.addStretch()
    def undo_crosshair(self):self.crosshair.review(True);self.status.setText(self.crosshair.status.text())
    def undo_mods(self):
        for check in self.mod_checks.values():check.setChecked(False)
        self.navigate(2);self.install_mods()
    def undo_servers(self):self.servers.apply_action('clear');self.status.setText(self.servers.status.text())
    def settings_page(self):
        v=self.page()
        f,c=card(tr('اللغة'),tr('اختر لغة الواجهة. يُطبّق التغيير بعد إعادة تشغيل البرنامج.'),icon_name='info');v.addWidget(f)
        row=QHBoxLayout();row.setSpacing(8);self.language=Combo();self.language.setMinimumWidth(180)
        for code,name in i18n.LANGUAGES.items():self.language.addItem(name,code)
        self.language.setCurrentIndex(max(0,self.language.findData(i18n.preferred(self.preferences_file))));self.language.currentIndexChanged.connect(self.language_changed);row.addWidget(self.language)
        self.restart_button=QPushButton(tr('إعادة التشغيل الآن'));self.restart_button.setObjectName('primary');self.restart_button.clicked.connect(self.restart);self.restart_button.hide();row.addWidget(self.restart_button);row.addStretch();c.addLayout(row)
        f,c=card(tr('حماية الإعدادات'),tr('يفحص البرنامج قيم التعديلات بدل الاعتماد على شكل الملف. إذا رجعت القيم، يدمج التخفيف مع الملفات الحالية ويحفظ نسخة قبل الإصلاح.'),icon_name='shield');v.addWidget(f)
        self.guard=QCheckBox(tr('إعادة تطبيق المستوى المحفوظ تلقائيًا بعد إغلاق اللعبة • أبقِ البرنامج مفتوحًا'));self.guard.setChecked(True);c.addWidget(self.guard)
        self.guard_status=label(tr('الحماية جاهزة • لا يكتب البرنامج ملفات أثناء تشغيل اللعبة.'),'stepPill');c.addWidget(self.guard_status)
        row=QHBoxLayout();button=QPushButton(tr('فحص وإصلاح رجوع الإعدادات الآن'));button.setIcon(icon('refresh',T.TEXT));button.clicked.connect(self.repair_settings);row.addWidget(button);row.addStretch();c.addLayout(row)
        f,c=card(tr('التحديثات'),tr('الفحص يقرأ صفحة الإصدارات العامة فقط.'),icon_name='updates');v.addWidget(f)
        auto=QCheckBox(tr('فحص عند تشغيل البرنامج • بحد أقصى مرة يوميًا'));auto.setChecked(self.updates.auto_check.isChecked());auto.toggled.connect(self.updates.auto_check.setChecked);self.updates.auto_check.toggled.connect(auto.setChecked);c.addWidget(auto)
        f,c=card(tr('عن البرنامج'),tr('Deadlock Toolbox {0} • مفتوح المصدر • مشروع مستقل من المجتمع، غير تابع لـ Valve.').format(__version__),icon_name='diamond');v.addWidget(f)
        row=QHBoxLayout();b=QPushButton('GitHub');b.setObjectName('quiet');b.setIcon(icon('external',T.TEXT_SOFT));b.clicked.connect(lambda:QDesktopServices.openUrl(QUrl('https://github.com/exelight7/deadlock-fps-')));row.addWidget(b);row.addStretch();c.addLayout(row);v.addStretch()
    def language_changed(self,*_):
        self.save_workspace();self.restart_button.setVisible(self.language.currentData()!=i18n.LANGUAGE);self.status.setText(tr('حُفظت اللغة. أعد تشغيل البرنامج لتطبيقها.'))
    def restart(self):
        from PySide6.QtCore import QProcess
        command=[sys.executable] if getattr(sys,'frozen',False) else [sys.executable,str(Path(sys.argv[0]).resolve())]
        if QProcess.startDetached(command[0],command[1:]+[a for a in sys.argv[1:] if a!='--install'])[0]:self.close()
    def changed(self,*_):
        if hasattr(self,'level') and 'fps' in self.controls:
            self.summary.setText(tr('الدقة محفوظة • تخفيف {0}/{1} • عرض الرؤية {2:.2f}').format(self.level.value(),MAX_LEVEL,self.aspect.value()/100))
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
        p=QFileDialog.getExistingDirectory(self,tr('اختر مجلد Deadlock'))
        if p:self.path.setText(p);self.refresh_accounts()
    def browse_mods(self):self.mods_page.browse_folder()
    def focus_game(self):
        self.navigate(0)
        self.path.setFocus()
        QTimer.singleShot(0,lambda:self.stack.widget(0).ensureWidgetVisible(self.path))
    def mod_task_busy(self):
        if self.mods_page.busy:self.status.setText(tr('انتظر اكتمال عملية المودات الحالية، ثم أعد المحاولة.'));return True
        return False
    def detect_game(self):
        if self.mods_page.applying:return
        games=detect_games()
        if games:self.path.setText(str(games[0]));self.refresh_accounts()
        else:self.connection_note.setText(tr('ما لقينا اللعبة تلقائيًا. من Steam: إدارة اللعبة ← استعراض الملفات المحلية، ثم اختر المجلد هنا.'));self.update_game_status()
    def remember_account(self,*_):
        self.preferred_account=self.accounts.currentData();self.save_workspace()
    def save_workspace(self):
        from .core import atomic
        try:atomic(self.preferences_file,json.dumps({'game':self.path.text(),'account':self.preferred_account,'language':self.language.currentData() if hasattr(self,'language') else i18n.preferred(self.preferences_file)},ensure_ascii=False).encode('utf-8'))
        except OSError:self.status.setText(tr('اللعبة مرتبطة، لكن تعذر حفظ اختيار المجلد للجلسة القادمة.'))
    def refresh_accounts(self):
        self.accounts.blockSignals(True);self.accounts.clear()
        try:
            from .core import game_root
            root=game_root(self.path.text())
            self.path.setText(str(root))
            for f in video_files(root):
                account=next((p.name for p in f.parents if p.parent.name=='userdata'),None)
                self.accounts.addItem('Steam '+account if account else tr('إعدادات محلية للعبة'),str(f));self.accounts.setItemData(self.accounts.count()-1,str(f),Qt.ToolTipRole)
            index=self.accounts.findData(self.preferred_account)
            if index>=0:self.accounts.setCurrentIndex(index)
            self.preferred_account=self.accounts.currentData()
            self.connection_note.setText(tr('✓ اللعبة مرتبطة · اختر الأداء بالأسفل، ثم راجع وطبّق.'));self.save_workspace()
            if not self.accounts.count():self.connection_note.setText(tr('✓ اللعبة مرتبطة · شغّل اللعبة مرة واحدة إذا احتجت إعدادات الفيديو والكروس هير.'))
            self.status.setText(tr('اللعبة مرتبطة • جاهز للتخصيص.'));self.game_chip.setText(tr('اللعبة مرتبطة'))
            saved=Studio(root,self.accounts.currentData()).state().get('settings')
            if saved:self.load_settings(Settings.from_dict(saved))
        except Exception as e:self.status.setText(str(e));self.connection_note.setText(tr('اختر مجلد Deadlock الصحيح أو استخدم البحث التلقائي.'));self.game_chip.setText(tr('ربط اللعبة'))
        finally:
            self.accounts.blockSignals(False);self.accounts.setVisible(self.accounts.count()>1);self.account_label.setVisible(self.accounts.count()>1)
        self.refresh_mod_library();self.update_game_status();self.refresh_home()
        if hasattr(self,'inspector'):self.inspector.invalidate()
    def studio(self):return Studio(self.path.text(),self.accounts.currentData())
    def error(self,e):QMessageBox.warning(self,tr('تعذر إكمال العملية'),str(e));self.status.setText(str(e))
    def preview(self):
        if self.mod_task_busy():return
        if not self.path.text().strip():self.focus_game();self.connection_note.setText(tr('باقي خطوة واحدة: اختر مجلد اللعبة أولًا.'));return
        try:
            studio=self.studio();s=self.settings();plan=studio.plan(s,self.library.cache)
            require_mods(self.library,studio.root,s.mods)
            if not plan:self.status.setText(tr('الإعدادات مطبقة بالفعل.'));return
            dialog=QDialog(self);dialog.setWindowTitle(tr('مراجعة التغييرات'));dialog.resize(880,650);v=QVBoxLayout(dialog);v.setContentsMargins(24,22,24,20);v.setSpacing(14)
            v.addWidget(label(tr('سيتم تعديل {0} ملفات مع حفظ الأصل. أغلق اللعبة قبل المتابعة.').format(len(plan)),'cardtitle'))
            out=QPlainTextEdit();out.setReadOnly(True);out.setLayoutDirection(Qt.LeftToRight);out.setFont(QFont('monospace',10));parts=[]
            for p,b in plan.items():
                parts.append(str(p))
                if p.suffix in {'.gi','.txt'} and b is not None:
                    old=p.read_text(errors='replace') if p.exists() else ''
                    parts.append(''.join(difflib.unified_diff(old.splitlines(True),b.decode().splitlines(True),fromfile='current',tofile='proposed')))
                else:parts.append('Remove managed file' if b is None else f'Install VPK: {len(b):,} bytes')
            name,description=level_info(s.level)
            v.addWidget(label(tr('الأداء: {0} · المستوى {1}/{2}\nحد الإطارات: ').format(name,s.level,MAX_LEVEL)+(str(s.fps)+' FPS' if s.fps else tr('بدون حد'))+tr('\nدقة اللعبة محفوظة. تستطيع التراجع من النسخ والاسترجاع.'),'subtitle'))
            out.setPlainText('\n\n'.join(parts));out.hide();more=QPushButton(tr('إظهار تفاصيل الملفات'));more.setObjectName('quiet');more.setIcon(icon('file',T.TEXT_SOFT));more.setCheckable(True);more.toggled.connect(out.setVisible);v.addWidget(more,0,Qt.AlignLeading);v.addWidget(out,1);v.addStretch(0)
            buttons=QDialogButtonBox();ok=buttons.addButton(tr('تطبيق وحفظ نسخة احتياطية'),QDialogButtonBox.AcceptRole);ok.setObjectName('primary');buttons.addButton(tr('إلغاء'),QDialogButtonBox.RejectRole);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);v.addWidget(buttons)
            if dialog.exec()==QDialog.Accepted:
                # Regenerate after preview to detect file changes before committing.
                fresh=studio.plan(s,self.library.cache)
                if fresh!=plan:raise ValueError(tr('تغيرت الملفات أثناء المعاينة. أعد المعاينة.'))
                self.status.setText(studio.apply(plan,s));self.refresh_mod_library();QMessageBox.information(self,tr('تم التطبيق'),self.status.text())
        except Exception as e:self.error(e)
    def restore(self):
        if self.mod_task_busy():return
        try:
            studio=self.studio()
            if QMessageBox.question(self,tr('استرجاع الأصل'),tr('سيتم حفظ الحالة الحالية ثم استرجاع النسخ الأصلية. متابعة؟'))==QMessageBox.Yes:self.guard.setChecked(False);self.status.setText(studio.restore(self.preserve.isChecked()))
        except Exception as e:self.error(e)
    def open_backups(self):
        try:
            studio=self.studio();studio.store.mkdir(parents=True,exist_ok=True);QDesktopServices.openUrl(QUrl.fromLocalFile(str(studio.store)))
        except Exception as e:self.error(e)
    def export_settings(self):
        try:
            s=self.settings();p,_=QFileDialog.getSaveFileName(self,tr('تصدير'),'deadlock-profile.json','JSON (*.json)')
            if p:Path(p).write_text(json.dumps(s.to_dict(),indent=2));self.status.setText(tr('تم تصدير الإعدادات.'))
        except Exception as e:self.error(e)
    def import_settings(self):
        try:
            p,_=QFileDialog.getOpenFileName(self,tr('استيراد'),'','JSON (*.json)')
            if p:
                s=Settings.from_dict(json.loads(Path(p).read_text()));s.validate();self.load_settings(s);self.status.setText(tr('تم الاستيراد • راجع ثم طبّق.'))
        except Exception as e:self.error(e)

def main():
    app=QApplication(sys.argv);app.setApplicationName('DeadlockToolbox');app.setApplicationDisplayName('Deadlock Toolbox');app.setOrganizationName('exelight7');app.setLayoutDirection(Qt.RightToLeft if i18n.rtl() else Qt.LeftToRight);app.setStyle('Fusion');load_fonts();app.setPalette(dark_palette());app.setStyleSheet(STYLE)
    window=Window()
    if '--crosshair' in sys.argv:window.navigate(5)
    if '--updates' in sys.argv:window.navigate(6)
    if '--inspector' in sys.argv:window.navigate(7)
    if '--mods' in sys.argv:window.navigate(2)
    if '--install' in sys.argv:
        window.navigate(6);QTimer.singleShot(100,window.updates.install_current)
    window.show();window.update_startup_timer.start(3000);sys.exit(app.exec())
