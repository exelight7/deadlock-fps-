"""What the application needs before any window exists: the bundled fonts, a palette for the widgets a stylesheet does not reach, and the emblem.

Replaces the parts of the old `design.py` that are still used. Colours come from the design tokens (`shell/tokens.json`), never from constants here.
"""
from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QFontDatabase, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

from ..core import ASSETS
from .tokens import Theme, argb

FONT_FILES = ('NotoSansArabic.ttf', 'NotoSans.ttf', 'ReemKufi.ttf')
_fonts_loaded = False


def load_fonts():
    """Register the bundled faces once. Safe before any window exists and safe to repeat."""
    global _fonts_loaded
    if not _fonts_loaded and QApplication.instance() is not None:
        _fonts_loaded = True
        for name in FONT_FILES:
            QFontDatabase.addApplicationFont(str(ASSETS / 'fonts' / name))


def dark_palette():
    """Palette for what a stylesheet does not reach (native-looking dialogs, item views), from the dark tokens."""
    t = Theme('dark')
    palette = QPalette()
    for role, token in [(QPalette.Window, 'color.bg.app'), (QPalette.WindowText, 'color.text.primary'), (QPalette.Base, 'color.bg.sunken'),
                        (QPalette.AlternateBase, 'color.bg.surface'), (QPalette.Text, 'color.text.primary'), (QPalette.Button, 'color.bg.surface'),
                        (QPalette.ButtonText, 'color.text.primary'), (QPalette.ToolTipBase, 'color.bg.raised'), (QPalette.ToolTipText, 'color.text.primary'),
                        (QPalette.Highlight, 'color.accent.fill'), (QPalette.HighlightedText, 'color.text.on-accent'), (QPalette.Link, 'color.text.link'),
                        (QPalette.PlaceholderText, 'color.text.muted'), (QPalette.Light, 'color.border.control'), (QPalette.Midlight, 'color.border.default'),
                        (QPalette.Mid, 'color.border.default'), (QPalette.Dark, 'color.bg.sunken'), (QPalette.Shadow, 'color.bg.sidebar'),
                        (QPalette.BrightText, 'color.text.primary')]:
        palette.setColor(role, QColor(argb(t[token])))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        palette.setColor(QPalette.Disabled, role, QColor(argb(t['color.text.disabled'])))
    return palette


def brand_logo(size=160):
    """The emblem as a pixmap."""
    try:
        source = (ASSETS / 'brand/emblem.svg').read_text(encoding='utf-8')
    except OSError:
        source = ''
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    renderer = QSvgRenderer(QByteArray(source.encode('utf-8')))
    if renderer.isValid():
        painter = QPainter(pixmap)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        renderer.render(painter, QRectF(0, 0, size, size))
        painter.end()
    return pixmap
