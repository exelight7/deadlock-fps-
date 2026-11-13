"""The Toolbox look: stylesheet, icons, artwork and shared widgets. Rules live in docs/DESIGN.md.

Nothing here knows about game files or networking. Pages build their layouts
from these parts and keep their own behaviour.
"""
from PySide6.QtCore import Qt, QByteArray, QEvent, QObject, QPointF, QRectF, QSize, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPainterPath, QPalette, QPen, QPixmap, QPolygonF
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QComboBox, QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget
from . import theme as T
from .core import ASSETS

# Page banner copy: kicker, title, description, banner motif.
PAGES = [
    ('OVERVIEW / 01', 'لعبتك، على طريقتك.', 'أداء أخف. تجربة أقرب لك. كل أدوات Deadlock في مكان واحد.', 'emblem'),
    ('GRAPHICS / 02', 'تفاصيل أقل. تحكّم أكثر.', 'وازن الأداء والوضوح، وخصّص عرض الرؤية وحد الإطارات.', 'emblem'),
    ('MOD LIBRARY / 03', 'موداتك. بدون تعقيد.', 'أضف الحزمة، اختر ما تحب، وركّب بأمان.', 'mods'),
    ('RECOVERY / 04', 'جرّب وأنت مطمئن.', 'نسخك الأصلية محفوظة. استرجعها أو شارك إعداداتك بسهولة.', 'backups'),
    ('CONNECTION / 05', 'اتصال أوضح. اختيار أسهل.', 'قِس زمن الاستجابة واختر مناطق اتصال Steam المناسبة لك.', 'servers'),
    ('CROSSHAIR / 06', 'Crosshair Designer', 'Preview, customize and apply your crosshair to Deadlock.', 'emblem'),
    ('UPDATES / 07', 'Update Center', 'تابع آخر إصدارات Deadlock Toolbox.', 'emblem'),
    ('INSPECTOR / 08', 'Mod Inspector', 'افحص ملفات المودات قبل التركيب.', 'mods'),
]
NAV_ICONS = ('overview', 'graphics', 'mods', 'backups', 'servers', 'crosshair', 'updates', 'inspector')


# --- Fonts, palette, vector assets -----------------------------------------------------------------

_fonts_loaded = False
_svg_text = {}
_icons = {}
_tiles = {}


def load_fonts():
    """Register the bundled faces once. Safe before any window exists and safe to repeat."""
    global _fonts_loaded
    if not _fonts_loaded and QApplication.instance() is not None:
        _fonts_loaded = True
        for name in T.FONT_FILES:
            QFontDatabase.addApplicationFont(str(ASSETS / 'fonts' / name))


def dark_palette():
    """Palette for the widgets a stylesheet does not reach (native-looking dialogs, item views)."""
    palette = QPalette()
    for role, color in [(QPalette.Window, T.BASE), (QPalette.WindowText, T.TEXT), (QPalette.Base, T.SUNKEN), (QPalette.AlternateBase, T.SURFACE),
                        (QPalette.Text, T.TEXT), (QPalette.Button, T.SURFACE), (QPalette.ButtonText, T.TEXT), (QPalette.ToolTipBase, T.RAISED),
                        (QPalette.ToolTipText, T.TEXT), (QPalette.Highlight, T.BRASS_DEEP), (QPalette.HighlightedText, T.TEXT), (QPalette.Link, T.BRASS_BRIGHT),
                        (QPalette.PlaceholderText, T.TEXT_MUTED), (QPalette.Light, T.LINE_STRONG), (QPalette.Midlight, T.LINE), (QPalette.Mid, T.LINE),
                        (QPalette.Dark, T.SUNKEN), (QPalette.Shadow, T.INK), (QPalette.BrightText, T.BRASS_BRIGHT)]:
        palette.setColor(role, QColor(color))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        palette.setColor(QPalette.Disabled, role, QColor(T.TEXT_OFF))
    return palette


def font(stack=T.BODY, size=13, weight=400, spacing=0):
    f = QFont()
    f.setFamilies(list(stack))
    f.setPixelSize(size)
    f.setWeight(QFont.Weight(weight))
    if spacing:
        f.setLetterSpacing(QFont.AbsoluteSpacing, spacing)
    return f


def svg_source(relative):
    if relative not in _svg_text:
        try:
            _svg_text[relative] = (ASSETS / relative).read_text(encoding='utf-8')
        except OSError:
            _svg_text[relative] = ''
    return _svg_text[relative]


def svg_pixmap(relative, width, height, ratio=1., tint=None):
    """Render a bundled SVG crisply for the given device pixel ratio; `tint` recolours the brass ink."""
    source = svg_source(relative)
    if tint and tint.lower() != T.BRASS:
        source = source.replace(T.BRASS_BRIGHT, tint).replace(T.BRASS, tint)
    pixmap = QPixmap(max(1, round(width * ratio)), max(1, round(height * ratio)))
    pixmap.fill(Qt.transparent)
    renderer = QSvgRenderer(QByteArray(source.encode('utf-8')))
    if renderer.isValid():
        painter = QPainter(pixmap)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        renderer.render(painter, QRectF(0, 0, pixmap.width(), pixmap.height()))
        painter.end()
    pixmap.setDevicePixelRatio(ratio)
    return pixmap


def icon(name, color=T.BRASS, size=24):
    """A line icon from assets/icons, tinted, with crisp 1x–3x pixmaps and a muted disabled state."""
    key = (name, color, size)
    if key not in _icons:
        result = QIcon()
        for scale in (1, 2, 3):
            result.addPixmap(svg_pixmap('icons/%s.svg' % name, size * scale, size * scale, 1., color), QIcon.Normal)
            result.addPixmap(svg_pixmap('icons/%s.svg' % name, size * scale, size * scale, 1., T.TEXT_OFF), QIcon.Disabled)
        _icons[key] = result
    return _icons[key]


def nav_icon(index):
    return icon(NAV_ICONS[index] if 0 <= index < len(NAV_ICONS) else 'diamond')


def mod_icon(key):
    return icon(key if key in ('daylock', 'names', 'health', 'sinner') else 'mods')


def tile(name, ratio=1.):
    """A pattern tile from assets/patterns for QPainter.drawTiledPixmap."""
    key = (name, ratio)
    if key not in _tiles:
        width, height = {'fan': (48, 48), 'lattice': (32, 32), 'chevron': (40, 20)}[name]
        _tiles[key] = svg_pixmap('patterns/%s.svg' % name, width, height, ratio)
    return _tiles[key]


def brand_logo(size=160):
    """The keyhole emblem as a pixmap."""
    return svg_pixmap('brand/emblem.svg', size, size)


def chamfer(rect, cut=T.CHAMFER):
    """The cut-corner outline every panel shares."""
    cut = min(cut, rect.width() / 2, rect.height() / 2)
    l, t, r, b = rect.left(), rect.top(), rect.right(), rect.bottom()
    path = QPainterPath()
    path.addPolygon(QPolygonF([QPointF(l + cut, t), QPointF(r - cut, t), QPointF(r, t + cut), QPointF(r, b - cut),
                               QPointF(r - cut, b), QPointF(l + cut, b), QPointF(l, b - cut), QPointF(l, t + cut)]))
    path.closeSubpath()
    return path


def paint_panel(painter, rect, fill=T.SURFACE, line=T.LINE, accent=T.BRASS_DEEP, cut=T.CHAMFER, width=1., dashed=False):
    """Fill and outline a cut-corner plate, with brass ticks on two opposite corners."""
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    rect = QRectF(rect).adjusted(width / 2, width / 2, -width / 2, -width / 2)
    pen = QPen(QColor(line), width)
    if dashed:
        pen.setStyle(Qt.CustomDashLine)
        pen.setDashPattern([5, 4])
    painter.setPen(pen)
    painter.setBrush(QColor(fill) if fill else Qt.NoBrush)
    painter.drawPath(chamfer(rect, cut))
    if accent:
        painter.setPen(QPen(QColor(accent), 1.5))
        cut = min(cut, rect.width() / 2, rect.height() / 2)
        painter.drawLine(QPointF(rect.left(), rect.top() + cut), QPointF(rect.left() + cut, rect.top()))
        painter.drawLine(QPointF(rect.right() - cut, rect.bottom()), QPointF(rect.right(), rect.bottom() - cut))
        painter.drawLine(QPointF(rect.right() - cut, rect.top()), QPointF(rect.right(), rect.top() + cut))
        painter.drawLine(QPointF(rect.left(), rect.bottom() - cut), QPointF(rect.left() + cut, rect.bottom()))
    painter.restore()


def repolish(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


# --- Stylesheet ---------------------------------------------------------------------------------------

def build_style(latin=False):
    """The application stylesheet. `latin` gives the left-to-right English crosshair workspace its own font order."""
    body = T.family(('Noto Sans', 'Noto Sans Arabic', 'Segoe UI') if latin else T.BODY)
    tokens = {name: value for name, value in vars(T).items() if name.isupper() and isinstance(value, str)}
    tokens.update(BODY_FONT=body, DISPLAY_FONT=T.family(T.DISPLAY), MONO_FONT=T.family(T.MONO),
                  QSS=(ASSETS / 'icons/qss').as_posix())
    sheet = '''
QWidget {color:@TEXT;font-family:@BODY_FONT;font-size:13px;}
QMainWindow,QDialog {background:@BASE;}
QLabel {background:transparent;}
QToolTip {color:@TEXT;background:@RAISED;border:1px solid @BRASS_DEEP;padding:6px 8px;}

QLabel#pageTitle {font-family:@DISPLAY_FONT;font-size:24px;font-weight:600;color:@TEXT;}
QLabel#crumb {color:@TEXT_MUTED;font-size:11px;}
QLabel#kicker {color:@BRASS;font-size:10px;font-weight:600;}
QLabel#kicker[tracked="true"] {letter-spacing:3px;}
QLabel#brand {font-family:@DISPLAY_FONT;font-size:21px;font-weight:600;color:@TEXT;}
QLabel#sectionLabel {color:@TEXT_MUTED;font-size:11px;}
QLabel#subtitle {color:@TEXT_SOFT;font-size:13px;}
QLabel#lead {color:@TEXT;font-size:15px;font-weight:600;}
QLabel#cardtitle {font-family:@DISPLAY_FONT;color:@TEXT;font-size:18px;font-weight:600;}
QLabel#value {font-family:@DISPLAY_FONT;color:@BRASS_BRIGHT;font-size:20px;font-weight:600;}
QLabel#modTitle {font-family:@DISPLAY_FONT;font-size:18px;font-weight:600;color:@TEXT;}
QLabel#heroTitle {font-family:@DISPLAY_FONT;color:@TEXT;font-size:26px;font-weight:600;}
QLabel#heroDescription {color:@TEXT_SOFT;font-size:13px;}
QLabel#pageHint {color:@TEXT_SOFT;font-size:13px;}
QLabel#badge {color:@BRASS;background:transparent;border:1px solid @BRASS_DEEP;border-radius:2px;padding:3px 9px;font-size:11px;font-weight:600;}
QLabel#stepPill {color:@TEXT_SOFT;background:@SUNKEN;border:1px solid @LINE;border-radius:2px;padding:6px 10px;font-size:12px;}
QLabel#stepPill[tone="success"] {color:@VERDIGRIS;background:@VERDIGRIS_WASH;border-color:@VERDIGRIS_LINE;}
QLabel#stepPill[tone="danger"] {color:@CRIMSON_TEXT;background:@CRIMSON_WASH;border-color:@CRIMSON_LINE;}
QLabel#selectionNotice {color:@TEXT_MUTED;font-size:12px;padding:6px 10px;border:1px solid @LINE;border-radius:2px;background:@SUNKEN;}
QLabel#selectionNotice[hasSelection="true"] {color:@BRASS_BRIGHT;background:@BRASS_WASH;border-color:@BRASS_DEEP;font-weight:600;}
QLabel#statusPill {background:@SUNKEN;border:1px solid @LINE;border-radius:2px;padding:2px 8px;font-size:11px;font-weight:600;color:@TEXT_MUTED;}
QLabel#statusPill[tone="success"] {background:@VERDIGRIS_WASH;border-color:@VERDIGRIS_LINE;color:@VERDIGRIS;}
QLabel#statusPill[tone="ready"] {background:@BRASS_WASH;border-color:@BRASS_DEEP;color:@BRASS_BRIGHT;}
QLabel#statusPill[tone="danger"] {background:@CRIMSON_WASH;border-color:@CRIMSON_LINE;color:@CRIMSON_TEXT;}
QLabel#noticeWarning {background:@BRASS_WASH;border:1px solid @BRASS_DEEP;border-radius:2px;color:@BRASS_BRIGHT;padding:10px 12px;}
QLabel#previewMode {color:@VERDIGRIS;background:@VERDIGRIS_WASH;border:1px solid @VERDIGRIS_LINE;border-radius:2px;padding:4px 9px;font-size:11px;font-weight:600;}
QLabel#stateTitle {font-family:@DISPLAY_FONT;font-size:20px;font-weight:600;color:@TEXT;}
QLabel#stateTitle[tone="success"] {color:@VERDIGRIS;}
QLabel#stateTitle[tone="danger"] {color:@CRIMSON_TEXT;}
QLabel#stateTitle[tone="ready"] {color:@BRASS_BRIGHT;}

QFrame#card,QFrame#modCard,QFrame#dropArea,QFrame#actionbar,QFrame#crosshairActions,QFrame#sidebar,QFrame#workspaceHeader {background:transparent;border:none;}

QPushButton {background:@SURFACE;color:@TEXT;border:1px solid @LINE_STRONG;border-radius:2px;padding:7px 14px;min-height:20px;font-weight:600;}
QPushButton:hover {background:@RAISED;border-color:@BRASS;color:@BRASS_BRIGHT;}
QPushButton:pressed {background:@ACTIVE;border-color:@BRASS_BRIGHT;}
QPushButton:focus {border-color:@BRASS;}
QPushButton:checked {background:@BRASS_WASH;border-color:@BRASS;color:@BRASS_BRIGHT;}
QPushButton[active="true"] {background:@BRASS_WASH;border:1px solid @BRASS;border-bottom:2px solid @BRASS_BRIGHT;color:@BRASS_BRIGHT;}
QPushButton:disabled {color:@TEXT_OFF;background:@SUNKEN;border-color:@LINE;}
QPushButton::menu-indicator {image:url("@QSS/chevron-down.svg");width:10px;height:10px;subcontrol-origin:padding;subcontrol-position:center right;right:9px;}
QPushButton::menu-indicator:disabled {image:url("@QSS/chevron-down-off.svg");}
QPushButton[menu="true"] {padding-left:26px;padding-right:26px;}
QPushButton#primary {font-size:14px;font-weight:700;background:@BRASS;color:@ON_BRASS;border:3px double @ON_BRASS;padding:6px 20px;}
QPushButton#primary:hover {background:@BRASS_BRIGHT;color:@ON_BRASS;border-color:@ON_BRASS;}
QPushButton#primary:pressed {background:@BRASS_DEEP;color:@ON_BRASS;}
QPushButton#primary:focus {border-color:@INK;}
QPushButton#primary:disabled {background:@SUNKEN;color:@TEXT_OFF;border:1px solid @LINE;padding:8px 22px;}
QPushButton#positive {background:transparent;color:@VERDIGRIS;border-color:@VERDIGRIS_LINE;}
QPushButton#positive:hover {background:@VERDIGRIS_WASH;border-color:@VERDIGRIS;color:@VERDIGRIS;}
QPushButton#positive:pressed {background:@VERDIGRIS_LINE;color:@TEXT;}
QPushButton#positive:disabled {color:@TEXT_OFF;background:@SUNKEN;border-color:@LINE;}
QPushButton#danger {background:transparent;color:@CRIMSON_TEXT;border-color:@CRIMSON_LINE;}
QPushButton#danger:hover {background:@CRIMSON;border-color:@CRIMSON;color:@TEXT;}
QPushButton#danger:pressed {background:@CRIMSON_LINE;color:@TEXT;}
QPushButton#danger:disabled {color:@TEXT_OFF;background:@SUNKEN;border-color:@LINE;}
QPushButton#quiet {background:transparent;border:1px solid @LINE;color:@TEXT_SOFT;}
QPushButton#quiet:hover {background:@SURFACE;border-color:@BRASS_DEEP;color:@BRASS_BRIGHT;}
QPushButton#quiet:checked {background:@BRASS_WASH;border-color:@BRASS_DEEP;color:@BRASS_BRIGHT;}
QPushButton#quiet:disabled {color:@TEXT_OFF;border-color:@LINE;background:transparent;}
QPushButton#chip {background:@SUNKEN;border:1px solid @LINE;border-radius:2px;padding:4px 12px;color:@TEXT_SOFT;font-size:12px;min-height:18px;}
QPushButton#chip:hover {border-color:@BRASS_DEEP;color:@BRASS_BRIGHT;background:@SURFACE;}
QPushButton#shortcut {font-size:14px;font-weight:600;background:@SURFACE;border:1px solid @LINE;padding:12px 14px;color:@TEXT;}
QPushButton#shortcut:hover {background:@RAISED;border-color:@BRASS;color:@BRASS_BRIGHT;}
QPushButton#shortcut:pressed {background:@ACTIVE;}
QPushButton#swatch {padding:0;min-height:0;border:1px solid @LINE_STRONG;border-radius:0;}
QPushButton#swatch:hover {border:2px solid @BRASS_BRIGHT;}

QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox,QPlainTextEdit {background:@SUNKEN;color:@TEXT;border:1px solid @LINE;border-radius:2px;padding:7px 10px;selection-background-color:@BRASS_DEEP;selection-color:@TEXT;}
QLineEdit:hover,QComboBox:hover,QSpinBox:hover,QDoubleSpinBox:hover {border-color:@LINE_STRONG;}
QLineEdit:focus,QComboBox:focus,QSpinBox:focus,QDoubleSpinBox:focus,QPlainTextEdit:focus {border-color:@BRASS;}
QLineEdit:disabled,QComboBox:disabled,QSpinBox:disabled,QDoubleSpinBox:disabled {color:@TEXT_OFF;border-color:@LINE;}
QPlainTextEdit {font-family:@MONO_FONT;font-size:12px;padding:10px;}
QPlainTextEdit#notes {font-family:@BODY_FONT;font-size:13px;}
QDoubleSpinBox,QSpinBox {padding:5px 8px;font-size:12px;}
QComboBox {min-height:20px;}
QComboBox::drop-down {width:28px;border:0;background:transparent;}
QComboBox::down-arrow {image:url("@QSS/chevron-down.svg");width:11px;height:11px;}
QComboBox::down-arrow:disabled {image:url("@QSS/chevron-down-off.svg");}
QComboBox QAbstractItemView {background:@SURFACE;color:@TEXT;border:1px solid @BRASS_DEEP;selection-background-color:@BRASS_SHADE;selection-color:@BRASS_BRIGHT;outline:0;padding:4px;}

QCheckBox {spacing:10px;padding:6px 0;background:transparent;color:@TEXT;}
QCheckBox:disabled {color:@TEXT_OFF;}
QCheckBox::indicator {width:18px;height:18px;border:1px solid @LINE_STRONG;border-radius:2px;background:@SUNKEN;}
QCheckBox::indicator:hover {border-color:@BRASS;}
QCheckBox::indicator:checked {background:@BRASS;border-color:@BRASS_BRIGHT;image:url("@QSS/check.svg");}
QCheckBox::indicator:disabled {border-color:@LINE;background:@SUNKEN;}
QCheckBox::indicator:checked:disabled {background:@ACTIVE;border-color:@LINE;image:url("@QSS/check-off.svg");}

QSlider {min-height:26px;background:transparent;}
QSlider::groove:horizontal {height:4px;background:@SUNKEN;border:1px solid @LINE;}
QSlider::sub-page:horizontal {background:@BRASS;border:1px solid @BRASS;}
QSlider::sub-page:horizontal:disabled {background:@ACTIVE;border-color:@LINE;}
QSlider::handle:horizontal {image:url("@QSS/handle.svg");width:18px;height:18px;margin:-7px -1px;}
QSlider::handle:horizontal:hover {image:url("@QSS/handle-hover.svg");}
QSlider::handle:horizontal:pressed {image:url("@QSS/handle-hover.svg");}
QSlider::handle:horizontal:disabled {image:url("@QSS/handle-off.svg");}

QScrollArea {border:0;background:transparent;}
QScrollArea > QWidget {background:transparent;}
QScrollArea > QWidget > QWidget {background:transparent;}
QScrollBar:vertical {background:transparent;width:10px;margin:2px;}
QScrollBar::handle:vertical {background:@LINE_STRONG;min-height:32px;}
QScrollBar::handle:vertical:hover {background:@BRASS_DEEP;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical {background:transparent;}
QScrollBar:horizontal {height:10px;background:transparent;margin:2px;}
QScrollBar::handle:horizontal {background:@LINE_STRONG;min-width:32px;}
QScrollBar::handle:horizontal:hover {background:@BRASS_DEEP;}
QScrollBar::add-line:horizontal,QScrollBar::sub-line:horizontal {width:0;}
QScrollBar::add-page:horizontal,QScrollBar::sub-page:horizontal {background:transparent;}

QTableWidget,QListWidget {background:@SURFACE;alternate-background-color:@SUNKEN;color:@TEXT;border:1px solid @LINE;gridline-color:@LINE;outline:0;}
QTableWidget::item {padding:6px 10px;font-size:12px;}
QTableWidget::item:selected {background:@BRASS_SHADE;color:@BRASS_BRIGHT;}
QHeaderView {background:transparent;}
QHeaderView::section {background:@RAISED;color:@TEXT_MUTED;border:0;border-bottom:1px solid @LINE_STRONG;padding:8px 10px;font-size:11px;font-weight:600;}
QTableCornerButton::section {background:@RAISED;border:0;}

QTabWidget::pane {border:0;background:transparent;}
QTabBar {background:transparent;}
QTabBar::tab {background:@SUNKEN;color:@TEXT_MUTED;border:1px solid @LINE;border-bottom:2px solid @LINE;padding:8px 16px;margin-bottom:10px;min-width:64px;font-weight:600;}
QTabBar::tab:hover {color:@TEXT;border-bottom-color:@LINE_STRONG;}
QTabBar::tab:selected {background:@BRASS_WASH;color:@BRASS_BRIGHT;border-color:@BRASS_DEEP;border-bottom:2px solid @BRASS_BRIGHT;}

QProgressBar {border:0;background:@SUNKEN;min-height:4px;max-height:4px;}
QProgressBar::chunk {background:@BRASS;}

QMenu {background:@SURFACE;color:@TEXT;border:1px solid @BRASS_DEEP;padding:5px;}
QMenu::item {padding:8px 22px;background:transparent;}
QMenu::item:selected {background:@BRASS_SHADE;color:@BRASS_BRIGHT;}
QMenu::item:disabled {color:@TEXT_OFF;}
QMenu::separator {height:1px;background:@LINE;margin:5px 8px;}

QSplitter::handle {background:transparent;}
QDialogButtonBox QPushButton {min-width:96px;}
'''
    for name in sorted(tokens, key=len, reverse=True):
        sheet = sheet.replace('@' + name, tokens[name])
    return sheet


STYLE = build_style()


# --- Shared widgets ------------------------------------------------------------------------------

class Text(QLabel):
    """A label that starts on the leading edge of its layout, whatever script its text is written in.

    A plain QLabel aligns by the direction of the text, so an English value inside
    an Arabic page would jump to the far side of its row.
    """
    def __init__(self, text='', style=None, wrap=True):
        super().__init__(text)
        self.leading = True
        self.setWordWrap(wrap)
        if style:
            self.setObjectName(style)
        self.follow()

    def setAlignment(self, alignment):
        self.leading = False
        super().setAlignment(alignment)

    def follow(self):
        if self.leading:
            side = Qt.AlignRight if self.layoutDirection() == Qt.RightToLeft else Qt.AlignLeft
            QLabel.setAlignment(self, side | Qt.AlignVCenter | Qt.AlignAbsolute)

    def changeEvent(self, event):
        if event.type() == QEvent.LayoutDirectionChange:
            self.follow()
        super().changeEvent(event)


def label(text, style=None, wrap=True):
    return Text(text, style, wrap)


class Combo(QComboBox):
    """QComboBox whose text follows its own layout direction (a styled combo otherwise follows the application's)."""
    def initStyleOption(self, option):
        super().initStyleOption(option)
        side = Qt.AlignRight if self.layoutDirection() == Qt.RightToLeft else Qt.AlignLeft
        option.textAlignment = side | Qt.AlignVCenter | Qt.AlignAbsolute


class Kicker(QLabel):
    """Small-capitals line. Tracked for Latin only: letter-spacing would break joined Arabic."""
    def __init__(self, text=''):
        super().__init__()
        self.setObjectName('kicker')
        self.setText(text)

    def setText(self, text):
        super().setText(text)
        tracked = not T.has_arabic(text)
        if self.property('tracked') != tracked:
            self.setProperty('tracked', tracked)
            repolish(self)


class Rule(QWidget):
    """Deco divider: a hairline with a brass diamond on the leading end."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(9)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        y = self.height() / 2
        rtl = self.layoutDirection() == Qt.RightToLeft
        start = self.width() - 4.5 if rtl else 4.5
        painter.setPen(QPen(QColor(T.LINE_STRONG), 1))
        painter.drawLine(QPointF(start + (-9 if rtl else 9), y), QPointF(0 if rtl else self.width(), y))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(T.BRASS))
        painter.drawPolygon(QPolygonF([QPointF(start, y - 4), QPointF(start + 4, y), QPointF(start, y + 4), QPointF(start - 4, y)]))


class Plate(QWidget):
    """A small cut-corner tile holding a step numeral or an icon."""
    def __init__(self, text='', icon_name=None, size=36):
        super().__init__()
        self.text = text
        self.icon_name = icon_name
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        paint_panel(painter, self.rect(), T.BRASS_WASH, T.BRASS_DEEP, None, 7)
        if self.icon_name:
            side = self.width() - 14
            painter.drawPixmap(QPointF(7, 7), svg_pixmap('icons/%s.svg' % self.icon_name, side, side, self.devicePixelRatioF(), T.BRASS_BRIGHT))
        else:
            painter.setFont(font(T.DISPLAY, round(self.height() * .5), 600))
            painter.setPen(QColor(T.BRASS_BRIGHT))
            painter.drawText(QRectF(self.rect()).adjusted(0, -1, 0, -1), int(Qt.AlignCenter), self.text)


class Panel(QFrame):
    """The cut-corner card. Optional leading plate, title and description; add content to `body`."""
    def __init__(self, title=None, description=None, step=None, icon_name=None, name='card', margins=(T.PANEL_PAD, 16, T.PANEL_PAD, 18), spacing=12):
        super().__init__()
        self.setObjectName(name)
        self.fill, self.line, self.accent, self.dashed = T.SURFACE, T.LINE, T.BRASS_DEEP, False
        self.pattern = None
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(*margins)
        self.body.setSpacing(spacing)
        self.title_label = None
        if title:
            row = QHBoxLayout()
            row.setSpacing(12)
            if step or icon_name:
                row.addWidget(Plate(step or '', icon_name), 0, Qt.AlignTop)
            copy = QVBoxLayout()
            copy.setSpacing(2)
            self.title_label = label(title, 'cardtitle')
            copy.addWidget(self.title_label)
            if description:
                copy.addWidget(label(description, 'subtitle'))
            row.addLayout(copy, 1)
            self.body.addLayout(row)
        elif description:
            self.body.addWidget(label(description, 'subtitle'))

    def look(self):
        """(fill, line, accent, line width) for the current state; subclasses override."""
        return self.fill, self.line, self.accent, 1.

    def paintEvent(self, event):
        painter = QPainter(self)
        fill, line, accent, width = self.look()
        paint_panel(painter, self.rect(), fill, line, accent, T.CHAMFER, width, self.dashed)
        if self.pattern:
            painter.setClipPath(chamfer(QRectF(self.rect()).adjusted(1, 1, -1, -1)))
            painter.setOpacity(.55)
            painter.drawTiledPixmap(self.rect(), tile(self.pattern, self.devicePixelRatioF()))


def card(title=None, description=None, step=None, icon_name=None):
    """A panel and its content layout."""
    panel = Panel(title, description, step, icon_name)
    return panel, panel.body


class ActionBar(Panel):
    """The pinned bar that carries a page's final action."""
    def __init__(self, name='actionbar', margins=(18, 12, 18, 12), spacing=10):
        super().__init__(name=name, margins=margins, spacing=spacing)
        self.fill, self.line, self.accent = T.SIDEBAR, T.LINE_STRONG, T.BRASS


class Rail(QFrame):
    """The directory rail: lattice texture and a double brass rule on its inner edge."""
    def __init__(self):
        super().__init__()
        self.setObjectName('sidebar')
        self.setFixedWidth(T.RAIL)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(T.SIDEBAR))
        painter.setOpacity(.5)
        painter.drawTiledPixmap(self.rect(), tile('lattice', self.devicePixelRatioF()))
        painter.setOpacity(1)
        edge = 0 if self.layoutDirection() == Qt.RightToLeft else self.width() - 1
        inner = 3 if edge == 0 else self.width() - 4
        painter.fillRect(edge, 0, 1, self.height(), QColor(T.BRASS_DEEP))
        painter.fillRect(inner, 0, 1, self.height(), QColor(T.LINE))


class BrandMark(QWidget):
    def __init__(self, parent=None, size=46):
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, svg_pixmap('brand/emblem.svg', self.width(), self.height(), self.devicePixelRatioF()))


class HintLine(QWidget):
    """One line of guidance under the page title, closed by a deco rule."""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.text_label = label('', 'pageHint')
        layout.addWidget(self.text_label)
        layout.addWidget(Rule())

    def setText(self, text):
        self.text_label.setText(text)

    def text(self):
        return self.text_label.text()


class UtilityHeader(Panel):
    """Lede strip for a utility page: icon plate, kicker, title and one sentence."""
    def __init__(self, index, title, description, tag):
        super().__init__(name='workspaceHeader', margins=(16, 12, 16, 12), spacing=0)
        self.fill = T.SIDEBAR
        self.pattern = 'fan'
        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(Plate(icon_name=NAV_ICONS[index], size=44), 0, Qt.AlignVCenter)
        copy = QVBoxLayout()
        copy.setSpacing(1)
        kicker = Kicker(tag)
        kicker.setLayoutDirection(Qt.LeftToRight)
        copy.addWidget(kicker)
        name = label(title, 'cardtitle')
        copy.addWidget(name)
        row.addLayout(copy)
        detail = label(description, 'subtitle')
        row.addWidget(detail, 1)
        self.body.addLayout(row)


class EmptyState(QWidget):
    """Illustration, one sentence, and nothing else. Floats over an empty list or table."""
    def __init__(self, illustration, title, detail='', parent=None):
        super().__init__(parent)
        self.illustration = illustration
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 12, 24, 12)
        layout.setSpacing(4)
        layout.addStretch()
        self.art = QLabel()
        self.art.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.art)
        self.title = label(title, 'cardtitle')
        self.title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title)
        self.detail = label(detail, 'subtitle')
        self.detail.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.detail)
        layout.addStretch()
        self.fit()

    def set_text(self, title, detail=''):
        self.title.setText(title)
        self.detail.setText(detail)
        self.detail.setVisible(bool(detail))

    def fit(self):
        compact = self.height() < 250
        self.art.setVisible(self.height() >= 150)
        width = 150 if compact else 220
        self.art.setPixmap(svg_pixmap('illustrations/%s.svg' % self.illustration, width, width * .6, self.devicePixelRatioF()))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit()


class Overlay(QObject):
    """Keeps an EmptyState stretched over a view's viewport."""
    def __init__(self, view, state):
        super().__init__(view)
        self.view, self.state = view, state
        state.setParent(view.viewport())
        state.setGeometry(view.viewport().rect())
        view.viewport().installEventFilter(self)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Resize:
            self.state.setGeometry(self.view.viewport().rect())
        return False


def empty_state(view, illustration, title, detail=''):
    state = EmptyState(illustration, title, detail)
    Overlay(view, state)
    state.hide()
    return state


class ArtworkHero(QWidget):
    """Skyline banner with the page's tagline. The artwork sits on the trailing side and mirrors with the layout."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)
        self.page_index = 0
        self.cache = None
        self.copy = QWidget(self)
        layout = QVBoxLayout(self.copy)
        layout.setContentsMargins(26, 12, 26, 18)
        layout.setSpacing(2)
        self.eyebrow = Kicker()
        self.eyebrow.setLayoutDirection(Qt.LeftToRight)
        self.title = label('', 'heroTitle')
        self.description = label('', 'heroDescription')
        layout.addStretch()
        layout.addWidget(self.eyebrow)
        layout.addWidget(self.title)
        layout.addWidget(self.description)
        layout.addStretch()
        self.effect = QGraphicsOpacityEffect(self.copy)
        self.copy.setGraphicsEffect(self.effect)
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(260)
        self.animation.valueChanged.connect(self.effect.setOpacity)

    def set_page(self, index, animate=True):
        self.page_index = index
        eyebrow, title, description, _ = PAGES[index]
        self.eyebrow.setText('DEADLOCK TOOLBOX   /   ' + eyebrow)
        self.eyebrow.setAlignment(Qt.AlignRight if self.layoutDirection() == Qt.RightToLeft else Qt.AlignLeft)
        self.title.setText(title)
        self.description.setText(description)
        self.setFixedHeight(self.banner_height())
        self.cache = None
        self.animation.stop()
        if animate and self.isVisible():
            self.animation.setStartValue(.25)
            self.animation.setEndValue(1.)
            self.animation.start()
        else:
            self.effect.setOpacity(1.)
        self.update()

    def banner_height(self):
        return 104 if self.page_index in (2, 4) else 124

    def resizeEvent(self, event):
        self.cache = None
        rtl = self.layoutDirection() == Qt.RightToLeft
        width = int(self.width() * .56)
        self.copy.setGeometry(self.width() - width if rtl else 0, 0, width, self.height())
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        ratio = self.devicePixelRatioF()
        art_width = self.height() * 1600 / 300
        if self.cache is None or self.cache[0] != (self.page_index, self.height(), ratio):
            self.cache = ((self.page_index, self.height(), ratio), svg_pixmap('art/banner-%s.svg' % PAGES[self.page_index][3], art_width, self.height(), ratio))
        bounds = QRectF(self.rect()).adjusted(.5, .5, -.5, -.5)
        painter.setClipPath(chamfer(bounds))
        painter.fillRect(self.rect(), QColor(T.BASE))
        ground = self.height() * 262 / 300
        painter.fillRect(QRectF(0, ground, self.width(), self.height() - ground), QColor(T.INK))
        painter.fillRect(QRectF(0, ground, self.width(), 1.5), QColor(T.BRASS))
        # The artwork's ground rules and zigzag run on across the calm half.
        scale = self.height() / 300
        painter.setPen(QPen(QColor(T.BRASS_DEEP), 1))
        painter.drawLine(QPointF(0, ground + 6.5 * scale), QPointF(self.width(), ground + 6.5 * scale))
        painter.setPen(QPen(QColor(T.LINE_STRONG), 1))
        zigzag, x, up = QPolygonF(), 0., False
        while x <= self.width() + 8 * scale:
            zigzag.append(QPointF(x, ground + (24 if up else 15) * scale))
            x += 8 * scale
            up = not up
        painter.drawPolyline(zigzag)
        if self.layoutDirection() == Qt.RightToLeft:
            painter.drawPixmap(QPointF(0, 0), self.cache[1])
        else:
            painter.save()
            painter.translate(self.width(), 0)
            painter.scale(-1, 1)
            painter.drawPixmap(QPointF(0, 0), self.cache[1])
            painter.restore()
        painter.setClipping(False)
        paint_panel(painter, self.rect(), None, T.LINE_STRONG, T.BRASS)
