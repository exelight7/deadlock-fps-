"""The two motions the shell still has: the page hand-over (a short cross-fade) and the launch reveal.

Both are event-driven: they start from an action and stop by themselves, so nothing repaints while the window is idle. A hidden host skips
straight to the final state, which keeps headless runs and tests deterministic. Colours come from the design tokens.
"""
import math

from PySide6.QtCore import QEasingCurve, QEvent, QPointF, QRect, QRectF, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from . import theme


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


class PageTransition(QWidget):
    """Cross-fades two snapshots of the page area while the real widgets switch underneath.

    The live page changes instantly, so navigation state is never delayed by the animation; this overlay only paints the hand-over and
    ignores the mouse. Everything between `top` and `bottom` (host coordinates) slides as the page; whatever sits below stays anchored.
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
        painter.fillRect(self.rect(), theme.color('color.bg.app'))
        painter.setOpacity(max(0., 1 - t * 2.2))
        painter.drawPixmap(QPointF(0, -self.direction * 12 * t), self.before)
        painter.setOpacity(max(0., min(1., (t - .1) / .9)))
        painter.drawPixmap(QPointF(0, self.direction * 22 * (1 - t)), self.after)


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
        accent = theme.color('color.accent.text')
        ink = theme.color('color.text.primary')
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        painter.fillRect(self.rect(), alpha(theme.color('color.bg.sidebar'), 1 - leave))
        center = QPointF(self.width() / 2, self.height() / 2 - 30)
        painter.setOpacity(arrive * (1 - leave))
        painter.setPen(QPen(alpha(accent, .22), 1))
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
        font.setFamilies(theme.current().families())
        font.setPixelSize(26)
        font.setWeight(QFont.DemiBold)
        painter.setFont(font)
        painter.setPen(ink)
        rise = 10 * (1 - arrive)
        painter.drawText(QRectF(0, center.y() + 84 + rise, self.width(), 38), int(Qt.AlignHCenter | Qt.AlignVCenter), self.title)
        if self.caption:
            font.setPixelSize(11)
            font.setLetterSpacing(QFont.AbsoluteSpacing, 3)
            painter.setFont(font)
            painter.setPen(accent)
            painter.drawText(QRectF(0, center.y() + 124 + rise, self.width(), 20), int(Qt.AlignHCenter | Qt.AlignVCenter), self.caption)
        line = QRectF(center.x() - 80, center.y() + 158, 160, 1.5)
        painter.setPen(Qt.NoPen)
        painter.setBrush(alpha(ink, .12))
        painter.drawRect(line)
        painter.setBrush(accent)
        painter.drawRect(QRectF(line.left(), line.top(), line.width() * ease(min(1., t / .6)), 1.5))
