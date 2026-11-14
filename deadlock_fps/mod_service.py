"""The one object the Hub, Installed Mods, Compatibility and Downloads pages share.

It owns what must exist once: the repository manager, one Installer per game folder, and the thread pool work. The
pages draw and call it; the engines (`repos`, `installer`) do the real work and know nothing about Qt.
"""
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QThreadPool, QRunnable

from .core import game_root
from .detection import manifest as steam_manifest
from .installer import Installer, InstallError, update_status
from .store.install import build as build_store_install


class _Signals(QObject):
    result = Signal(object)
    failure = Signal(str, str)           # message, stable error code
    done = Signal()


class _Job(QRunnable):
    def __init__(self, fn):
        super().__init__()
        self.fn = fn
        self.signals = _Signals()

    def run(self):
        try:
            self.signals.result.emit(self.fn())
        except Exception as error:      # engines raise InstallError / RepoError with a stable code
            self.signals.failure.emit(getattr(error, 'message', None) or str(error), getattr(error, 'code', None) or type(error).__name__)
        finally:
            self.signals.done.emit()


class ModService(QObject):
    changed = Signal()                  # installed mods or history changed
    busyChanged = Signal(bool)
    progress = Signal(int, int)         # bytes done, bytes total (0 = unknown)
    notice = Signal(str)                # something to tell the user, already phrased

    def __init__(self, manager, game_path, parent=None, transport=None):
        super().__init__(parent)
        self.manager = manager
        self.game_path = game_path      # callable returning the folder text the user linked
        self.transport = transport or manager.transport
        self._installers = {}
        self._jobs = []
        self.cancel_event = None
        self.recovered = []
        self.busy = False

    # ---- the game -----------------------------------------------------------

    def installer(self):
        """The Installer for the linked game, created (and its interrupted work recovered) once. Raises InstallError(no-game)."""
        text = (self.game_path() or '').strip()
        if not text:
            raise InstallError('no-game', 'Link your Deadlock folder on the Home page first.')
        try:
            root = game_root(text)
        except ValueError as error:
            raise InstallError('no-game', str(error)) from None
        key = str(root)
        if key not in self._installers:
            installer = Installer(root, self.transport)
            self._installers[key] = installer
            try:
                self.recovered = installer.recover()
            except InstallError as error:
                # Recovery itself failed. Say so, and keep the installer: its operations refuse to run while a journal is pending.
                self.recovered = []
                self.notice.emit(error.message)
            if self.recovered:
                self.notice.emit(' '.join(self.recovered))
        return self._installers[key]

    def ready(self):
        try:
            self.installer()
            return True
        except InstallError:
            return False

    def game_build(self):
        try:
            value = steam_manifest(self.installer().root).get('buildid', '')
            return int(value) if value.isdigit() else None
        except (InstallError, OSError):
            return None

    def statuses(self):
        try:
            return update_status(self.installer().installed(), self.manager, self.game_build())
        except InstallError:
            return []

    # ---- background work -----------------------------------------------------

    def run(self, work, done, failed=None, *, cancel=None):
        """Run `work()` off the interface thread. `done(result)` and `failed(message, code)` run on it."""
        job = _Job(work)
        self.cancel_event = cancel
        self._jobs.append(job)
        self._set_busy(True)

        def on_failure(message, code):
            if failed:
                failed(message, code)
            else:
                self.notice.emit(message)

        def finish():
            if job in self._jobs:
                self._jobs.remove(job)
            self._set_busy(bool(self._jobs))
        job.signals.result.connect(done)
        job.signals.failure.connect(on_failure)
        job.signals.done.connect(finish)
        QThreadPool.globalInstance().start(job)
        return job

    def _set_busy(self, value):
        if self.busy != value:
            self.busy = value
            self.busyChanged.emit(value)

    def cancel(self):
        if self.cancel_event is not None:
            self.cancel_event.set()

    # ---- operations (each returns after scheduling) ---------------------------

    def prepare(self, repository_id, mod_id, version_text, done, failed):
        """Download, verify, inspect and stage. `done(plan)`; the game folder is untouched."""
        found = self.manager.find_mod(repository_id, mod_id)
        if found is None:
            failed('That mod is no longer in the repository catalogue.', 'not-found')
            return
        view, mod = found
        version = mod.find(version_text)
        if version is None:
            failed('That version is no longer listed.', 'not-found')
            return
        installer = self.installer()
        cancel = threading.Event()
        self.run(lambda: installer.prepare(view, mod, version, progress=self.progress.emit, cancel=cancel), done, failed, cancel=cancel)

    def prepare_store(self, profile, file_id, done, failed):
        """`prepare` for one file of a Mod Store listing: the same download, verification, inspection and staging."""
        file = next((f for f in profile.files if f.id == file_id), None)
        if file is None:
            failed('That file is no longer listed.', 'not-found')
            return
        view, mod, version = build_store_install(profile, file)
        installer = self.installer()
        cancel = threading.Event()
        self.run(lambda: installer.prepare(view, mod, version, progress=self.progress.emit, cancel=cancel), done, failed, cancel=cancel)

    def commit(self, plan, acknowledged, done, failed):
        installer = self.installer()

        def work():
            return installer.commit(plan, acknowledged=acknowledged)
        self.run(work, lambda mod: (self.changed.emit(), done(mod)), failed)

    def discard(self, plan):
        try:
            self.installer().discard(plan)
        except InstallError:
            pass

    def operate(self, name, args, done, failed):
        """uninstall | set_enabled | restore_previous | repair on the worker thread."""
        installer = self.installer()
        method = getattr(installer, name)
        self.run(lambda: method(*args), lambda result: (self.changed.emit(), done(result)), failed)

