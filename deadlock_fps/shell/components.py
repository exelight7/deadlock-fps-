"""Base widgets of the redesign, with exactly the names, variants and states of vault/Design/New Design/04 Components.md.

Every widget sets a `component` property (its name); `variant`, `size` and `state` are dynamic
properties matched by shell/style.qss. Change them with `set_props(widget, variant=..., state=...)`,
which re-polishes the widget. Painted widgets read colours from `theme.color(...)` and repaint on a
theme switch. Phase 2 builds the parts; Phase 3 builds the pages from them.
"""
from PySide6.QtCore import QEasingCurve, QPointF, QPropertyAnimation, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen
from PySide6.QtWidgets import (QAbstractButton, QAbstractItemView, QCheckBox, QComboBox, QDialog, QFrame, QGraphicsDropShadowEffect,
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMenu, QProgressBar, QPushButton, QScrollArea,
                               QSizePolicy, QTableWidget, QToolButton, QVBoxLayout, QWidget)

from ..i18n import tr
from . import theme

COMPONENTS = ('Button', 'IconButton', 'LinkButton', 'Menu', 'TextField', 'SearchField', 'PathField', 'Select', 'Checkbox', 'Switch',
              'SegmentedControl', 'Slider', 'Chip', 'Card', 'DoorCard', 'ModCard', 'StatTile', 'Tabs', 'Sidebar', 'NavItem', 'TopBar',
              'GamePill', 'ActionBar', 'Sheet', 'Dialog', 'DataTable', 'List', 'ListRow', 'KeyValue', 'Badge', 'Bar', 'ConfidenceBar',
              'Banner', 'Toast', 'ProgressBar', 'Spinner', 'Skeleton', 'EmptyState', 'Tooltip')
BUTTON_VARIANTS = ('primary', 'secondary', 'ghost', 'danger', 'danger-quiet')
SIZES = ('sm', 'md', 'lg')
BADGE_VARIANTS = ('neutral', 'success', 'warning', 'danger', 'info', 'count')
BANNER_VARIANTS = ('info', 'success', 'warning', 'danger')
_ICON_TOKEN = {'primary': 'color.text.on-accent', 'danger': 'color.text.on-accent', 'danger-quiet': 'color.danger.text'}


def set_props(widget, **props):
    """Set dynamic properties (variant, size, state, ...) and re-polish so the stylesheet follows."""
    for name, value in props.items():
        widget.setProperty(name, value)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def mark(widget, component, **props):
    widget.setProperty('component', component)
    for name, value in props.items():
        if value is not None:
            widget.setProperty(name, value)
    return widget


def text_label(text, component, plain=True, wrap=True):
    """A label for any text; text from outside the app is always shown as plain text."""
    lab = mark(QLabel(text), component)
    if plain:
        lab.setTextFormat(Qt.PlainText)
    lab.setWordWrap(wrap)
    return lab


def breakable(text, longest=24):
    """Let a long unbroken word (an address, a file name) wrap: a zero-width space after its separators. Short words are left alone.

    A wrapped label cannot be narrower than its longest word, so one long address would otherwise widen a whole panel."""
    out = []
    for word in text.split(' '):
        if len(word) > longest:
            for mark_ in '/.-_?&=:':
                word = word.replace(mark_, mark_ + '​')
        out.append(word)
    return ' '.join(out)


def _shadow(widget, blur, offset):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, offset)
    effect.setColor(theme.color('color.shadow'))
    widget.setGraphicsEffect(effect)
    return effect


class _Painted(QWidget):
    """Base for painted widgets: repaint after a theme switch."""
    def __init__(self, component, parent=None):
        super().__init__(parent)
        mark(self, component)
        theme.watch(self, 'update')


# --- Actions ------------------------------------------------------------------------------------

class Button(QPushButton):
    def __init__(self, text='', variant='secondary', size='md', icon=None, parent=None):
        if variant not in BUTTON_VARIANTS or size not in SIZES:
            raise ValueError('unknown button variant or size')
        super().__init__(text, parent)
        mark(self, 'Button', variant=variant, size=size)
        self.icon_name = icon
        self.busy = False
        self.setCursor(Qt.PointingHandCursor)
        self._spinner = None
        self._label = text
        self.refresh_icon()
        theme.watch(self, 'refresh_icon')

    def refresh_icon(self):
        if self.icon_name:
            self.setIcon(theme.icon(self.icon_name, _ICON_TOKEN.get(self.property('variant'), 'color.text.primary'), 16))
            self.setIconSize(QSize(16, 16))

    def set_variant(self, variant):
        set_props(self, variant=variant)
        self.refresh_icon()

    def set_busy(self, busy):
        """Busy: disabled, keeps its width, shows a Spinner in place of the icon."""
        self.busy = bool(busy)
        self.setEnabled(not busy)
        set_props(self, state='busy' if busy else None)
        if busy and self._spinner is None:
            self._spinner = Spinner(self)
            self._spinner.move(8, (self.height() - 16) // 2)
        if self._spinner:
            self._spinner.setVisible(self.busy)



class IconButton(QToolButton):
    def __init__(self, icon, name, variant='secondary', size='md', parent=None):
        if not name:
            raise ValueError('an icon-only button needs an accessible name')
        super().__init__(parent)
        mark(self, 'IconButton', variant=variant, size=size)
        self.icon_name = icon
        self.setAccessibleName(name)
        self.setToolTip(name)
        self.setCursor(Qt.PointingHandCursor)
        self.refresh_icon()
        theme.watch(self, 'refresh_icon')

    def refresh_icon(self):
        px = 16 if self.property('size') == 'sm' else 20
        self.setIcon(theme.icon(self.icon_name, 'color.text.secondary', px))
        self.setIconSize(QSize(px, px))


class LinkButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        mark(self, 'LinkButton')
        self.setCursor(Qt.PointingHandCursor)
        self.setFlat(True)
        self.setLayoutDirection(Qt.LeftToRight if self.isLeftToRight() else Qt.RightToLeft)
        self.setIcon(theme.icon('chev', 'color.text.link', 16))


class Menu(QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        mark(self, 'Menu')
        self.setAttribute(Qt.WA_TranslucentBackground, False)

    def add(self, text, callback, icon=None, danger=False):
        """An item; a danger item comes last, after a separator."""
        if danger:
            self.addSeparator()
        action = self.addAction(text)
        if icon:
            action.setIcon(theme.icon(icon, 'color.danger.text' if danger else 'color.text.secondary', 16))
        action.triggered.connect(callback)
        return action


# --- Inputs ------------------------------------------------------------------------------------

class TextField(QWidget):
    """A line edit with an optional label above and help below; `set_error(text)` shows the error state."""
    def __init__(self, label='', help='', placeholder='', icon=None, parent=None, component='TextField'):
        super().__init__(parent)
        mark(self, component)
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(4)
        self.label = text_label(label, 'FieldLabel') if label else None
        if self.label:
            box.addWidget(self.label)
        self.edit = mark(QLineEdit(), component)
        self.edit.setPlaceholderText(placeholder)
        if icon:
            self.edit.addAction(theme.icon(icon, 'color.text.muted', 16), QLineEdit.LeadingPosition)
        box.addWidget(self.edit)
        self.help_text = help
        self.help = text_label(help, 'FieldHelp')
        self.help.setVisible(bool(help))
        box.addWidget(self.help)
        if self.label:
            self.label.setBuddy(self.edit)
        self.setFocusProxy(self.edit)

    def text(self):
        return self.edit.text()

    def setText(self, text):
        self.edit.setText(text)

    def set_error(self, message=''):
        set_props(self.edit, state='error' if message else None)
        set_props(self.help, state='error' if message else None)
        self.help.setText(message or self.help_text)
        self.help.setVisible(bool(message or self.help_text))


class SearchField(TextField):
    """Filters as you type; Esc clears; a clear button shows when not empty."""
    def __init__(self, placeholder='', parent=None):
        super().__init__(placeholder=placeholder, icon='search', parent=parent, component='SearchField')
        self.edit.setClearButtonEnabled(True)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self.edit.text():
            self.edit.clear()
            return
        super().keyPressEvent(event)


class PathField(TextField):
    """A folder path: monospace, always left-to-right."""
    def __init__(self, placeholder='', parent=None):
        super().__init__(placeholder=placeholder, icon='folder', parent=parent, component='PathField')
        self.edit.setLayoutDirection(Qt.LeftToRight)
        font = QFont()
        font.setFamilies(theme.current().families('font.family.mono'))
        self.edit.setFont(font)


class Select(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        mark(self, 'Select')


class Checkbox(QCheckBox):
    def __init__(self, text='', parent=None):
        super().__init__(text, parent)
        mark(self, 'Checkbox')


class Switch(QAbstractButton):
    """A 36 × 20 pill; off at the leading side, on at the trailing side (mirrors in right-to-left)."""
    def __init__(self, text='', parent=None):
        super().__init__(parent)
        mark(self, 'Switch')
        self.setCheckable(True)
        self.setText(text)
        self.setAccessibleName(text)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self._pos = 0.
        self._anim = QPropertyAnimation(self, b'pos_value', self)
        self._anim.setDuration(theme.current().ms('motion.fast'))
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self._animate)
        theme.watch(self, 'update')

    def _animate(self, on):
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1. if on else 0.)
        self._anim.start()

    def _get(self):
        return self._pos

    def _set(self, value):
        self._pos = value
        self.update()

    from PySide6.QtCore import Property as _Property
    pos_value = _Property(float, _get, _set)

    def sizeHint(self):
        width = 36 + (8 + self.fontMetrics().horizontalAdvance(self.text()) if self.text() else 0) + 8
        return QSize(width, 28)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rtl = self.layoutDirection() == Qt.RightToLeft
        track = QRectF(self.width() - 40 if rtl else 4, (self.height() - 20) / 2, 36, 20)
        on = self.isChecked()
        p.setPen(Qt.NoPen if on else QPen(theme.color('color.border.control'), 1))
        p.setBrush(theme.color('color.accent.fill') if on else theme.color('color.bg.sunken'))
        p.drawRoundedRect(track, 10, 10)
        t = self._pos if not rtl else 1 - self._pos
        knob = QPointF(track.left() + 10 + t * 16, track.center().y())
        p.setPen(Qt.NoPen)
        p.setBrush(QColor('#FFFFFF') if on else theme.color('color.text.muted'))
        p.drawEllipse(knob, 7, 7)
        if self.hasFocus():
            p.setPen(QPen(theme.color('color.border.focus'), 2))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(track.adjusted(-3, -3, 3, 3), 13, 13)
        if self.text():
            p.setPen(theme.color('color.text.primary') if self.isEnabled() else theme.color('color.text.disabled'))
            text_rect = QRectF(0, 0, self.width() - 48, self.height()) if rtl else QRectF(48, 0, self.width() - 48, self.height())
            p.drawText(text_rect, Qt.AlignVCenter | (Qt.AlignRight if rtl else Qt.AlignLeft), self.text())


class SegmentedControl(QFrame):
    """2 to 4 short choices; emits `changed(key)`."""
    changed = Signal(str)

    def __init__(self, choices, parent=None):
        super().__init__(parent)
        if not 2 <= len(choices) <= 4:
            raise ValueError('a segmented control has 2 to 4 choices')
        mark(self, 'SegmentedControl')
        row = QHBoxLayout(self)
        row.setContentsMargins(3, 3, 3, 3)
        row.setSpacing(2)
        self.buttons = {}
        for key, text in choices:
            b = mark(QPushButton(text), 'Segment')
            b.setCheckable(True)
            b.setAutoExclusive(True)
            b.clicked.connect(lambda _=False, k=key: self.changed.emit(k))
            row.addWidget(b)
            self.buttons[key] = b
        next(iter(self.buttons.values())).setChecked(True)

    def value(self):
        """The chosen key, or None when `set_value(None)` left every segment off (a custom value between presets)."""
        return next((k for k, b in self.buttons.items() if b.isChecked()), None)

    def set_value(self, key):
        if key is None:
            for b in self.buttons.values():
                b.setAutoExclusive(False)
                b.setChecked(False)
                b.setAutoExclusive(True)
            return
        self.buttons[key].setChecked(True)


class Slider(_Painted):
    """4 px track, accent fill from the leading side, 18 px knob. Arrow keys step, Page keys step by ten."""
    valueChanged = Signal(int)

    def __init__(self, minimum=0, maximum=100, value=0, parent=None):
        super().__init__('Slider', parent)
        self.minimum, self.maximum, self._value = minimum, maximum, value
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumHeight(28)
        self.setCursor(Qt.PointingHandCursor)

    def value(self):
        return self._value

    def setValue(self, value):
        value = max(self.minimum, min(self.maximum, int(value)))
        if value != self._value:
            self._value = value
            self.valueChanged.emit(value)
            self.update()

    def _fraction(self):
        span = self.maximum - self.minimum
        return (self._value - self.minimum) / span if span else 0.

    def keyPressEvent(self, event):
        steps = {Qt.Key_Right: 1, Qt.Key_Up: 1, Qt.Key_Left: -1, Qt.Key_Down: -1, Qt.Key_PageUp: 10, Qt.Key_PageDown: -10}
        if event.key() in steps:
            step = steps[event.key()]
            if event.key() in (Qt.Key_Left, Qt.Key_Right) and self.layoutDirection() == Qt.RightToLeft:
                step = -step
            self.setValue(self._value + step)
        elif event.key() == Qt.Key_Home:
            self.setValue(self.minimum)
        elif event.key() == Qt.Key_End:
            self.setValue(self.maximum)
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        self._seek(event.position().x())

    def mouseMoveEvent(self, event):
        self._seek(event.position().x())

    def _seek(self, x):
        width = max(1, self.width() - 20)
        t = min(1., max(0., (x - 10) / width))
        if self.layoutDirection() == Qt.RightToLeft:
            t = 1 - t
        self.setValue(round(self.minimum + t * (self.maximum - self.minimum)))

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rtl = self.layoutDirection() == Qt.RightToLeft
        y = self.height() / 2
        track = QRectF(10, y - 2, self.width() - 20, 4)
        p.setPen(Qt.NoPen)
        p.setBrush(theme.color('color.bg.sunken'))
        p.drawRoundedRect(track, 2, 2)
        filled = track.width() * self._fraction()
        fill = QRectF(track.right() - filled if rtl else track.left(), track.top(), filled, 4)
        p.setBrush(theme.color('color.accent.fill') if self.isEnabled() else theme.color('color.text.disabled'))
        p.drawRoundedRect(fill, 2, 2)
        x = fill.left() if rtl else fill.right()
        p.setBrush(QColor('#FFFFFF'))
        p.setPen(QPen(theme.color('color.border.focus') if self.hasFocus() else theme.color('color.accent.fill'), 2))
        p.drawEllipse(QPointF(x, y), 8, 8)


class Chip(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        mark(self, 'Chip')
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.toggled.connect(lambda on: self.setIcon(theme.icon('check', 'color.accent.text', 16) if on else QIcon()))


# --- Containers ----------------------------------------------------------------------------------

class Card(QFrame):
    """`plain` (title, one sentence, then `body`), `flat` (no padding; holds a table or a list), `clickable` (emits `clicked`)."""
    clicked = Signal()

    def __init__(self, title='', text='', variant='plain', parent=None, component='Card'):
        super().__init__(parent)
        mark(self, component, variant=variant, clickable='true' if variant == 'clickable' else 'false')
        t = theme.current()
        self.body = QVBoxLayout(self)
        pad = 0 if variant == 'flat' else t.px('space.5')
        self.body.setContentsMargins(pad, pad, pad, pad)
        self.body.setSpacing(t.px('space.2'))
        self.title = text_label(title, 'CardTitle') if title else None
        self.text = text_label(text, 'CardText') if text else None
        for part in (self.title, self.text):
            if part:
                self.body.addWidget(part)
        if variant == 'clickable':
            self.setCursor(Qt.PointingHandCursor)
            self.setFocusPolicy(Qt.StrongFocus)

    def mouseReleaseEvent(self, event):
        if self.property('variant') == 'clickable' and event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if self.property('variant') == 'clickable' and event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.clicked.emit()
            return
        super().keyPressEvent(event)


class DoorCard(Card):
    """Home only: a 40 px tinted icon, the name, one status line, an action line. Dimmed when `set_available(False)`."""
    def __init__(self, icon, title, status='', action='', parent=None):
        super().__init__(variant='clickable', parent=parent, component='DoorCard')
        head = QHBoxLayout()
        head.setSpacing(12)
        plate = mark(QLabel(), 'DoorIcon')
        plate.setFixedSize(40, 40)
        plate.setAlignment(Qt.AlignCenter)
        plate.setPixmap(theme.icon(icon, 'color.accent.text', 20).pixmap(20, 20))
        head.addWidget(plate)
        self.title = text_label(title, 'CardTitle')
        head.addWidget(self.title, 1)
        self.body.addLayout(head)
        self.status = text_label(status, 'CardText')
        self.body.addWidget(self.status)
        self.body.addStretch(1)
        self.action = LinkButton(action) if action else None
        if self.action:
            self.action.clicked.connect(self.clicked.emit)
            self.body.addWidget(self.action, 0, Qt.AlignLeading)

    def set_available(self, available):
        effect = None
        if not available:
            from PySide6.QtWidgets import QGraphicsOpacityEffect
            effect = QGraphicsOpacityEffect(self)
            effect.setOpacity(.55)
        self.setGraphicsEffect(effect)


class ElidedLabel(QLabel):
    """One line of plain text that is cut with '…' instead of widening its card. `text()` is the whole text; the tooltip shows it when cut."""
    def __init__(self, text, component, parent=None):
        super().__init__(parent)
        mark(self, component)
        self.setTextFormat(Qt.PlainText)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumWidth(0)
        self._full = ''
        self.setText(text)

    def text(self):
        return self._full

    def setText(self, text):
        self._full = text
        self._fit()

    def _fit(self):
        width = self.contentsRect().width()
        shown = self.fontMetrics().elidedText(self._full, Qt.ElideRight, width) if width > 0 else self._full
        super().setText(shown)
        self.setToolTip(self._full if shown != self._full else '')

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit()


class ModCard(Card):
    """A 16:9 picture area, the name on one line, then 'type · author'. `set_selected` while its sheet is open.

    The picture area holds a quiet box icon until `set_picture` is given a real picture (pictures are off by default)."""
    def __init__(self, name, line='', installed=False, parent=None):
        super().__init__(variant='clickable', parent=parent, component='ModCard')
        self.body.setContentsMargins(0, 0, 0, 12)
        self.picture = mark(QLabel(), 'ModPicture')
        self.picture.setMinimumHeight(90)
        self.picture.setAlignment(Qt.AlignCenter)
        self.picture.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.body.addWidget(self.picture)
        self.installed = Badge(tr('Installed'), 'success', parent=self.picture) if installed else None
        self.name = ElidedLabel(name, 'CardTitle')
        self.name.setContentsMargins(12, 0, 12, 0)
        self.body.addWidget(self.name)
        self.line = ElidedLabel(line, 'Muted')
        self.line.setContentsMargins(12, 0, 12, 0)
        self.body.addWidget(self.line)
        self.has_picture = False
        self.refresh_icon()
        theme.watch(self, 'refresh_icon')

    def refresh_icon(self):
        if not self.has_picture:
            self.picture.setPixmap(theme.icon('box', 'color.text.muted', 24).pixmap(24, 24))

    def set_picture(self, pixmap):
        """A real picture, cropped to fill the 16:9 area."""
        self.has_picture = True
        self.picture.setScaledContents(False)
        self._picture_source = pixmap
        self.fit_picture()

    def fit_picture(self):
        if self.has_picture and self.picture.width() > 0:
            cut = self._picture_source.scaled(self.picture.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self.picture.setPixmap(cut)

    def place_badge(self):
        if self.installed is not None:
            self.installed.adjustSize()
            gap = 8
            x = gap if self.picture.layoutDirection() == Qt.RightToLeft else self.picture.width() - self.installed.width() - gap
            self.installed.move(max(0, x), gap)

    def resizeEvent(self, event):
        self.picture.setFixedHeight(int(self.width() * 9 / 16))
        super().resizeEvent(event)
        self.place_badge()
        self.fit_picture()

    def set_selected(self, selected):
        set_props(self, state='selected' if selected else None)



class StatTile(Card):
    def __init__(self, value, label, parent=None):
        super().__init__(parent=parent, component='StatTile')
        self.value = text_label(value, 'StatValue', wrap=False)
        self.value.setLayoutDirection(Qt.LeftToRight)
        self.body.addWidget(self.value)
        self.label = text_label(label, 'Muted')
        self.body.addWidget(self.label)

    def set_value(self, value):
        self.value.setText(value)


class Tabs(QFrame):
    """Text tabs with an accent underline on the current one. Emits `changed(id)`; Ctrl+Tab moves on."""
    changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        mark(self, 'Tabs')
        self.row = QHBoxLayout(self)
        self.row.setContentsMargins(0, 0, 0, 0)
        self.row.setSpacing(4)
        self.row.addStretch()
        self.buttons = {}

    def set_tabs(self, tabs):
        """`tabs` is a list of (id, title). Replaces the current tabs."""
        for b in self.buttons.values():
            self.row.removeWidget(b)
            b.hide()
            b.setParent(None)
            b.deleteLater()
        self.buttons = {}
        for position, (key, title) in enumerate(tabs):
            b = mark(QPushButton(title), 'Tab')
            font = b.font()
            font.setWeight(QFont.Medium)       # set here, not in the stylesheet, so the width Qt measures fits the text
            b.setFont(font)
            b.setMinimumWidth(b.fontMetrics().horizontalAdvance(title) + 2 * theme.current().px('space.3') + 8)
            b.setCheckable(True)
            b.setAutoExclusive(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=key: self.changed.emit(k))
            self.row.insertWidget(position, b)
            self.buttons[key] = b

    def set_current(self, key):
        if key in self.buttons:
            self.buttons[key].setChecked(True)

    def current(self):
        return next((k for k, b in self.buttons.items() if b.isChecked()), None)

    def step(self, delta):
        keys = list(self.buttons)
        if keys:
            here = keys.index(self.current()) if self.current() in keys else 0
            self.changed.emit(keys[(here + delta) % len(keys)])


class Sidebar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        mark(self, 'Sidebar')
        t = theme.current()
        self.setFixedWidth(t.px('size.sidebar'))
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(t.px('space.3'), t.px('space.4'), t.px('space.3'), t.px('space.3'))
        self.box.setSpacing(2)


class NavItem(QPushButton):
    """A sidebar entry: icon and label; `set_count(n)` shows a count badge, `set_dot(True)` a news dot."""
    def __init__(self, page_id, title, icon, parent=None):
        super().__init__(title, parent)
        mark(self, 'NavItem')
        self.page_id = page_id
        self.icon_name = icon
        self.title = title
        self.badged = False
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setIconSize(QSize(20, 20))
        self.toggled.connect(lambda _on: self.refresh_icon())
        self.refresh_icon()
        theme.watch(self, 'refresh_icon')

    def refresh_icon(self):
        self.setIcon(theme.icon(self.icon_name, 'color.accent.text' if self.isChecked() else 'color.text.secondary', 20))

    def set_dot(self, on):
        """News (for example an update is available): a trailing ' •' the way the old rail showed it."""
        self.badged = bool(on)
        self.setText(self.title + (' •' if on else ''))


class TopBar(QFrame):
    """Optional Back, the page name, then (trailing) whatever `add_trailing` puts there, e.g. the GamePill."""
    back = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        mark(self, 'TopBar')
        t = theme.current()
        self.setMinimumHeight(t.px('size.topbar'))
        self.row = QHBoxLayout(self)
        self.row.setContentsMargins(0, 0, 0, 0)
        self.row.setSpacing(t.px('space.3'))
        self.back_button = IconButton('back', tr('رجوع'), 'ghost')
        self.back_button.clicked.connect(self.back.emit)
        self.back_button.hide()
        self.row.addWidget(self.back_button)
        self.title = text_label('', 'PageTitle', wrap=False)
        self.row.addWidget(self.title, 1)

    def set_title(self, text):
        self.title.setText(text)

    def add_trailing(self, widget):
        self.row.addWidget(widget, 0, Qt.AlignVCenter)


class GamePill(QPushButton):
    """Says whether the game is linked: state `none`, `linked` or `running`."""
    def __init__(self, text='', parent=None):
        super().__init__(text, parent)
        mark(self, 'GamePill', state='none')
        self.setCursor(Qt.PointingHandCursor)

    def set_state(self, state, text):
        set_props(self, state=state)
        self.setText(text)


class ActionBar(QFrame):
    """Pinned to the bottom of a page: summary at the leading side, buttons at the trailing side, primary last."""
    def __init__(self, parent=None):
        super().__init__(parent)
        mark(self, 'ActionBar')
        t = theme.current()
        self.row = QHBoxLayout(self)
        self.row.setContentsMargins(t.px('space.4'), t.px('space.3'), t.px('space.4'), t.px('space.3'))
        self.row.setSpacing(t.px('space.2'))
        self.summary = text_label('', 'CardText')
        self.row.addWidget(self.summary, 1)

    def add(self, button):
        self.row.addWidget(button)
        return button


class Sheet(QFrame):
    """A panel that slides in from the trailing edge over a page (not the sidebar). Esc or the close button closes it."""
    closed = Signal()

    def __init__(self, host, title='', parent=None):
        super().__init__(parent or host)
        mark(self, 'Sheet')
        self.host = host
        t = theme.current()
        self.setFixedWidth(t.px('size.sheet') * t.scale // 100)         # grows with the text size, so the same words fit
        _shadow(self, 56, 20)
        box = QVBoxLayout(self)
        box.setContentsMargins(t.px('space.5'), t.px('space.4'), t.px('space.5'), t.px('space.4'))
        head = QHBoxLayout()
        self.title = text_label(title, 'DialogTitle')
        head.addWidget(self.title, 1)
        close = IconButton('x', tr('إغلاق'), 'ghost', 'sm')
        close.clicked.connect(self.close_sheet)
        head.addWidget(close)
        box.addLayout(head)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget()
        self.body = QVBoxLayout(inner)
        gap = t.px('space.3')                                  # keeps the content off the scroll bar, which sits at the trailing edge
        rtl = host.layoutDirection() == Qt.RightToLeft
        self.body.setContentsMargins(gap if rtl else 0, 0, 0 if rtl else gap, 0)
        self.scroll.setWidget(inner)
        box.addWidget(self.scroll, 1)
        self.foot = QHBoxLayout()
        box.addLayout(self.foot)
        self.hide()

    def reposition(self):
        """Stick to the trailing edge of the host, full height (call again when the host is resized)."""
        rtl = self.host.layoutDirection() == Qt.RightToLeft
        self.setGeometry(0 if rtl else self.host.width() - self.width(), 0, self.width(), self.host.height())

    def open_sheet(self):
        self.reposition()
        self.show()
        self.raise_()
        self.setFocus()

    def close_sheet(self):
        self.hide()
        self.closed.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close_sheet()
            return
        super().keyPressEvent(event)


class Dialog(QDialog):
    """`confirm` (440 wide: a question, one or two sentences, Cancel + action) or `review` (600 wide: facts, then the action)."""
    def __init__(self, title, text='', variant='confirm', action='', cancel='', danger=False, parent=None):
        super().__init__(parent)
        mark(self, 'Dialog', variant=variant)
        t = theme.current()
        self.setModal(True)
        self.setWindowTitle(title)
        self.setMinimumWidth(t.px('size.dialog.md' if variant == 'review' else 'size.dialog.sm'))
        box = QVBoxLayout(self)
        box.setContentsMargins(t.px('space.6'), t.px('space.5'), t.px('space.6'), t.px('space.5'))
        box.setSpacing(t.px('space.3'))
        box.addWidget(text_label(title, 'DialogTitle'))
        if text:
            box.addWidget(text_label(text, 'CardText'))
        self.body = QVBoxLayout()
        box.addLayout(self.body, 1)
        row = QHBoxLayout()
        row.addStretch()
        self.cancel_button = Button(cancel or tr('إلغاء'), 'secondary')
        self.cancel_button.clicked.connect(self.reject)
        row.addWidget(self.cancel_button)
        self.action_button = Button(action, 'danger' if danger else 'primary') if action else None
        if self.action_button:
            self.action_button.clicked.connect(self.accept)
            self.action_button.setDefault(True)
            row.addWidget(self.action_button)
        box.addLayout(row)

    def showEvent(self, event):
        super().showEvent(event)
        layout = self.layout()
        layout.activate()
        needed = layout.totalHeightForWidth(self.width())          # wrapped text needs more height than the one-line size hints add up to
        if needed > self.height():
            self.resize(self.width(), needed)


def confirm(parent, title, text, action, danger=False, cancel=''):
    """A confirm Dialog (440 wide: a question, one or two sentences, Cancel and the action). True when the action was pressed."""
    dialog = Dialog(title, text, 'confirm', action, cancel or tr('Cancel'), danger, parent)
    return dialog.exec() == QDialog.Accepted


# --- Data ------------------------------------------------------------------------------------------

class DataTable(QTableWidget):
    """Rows at least 44 high, no vertical lines, header muted; number columns align to the trailing side."""
    def __init__(self, headers, numeric=(), parent=None):
        super().__init__(0, len(headers), parent)
        mark(self, 'DataTable')
        self.numeric = set(numeric)
        self.setHorizontalHeaderLabels(headers)
        self.verticalHeader().hide()
        self.verticalHeader().setDefaultSectionSize(44)
        self.setShowGrid(False)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.horizontalHeader().setDefaultAlignment(Qt.AlignLeading | Qt.AlignVCenter)
        for column in self.numeric:
            item = self.horizontalHeaderItem(column)
            if item:
                item.setTextAlignment(Qt.AlignTrailing | Qt.AlignVCenter)

    def fit_height(self):
        """As tall as its header and rows, with no scroll bar of its own (for a short table inside a page that scrolls)."""
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        rows = sum(self.rowHeight(r) for r in range(self.rowCount()))
        self.setFixedHeight(self.horizontalHeader().height() + rows + 2 * self.frameWidth() + 2)

    def add_row(self, values, data=None):
        from PySide6.QtWidgets import QTableWidgetItem
        row = self.rowCount()
        self.insertRow(row)
        for column, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            if column in self.numeric:
                item.setTextAlignment(Qt.AlignTrailing | Qt.AlignVCenter)
            if column == 0 and data is not None:
                item.setData(Qt.UserRole, data)
            self.setItem(row, column, item)
        return row


class List(QFrame):
    """Rows one under another. `variant='flat'` has no border or fill of its own, for use inside a flat Card."""
    def __init__(self, parent=None, variant='plain'):
        super().__init__(parent)
        mark(self, 'List', variant=variant)
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(0, 0, 0, 0)
        self.box.setSpacing(0)
        self.rows = []

    def add(self, row):
        """Rows are separated by a line; the last one has none (the list's own border closes it)."""
        if self.rows:
            set_props(self.rows[-1], last='false')
        self.box.addWidget(row)
        self.rows.append(row)
        set_props(row, last='true')
        return row

    def clear(self):
        for row in self.rows:
            self.box.removeWidget(row)          # out of the layout now, not when deleteLater runs, so a rebuild never shows old and new rows together
            row.hide()
            row.setParent(None)
            row.deleteLater()
        self.rows = []


class ListRow(QFrame):
    """Optional leading icon, a title, a muted line, one control at the trailing side."""
    TONES = ('danger', 'warning', 'info', 'success')

    def __init__(self, title, line='', icon=None, control=None, parent=None, tone=None, lead=None):
        """`tone` (danger, warning, info, success) puts the icon on a tinted round plate, as in the Home attention list.
        `lead` is a widget (a Switch) placed before everything else."""
        super().__init__(parent)
        mark(self, 'ListRow')
        t = theme.current()
        row = QHBoxLayout(self)
        row.setContentsMargins(t.px('space.4'), t.px('space.3'), t.px('space.4'), t.px('space.3'))
        row.setSpacing(t.px('space.3'))
        self.lead = lead
        if lead is not None:
            row.addWidget(lead, 0, Qt.AlignVCenter)
        if icon:
            if tone in self.TONES:
                glyph = mark(QLabel(), 'RowIcon', tone=tone)
                glyph.setAlignment(Qt.AlignCenter)
                glyph.setPixmap(theme.icon(icon, 'color.%s.text' % tone, 16).pixmap(16, 16))
            else:
                glyph = QLabel()
                glyph.setPixmap(theme.icon(icon, 'color.text.secondary', 20).pixmap(20, 20))
            row.addWidget(glyph, 0, Qt.AlignTop)
        copy = QVBoxLayout()
        copy.setSpacing(2)
        self.title = text_label(title, 'RowTitle')
        copy.addWidget(self.title)
        self.line = text_label(line, 'Muted')
        self.line.setVisible(bool(line))
        copy.addWidget(self.line)
        row.addLayout(copy, 1)
        self.control = control
        if control is not None:
            row.addWidget(control, 0, Qt.AlignVCenter)


class KeyValue(QWidget):
    """Two columns: muted label, value."""
    def __init__(self, pairs=(), parent=None):
        super().__init__(parent)
        mark(self, 'KeyValue')
        from PySide6.QtWidgets import QFormLayout
        self.form = QFormLayout(self)
        self.form.setContentsMargins(0, 0, 0, 0)
        for key, value in pairs:
            self.add(key, value)

    def add(self, key, value):
        """`value` is text, or a widget (a Badge, a row of Badges) that is placed as it is."""
        if isinstance(value, str):
            value = text_label(value, 'KeyValueValue')
            # next to its label in either direction, whatever the first letter of the text is (a number wrapped in direction marks would otherwise jump to the far side)
            from PySide6.QtGui import QGuiApplication
            rtl = QGuiApplication.layoutDirection() == Qt.RightToLeft
            value.setAlignment(Qt.AlignAbsolute | (Qt.AlignRight if rtl else Qt.AlignLeft) | Qt.AlignVCenter)
        self.form.addRow(text_label(key, 'KeyLabel', wrap=False), value)

    def clear(self):
        while self.form.rowCount():
            self.form.removeRow(0)


class Badge(QLabel):
    def __init__(self, text, variant='neutral', parent=None):
        if variant not in BADGE_VARIANTS:
            raise ValueError('unknown badge variant')
        super().__init__(text, parent)
        mark(self, 'Badge', variant=variant)
        self.setTextFormat(Qt.PlainText)
        self.setAlignment(Qt.AlignCenter)

    def set_variant(self, variant):
        set_props(self, variant=variant)


class Bar(_Painted):
    """An 8 px rounded bar that fills from the leading side; value 0 to 1."""
    def __init__(self, value=0., parent=None):
        super().__init__('Bar', parent)
        self.value = value
        self.setFixedHeight(8)
        self.setMinimumWidth(40)

    def set_value(self, value):
        self.value = max(0., min(1., float(value)))
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(theme.color('color.bg.sunken'))
        p.drawRoundedRect(QRectF(self.rect()), 4, 4)
        w = self.width() * self.value
        x = self.width() - w if self.layoutDirection() == Qt.RightToLeft else 0
        p.setBrush(theme.color('color.accent.fill'))
        p.drawRoundedRect(QRectF(x, 0, w, self.height()), 4, 4)


class ConfidenceBar(_Painted):
    """A range (low, high) on a 0–100 % track with a mark at 50 %: green above, red below, grey across."""
    def __init__(self, low=0., high=0., parent=None):
        super().__init__('ConfidenceBar', parent)
        self.low, self.high = low, high
        self.setFixedHeight(8)
        self.setMinimumWidth(60)

    def set_range(self, low, high):
        self.low, self.high = max(0., min(low, high)), min(1., max(low, high))
        self.update()

    def verdict(self):
        if self.low > .5:
            return 'success'
        if self.high < .5:
            return 'danger'
        return 'neutral'

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(theme.color('color.bg.sunken'))
        p.drawRoundedRect(QRectF(self.rect()), 4, 4)
        rtl = self.layoutDirection() == Qt.RightToLeft
        a, b = (1 - self.high, 1 - self.low) if rtl else (self.low, self.high)
        colour = {'success': 'color.success.text', 'danger': 'color.danger.text'}.get(self.verdict(), 'color.text.muted')
        p.setBrush(theme.color(colour))
        p.drawRoundedRect(QRectF(a * self.width(), 0, max(2., (b - a) * self.width()), self.height()), 4, 4)
        p.setBrush(theme.color('color.text.primary'))
        p.drawRect(QRectF(self.width() / 2 - .5, 0, 1, self.height()))


class Banner(QFrame):
    """A tinted strip: icon, a bold line, an optional second line, optional small buttons at the trailing side."""
    ICONS = {'info': ('info', 'color.info.text'), 'success': ('check', 'color.success.text'),
             'warning': ('warn', 'color.warning.text'), 'danger': ('warn', 'color.danger.text')}

    def __init__(self, title, text='', variant='info', parent=None):
        if variant not in BANNER_VARIANTS:
            raise ValueError('unknown banner variant')
        super().__init__(parent)
        mark(self, 'Banner', variant=variant)
        t = theme.current()
        row = QHBoxLayout(self)
        row.setContentsMargins(t.px('space.4'), t.px('space.3'), t.px('space.4'), t.px('space.3'))
        row.setSpacing(t.px('space.3'))
        name, token = self.ICONS[variant]
        glyph = QLabel()
        glyph.setPixmap(theme.icon(name, token, 20).pixmap(20, 20))
        row.addWidget(glyph, 0, Qt.AlignTop)
        copy = QVBoxLayout()
        copy.setSpacing(2)
        self.title = text_label(title, 'BannerTitle')
        copy.addWidget(self.title)
        self.text = text_label(text, 'CardText')
        self.text.setVisible(bool(text))
        copy.addWidget(self.text)
        row.addLayout(copy, 1)
        self.actions = QHBoxLayout()
        row.addLayout(self.actions)

    def add_action(self, button):
        self.actions.addWidget(button)
        return button


class Toast(QFrame):
    """A small raised card at the bottom trailing corner; leaves after 6 seconds or on Esc. Never for errors."""
    def __init__(self, host, text, undo=None, undo_text='', icon='check', timeout=6000):
        super().__init__(host)
        mark(self, 'Toast')
        _shadow(self, 24, 8)
        row = QHBoxLayout(self)
        row.setContentsMargins(14, 10, 14, 10)
        glyph = QLabel()
        glyph.setPixmap(theme.icon(icon, 'color.success.text', 20).pixmap(20, 20))
        row.addWidget(glyph)
        row.addWidget(text_label(text, 'CardText'), 1)
        if undo:
            b = Button(undo_text, 'ghost', 'sm')
            b.clicked.connect(undo)
            b.clicked.connect(self.close)
            row.addWidget(b)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.close)
        self.timer.start(timeout)
        self.adjustSize()
        margin = 24
        x = margin if host.layoutDirection() == Qt.RightToLeft else host.width() - self.width() - margin
        self.move(max(0, x), max(0, host.height() - self.height() - margin))
        self.show()
        self.raise_()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)


class ProgressBar(QProgressBar):
    """6 px, accent fill; `set_unknown()` slides when the total is not known."""
    def __init__(self, parent=None):
        super().__init__(parent)
        mark(self, 'ProgressBar')
        self.setTextVisible(False)

    def set_unknown(self):
        self.setRange(0, 0)

    def set_known(self, value, total):
        self.setRange(0, max(1, total))
        self.setValue(value)


class Spinner(_Painted):
    """A 16 px ring that turns."""
    def __init__(self, parent=None, size=16):
        super().__init__('Spinner', parent)
        self.setFixedSize(size, size)
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._turn)

    def _turn(self):
        self.angle = (self.angle + 8) % 360
        self.update()

    def showEvent(self, event):
        self.timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        p.setPen(QPen(theme.color('color.border.default'), 2))
        p.drawEllipse(r)
        pen = QPen(theme.color('color.accent.fill'), 2)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawArc(r, -self.angle * 16, 90 * 16)


class Skeleton(_Painted):
    """A grey rounded block in the shape of content that is loading."""
    def __init__(self, width=None, height=14, parent=None):
        super().__init__('Skeleton', parent)
        self.setFixedHeight(height)
        if width:
            self.setFixedWidth(width)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(theme.color('color.bg.raised'))
        p.drawRoundedRect(QRectF(self.rect()), 6, 6)


class EmptyState(QWidget):
    """Centred: a 56 px round icon, a title, one sentence, at most one button. `danger` for "could not"."""
    def __init__(self, icon, title, text='', button=None, variant='neutral', parent=None):
        super().__init__(parent)
        mark(self, 'EmptyState', variant=variant)
        box = QVBoxLayout(self)
        box.setAlignment(Qt.AlignCenter)
        box.setSpacing(theme.current().px('space.2'))
        plate = mark(QLabel(), 'EmptyIcon')
        plate.setAlignment(Qt.AlignCenter)
        plate.setPixmap(theme.icon(icon, 'color.danger.text' if variant == 'danger' else 'color.text.secondary', 24).pixmap(24, 24))
        box.addWidget(plate, 0, Qt.AlignHCenter)
        self.title = text_label(title, 'EmptyTitle')
        self.title.setAlignment(Qt.AlignCenter)
        box.addWidget(self.title)
        self.text = text_label(text, 'CardText')
        self.text.setAlignment(Qt.AlignCenter)
        self.text.setFixedWidth(theme.current().px('size.dialog.sm'))      # a wrapped label in a centred layout is only tall enough for its own idea of its width
        self.text.setVisible(bool(text))
        box.addWidget(self.text, 0, Qt.AlignHCenter)
        self.button = button
        if button is not None:
            box.addWidget(button, 0, Qt.AlignHCenter)

    def showEvent(self, event):
        super().showEvent(event)
        self.fit_text()

    def fit_text(self):
        if self.text.isVisibleTo(self):                        # now the stylesheet's font is known: make the label as tall as its wrapped text
            self.text.setMinimumHeight(self.text.heightForWidth(self.text.width()))

    def set_text(self, title, text=''):
        """Change the words (a page whose empty state depends on what was asked)."""
        self.title.setText(title)
        self.text.setText(text)
        self.text.setVisible(bool(text))
        self.text.setMinimumHeight(0)
        self.fit_text()


def Tooltip(widget, text):
    """Tooltips are Qt's own (inverted colours come from the stylesheet); this sets one and the accessible description."""
    widget.setToolTip(text)
    widget.setAccessibleDescription(text)
    return widget
