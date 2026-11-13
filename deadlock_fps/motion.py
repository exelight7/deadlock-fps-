"""Interface motion for the Toolbox shell.

Every animation here is short and event-driven: it starts from a user action and
stops by itself, so nothing repaints while the window is idle. Widgets that are
not on screen skip straight to their final state, which keeps headless runs and
tests deterministic.
"""
import math
from PySide6.QtCore import Qt, QObject, QEvent, QEasingCurve, QVariantAnimation, QRect, QRectF, QPointF, QTimer, QSize
from PySide6.QtGui import QColor, QPainter, QPixmap, QPolygonF, QPen, QFont, QIcon
from PySide6.QtWidgets import QWidget, QPushButton, QFrame, QGraphicsDropShadowEffect
from . import theme as T

BASE = QColor(T.BASE)
GOLD = QColor(T.BRASS)
GOLD_BRIGHT = QColor(T.BRASS_BRIGHT)
MINT = QColor(T.VERDIGRIS)
AMBER = QColor(T.AMBER)
MUTED = QColor(T.TEXT_MUTED)
TEXT = QColor(T.TEXT)
FAMILIES = list(T.DISPLAY)
LABELS = list(T.BODY)


def mix(a, b, t):
    """Blend two colours; t=0 gives a, t=1 gives b."""
    t = max(0., min(1., t))
    return QColor(round(a.red() + (b.red() - a.red()) * t), round(a.green() + (b.green() - a.green()) * t),
                  round(a.blue() + (b.blue() - a.blue()) * t), round(a.alpha() + (b.alpha() - a.alpha()) * t))


def alpha(color, value):
    result = QColor(color)
    result.setAlphaF(max(0., min(1., value)))
    return result


def tween(owner, duration, step, curve=QEasingCurve.OutCubic):
    """A 0→1 animation owned by `owner`; `step` receives each eased value."""
    animation = QVariantAnimation(owner)
    animation.setDuration(duration)
    animation.setEasingCurve(curve)
    animation.setStartValue(0.)
    animation.setEndValue(1.)
    animation.valueChanged.connect(step)
    return animation


class Fader(QVariantAnimation):
    """A level between 0 and 1 that eases toward its latest target from wherever it is."""
    def __init__(self, owner, duration, changed, curve=QEasingCurve.OutCubic):
        super().__init__(owner)
        self.level = 0.
        self.changed = changed
        self.setDuration(duration)
        self.setEasingCurve(curve)
        self.valueChanged.connect(self.store)

    def store(self, value):
        self.level = float(value)
        self.changed()

    def to(self, target, animate=True):
        self.stop()
        target = float(target)
        if not animate or abs(target - self.level) < .001:
            self.level = target
            self.changed()
            return
        self.setStartValue(self.level)
        self.setEndValue(target)
        self.start()


class PageTransition(QWidget):
    """Cross-fades two snapshots of the page area while the real widgets switch underneath.

    The live page changes instantly, so navigation state is never delayed by the
    animation; this overlay only paints the hand-over and ignores the mouse.
    Everything between `top` and `bottom` (host coordinates) slides as the page;
    whatever sits below, such as the action bar, stays anchored and only fades.
    """
    def __init__(self, host, top, bottom):
        super().__init__(host)
        self.host = host
        self.top = top
        self.bottom = bottom
        self.split = 0
        self.before = None
        self.after = None
        self.progress = 1.
        self.direction = 1
        self.capturing = False
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.hide()
        self.animation = tween(self, 300, self.step)
        self.animation.finished.connect(self.finish)
        # The new page is captured one event-loop turn later, after layouts settle.
        self.settle = QTimer(self)
        self.settle.setSingleShot(True)
        self.settle.setInterval(0)
        self.settle.timeout.connect(self.reveal)
        host.installEventFilter(self)

    def region(self):
        top = max(0, int(self.top()))
        return QRect(0, top, self.host.width(), self.host.height() - top)

    def snapshot(self, region):
        self.capturing = True
        try:
            return self.host.grab(region)
        finally:
            self.capturing = False

    def capture(self, direction=1):
        """Call just before the page changes."""
        if not self.host.isVisible():
            return
        region = self.region()
        if region.width() < 2 or region.height() < 2:
            return
        # Starting again mid-transition continues from the frame already on screen.
        frame = self.grab() if self.isVisible() and self.before is not None else self.snapshot(region)
        self.animation.stop()
        self.before, self.after, self.progress, self.direction = frame, None, 0., direction
        self.split = int(self.bottom()) - region.top()
        self.setGeometry(region)
        self.raise_()
        self.show()
        self.settle.start()

    def reveal(self):
        if self.before is None:
            return
        region = self.region()
        if region.size() != self.size():
            self.finish()
            return
        self.after = self.snapshot(region)
        self.split = max(0, min(self.split, int(self.bottom()) - region.top(), region.height()))
        self.raise_()
        self.animation.start()

    def step(self, value):
        self.progress = float(value)
        self.update()

    def finish(self):
        self.settle.stop()
        self.animation.stop()
        self.before = self.after = None
        self.progress = 1.
        self.hide()

    def eventFilter(self, watched, event):
        if watched is self.host and event.type() == QEvent.Resize and self.isVisible():
            self.finish()
        return False

    def paintEvent(self, event):
        if self.capturing or self.before is None:
            return
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.before)
        if self.after is None:
            return
        t = self.progress
        # Anchored strip: an exact cross-fade, so unchanged controls never flicker.
        painter.setClipRect(QRect(0, self.split, self.width(), self.height() - self.split))
        painter.setOpacity(t)
        painter.drawPixmap(0, 0, self.after)
        # Page: the old one lifts away while the new one settles into place.
        painter.setClipRect(QRect(0, 0, self.width(), self.split))
        painter.setOpacity(1)
        painter.fillRect(self.rect(), BASE)
        painter.setOpacity(max(0., 1 - t * 2.2))
        painter.drawPixmap(QPointF(0, -self.direction * 12 * t), self.before)
        painter.setOpacity(max(0., min(1., (t - .1) / .9)))
        painter.drawPixmap(QPointF(0, self.direction * 22 * (1 - t)), self.after)


class NavButton(QPushButton):
    """Sidebar entry with eased hover and selection colours.

    A trailing ' •' in the text (used for "update available") is drawn as a
    glowing dot instead of a character.
    """
    def __init__(self, text, icon):
        super().__init__(text)
        self.glyph = icon
        self.keyboard_focus = False
        self.badged = False
        self.setObjectName('nav')
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(42)
        self.hover = Fader(self, 150, self.update)
        self.active = Fader(self, 260, self.update)
        self.pulse = tween(self, 1500, lambda _: self.update(), QEasingCurve.Linear)
        self.pulse.setLoopCount(3)
        self.toggled.connect(lambda on: self.active.to(on, self.isVisible()))

    def setText(self, text):
        super().setText(text)
        badged = text.endswith(' •')
        if badged and not self.badged and self.isVisible():
            self.pulse.start()
        self.badged = badged

    def enterEvent(self, event):
        self.hover.to(1)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover.to(0)
        super().leaveEvent(event)

    def focusInEvent(self, event):
        self.keyboard_focus = event.reason() in (Qt.TabFocusReason, Qt.BacktabFocusReason, Qt.ShortcutFocusReason)
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.keyboard_focus = False
        super().focusOutEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        painter.setLayoutDirection(Qt.LeftToRight)
        rect = QRectF(self.rect()).adjusted(.5, .5, -.5, -.5)
        hover, active = self.hover.level, self.active.level
        if not self.isEnabled():
            painter.setOpacity(.45)
        rtl = self.layoutDirection() == Qt.RightToLeft
        if hover > 0 and active < 1:
            # A hairline plate rises under the pointer; the selected plate belongs to NavIndicator.
            painter.setPen(QPen(alpha(QColor(T.LINE_STRONG), hover * (1 - active)), 1))
            painter.setBrush(alpha(QColor(T.SURFACE), .9 * hover * (1 - active)))
            painter.drawRect(rect)
        if self.keyboard_focus and self.hasFocus():
            painter.setPen(QPen(alpha(GOLD, .9), 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect.adjusted(2, 2, -2, -2))
        margin, size = 16, 20
        drift = 3 * hover * (1 - active) * (-1 if rtl else 1)
        icon_left = (rect.right() - margin - size if rtl else rect.left() + margin) + drift
        opacity = painter.opacity()
        painter.setOpacity(opacity * (.55 + .45 * max(hover, active)))
        self.glyph.paint(painter, QRect(round(icon_left), round((self.height() - size) / 2), size, size))
        painter.setOpacity(opacity)
        text = self.text()
        badge = text.endswith(' •')
        if badge:
            text = text[:-2]
        font = QFont(self.font())
        font.setFamilies(LABELS)
        font.setPixelSize(14)
        font.setWeight(QFont.DemiBold)
        painter.setFont(font)
        painter.setPen(mix(mix(QColor(T.TEXT_SOFT), TEXT, hover), GOLD_BRIGHT, active))
        reserve = 22 if badge else 0
        if rtl:
            area = QRectF(rect.left() + margin + reserve, rect.top(), icon_left - 12 - rect.left() - margin - reserve, rect.height())
            flags = Qt.AlignRight
        else:
            area = QRectF(icon_left + size + 12, rect.top(), rect.right() - margin - reserve - icon_left - size - 12, rect.height())
            flags = Qt.AlignLeft
        text = painter.fontMetrics().elidedText(text, Qt.ElideRight, max(0, int(area.width())))
        painter.drawText(area.adjusted(0, -1, 0, -1), int(flags | Qt.AlignVCenter | Qt.AlignAbsolute | Qt.TextSingleLine), text)
        if badge:
            center = QPointF(rect.left() + margin + 5 if rtl else rect.right() - margin - 5, rect.center().y())
            if self.pulse.state() == QVariantAnimation.Running:
                wave = float(self.pulse.currentValue() or 0.)
                painter.setPen(QPen(alpha(GOLD, .6 * (1 - wave)), 1))
                painter.setBrush(Qt.NoBrush)
                painter.drawPolygon(diamond(center, 5 + 8 * wave))
            painter.setPen(Qt.NoPen)
            painter.setBrush(GOLD_BRIGHT)
            painter.drawPolygon(diamond(center, 4.5))


def diamond(center, radius):
    return QPolygonF([QPointF(center.x(), center.y() - radius), QPointF(center.x() + radius, center.y()),
                      QPointF(center.x(), center.y() + radius), QPointF(center.x() - radius, center.y())])


class NavIndicator(QWidget):
    """The selected-page pill. It glides between sidebar entries with a short elastic stretch."""
    def __init__(self, parent):
        super().__init__(parent)
        self.target = None
        self.origin = QRectF()
        self.goal = QRectF()
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.hide()
        self.lower()
        self.slide = tween(self, 340, self.step, QEasingCurve.Linear)

    def move_to(self, button, animate=True):
        if self.target is not button:
            if self.target is not None:
                self.target.removeEventFilter(self)
            self.target = button
            button.installEventFilter(self)
        goal = button.geometry()
        moving = animate and self.isVisible() and self.width() > 0 and goal != self.geometry()
        self.slide.stop()
        if moving:
            self.origin, self.goal = QRectF(self.geometry()), QRectF(goal)
            self.slide.start()
        else:
            self.setGeometry(goal)
        self.lower()
        self.show()

    def step(self, value):
        t = float(value)
        lead = 1 - (1 - t) ** 3
        trail = t * t * t * (t * (6 * t - 15) + 10)
        down = self.goal.top() >= self.origin.top()
        top = self.origin.top() + (self.goal.top() - self.origin.top()) * (trail if down else lead)
        bottom = self.origin.bottom() + (self.goal.bottom() - self.origin.bottom()) * (lead if down else trail)
        self.setGeometry(QRect(round(self.goal.left()), round(top), round(self.goal.width()), max(1, round(bottom - top))))

    def eventFilter(self, watched, event):
        if watched is self.target and event.type() in (QEvent.Move, QEvent.Resize):
            if self.slide.state() == QVariantAnimation.Running:
                self.goal = QRectF(watched.geometry())
            else:
                self.setGeometry(watched.geometry())
        return False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(.5, .5, -.5, -.5)
        rtl = self.layoutDirection() == Qt.RightToLeft
        cut = min(9., rect.height() / 2)
        # A brass-washed plate: square on the leading edge, cut on the trailing corners.
        if rtl:
            points = [rect.topRight(), QPointF(rect.left() + cut, rect.top()), QPointF(rect.left(), rect.top() + cut),
                      QPointF(rect.left(), rect.bottom() - cut), QPointF(rect.left() + cut, rect.bottom()), rect.bottomRight()]
        else:
            points = [rect.topLeft(), QPointF(rect.right() - cut, rect.top()), QPointF(rect.right(), rect.top() + cut),
                      QPointF(rect.right(), rect.bottom() - cut), QPointF(rect.right() - cut, rect.bottom()), rect.bottomLeft()]
        painter.setPen(QPen(QColor(T.BRASS_DEEP), 1))
        painter.setBrush(QColor(T.BRASS_WASH))
        painter.drawPolygon(QPolygonF(points))
        painter.setPen(Qt.NoPen)
        painter.setBrush(GOLD_BRIGHT)
        painter.drawRect(QRectF(rect.right() - 2.5 if rtl else rect.left() - .5, rect.top() - .5, 3, rect.height() + 1))


class Glow(QObject):
    """Soft halo that eases in on hover and tightens while pressed.

    The effect is created on first use and switched off at rest, so idle widgets
    paint exactly as they did before.
    """
    def __init__(self, widget, color, radius=24, strength=.55):
        super().__init__(widget)
        self.widget = widget
        self.color = QColor(color)
        self.radius = radius
        self.strength = strength
        self.effect = None
        self.fade = Fader(self, 190, self.apply)
        widget.installEventFilter(self)

    def eventFilter(self, watched, event):
        kind = event.type()
        if kind == QEvent.Enter:
            if watched.isEnabled():
                self.fade.to(1)
        elif kind == QEvent.Leave:
            self.fade.to(0)
        elif kind == QEvent.MouseButtonPress:
            if watched.isEnabled():
                self.fade.to(.4)
        elif kind == QEvent.MouseButtonRelease:
            self.fade.to(1 if watched.isEnabled() and watched.underMouse() else 0)
        elif kind in (QEvent.Hide, QEvent.EnabledChange):
            if kind == QEvent.Hide or not watched.isEnabled():
                self.fade.to(0, False)
        return False

    def apply(self):
        level = self.fade.level
        if self.effect is None:
            if level <= 0:
                return
            self.effect = QGraphicsDropShadowEffect(self.widget)
            self.effect.setOffset(0, 0)
            self.widget.setGraphicsEffect(self.effect)
        self.effect.setColor(alpha(self.color, self.strength * level))
        self.effect.setBlurRadius(self.radius * level)
        self.effect.setEnabled(level > .01)


GLOWS = {'primary': (T.BRASS, 24, .50), 'positive': (T.VERDIGRIS, 20, .32), 'danger': (T.CRIMSON, 22, .55), 'shortcut': (T.BRASS, 20, .26)}


def enliven(root):
    """Give the accent buttons and cards under `root` their hover glow (safe to call again)."""
    widgets = [(button, GLOWS.get(button.objectName())) for button in root.findChildren(QPushButton)]
    widgets += [(card, (T.BRASS, 24, .24)) for card in root.findChildren(QFrame, 'modCard')]
    for widget, spec in widgets:
        if spec and not widget.property('glow'):
            widget.setProperty('glow', True)
            Glow(widget, *spec)


class StatusChip(QPushButton):
    """Header chip whose dot turns from amber to mint once the game is connected."""
    CONNECTED = ('اللعبة مرتبطة', 'Game connected')

    def __init__(self, text):
        super().__init__()
        self.setObjectName('chip')
        self.setCursor(Qt.PointingHandCursor)
        self.setIconSize(QSize(14, 14))
        self.state = Fader(self, 480, self.draw_dot)
        self.setText(text)

    def setText(self, text):
        super().setText(text)
        self.state.to(text in self.CONNECTED, self.isVisible())

    def draw_dot(self):
        level = self.state.level
        color = mix(AMBER, MINT, level)
        pixmap = QPixmap(28, 28)
        pixmap.setDevicePixelRatio(2)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        # The outline swells mid-change, then settles.
        swell = 1 - abs(2 * level - 1)
        painter.setPen(QPen(alpha(color, .35 + .4 * swell), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawPolygon(diamond(QPointF(7, 7), 5.5 + 1.2 * swell))
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawPolygon(diamond(QPointF(7, 7), 3.4))
        painter.end()
        self.setIcon(QIcon(pixmap))


class LevelMeter(QWidget):
    """Read-only gauge of the reduction level; it eases to each new value."""
    def __init__(self, maximum, marks=()):
        super().__init__()
        self.maximum = maximum
        self.marks = marks
        self.shown = 0.
        self.setFixedHeight(24)
        self.setLayoutDirection(Qt.LeftToRight)
        self.glide = QVariantAnimation(self)
        self.glide.setDuration(520)
        self.glide.setEasingCurve(QEasingCurve.OutCubic)
        self.glide.valueChanged.connect(self.step)

    def set_value(self, value):
        value = float(max(0, min(self.maximum, value)))
        self.glide.stop()
        if self.isVisible() and abs(value - self.shown) > .01:
            self.glide.setStartValue(self.shown)
            self.glide.setEndValue(value)
            self.glide.start()
        else:
            self.step(value)

    def step(self, value):
        self.shown = float(value)
        self.update()

    def paintEvent(self, event):
        # A segmented gauge: verdigris for gentle levels, brass through the working range, crimson at the experimental end.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        left, right = 6., self.width() - 6.
        count = max(12, int((right - left) // 7))
        step = (right - left) / count
        top, height = 9., self.height() - 11.
        ratio = self.shown / self.maximum if self.maximum else 0
        low, middle, high = QColor(T.VERDIGRIS), QColor(T.BRASS), QColor(T.CRIMSON_TEXT)
        painter.setPen(Qt.NoPen)
        for index in range(count):
            at = (index + .5) / count
            lit = max(0., min(1., ratio * count - index))
            shade = mix(mix(low, middle, at / .42), high, (at - .42) / .58)
            painter.setBrush(mix(QColor(T.SUNKEN), shade, .12 + .88 * lit))
            painter.drawRect(QRectF(left + index * step + 1, top, step - 2, height))
        for mark in self.marks:
            x = left + (right - left) * mark / self.maximum
            painter.setBrush(GOLD_BRIGHT if mark <= self.shown else QColor(T.LINE_STRONG))
            painter.drawPolygon(diamond(QPointF(x, 4), 3))


class Intro(QWidget):
    """One-shot launch reveal: the mark settles, then the workspace fades in beneath it."""
    def __init__(self, host, logo, title='Deadlock Toolbox', caption=''):
        super().__init__(host)
        self.host = host
        self.logo = logo
        self.title = title
        self.caption = caption
        self.progress = 0.
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setGeometry(host.rect())
        self.animation = tween(self, 1050, self.step, QEasingCurve.Linear)
        self.animation.finished.connect(self.deleteLater)
        host.installEventFilter(self)
        self.raise_()
        self.show()
        self.animation.start()

    def step(self, value):
        self.progress = float(value)
        self.update()

    def eventFilter(self, watched, event):
        if watched is self.host and event.type() == QEvent.Resize:
            self.setGeometry(self.host.rect())
        return False

    def paintEvent(self, event):
        t = self.progress
        ease = QEasingCurve(QEasingCurve.OutCubic).valueForProgress
        arrive = ease(min(1., t / .38))
        leave = ease(max(0., (t - .52) / .48))
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        painter.fillRect(self.rect(), alpha(QColor(T.INK), 1 - leave))
        center = QPointF(self.width() / 2, self.height() / 2 - 30)
        painter.setOpacity(arrive * (1 - leave))
        # The sunburst opens behind the emblem as it arrives.
        painter.setPen(QPen(alpha(GOLD, .22), 1))
        for index in range(48):
            if 45 < index * 7.5 < 135:      # keep the rays clear of the title below the emblem
                continue
            angle = math.radians(index * 7.5)
            inner, outer = 96, 96 + (150 if index % 4 == 0 else 96) * arrive
            painter.drawLine(QPointF(center.x() + inner * math.cos(angle), center.y() + inner * math.sin(angle)),
                             QPointF(center.x() + outer * math.cos(angle), center.y() + outer * math.sin(angle)))
        size = 132 * (.92 + .08 * arrive + .10 * leave)
        if not self.logo.isNull():
            painter.drawPixmap(QRectF(center.x() - size / 2, center.y() - size / 2, size, size), self.logo, QRectF(self.logo.rect()))
        font = QFont()
        font.setFamilies(FAMILIES)
        font.setPixelSize(26)
        font.setWeight(QFont.DemiBold)
        painter.setFont(font)
        painter.setPen(TEXT)
        rise = 10 * (1 - arrive)
        painter.drawText(QRectF(0, center.y() + 84 + rise, self.width(), 38), int(Qt.AlignHCenter | Qt.AlignVCenter), self.title)
        if self.caption:
            font.setFamilies(list(T.BODY))
            font.setPixelSize(11)
            font.setLetterSpacing(QFont.AbsoluteSpacing, 0 if T.has_arabic(self.caption) else 3)
            painter.setFont(font)
            painter.setPen(GOLD)
            painter.drawText(QRectF(0, center.y() + 124 + rise, self.width(), 20), int(Qt.AlignHCenter | Qt.AlignVCenter), self.caption)
        line = QRectF(center.x() - 80, center.y() + 158, 160, 1.5)
        painter.setPen(Qt.NoPen)
        painter.setBrush(alpha(TEXT, .12))
        painter.drawRect(line)
        painter.setBrush(GOLD_BRIGHT)
        painter.drawRect(QRectF(line.left(), line.top(), line.width() * ease(min(1., t / .6)), 1.5))
