"""Small pieces shared by several pages: text helpers for numbers, sizes and times, and the background `Job`."""
from datetime import datetime

from PySide6.QtCore import QObject, QRunnable, Signal

from .i18n import tr


def ltr(value):
    """Keep numbers, dates and addresses in reading order inside a right-to-left table."""
    return '‎%s‎' % value


def size_text(value):
    if not value:
        return '—'
    for unit in ('B', 'KB', 'MB', 'GB'):
        if value < 1024 or unit == 'GB':
            return ('%d %s' % (value, unit)) if unit == 'B' else ('%.1f %s' % (value, unit))
        value /= 1024


def time_text(stamp):
    try:
        return datetime.fromtimestamp(stamp).astimezone().strftime('%Y-%m-%d %H:%M') if stamp else tr('Never')
    except (ValueError, OSError, OverflowError):
        return tr('Never')


def iso_text(stamp):
    """'2026-11-14T10:00:00+0300' -> '2026-11-14 10:00', or '—'."""
    return stamp[:16].replace('T', ' ') if stamp else '—'


class JobSignals(QObject):
    result = Signal(object)
    failure = Signal(str)
    done = Signal()
    progress = Signal(object)


class Job(QRunnable):
    """Slow work off the interface thread: `fn()` (or `fn(progress)`) runs on the pool, `signals.result`/`failure`/`done` come back on the interface."""

    def __init__(self, fn, progress=False):
        super().__init__()
        self.fn = fn
        self.with_progress = progress
        self.signals = JobSignals()

    def run(self):
        try:
            self.signals.result.emit(self.fn(self.signals.progress.emit) if self.with_progress else self.fn())
        except Exception as error:
            self.signals.failure.emit(str(error))
        finally:
            self.signals.done.emit()
