"""The Qt side of the tokens: the current theme, its stylesheet, icons, direction and the title bar.

One `Theme` is current at a time (`current()`). `apply(app, mode, accent, scale)` resolves the theme,
re-applies the stylesheet (the old `design.STYLE` first, then the new components' rules) and tells
every listener, so painted widgets repaint; nothing needs a restart. `mode='system'` follows
`QStyleHints.colorScheme()`.
"""
import sys
import weakref
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap, QTransform, QGuiApplication
from PySide6.QtSvg import QSvgRenderer

from .tokens import Theme, argb

ICONS = Path(__file__).resolve().parents[2] / 'assets' / 'icons2'
if getattr(sys, 'frozen', False):
    ICONS = Path(getattr(sys, '_MEIPASS', '.')) / 'assets' / 'icons2'
MIRRORED = ('chev', 'back', 'ext')       # icons that point somewhere flip in right-to-left
STYLE_FILE = Path(__file__).with_name('style.qss')

_current = Theme('dark')
_choice = ('dark', 'blue', 100)
_listeners = []
_watched = weakref.WeakKeyDictionary()     # widget → name of the method to call after a switch
_icons = {}
_base_style = ''


def current():
    return _current


def choice():
    """What the user chose: (mode, accent, scale); mode may be 'system'."""
    return _choice


def color(name):
    """A token colour as a QColor (alpha handled)."""
    return QColor(argb(_current[name]))


def on_change(callback):
    """Call `callback(theme)` after every theme switch. Returns the callback (usable as a decorator)."""
    _listeners.append(callback)
    return callback


def watch(widget, method):
    """Call `widget.<method>()` after every theme switch, for as long as the widget lives."""
    _watched[widget] = method


def system_mode():
    app = QGuiApplication.instance()
    try:
        scheme = app.styleHints().colorScheme() if app else None
        return 'light' if scheme == Qt.ColorScheme.Light else 'dark'
    except AttributeError:
        return 'dark'


def font_rule(theme):
    """The text face of every widget. The Arabic face has no Latin letters of its own and doubles the line height of English
    text, so in a left-to-right language the Latin faces come first (IBM Plex has both scripts; the bundled Noto faces do not)."""
    from .. import i18n
    names = theme.families()
    if not i18n.rtl():
        names = [n for n in names if 'Arabic' not in n] + [n for n in names if 'Arabic' in n]
    return 'QWidget { font-family: %s; }' % ', '.join('"%s"' % n for n in names)


def stylesheet(theme=None):
    """The new components' stylesheet for a theme (the template with every placeholder filled)."""
    theme = theme or _current
    return font_rule(theme) + chr(10) + theme.render(STYLE_FILE.read_text(encoding='utf-8'))


def set_base_style(text):
    """The old system's stylesheet, kept in front of the new rules until Phase 3 removes it."""
    global _base_style
    _base_style = text


def apply(app=None, mode=None, accent=None, scale=None):
    """Switch theme, accent or text size; re-applies the stylesheet at once."""
    global _current, _choice
    mode = mode or _choice[0]
    accent = accent or _choice[1]
    scale = scale or _choice[2]
    resolved = system_mode() if mode == 'system' else mode
    _current = Theme(resolved, accent, scale)
    _choice = (mode, accent, scale)
    _icons.clear()
    app = app or QGuiApplication.instance()
    if app is not None and hasattr(app, 'setStyleSheet'):
        app.setStyleSheet(_base_style + '\n' + stylesheet(_current))
        for window in app.topLevelWidgets() if hasattr(app, 'topLevelWidgets') else []:
            if window.isVisible() and window.windowType() in (Qt.Window, Qt.Dialog):
                dark_title_bar(window, resolved == 'dark')
    for callback in list(_listeners):
        callback(_current)
    for widget, method in list(_watched.items()):
        try:
            getattr(widget, method)()
        except RuntimeError:        # the Qt object is already gone
            pass
    return _current


def apply_direction(app, rtl):
    app.setLayoutDirection(Qt.RightToLeft if rtl else Qt.LeftToRight)


def icon(name, token='color.text.secondary', size=20, rtl=None):
    """A redesign line icon tinted with a token colour; `chev`, `back` and `ext` mirror in right-to-left."""
    if rtl is None:
        app = QGuiApplication.instance()
        rtl = bool(app) and app.layoutDirection() == Qt.RightToLeft
    key = (name, _current[token], size, rtl and name in MIRRORED)
    if key not in _icons:
        source = (ICONS / (name + '.svg')).read_text(encoding='utf-8')
        result = QIcon()
        for mode, colour in ((QIcon.Normal, _current[token]), (QIcon.Disabled, _current['color.text.disabled'])):
            svg = source.replace('currentColor', colour[:7])
            for ratio in (1, 2, 3):
                pixmap = QPixmap(size * ratio, size * ratio)
                pixmap.fill(Qt.transparent)
                renderer = QSvgRenderer(QByteArray(svg.encode('utf-8')))
                painter = QPainter(pixmap)
                painter.setRenderHint(QPainter.Antialiasing)
                renderer.render(painter, QRectF(0, 0, pixmap.width(), pixmap.height()))
                painter.end()
                if key[3]:
                    pixmap = pixmap.transformed(QTransform().scale(-1, 1))
                pixmap.setDevicePixelRatio(ratio)
                result.addPixmap(pixmap, mode)
        _icons[key] = result
    return _icons[key]


def icon_names():
    return sorted(p.stem for p in ICONS.glob('*.svg'))


def dark_title_bar(window, dark):
    """Windows only: ask DWM for a dark or light native title bar. Silently does nothing elsewhere."""
    if sys.platform != 'win32' or not hasattr(window, 'winId'):
        return False
    try:
        import ctypes
        value = ctypes.c_int(1 if dark else 0)
        for attribute in (20, 19):          # DWMWA_USE_IMMERSIVE_DARK_MODE (new, then old builds)
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(int(window.winId()), attribute, ctypes.byref(value), ctypes.sizeof(value)) == 0:
                return True
    except Exception:
        pass
    return False
