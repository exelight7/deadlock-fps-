"""Shared visual language and lightweight, locally rendered page artwork."""
from PySide6.QtCore import Qt, QRectF, QSize, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QPainterPath, QLinearGradient, QPixmap, QIcon
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsOpacityEffect
from .core import ASSETS

PAGES = [
    ('OVERVIEW / 01', 'لعبتك، على طريقتك.', 'أداء أخف. تجربة أقرب لك. كل أدوات Deadlock في مكان واحد.', 'rem.jpg', (0, .08, 1, .78)),
    ('GRAPHICS / 02', 'تفاصيل أقل. تحكّم أكثر.', 'وازن الأداء والوضوح، وخصّص عرض الرؤية وحد الإطارات.', 'deadlock.jpg', (0, 0, 1, .59)),
    ('MOD LIBRARY / 03', 'لمستك الخاصة للعبة.', 'مكتبة واحدة لموداتك. استورد، اختر، واترك التركيب للأداة.', 'duo.jpg', (0, 0, 1, 1)),
    ('RECOVERY / 04', 'جرّب وأنت مطمئن.', 'نسخك الأصلية محفوظة. استرجعها أو شارك إعداداتك بسهولة.', 'deadlock.jpg', (0, .62, 1, .36)),
    ('CONNECTION / 05', 'اتصال أوضح. اختيار أسهل.', 'قِس زمن الاستجابة واختر مناطق اتصال Steam المناسبة لك.', 'rem.jpg', (0, .2, 1, .6)),
    ('CROSSHAIR / 06', 'Crosshair Designer', 'Preview, customize and apply your crosshair to Deadlock.', 'deadlock.jpg', (0, .62, 1, .36)),
]

STYLE = '''
QWidget {background:#121416;color:#eeeae2;font-family:"Noto Sans Arabic","Segoe UI",sans-serif;font-size:14px;}
QMainWindow {background:#121416;}
QLabel {background:transparent;}
QFrame#sidebar {background:#191b1e;border-left:1px solid #303236;}
QLabel#brand {color:#f3eee4;font-size:25px;font-weight:800;}
QLabel#eyebrow {color:#cfad7c;font-size:10px;font-weight:700;}
QLabel#sectionLabel {color:#92948e;font-size:11px;}
QLabel#crumb {color:#aaa9a3;font-size:12px;}
QLabel#badge {color:#d8b782;background:#28251f;border:1px solid #4b4031;border-radius:10px;padding:3px 10px;font-size:10px;}
QLabel#heroTitle {color:#f7f0e4;font-size:28px;font-weight:800;background:transparent;}
QLabel#heroDescription {color:#c0bfb8;font-size:13px;background:transparent;}
QLabel#heroEyebrow {color:#edc990;font-size:10px;font-weight:700;background:transparent;}
QLabel#subtitle {color:#b0b2ae;font-size:13px;}
QLabel#selectionNotice {color:#a8aba8;font-size:12px;padding:5px 10px;border:1px solid #34383b;border-radius:8px;}
QLabel#selectionNotice[hasSelection="true"] {color:#f5d8a6;background:#3b3427;border-color:#887047;font-weight:700;}
QLabel#cardtitle {color:#f1ece3;font-size:17px;font-weight:700;}
QFrame#card {background:#1b1e21;border:1px solid #323539;border-radius:15px;}
QFrame#card QLabel {background:transparent;}
QFrame#actionbar {background:#1c1f22;border:1px solid #36393c;border-radius:14px;}
QPushButton {background:#292d31;border:1px solid #3c4044;border-radius:9px;padding:9px 13px;font-weight:600;}
QPushButton:hover {background:#353a3f;border-color:#ad8e60;}
QPushButton:pressed {background:#443a2b;}
QPushButton:focus {border-color:#d0aa72;}
QPushButton#nav {background:transparent;border:1px solid transparent;text-align:right;padding:10px 14px;color:#b4b6b5;font-size:13px;}
QPushButton#nav:hover {background:#24272b;color:#f7f0e4;}
QPushButton#nav:checked {background:#342d23;color:#f4d9ae;border:1px solid #655039;}
QPushButton#primary {background:#e7c08a;color:#251f16;border:1px solid #e7c08a;font-size:13px;padding:12px 18px;font-weight:700;}
QPushButton#primary:hover {background:#f3d7b0;border-color:#f3d7b0;}
QPushButton#positive {background:#23392f;color:#bbebcf;border-color:#436e56;}
QPushButton#positive:hover {background:#30523f;border-color:#80ba96;}
QPushButton#positive:disabled {color:#717572;background:#222629;border-color:#303438;}
QPushButton:disabled {color:#717572;background:#222629;border-color:#303438;}
QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox,QPlainTextEdit {background:#141719;border:1px solid #3d4145;border-radius:8px;padding:8px;selection-background-color:#6c5435;}
QLineEdit:focus,QComboBox:focus,QSpinBox:focus {border-color:#d0aa72;}
QComboBox QAbstractItemView {background:#1d2023;selection-background-color:#493c2c;color:#eeeae2;}
QCheckBox {spacing:10px;padding:8px 0;background:transparent;}
QCheckBox::indicator {width:20px;height:20px;border:1px solid #707571;border-radius:5px;background:#141719;}
QCheckBox::indicator:checked {background:#e7c08a;border-color:#e7c08a;image:url("CHECK_ASSET");}
QSlider {min-height:28px;background:transparent;}
QSlider::groove:horizontal {height:5px;background:#3a3f40;border-radius:2px;}
QSlider::sub-page:horizontal {background:#d6b17c;border-radius:2px;}
QSlider::handle:horizontal {width:18px;margin:-7px 0;background:#f0d2a6;border:3px solid #8e724d;border-radius:9px;}
QSlider::handle:horizontal:hover {background:#fff0d8;border-color:#c39d66;}
QScrollArea {border:0;background:transparent;}
QScrollBar:vertical {background:transparent;width:7px;margin:2px;}
QScrollBar::handle:vertical {background:#5c5b51;border-radius:3px;min-height:30px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical {background:transparent;}
QScrollBar:horizontal {height:8px;background:#171a1c;}
QScrollBar::handle:horizontal {background:#5c5b51;border-radius:3px;min-width:30px;}
QScrollBar::add-line:horizontal,QScrollBar::sub-line:horizontal {width:0;}
QTableWidget {background:#191c1f;alternate-background-color:#202427;gridline-color:#32383b;border:1px solid #3b4144;border-radius:10px;}
QTableWidget::item {padding:7px;font-size:12px;}
QTableWidget::item:selected {background:#40372a;color:#f8e1bd;}
QHeaderView::section {background:#2b2e30;color:#d7c6ac;border:0;border-bottom:1px solid #484238;padding:9px;font-size:11px;font-weight:600;}
QMenu {background:#232629;color:#eeeae2;border:1px solid #575044;padding:6px;}
QMenu::item {padding:9px 20px;}
QMenu::item:selected {background:#493c2c;border-radius:5px;}
QToolTip {color:#f3eadb;background:#2a2c2e;border:1px solid #756141;padding:8px;}
QDialog {background:#16191c;}
'''.replace('CHECK_ASSET', (ASSETS/'check.svg').as_posix())


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
            p.drawLine(x,3,x,21);p.setBrush(QColor('#191b1e'));p.drawEllipse(QRectF(x-3,y-3,6,6));p.setBrush(Qt.NoBrush)
    elif index == 2:
        path=QPainterPath();path.moveTo(3,7);path.lineTo(12,2);path.lineTo(21,7);path.lineTo(21,17);path.lineTo(12,22);path.lineTo(3,17);path.closeSubpath();p.drawPath(path)
        p.drawLine(3,7,12,12);p.drawLine(12,12,21,7);p.drawLine(12,12,12,22)
    elif index == 3:
        p.drawArc(QRectF(4,4,16,16),20*16,300*16);p.drawLine(3,3,3,9);p.drawLine(3,9,9,9);p.drawLine(12,7,12,12);p.drawLine(12,12,16,14)
    elif index==5:
        p.drawEllipse(QRectF(6,6,12,12));p.drawLine(12,1,12,7);p.drawLine(12,17,12,23);p.drawLine(1,12,7,12);p.drawLine(17,12,23,12)
    else:
        p.drawEllipse(QRectF(3,3,18,18));p.drawEllipse(QRectF(8,3,8,18));p.drawLine(3,12,21,12)
    p.end();return QIcon(pix)


class ArtworkHero(QWidget):
    """Portrait-friendly image composition with a short text transition on navigation."""
    def __init__(self,parent=None):
        super().__init__(parent);self.setFixedHeight(186)
        self.images={name:QPixmap(str(ASSETS/'artwork'/name)) for name in ('rem.jpg','deadlock.jpg','duo.jpg')}
        self.page_index=0
        self.copy=QWidget(self);self.copy.setStyleSheet('background:transparent;')
        layout=QVBoxLayout(self.copy);layout.setContentsMargins(0,20,24,20);layout.setSpacing(5)
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
        return (116 if self.page_index in (4,5) else 150) if self.width()<760 else (150 if self.page_index in (4,5) else 186)
    def resizeEvent(self,event):
        self.setFixedHeight(self.banner_height())
        self.title.setStyleSheet('font-size:24px;' if self.width()<760 else 'font-size:28px;')
        self.copy.setGeometry(int(self.width()*.36),0,int(self.width()*.64),self.height());super().resizeEvent(event)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHints(QPainter.Antialiasing|QPainter.SmoothPixmapTransform)
        bounds=QRectF(self.rect()).adjusted(.5,.5,-.5,-.5);clip=QPainterPath();clip.addRoundedRect(bounds,18,18);p.setClipPath(clip)
        p.fillRect(self.rect(),QColor('#232523'))
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
        for stop,color in [(0,'#15202020'),(.20,'#28232523'),(.43,'#ee232523'),(.6,'#ff232523'),(1,'#ff232523')]:gradient.setColorAt(stop,QColor(color))
        p.fillRect(self.rect(),gradient)
        p.setClipping(False);p.setPen(QColor('#46443b'));p.setBrush(Qt.NoBrush);p.drawRoundedRect(bounds,18,18);p.end()


class BrandMark(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent);self.setFixedSize(68,58);self.pix=QPixmap(str(ASSETS/'artwork/logo.jpg'))
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHints(QPainter.Antialiasing|QPainter.SmoothPixmapTransform)
        path=QPainterPath();path.addRoundedRect(QRectF(self.rect()),12,12);p.setClipPath(path);p.fillRect(self.rect(),QColor('#000000'))
        if not self.pix.isNull():p.drawPixmap(QRectF(6,7,56,44),self.pix,QRectF(70,300,600,430))
        p.end()
