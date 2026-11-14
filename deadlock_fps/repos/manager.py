"""The Repository Manager: the one object the interface and the installer talk to.

It owns the list of repositories, their sync state, trust labels and cached
catalogues. It is independent of Qt and of the installation engine; the
interface calls it from worker threads, so mutations are serialised with a lock
while network I/O happens outside it.
"""
import hashlib
import json
import threading
import time
from dataclasses import dataclass, replace

from . import spec
from .errors import RepoError, DUPLICATE, NOT_FOUND, INVALID_INDEX
from .model import Compat, RepositorySource, RepositoryView, SyncState
from .providers import default_registry
from .providers.base import slug
from .search import search as run_search, categories as run_categories
from .store import RepositoryStore
from .transport import Transport
from .trust import TrustRegistry
from .urls import check_https_url

MAX_REPOSITORIES = 200


@dataclass
class ImportResult:
    kind: str                       # 'index' or 'list'
    added: list                     # RepositoryView per repository added
    skipped: list                   # (what, reason) for entries that were not added


class RepositoryManager:
    def __init__(self, store: RepositoryStore, transport: Transport, registry=None, trust=None, clock=time.time):
        self.store = store
        self.transport = transport
        self.registry = registry or default_registry()
        self.trust = trust or TrustRegistry.load()
        self.clock = clock
        self._lock = threading.RLock()
        self._sources = {s.id: s for s in store.load_sources()}
        self._states = {}
        self._indexes = {}

    # ---- reading -----------------------------------------------------------

    def _state(self, source):
        if source.id not in self._states:
            self._states[source.id] = self.store.load_state(source.uid)
        return self._states[source.id]

    def _index(self, source):
        """The cached, re-validated catalogue of a repository, or None."""
        state = self._state(source)
        if source.id not in self._indexes:
            raw = self.store.load_index_bytes(source.uid) if state.status in ('ok', 'error') else None
            index = None
            if raw is not None:
                try:
                    index = spec.parse_index(raw, derived=state.compat == Compat.TRANSLATED.value)
                except RepoError as error:
                    self.store.problems.append('cached index of %s is invalid (%s); refresh it' % (source.id, error.message))
            self._indexes[source.id] = index
        return self._indexes[source.id]

    def _view(self, source):
        label, note = self.trust.label_for(source.id)
        index = self._index(source)
        return RepositoryView(source, self._state(source), label, note, index.info if index else None)

    def list(self):
        with self._lock:
            return [self._view(s) for s in sorted(self._sources.values(), key=lambda s: (s.added, s.id))]

    def get(self, repository_id):
        with self._lock:
            return self._view(self._require(repository_id))

    def index(self, repository_id):
        with self._lock:
            return self._index(self._require(repository_id))

    def _require(self, repository_id):
        source = self._sources.get(repository_id)
        if not source:
            raise RepoError(NOT_FOUND, 'no such repository: %s' % repository_id)
        return source

    # ---- changing the list ---------------------------------------------------

    def add(self, url, *, provider='', name='', enabled=True):
        """Register a repository. Nothing is fetched; call refresh() to load its catalogue."""
        url = (url or '').strip()
        identity = self.registry.identify(check_https_url(url, what='Repository address'), provider)
        with self._lock:
            if identity.id in self._sources:
                raise RepoError(DUPLICATE, 'this repository is already in the list')
            if len(self._sources) >= MAX_REPOSITORIES:
                raise RepoError('limit', 'too many repositories; remove some first')
            source = RepositorySource(identity.id, identity.kind, identity.url, name.strip()[:120], enabled, self.clock(), provider)
            self._sources[source.id] = source
            self._persist()
            return self._view(source)

    def add_and_sync(self, url, **kwargs):
        view = self.add(url, **kwargs)
        return self.refresh(view.source.id)

    def import_config(self, data, *, replace_existing=False):
        """Import a repository index file (becomes a local repository) or a shared list of repository URLs."""
        kind = spec.kind_of(data)
        if kind == 'index':
            return self._import_local(data, replace_existing)
        if kind == 'list':
            added, skipped = [], []
            for entry in spec.parse_repository_list(data):
                try:
                    added.append(self.add(entry['url'], provider=entry['provider'], name=entry['name']))
                except RepoError as error:
                    skipped.append((entry['url'], error.message))
            return ImportResult('list', added, skipped)
        raise RepoError(INVALID_INDEX, 'this is neither a repository index nor a repository list')

    def _import_local(self, data, replace_existing):
        raw = data if isinstance(data, bytes) else json.dumps(data).encode('utf-8')
        index = spec.parse_index(raw)
        ident = 'local:' + (slug(index.info.id) or hashlib.sha256(raw).hexdigest()[:12])
        with self._lock:
            if ident in self._sources and not replace_existing:
                raise RepoError(DUPLICATE, 'a local repository with this id is already imported')
            old = self._sources.get(ident)
            source = replace(old) if old else RepositorySource(ident, 'local', '', '', True, self.clock())
            self._sources[ident] = source
            self.store.save_index_bytes(source.uid, raw)
            self._indexes.pop(ident, None)
            now = self.clock()
            self._states[ident] = SyncState('ok', Compat.NATIVE.value, 'Imported from a configuration file. Local imports do not update themselves; import the file again to change it.',
                                            last_sync=now, last_attempt=now, mod_count=len(index.mods), warnings=index.warnings, display_name=index.info.name)
            self.store.save_state(source.uid, self._states[ident])
            self._persist()
            return ImportResult('index', [self._view(source)], [])

    def export_config(self):
        """The user's repositories as a shareable list. Local imports have no address and are left out."""
        with self._lock:
            entries = [{'url': s.url, 'name': s.name, 'provider': s.provider} for s in self._sources.values() if s.url]
        document = {'schema': spec.LIST_SCHEMA, 'schema_version': '1.0', 'repositories': entries}
        return json.dumps(document, indent=2, ensure_ascii=False).encode('utf-8')

    def remove(self, repository_id):
        with self._lock:
            source = self._require(repository_id)
            del self._sources[repository_id]
            self._persist()
            self._states.pop(repository_id, None)
            self._indexes.pop(repository_id, None)
            self.store.delete(source.uid)

    def set_enabled(self, repository_id, enabled):
        with self._lock:
            source = self._require(repository_id)
            self._sources[repository_id] = replace(source, enabled=bool(enabled))
            self._persist()
            return self._view(self._sources[repository_id])

    def rename(self, repository_id, name):
        with self._lock:
            source = self._require(repository_id)
            self._sources[repository_id] = replace(source, name=name.strip()[:120])
            self._persist()
            return self._view(self._sources[repository_id])

    def _persist(self):
        self.store.save_sources(sorted(self._sources.values(), key=lambda s: (s.added, s.id)))

    # ---- synchronising -------------------------------------------------------

    def refresh(self, repository_id):
        """Fetch one repository now. Failures are recorded in its state, never raised: an unreachable server is a status."""
        with self._lock:
            source = self._require(repository_id)
            previous = self._state(source)
            has_cache = self._index(source) is not None
        if source.kind == 'local':
            return self.get(repository_id)
        provider = self.registry.get(source.kind)
        started = self.clock()
        try:
            if provider is None:
                raise RepoError('bad-provider', 'no provider is installed for %r repositories' % source.kind)
            result = provider.sync(source, self.transport, previous.etag if has_cache else '')
        except RepoError as error:
            return self._record(source, replace(previous, status='error', error_code=error.code, error_message=error.message, last_attempt=started))
        except Exception as error:  # a provider bug must not take the others down
            return self._record(source, replace(previous, status='error', error_code='internal', error_message='%s: %s' % (type(error).__name__, error), last_attempt=started))
        return self._apply(source, previous, result, started)

    def _apply(self, source, previous, result, started):
        base = dict(error_code='', error_message='', last_attempt=started, display_name=result.display_name or previous.display_name)
        if result.not_modified:
            state = replace(previous, status='ok', last_sync=started, **base)
            return self._record(source, state)
        if result.index is not None:
            with self._lock:
                self.store.save_index_bytes(source.uid, result.raw)
                self._indexes[source.id] = result.index
            state = SyncState('ok', result.compat.value, result.reason, '', '', started, started, result.etag, len(result.index.mods), tuple(result.warnings), result.display_name)
            return self._record(source, state)
        with self._lock:
            self._indexes[source.id] = None
            self.store.delete(source.uid)
        return self._record(source, SyncState('unsupported', result.compat.value, result.reason, '', '', previous.last_sync, started, '', 0, tuple(result.warnings), result.display_name))

    def _record(self, source, state):
        with self._lock:
            self._states[source.id] = state
            self.store.save_state(source.uid, state)
            return self._view(source)

    def refresh_all(self, *, only_enabled=True, progress=None):
        """Refresh every (enabled) repository, one after another. `progress(done, total, view)` is called after each."""
        with self._lock:
            targets = [s.id for s in self._sources.values() if s.enabled or not only_enabled]
        views = []
        for position, repository_id in enumerate(targets, 1):
            try:
                view = self.refresh(repository_id)
            except RepoError:       # removed while we were working
                continue
            views.append(view)
            if progress:
                progress(position, len(targets), view)
        return views

    # ---- searching ------------------------------------------------------------

    def _searchable(self):
        with self._lock:
            pairs = []
            for source in self._sources.values():
                if not source.enabled:
                    continue
                state = self._state(source)
                if state.status not in ('ok', 'error') or state.compat not in (Compat.NATIVE.value, Compat.TRANSLATED.value):
                    continue
                index = self._index(source)
                if index is not None:
                    pairs.append((self._view(source), index))
            return pairs

    def search(self, query='', **filters):
        """Search every enabled repository's cached catalogue. See search.search for the filters."""
        return run_search(self._searchable(), query, **filters)

    def categories(self):
        return run_categories(self._searchable())

    def find_mod(self, repository_id, mod_id):
        """(RepositoryView, Mod) for an entry in one repository's cached catalogue, or None."""
        with self._lock:
            source = self._require(repository_id)
            index = self._index(source)
            mod = index.get(mod_id) if index else None
            return (self._view(source), mod) if mod else None
