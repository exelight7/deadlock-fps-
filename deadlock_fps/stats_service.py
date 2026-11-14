"""Qt side of the statistics page: runs the engine's blocking calls off the interface thread.

Nothing here runs by itself. A load starts only when the user presses a button; the page may read what is already saved
on disk (no network) but never starts a request on its own. The Steam account number leaves the computer only through
`load_player`, and nothing about a player is written to disk.
"""
import time
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QThreadPool, QRunnable, QStandardPaths

from .repos import UrllibTransport
from .repos.errors import RepoError
from .stats.api import USER_AGENT, DeadlockApi
from .stats.cache import Cache
from .stats.source import StatsSource


COMPARE_DAYS = 30                  # the window everyone's numbers come from when a player looks at all of their matches


@dataclass(frozen=True)
class Overview:
    meta: object                       # source.Loaded holding a Meta
    distribution: object               # source.Loaded holding a Distribution, or None when it could not be had
    tiers: dict                        # {tier number: name}, empty when unknown
    distribution_error: str = ''


@dataclass(frozen=True)
class PlayerView:
    player: object                     # stats.model.Player
    meta: object                       # source.Loaded for the same period and mode, or None: what the comparison column uses


class _Signals(QObject):
    result = Signal(object)
    failure = Signal(str, str)
    done = Signal()


class _Job(QRunnable):
    def __init__(self, fn):
        super().__init__()
        self.fn = fn
        self.signals = _Signals()

    def run(self):
        try:
            self.signals.result.emit(self.fn())
        except Exception as error:      # the engine raises RepoError with a stable code; a ValueError means the request was malformed
            self.signals.failure.emit(getattr(error, 'message', None) or str(error), getattr(error, 'code', None) or type(error).__name__)
        finally:
            self.signals.done.emit()


class StatsService(QObject):
    busyChanged = Signal(bool)          # a load started or ended

    def __init__(self, folder=None, transport=None, parent=None, clock=time.time):
        super().__init__(parent)
        folder = Path(folder) if folder is not None else Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / 'stats'
        self.transport = transport or UrllibTransport(user_agent=USER_AGENT)
        self.source = StatsSource(DeadlockApi(self.transport, clock=clock), Cache(folder, clock), clock)
        self.busy = False
        self._jobs = []

    # ---- what is saved on disk (no network) ----

    def cached_overview(self, window_days, mode, tier):
        """An Overview built only from saved copies, or None when the meta for this question is not saved (or no longer fresh)."""
        meta = self.source.cached_meta(window_days, mode, tier)
        if meta is None:
            return None
        return Overview(meta, self.source.cached_distribution(window_days, mode), self.source.cached_rank_names())

    # ---- background work ----

    def _run(self, work, done, failed):
        job = _Job(work)
        self._jobs.append(job)
        self._set_busy(True)

        def finish():
            if job in self._jobs:
                self._jobs.remove(job)
            self._set_busy(bool(self._jobs))
        job.signals.result.connect(done)
        job.signals.failure.connect(failed)
        job.signals.done.connect(finish)
        QThreadPool.globalInstance().start(job)

    def _set_busy(self, value):
        if self.busy != value:
            self.busy = value
            self.busyChanged.emit(value)

    def load_overview(self, window_days, mode, tier, refresh, done, failed):
        """The meta for one question, the rank distribution and the rank names. Only the three choices are sent to the server."""
        if self.busy:
            return False

        def work():
            meta = self.source.meta(window_days, mode, tier, refresh)
            distribution, problem = None, ''
            try:
                distribution = self.source.distribution(window_days, mode, refresh)
            except RepoError as error:
                problem = error.message
            try:
                tiers = self.source.rank_names()
            except RepoError:
                tiers = {}
            return Overview(meta, distribution, tiers, problem)
        self._run(work, done, failed)
        return True

    def load_player(self, account_id, window_days, mode, done, failed):
        """One player's rank and hero totals. `account_id` is the one thing here that identifies a person; the page calls this only for a button press."""
        if self.busy:
            return False

        def work():
            player = self.source.player(account_id, window_days, mode)
            try:
                meta = self.source.meta(window_days or COMPARE_DAYS, mode, 0)      # all time is compared with the most recent month: the meta has no longer window
            except RepoError:
                meta = None
            return PlayerView(player, meta)
        self._run(work, done, failed)
        return True
