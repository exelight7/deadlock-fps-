"""On-disk state for the Repository Manager.

    <folder>/sources.json        the repositories the user added
    <folder>/state/<uid>.json    what the last sync learned (status, errors, etag, warnings)
    <folder>/index/<uid>.json    the validated index document that sync produced

Every write is atomic (temp file, fsync, rename). Reads are size-limited and a
damaged file is reported and ignored rather than crashing start-up: a corrupt
cache only means "refresh again".
"""
import json
import os
import tempfile
from dataclasses import asdict, fields
from pathlib import Path

from .errors import RepoError, STORE
from .model import RepositorySource, SyncState

SOURCES_SCHEMA = 'deadlock-toolbox-repositories'
MAX_FILE = 16 * 1024 * 1024


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.repo-')
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    except OSError as error:
        raise RepoError(STORE, 'cannot write %s: %s' % (path.name, error)) from None
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _read(path):
    path = Path(path)
    if path.stat().st_size > MAX_FILE:
        raise ValueError('file is too large')
    return path.read_bytes()


def _known(cls, data):
    names = {f.name for f in fields(cls)}
    return {k: v for k, v in data.items() if k in names}


class RepositoryStore:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.problems = []          # human-readable notes about files that could not be read

    # sources
    def load_sources(self):
        path = self.folder / 'sources.json'
        try:
            document = json.loads(_read(path).decode('utf-8'))
            if document.get('schema') != SOURCES_SCHEMA:
                raise ValueError('unknown schema')
            sources = []
            for item in document.get('sources', []):
                item = _known(RepositorySource, item)
                item['added'] = float(item.get('added', 0.0))
                sources.append(RepositorySource(**item))
            return sources
        except FileNotFoundError:
            return []
        except (OSError, ValueError, TypeError, AttributeError) as error:
            self.problems.append('sources.json could not be read (%s); starting with no repositories' % error)
            return []

    def save_sources(self, sources):
        document = {'schema': SOURCES_SCHEMA, 'version': 1, 'sources': [asdict(s) for s in sources]}
        atomic_write(self.folder / 'sources.json', json.dumps(document, indent=2, ensure_ascii=False).encode('utf-8'))

    # sync state
    def load_state(self, uid):
        try:
            data = json.loads(_read(self.folder / 'state' / (uid + '.json')).decode('utf-8'))
            data = _known(SyncState, data)
            data['warnings'] = tuple(str(w) for w in data.get('warnings', ()))[:200]
            return SyncState(**data)
        except FileNotFoundError:
            return SyncState()
        except (OSError, ValueError, TypeError, AttributeError) as error:
            self.problems.append('state of %s could not be read (%s)' % (uid, error))
            return SyncState()

    def save_state(self, uid, state):
        atomic_write(self.folder / 'state' / (uid + '.json'), json.dumps(asdict(state), indent=2, ensure_ascii=False).encode('utf-8'))

    # cached index
    def load_index_bytes(self, uid):
        try:
            return _read(self.folder / 'index' / (uid + '.json'))
        except FileNotFoundError:
            return None
        except OSError as error:
            self.problems.append('index of %s could not be read (%s)' % (uid, error))
            return None

    def save_index_bytes(self, uid, data):
        atomic_write(self.folder / 'index' / (uid + '.json'), data)

    def delete(self, uid):
        for part in ('state', 'index'):
            try:
                (self.folder / part / (uid + '.json')).unlink()
            except FileNotFoundError:
                pass
            except OSError as error:
                raise RepoError(STORE, 'cannot remove cached data: %s' % error) from None
