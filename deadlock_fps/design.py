"""Shared visual language and lightweight, locally rendered page artwork."""
from PySide6.QtCore import Qt, QRectF, QSize, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QPainterPath, QLinearGradient, QPixmap, QIcon, QImage, QPen
from PySide6.QtWidgets import QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QGraphicsOpacityEffect
from .core import ASSETS

PAGES = [
    ('OVERVIEW / 01', 'لعبتك، على طريقتك.', 'أداء أخف. تجربة أقرب لك. كل أدوات Deadlock في مكان واحد.', 'rem.jpg', (0, .08, 1, .78)),
    ('GRAPHICS / 02', 'تفاصيل أقل. تحكّم أكثر.', 'وازن الأداء والوضوح، وخصّص عرض الرؤية وحد الإطارات.', 'deadlock.jpg', (0, 0, 1, .59)),
    ('MOD LIBRARY / 03', 'موداتك. بدون تعقيد.', 'أضف الحزمة، اختر ما تحب، وركّب بأمان.', 'duo.jpg', (0, 0, 1, 1)),
    ('RECOVERY / 04', 'جرّب وأنت مطمئن.', 'نسخك الأصلية محفوظة. استرجعها أو شارك إعداداتك بسهولة.', 'deadlock.jpg', (0, .62, 1, .36)),
    ('CONNECTION / 05', 'اتصال أوضح. اختيار أسهل.', 'قِس زمن الاستجابة واختر مناطق اتصال Steam المناسبة لك.', 'rem.jpg', (0, .2, 1, .6)),
    ('CROSSHAIR / 06', 'Crosshair Designer', 'Preview, customize and apply your crosshair to Deadlock.', 'deadlock.jpg', (0, .62, 1, .36)),
    ('UPDATES / 07', 'Update Center', 'تابع آخر إصدارات Deadlock Toolbox.', 'deadlock.jpg', (0, .62, 1, .36)),
    ('INSPECTOR / 08', 'Mod Inspector', 'افحص ملفات المودات قبل التركيب.', 'duo.jpg', (0,0,1,1)),
]

STYLE = '''
QWidget {background:#0a1016;color:#e8eff3;font-family:"Noto Sans Arabic","Segoe UI",sans-serif;font-size:13px;}
QMainWindow {background:#0a1016;}
QLabel {background:transparent;}
QFrame#sidebar {background:#0d151c;border-left:1px solid #1b2934;}
QLabel#brand {color:#f4f6f3;font-size:25px;font-weight:800;}
QLabel#eyebrow {color:#e9c48c;font-size:10px;font-weight:700;letter-spacing:3px;}
QLabel#sectionLabel {color:#74899a;font-size:11px;}
QLabel#crumb {color:#8da1ae;font-size:12px;}
QLabel#badge {color:#ecd0a1;background:#1b2224;border:1px solid #4a4634;border-radius:10px;padding:3px 10px;font-size:10px;font-weight:600;}
QLabel#heroTitle {color:#f6f6f0;font-size:28px;font-weight:800;background:transparent;}
QLabel#heroDescription {color:#b4c4ce;font-size:13px;background:transparent;}
QLabel#heroEyebrow {color:#e9c48c;font-size:10px;font-weight:700;letter-spacing:1px;background:transparent;}
QLabel#subtitle {color:#9fb3c0;font-size:13px;}
QLabel#selectionNotice {color:#9fb3c0;font-size:12px;padding:5px 10px;border:1px solid #223340;border-radius:9px;}
QLabel#selectionNotice[hasSelection="true"] {color:#f7dbac;background:#2d2c21;border-color:#7b6c48;font-weight:700;}
QLabel#cardtitle {color:#f0f5f6;font-size:17px;font-weight:700;}
QFrame#card {background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #14212b,stop:1 #0f1a22);border:1px solid #223441;border-top-color:#30475a;border-radius:16px;}
QFrame#card QLabel {background:transparent;}
QFrame#actionbar {background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #16242e,stop:1 #101b23);border:1px solid #2b4150;border-radius:15px;}
QFrame#actionbar QLabel {background:transparent;}
QPushButton {background:#17252f;border:1px solid #2a3e4b;border-radius:10px;padding:8px 14px;font-weight:600;}
QPushButton:hover {background:#203441;border-color:#bfa172;color:#ffffff;}
QPushButton:pressed {background:#2a3328;border-color:#e9c48c;}
QPushButton:focus {border-color:#e9c48c;}
QPushButton:checked {background:#2a3328;border-color:#8f8259;color:#f5dfb7;}
QPushButton#nav {background:transparent;border:1px solid transparent;text-align:right;padding:7px 12px;color:#a6b9c5;font-size:13px;}
QPushButton#primary {background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #f6dcae,stop:1 #deb679);color:#191e21;border:1px solid #f0cf9b;font-size:13px;padding:12px 18px;font-weight:700;}
QPushButton#primary:hover {background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #fdeccb,stop:1 #e9c48c);border-color:#fdeccb;color:#191e21;}
QPushButton#primary:pressed {background:#d4ab6f;border-color:#d4ab6f;}
QPushButton#positive {background:#13332f;color:#aeeddc;border-color:#2f6e63;}
QPushButton#positive:hover {background:#1b4a42;border-color:#86e3c3;color:#d5fbf0;}
QPushButton#positive:disabled {color:#5d7280;background:#111b23;border-color:#1f303c;}
QPushButton:disabled {color:#5d7280;background:#111b23;border-color:#1f303c;}
QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox,QPlainTextEdit {background:#0c151c;border:1px solid #263a47;border-radius:9px;padding:8px;selection-background-color:#5d5237;selection-color:#ffffff;}
QLineEdit:hover,QComboBox:hover,QSpinBox:hover {border-color:#3b5564;}
QLineEdit:focus,QComboBox:focus,QSpinBox:focus {border-color:#e9c48c;}
QComboBox QAbstractItemView {background:#121e27;border:1px solid #2b4150;selection-background-color:#3a3a2a;color:#e8eff3;outline:0;}
QCheckBox {spacing:10px;padding:8px 0;background:transparent;}
QCheckBox::indicator {width:20px;height:20px;border:1px solid #4d6676;border-radius:6px;background:#0c151c;}
QCheckBox::indicator:hover {border-color:#e9c48c;}
QCheckBox::indicator:checked {background:#e9c48c;border-color:#e9c48c;image:url("CHECK_ASSET");}
QCheckBox::indicator:disabled {border-color:#2a3e4b;background:#111b23;}
QSlider {min-height:28px;background:transparent;}
QSlider::groove:horizontal {height:6px;background:#1c2d39;border-radius:3px;}
QSlider::sub-page:horizontal {background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #c79d5f,stop:1 #f3d6a4);border-radius:3px;}
QSlider::handle:horizontal {width:12px;margin:-7px 0;background:#fff3dc;border:4px solid #c9a064;border-radius:10px;}
QSlider::handle:horizontal:hover {background:#ffffff;border-color:#f3d6a4;}
QSlider::handle:horizontal:pressed {background:#ffffff;border-color:#e9c48c;}
QScrollArea {border:0;background:transparent;}
QScrollBar:vertical {background:transparent;width:8px;margin:2px;}
QScrollBar::handle:vertical {background:#2f4553;border-radius:3px;min-height:30px;}
QScrollBar::handle:vertical:hover {background:#b99a68;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical {background:transparent;}
QScrollBar:horizontal {height:8px;background:transparent;margin:2px;}
QScrollBar::handle:horizontal {background:#2f4553;border-radius:3px;min-width:30px;}
QScrollBar::handle:horizontal:hover {background:#b99a68;}
QScrollBar::add-line:horizontal,QScrollBar::sub-line:horizontal {width:0;}
QScrollBar::add-page:horizontal,QScrollBar::sub-page:horizontal {background:transparent;}
QTableWidget {background:#0d171e;alternate-background-color:#111d26;gridline-color:#1f303c;border:1px solid #223441;border-radius:12px;}
QTableWidget::item {padding:7px;font-size:12px;}
QTableWidget::item:selected {background:#3a3a2a;color:#f8e4c1;}
QHeaderView {background:transparent;}
QHeaderView::section {background:#15232d;color:#a9bdc8;border:0;border-bottom:1px solid #2b4150;padding:9px;font-size:11px;font-weight:600;}
QTableCornerButton::section {background:#15232d;border:0;}
QMenu {background:#121e27;color:#e8eff3;border:1px solid #2f4553;padding:6px;}
QMenu::item {padding:9px 20px;border-radius:6px;background:transparent;}
QMenu::item:selected {background:#3a3a2a;color:#f8e4c1;}
QMenu::separator {height:1px;background:#263a47;margin:5px 8px;}
QToolTip {color:#f0f5f6;background:#16242e;border:1px solid #6e6246;padding:8px;}
QDialog {background:#0d151c;}

QPushButton[active="true"] {background:#2b2a1f;border-color:#d9bc88;color:#f7deb2;}
QPushButton#quiet {background:transparent;border:1px solid #2a3e4b;color:#afc5cd;}
QPushButton#quiet:hover {background:#17252f;border-color:#bfa172;color:#ffffff;}
QPushButton#chip {background:#101b23;border:1px solid #2a3e4b;border-radius:13px;padding:6px 14px;color:#cfdde3;font-size:12px;}
QPushButton#chip:hover {background:#17252f;border-color:#bfa172;color:#ffffff;}
QPushButton#danger {background:#33211f;border-color:#6f4441;color:#f3b4aa;}
QPushButton#danger:hover {background:#462a27;border-color:#f08f85;color:#ffd9d2;}
QPushButton#primary:disabled {background:#1a2832;border-color:#2a3e4b;color:#74899a;}
QLabel#statusPill {background:#15222c;border:1px solid #2a3e4b;border-radius:9px;padding:2px 9px;font-size:10px;font-weight:600;color:#a0b5c1;}
QLabel#statusPill[tone="success"] {background:#13332f;border-color:#2f6e63;color:#aeeddc;}
QLabel#statusPill[tone="ready"] {background:#2b2a1f;border-color:#6e6246;color:#ecd9aa;}
QLabel#pageHint {background:#0e1921;border:1px solid #1f303c;border-right:3px solid #e9c48c;border-radius:10px;padding:7px 12px;font-size:12px;color:#c6d6de;}
QLabel#stepPill {background:#0e1921;border:1px solid #1f303c;border-radius:10px;padding:6px 11px;font-size:11px;color:#b9cbd5;}
QLabel#modTitle {font-size:15px;font-weight:700;color:#f0f5f6;}
QLabel#noticeWarning {background:#2e2b1f;border:1px solid #6e6246;border-radius:10px;color:#eed7a3;padding:10px;}
QFrame#modCard {background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #14212b,stop:1 #0f1a22);border:1px solid #223441;border-radius:15px;}
QFrame#modCard:hover {background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #192a35,stop:1 #12202a);border-color:#56707e;}
QFrame#modCard[selected="true"] {background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #26301f,stop:1 #172320);border:2px solid #d9bc88;}
QFrame#modCard QLabel {background:transparent;}
QFrame#dropArea {background:#0e1a22;border:1px dashed #44606e;border-radius:16px;}
QFrame#dropArea:hover {border-color:#bfa172;}
QFrame#dropArea[dragging="true"] {background:#16302c;border:2px solid #86e3c3;}
QFrame#dropArea QLabel {background:transparent;}
QProgressBar {border:0;background:#1a2a35;border-radius:3px;}
QProgressBar::chunk {background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #86e3c3,stop:1 #e9c48c);border-radius:3px;}
QFrame#workspaceHeader {background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #1b2f3a,stop:.55 #13212b,stop:1 #101a22);border:1px solid #2b4150;border-radius:17px;}
QFrame#workspaceHeader QLabel {background:transparent;}
QLabel#utilityTitle {font-size:25px;font-weight:800;color:#f4f6f3;}
QLabel#utilityKicker {font-size:10px;font-weight:700;color:#e9c48c;letter-spacing:2px;}
QLabel#utilityIcon {background:#2a2c20;border:1px solid #6e6246;border-radius:13px;padding:10px;}
QPushButton#shortcut {background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #15232d,stop:1 #101b23);border:1px solid #263a47;border-radius:13px;padding:12px;font-size:13px;}
QPushButton#shortcut:hover {background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #1c3038,stop:1 #14232b);border-color:#86c9bd;color:#ffffff;}
QPushButton#shortcut:pressed {background:#14232b;border-color:#86e3c3;}
QComboBox {min-height:21px;padding-left:28px;}
QComboBox::drop-down {width:24px;border:0;background:transparent;}
QComboBox::down-arrow {image:url("ARROW_ASSET");width:11px;height:8px;}
'''.replace('CHECK_ASSET', (ASSETS/'check.svg').as_posix()).replace('ARROW_ASSET',(ASSETS/'chevron-down.svg').as_posix())


def mod_icon(key):
    pix=QPixmap(64,64);pix.setDevicePixelRatio(2);pix.fill(Qt.transparent);p=QPainter(pix);p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor('#e9c48c'),1.8,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));p.setBrush(Qt.NoBrush)
    if key=='daylock':
        p.drawEllipse(QRectF(10,10,12,12))
        for rotation in range(0,360,45):p.save();p.translate(16,16);p.rotate(rotation);p.drawLine(0,-11,0,-14);p.restore()
    elif key=='names':
        path=QPainterPath();path.moveTo(4,7);path.lineTo(21,7);path.lineTo(29,16);path.lineTo(21,25);path.lineTo(4,25);path.closeSubpath();p.drawPath(path);p.drawEllipse(QRectF(19,13,5,5));p.drawLine(8,12,15,12);p.drawLine(8,19,14,19)
    elif key=='health':
        p.drawRoundedRect(QRectF(3,9,26,14),3,3);p.drawLine(8,16,14,16);p.drawLine(11,13,11,19);p.drawLine(19,12,19,20);p.drawLine(23,12,23,20)
    else:
        p.drawArc(QRectF(6,6,20,20),40*16,280*16);p.drawLine(24,3,24,11);p.drawLine(24,11,16,11);p.drawLine(11,17,15,21);p.drawLine(15,21,23,13)
    p.end();return QIcon(pix)

def nav_icon(index):
    """Small vector icons, with no font-dependent symbols."""
    pix = QPixmap(48,48); pix.setDevicePixelRatio(2); pix.fill(Qt.transparent)
    p = QPainter(pix);p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor('#e9c48c'),1.6,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));p.setBrush(Qt.NoBrush)
    if index == 0:
        for x,y in [(3,3),(14,3),(3,14),(14,14)]:p.drawRoundedRect(QRectF(x,y,7,7),2,2)
    elif index == 1:
        for x,y in [(5,8),(12,16),(19,10)]:
            p.drawLine(x,3,x,21);p.setBrush(QColor('#0d151c'));p.drawEllipse(QRectF(x-3,y-3,6,6));p.setBrush(Qt.NoBrush)
    elif index == 2:
        path=QPainterPath();path.moveTo(3,7);path.lineTo(12,2);path.lineTo(21,7);path.lineTo(21,17);path.lineTo(12,22);path.lineTo(3,17);path.closeSubpath();p.drawPath(path)
        p.drawLine(3,7,12,12);p.drawLine(12,12,21,7);p.drawLine(12,12,12,22)
    elif index == 3:
        p.drawArc(QRectF(4,4,16,16),20*16,300*16);p.drawLine(3,3,3,9);p.drawLine(3,9,9,9);p.drawLine(12,7,12,12);p.drawLine(12,12,16,14)
    elif index==5:
        p.drawEllipse(QRectF(6,6,12,12));p.drawLine(12,1,12,7);p.drawLine(12,17,12,23);p.drawLine(1,12,7,12);p.drawLine(17,12,23,12)
    elif index==6:
        p.drawLine(12,2,12,15);p.drawLine(7,10,12,15);p.drawLine(12,15,17,10)
        p.drawLine(3,16,3,21);p.drawLine(3,21,21,21);p.drawLine(21,21,21,16)
    elif index==7:
        p.drawEllipse(QRectF(3,3,12,12));p.drawLine(14,14,22,22);p.drawLine(7,9,9,11);p.drawLine(9,11,12,6)
    else:
        p.drawEllipse(QRectF(3,3,18,18));p.drawEllipse(QRectF(8,3,8,18));p.drawLine(3,12,21,12)
    p.end();return QIcon(pix)


class UtilityHeader(QFrame):
    def __init__(self,index,title,description,tag):
        super().__init__();self.setObjectName('workspaceHeader');v=QVBoxLayout(self);v.setContentsMargins(18,14,18,14);v.setSpacing(4)
        row=QHBoxLayout();row.setSpacing(12);icon=QLabel();icon.setObjectName('utilityIcon');icon.setPixmap(nav_icon(index).pixmap(26,26));row.addWidget(icon)
        copy=QVBoxLayout();copy.setSpacing(0);kicker=QLabel(tag);kicker.setObjectName('utilityKicker');kicker.setLayoutDirection(Qt.LeftToRight);copy.addWidget(kicker);name=QLabel(title);name.setObjectName('utilityTitle');name.setLayoutDirection(Qt.LeftToRight);copy.addWidget(name);row.addLayout(copy,1);v.addLayout(row)
        detail=QLabel(description);detail.setObjectName('subtitle');detail.setWordWrap(True);v.addWidget(detail)

class ArtworkHero(QWidget):
    """Portrait-friendly image composition with a short text transition on navigation."""
    def __init__(self,parent=None):
        super().__init__(parent);self.setFixedHeight(158)
        self.images={name:QPixmap(str(ASSETS/'artwork'/name)) for name in ('rem.jpg','deadlock.jpg','duo.jpg')}
        self.page_index=0
        self.copy=QWidget(self);self.copy.setStyleSheet('background:transparent;')
        layout=QVBoxLayout(self.copy);layout.setContentsMargins(0,12,30,12);layout.setSpacing(5)
        self.eyebrow=QLabel();self.eyebrow.setObjectName('heroEyebrow');self.eyebrow.setLayoutDirection(Qt.LeftToRight);self.eyebrow.setAlignment(Qt.AlignRight)
        self.title=QLabel();self.title.setObjectName('heroTitle');self.title.setWordWrap(True)
        self.description=QLabel();self.description.setObjectName('heroDescription');self.description.setWordWrap(True)
        layout.addWidget(self.eyebrow);layout.addStretch();layout.addWidget(self.title);layout.addWidget(self.description);layout.addStretch()
        self.effect=QGraphicsOpacityEffect(self.copy);self.copy.setGraphicsEffect(self.effect)
        self.animation=QVariantAnimation(self);self.animation.setDuration(260);self.animation.valueChanged.connect(self.effect.setOpacity)
    def set_page(self,index,animate=True):
        self.page_index=index;eyebrow,title,description,_,_=PAGES[index]
        self.eyebrow.setText('DEADLOCK TOOLBOX   /   '+eyebrow);self.title.setText(title);self.description.setText(description)
        self.setFixedHeight(self.banner_height())
        self.animation.stop()
        if animate and self.isVisible():
            self.animation.setStartValue(.25);self.animation.setEndValue(1.);self.animation.start()
        else:self.effect.setOpacity(1.)
        self.update()
    def banner_height(self):
        return 112 if self.page_index in (2,4) else (138 if self.width()<760 else 158)
    def resizeEvent(self,event):
        self.setFixedHeight(self.banner_height())
        self.title.setStyleSheet('font-size:22px;' if self.width()<760 else 'font-size:28px;')
        self.copy.setGeometry(int(self.width()*.36),0,int(self.width()*.64),self.height());super().resizeEvent(event)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHints(QPainter.Antialiasing|QPainter.SmoothPixmapTransform)
        bounds=QRectF(self.rect()).adjusted(.5,.5,-.5,-.5);clip=QPainterPath();clip.addRoundedRect(bounds,18,18);p.setClipPath(clip)
        p.fillRect(self.rect(),QColor('#111c25'))
        _,_,_,name,crop=PAGES[self.page_index];pix=self.images[name]
        if not pix.isNull():
            source=QRectF(pix.width()*crop[0],pix.height()*crop[1],pix.width()*crop[2],pix.height()*crop[3])
            dest=QRectF(0,0,self.width()*.49,self.height())
            # Keep the requested portraits visible instead of stretching them into a banner.
            ratio=dest.width()/dest.height()
            if source.width()/source.height()>ratio:
                w=source.height()*ratio;source.setLeft(source.center().x()-w/2);source.setWidth(w)
            else:
                h=source.width()/ratio;source.setTop(source.top()+max(0,(source.height()-h)*(0 if name=='duo.jpg' or self.page_index==1 else .28)));source.setHeight(h)
            p.drawPixmap(dest,pix,source)
        gradient=QLinearGradient(0,0,self.width(),0)
        for stop,color in [(0,'#f5111c25'),(.07,'#3a111c25'),(.20,'#30111c25'),(.43,'#ee111c25'),(.58,'#ff111c25'),(1,'#ff16242e')]:gradient.setColorAt(stop,QColor(color))
        p.fillRect(self.rect(),gradient)
        # A warm edge on the reading side ties the banner to the gold accent.
        warm=QLinearGradient(self.width(),0,self.width()*.62,0);warm.setColorAt(0,QColor(233,196,140,26));warm.setColorAt(1,QColor(233,196,140,0));p.fillRect(self.rect(),warm)
        bar=QLinearGradient(0,22,0,self.height()-22);bar.setColorAt(0,QColor('#f7deb2'));bar.setColorAt(1,QColor(233,196,140,40))
        p.setPen(Qt.NoPen);p.setBrush(bar);p.drawRoundedRect(QRectF(self.width()-15,22,3,max(0,self.height()-44)),1.5,1.5)
        p.setClipping(False);p.setPen(QColor('#2b4150'));p.setBrush(Qt.NoBrush);p.drawRoundedRect(bounds,18,18);p.end()


def brand_logo(size=160):
    """The sketched eye mark as light strokes on transparency, cut from the black artwork."""
    art=QImage(str(ASSETS/'artwork/logo.jpg'))
    if art.isNull():return QPixmap()
    art=art.copy(55,205,626,626).scaled(size,size,Qt.KeepAspectRatio,Qt.SmoothTransformation)
    strokes=QImage(art.size(),QImage.Format_ARGB32);strokes.fill(QColor('#f4efe4'))
    strokes.setAlphaChannel(art.convertToFormat(QImage.Format_Grayscale8))
    return QPixmap.fromImage(strokes)


class BrandMark(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent);self.setFixedSize(58,58);self.pix=brand_logo(116)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHints(QPainter.Antialiasing|QPainter.SmoothPixmapTransform)
        tile=QRectF(self.rect()).adjusted(.5,.5,-.5,-.5)
        fill=QLinearGradient(0,0,0,self.height());fill.setColorAt(0,QColor('#1c2a2a'));fill.setColorAt(1,QColor('#0a1016'))
        ring=QLinearGradient(0,0,self.width(),self.height());ring.setColorAt(0,QColor('#f7deb2'));ring.setColorAt(1,QColor(233,196,140,70))
        p.setPen(QPen(ring,1));p.setBrush(fill);p.drawRoundedRect(tile,15,15)
        if not self.pix.isNull():p.drawPixmap(QRectF(6,6,46,46),self.pix,QRectF(self.pix.rect()))
        p.end()
