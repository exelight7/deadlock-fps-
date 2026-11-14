"""Qt side of the mod store: owns the local catalogue and runs synchronisation and profile fetches off the interface thread.

Nothing here runs by itself. A sync starts only when the user asks for it, and it is cancelled when the application
quits, so the store never leaves hidden activity behind.
"""
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QThreadPool, QRunnable, QStandardPaths, QCoreApplication

from .repos import UrllibTransport
from .repos.errors import RepoError
from .store import Catalog, GameBananaClient, StoreSync
from .store.gamebanana import USER_AGENT


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
        except Exception as error:      # the engine raises RepoError with a stable code
            self.signals.failure.emit(getattr(error, 'message', None) or str(error), getattr(error, 'code', None) or type(error).__name__)
        finally:
            self.signals.done.emit()


class StoreService(QObject):
    changed = Signal()                  # the catalogue gained or refreshed listings
    busyChanged = Signal(bool)          # a synchronisation started or ended
    progress = Signal(int, int)         # pages done, pages expected

    def __init__(self, folder=None, transport=None, parent=None, pause=0.6):
        super().__init__(parent)
        folder = Path(folder) if folder is not None else Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / 'store'
        self.transport = transport or UrllibTransport(user_agent=USER_AGENT)
        self.client = GameBananaClient(self.transport)
        self.catalog = None
        self.sync = None
        self.error = ''                 # why the catalogue is unavailable, when it is
        try:
            self.catalog = Catalog(folder / 'catalog.sqlite')
            self.sync = StoreSync(self.client, self.catalog, pause=pause, sleep=self._sleep)
        except RepoError as error:
            self.error = error.message
        self.busy = False
        self._jobs = []
        self._cancel = threading.Event()
        application = QCoreApplication.instance()
        if application is not None:
            application.aboutToQuit.connect(self.cancel)

    @property
    def ready(self):
        return self.catalog is not None

    def _sleep(self, seconds):
        self._cancel.wait(seconds)      # wakes at once when the user cancels or the application quits

    def summary(self):
        """What the page shows about the catalogue: listings held, when it was last brought up to date, and whether the first download is still pending."""
        if not self.ready:
            return {'count': 0, 'last': 0, 'first_download': True, 'resumable': False}
        catalog = self.catalog
        return {'count': catalog.count(), 'last': max(catalog.meta_int('crawl_done'), catalog.meta_int('refreshed_at')),
                'first_download': self.sync.needs_crawl, 'resumable': catalog.meta_int('crawl_next') > 1}

    # ---- background work ---------------------------------------------------------

    def _run(self, work, done, failed, track):
        job = _Job(work)
        self._jobs.append(job)
        if track:
            self._set_busy(True)

        def finish():
            if job in self._jobs:
                self._jobs.remove(job)
            if track:
                self._set_busy(False)
        job.signals.result.connect(done)
        job.signals.failure.connect(failed)
        job.signals.done.connect(finish)
        QThreadPool.globalInstance().start(job)

    def _set_busy(self, value):
        if self.busy != value:
            self.busy = value
            self.busyChanged.emit(value)

    def start_sync(self, done, failed):
        """Download the catalogue, or refresh it when it is already complete. `done(report)` / `failed(message, code)` run on the interface thread."""
        if self.busy or not self.ready:
            return False
        self._cancel = threading.Event()
        cancel = self._cancel
        self._run(lambda: self.sync.sync(progress=self.progress.emit, cancel=cancel), done, failed, track=True)
        return True

    def cancel(self):
        self._cancel.set()

    def fetch_profile(self, mod_id, done, failed):
        """The full page of one mod (description, files, counts). The counts are kept in the catalogue."""
        if not self.ready:
            return

        def work():
            profile = self.client.profile(mod_id)
            self.catalog.apply_profile(profile)
            return profile
        self._run(work, done, failed, track=False)
