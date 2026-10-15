"""Shared visual language and lightweight, locally rendered page artwork."""
from PySide6.QtCore import Qt, QRectF, QSize, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QPainterPath, QLinearGradient, QPixmap, QIcon
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
QWidget {background:#0b1218;color:#e5eef2;font-family:"Noto Sans Arabic","Segoe UI",sans-serif;font-size:13px;}
QMainWindow {background:#0b1218;}
QLabel {background:transparent;}
QFrame#sidebar {background:#101a22;border-left:1px solid #303236;}
QLabel#brand {color:#f1f4f2;font-size:25px;font-weight:800;}
QLabel#eyebrow {color:#ddbb87;font-size:10px;font-weight:700;}
QLabel#sectionLabel {color:#8196a4;font-size:11px;}
QLabel#crumb {color:#8da0ac;font-size:12px;}
QLabel#badge {color:#e4c492;background:#232b2c;border:1px solid #475349;border-radius:10px;padding:3px 10px;font-size:10px;}
QLabel#heroTitle {color:#f4f5ef;font-size:28px;font-weight:800;background:transparent;}
QLabel#heroDescription {color:#afc0ca;font-size:13px;background:transparent;}
QLabel#heroEyebrow {color:#e5c492;font-size:10px;font-weight:700;background:transparent;}
QLabel#subtitle {color:#a5b7c3;font-size:13px;}
QLabel#selectionNotice {color:#a0b4c0;font-size:12px;padding:5px 10px;border:1px solid #2a3c48;border-radius:8px;}
QLabel#selectionNotice[hasSelection="true"] {color:#f7dbac;background:#343729;border-color:#7b7850;font-weight:700;}
QLabel#cardtitle {color:#edf3f4;font-size:17px;font-weight:700;}
QFrame#card {background:#121f28;border:1px solid #283a46;border-radius:16px;}
QFrame#card QLabel {background:transparent;}
QFrame#actionbar {background:#13212b;border:1px solid #334957;border-radius:14px;}
QPushButton {background:#1b2c37;border:1px solid #344a59;border-radius:9px;padding:8px 14px;font-weight:600;}
QPushButton:hover {background:#273d4a;border-color:#c9b185;}
QPushButton:pressed {background:#39402e;}
QPushButton:focus {border-color:#e6c391;}
QPushButton#nav {background:transparent;border:1px solid transparent;text-align:right;padding:7px 12px;color:#a6b9c5;font-size:13px;}
QPushButton#nav:hover {background:#1a2a35;color:#f4f5ef;}
QPushButton#nav:checked {background:#2b352e;color:#f5dfb7;border:1px solid #627057;}
QPushButton#primary {background:#e6c391;color:#1b2226;border:1px solid #e6c391;font-size:13px;padding:12px 18px;font-weight:700;}
QPushButton#primary:hover {background:#f4d9ae;border-color:#f4d9ae;}
QPushButton#positive {background:#173a36;color:#aeeddc;border-color:#35796d;}
QPushButton#positive:hover {background:#23544a;border-color:#88d7bd;}
QPushButton#positive:disabled {color:#657985;background:#14212a;border-color:#253944;}
QPushButton:disabled {color:#657985;background:#14212a;border-color:#253944;}
QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox,QPlainTextEdit {background:#0e1921;border:1px solid #304958;border-radius:8px;padding:8px;selection-background-color:#4b624e;}
QLineEdit:focus,QComboBox:focus,QSpinBox:focus {border-color:#e6c391;}
QComboBox QAbstractItemView {background:#14232e;selection-background-color:#344331;color:#e5eef2;}
QCheckBox {spacing:10px;padding:8px 0;background:transparent;}
QCheckBox::indicator {width:20px;height:20px;border:1px solid #5d7887;border-radius:5px;background:#0e1921;}
QCheckBox::indicator:checked {background:#e6c391;border-color:#e6c391;image:url("CHECK_ASSET");}
QSlider {min-height:28px;background:transparent;}
QSlider::groove:horizontal {height:5px;background:#2c4553;border-radius:2px;}
QSlider::sub-page:horizontal {background:#d9bc8c;border-radius:2px;}
QSlider::handle:horizontal {width:18px;margin:-7px 0;background:#f1d8ac;border:3px solid #798367;border-radius:9px;}
QSlider::handle:horizontal:hover {background:#fff0d5;border-color:#bdc397;}
QScrollArea {border:0;background:transparent;}
QScrollBar:vertical {background:transparent;width:7px;margin:2px;}
QScrollBar::handle:vertical {background:#536c7a;border-radius:3px;min-height:30px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical {background:transparent;}
QScrollBar:horizontal {height:8px;background:#0f1c25;}
QScrollBar::handle:horizontal {background:#536c7a;border-radius:3px;min-width:30px;}
QScrollBar::add-line:horizontal,QScrollBar::sub-line:horizontal {width:0;}
QTableWidget {background:#101b24;alternate-background-color:#15242e;gridline-color:#293d49;border:1px solid #304653;border-radius:10px;}
QTableWidget::item {padding:7px;font-size:12px;}
QTableWidget::item:selected {background:#39422f;color:#f8e4c1;}
QHeaderView::section {background:#1d303d;color:#bacdd4;border:0;border-bottom:1px solid #3d5662;padding:9px;font-size:11px;font-weight:600;}
QMenu {background:#142630;color:#e5eef2;border:1px solid #4b655e;padding:6px;}
QMenu::item {padding:9px 20px;}
QMenu::item:selected {background:#344331;border-radius:5px;}
QToolTip {color:#e9f3f3;background:#1a2e39;border:1px solid #67816e;padding:8px;}
QDialog {background:#0f1c25;}

QPushButton#quiet {background:transparent;border:1px solid #344a59;color:#afc5cd;}
QPushButton#danger {background:#37262a;border-color:#754b4e;color:#f0b0a7;}
QPushButton#danger:hover {background:#4b2e33;border-color:#d2978f;}
QPushButton#primary:disabled {background:#223440;border-color:#344a59;color:#8196a4;}
QLabel#statusPill {background:#1a2d38;border:1px solid #355260;border-radius:8px;padding:2px 8px;font-size:10px;color:#a7beca;}
QLabel#statusPill[tone="success"] {background:#173a36;border-color:#35796d;color:#aeeddc;}
QLabel#statusPill[tone="ready"] {background:#303929;border-color:#64704c;color:#e4d5aa;}
QLabel#stepPill {background:#12232e;border:1px solid #2d4553;border-radius:9px;padding:6px 10px;font-size:11px;color:#b7cdd6;}
QLabel#modTitle {font-size:15px;font-weight:700;color:#eef5f6;}
QLabel#noticeWarning {background:#38372a;border:1px solid #746d4d;border-radius:10px;color:#eed7a3;padding:10px;}
QFrame#modCard {background:#12232d;border:1px solid #2b4554;border-radius:14px;}
QFrame#modCard:hover {background:#172d38;border-color:#5f7c87;}
QFrame#modCard[selected="true"] {background:#21362f;border:2px solid #b9bd88;}
QFrame#dropArea {background:#11242d;border:1px dashed #577a83;border-radius:16px;}
QFrame#dropArea[dragging="true"] {background:#1c3c38;border:2px solid #b9d5ab;}
QProgressBar {border:0;background:#223c49;border-radius:3px;}
QProgressBar::chunk {background:#a5dac4;border-radius:3px;}
QFrame#workspaceHeader {background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #1c333e,stop:1 #12212c);border:1px solid #36515f;border-radius:17px;}
QLabel#utilityTitle {font-size:25px;font-weight:800;color:#f0f5f4;}
QLabel#utilityKicker {font-size:10px;font-weight:700;color:#d7c298;}
QLabel#utilityIcon {background:#293b37;border:1px solid #54675a;border-radius:12px;padding:10px;}
QPushButton#shortcut {background:#142834;border:1px solid #34505e;border-radius:12px;padding:12px;font-size:13px;}
QPushButton#shortcut:hover {background:#203b43;border-color:#89b5ac;}
QComboBox {min-height:21px;padding-left:28px;}
QComboBox::drop-down {width:24px;border:0;background:transparent;}
QComboBox::down-arrow {image:url("ARROW_ASSET");width:11px;height:8px;}
'''.replace('CHECK_ASSET', (ASSETS/'check.svg').as_posix()).replace('ARROW_ASSET',(ASSETS/'chevron-down.svg').as_posix())


def mod_icon(key):
    pix=QPixmap(32,32);pix.fill(Qt.transparent);p=QPainter(pix);p.setRenderHint(QPainter.Antialiasing)
    from PySide6.QtGui import QPen
    p.setPen(QPen(QColor('#e6c391'),1.8,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));p.setBrush(Qt.NoBrush)
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
    pix = QPixmap(24,24); pix.fill(Qt.transparent)
    p = QPainter(pix);p.setRenderHint(QPainter.Antialiasing)
    from PySide6.QtGui import QPen
    p.setPen(QPen(QColor('#d7b989'),1.6,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));p.setBrush(Qt.NoBrush)
    if index == 0:
        for x,y in [(3,3),(14,3),(3,14),(14,14)]:p.drawRoundedRect(QRectF(x,y,7,7),2,2)
    elif index == 1:
        for x,y in [(5,8),(12,16),(19,10)]:
            p.drawLine(x,3,x,21);p.setBrush(QColor('#101a22'));p.drawEllipse(QRectF(x-3,y-3,6,6));p.setBrush(Qt.NoBrush)
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
        layout=QVBoxLayout(self.copy);layout.setContentsMargins(0,12,24,12);layout.setSpacing(5)
        self.eyebrow=QLabel();self.eyebrow.setObjectName('heroEyebrow');self.eyebrow.setLayoutDirection(Qt.LeftToRight);self.eyebrow.setAlignment(Qt.AlignRight)
        self.title=QLabel();self.title.setObjectName('heroTitle');self.title.setWordWrap(True)
        self.description=QLabel();self.description.setObjectName('heroDescription');self.description.setWordWrap(True)
        layout.addWidget(self.eyebrow);layout.addStretch();layout.addWidget(self.title);layout.addWidget(self.description);layout.addStretch()
        self.effect=QGraphicsOpacityEffect(self.copy);self.copy.setGraphicsEffect(self.effect)
        self.animation=QVariantAnimation(self);self.animation.setDuration(170);self.animation.valueChanged.connect(self.effect.setOpacity)
    def set_page(self,index,animate=True):
        self.page_index=index;eyebrow,title,description,_,_=PAGES[index]
        self.eyebrow.setText('DEADLOCK TOOLBOX   /   '+eyebrow);self.title.setText(title);self.description.setText(description)
        self.setFixedHeight(self.banner_height())
        self.animation.stop()
        if animate and self.isVisible():
            self.animation.setStartValue(.4);self.animation.setEndValue(1.);self.animation.start()
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
        p.fillRect(self.rect(),QColor('#15252e'))
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
        for stop,color in [(0,'#15202020'),(.20,'#28232523'),(.43,'#ee15252e'),(.6,'#ff15252e'),(1,'#ff15252e')]:gradient.setColorAt(stop,QColor(color))
        p.fillRect(self.rect(),gradient)
        p.setClipping(False);p.setPen(QColor('#36505e'));p.setBrush(Qt.NoBrush);p.drawRoundedRect(bounds,18,18);p.end()


class BrandMark(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent);self.setFixedSize(68,58);self.pix=QPixmap(str(ASSETS/'artwork/logo.jpg'))
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHints(QPainter.Antialiasing|QPainter.SmoothPixmapTransform)
        path=QPainterPath();path.addRoundedRect(QRectF(self.rect()),12,12);p.setClipPath(path);p.fillRect(self.rect(),QColor('#000000'))
        if not self.pix.isNull():p.drawPixmap(QRectF(6,7,56,44),self.pix,QRectF(70,300,600,430))
        p.end()
