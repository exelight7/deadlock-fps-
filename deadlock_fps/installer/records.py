"""What is installed, and how it got there. One JSON file per game install, written atomically.

    <game>/.deadlock-fps-studio/mods/installed.json
"""
import json
import os
import re
import tempfile
from dataclasses import dataclass, field, asdict, fields
from pathlib import Path

from .errors import InstallError, DISK

SCHEMA = 'deadlock-toolbox-installed'
MAX_FILE = 8 * 1024 * 1024
PAK = re.compile(r'pak(\d{2})_dir\.vpk', re.IGNORECASE)
MAX_LOG = 300


def pak_name(slot):
    return 'pak%02d_dir.vpk' % slot


def pak_slot(name):
    match = PAK.fullmatch(name)
    return int(match.group(1)) if match else None


@dataclass(frozen=True)
class InstalledFile:
    name: str            # the file in game/citadel/addons, e.g. pak04_dir.vpk
    sha256: str
    size: int
    source: str = ''     # path inside the package it came from


@dataclass(frozen=True)
class Previous:
    version: str
    backup: str          # transaction id of the backup folder
    files: tuple         # names inside that folder
    at: str = ''


@dataclass
class InstalledMod:
    repository_id: str
    mod_id: str
    name: str
    version: str
    files: tuple
    enabled: bool = True
    author: str = ''
    repository_name: str = ''
    trust: str = 'UNVERIFIED'
    source_url: str = ''
    package_url: str = ''
    package_sha256: str = ''
    package_verified: bool = False     # True only when the publisher's SHA-256 matched the download
    installed_at: str = ''
    updated_at: str = ''
    dependencies: tuple = ()           # ((mod_id, range), ...)
    conflicts: tuple = ()              # ((mod_id, range, reason), ...)
    previous: tuple = ()
    history: tuple = ()                # ({'at', 'action', 'version', 'note'}, ...)

    @property
    def key(self):
        return (self.repository_id, self.mod_id)

    def file_names(self):
        return [f.name for f in self.files]


def _mod_from(data):
    names = {f.name for f in fields(InstalledMod)}
    data = {k: v for k, v in data.items() if k in names}
    data['files'] = tuple(InstalledFile(**{k: v for k, v in f.items() if k in ('name', 'sha256', 'size', 'source')}) for f in data.get('files', []))
    data['previous'] = tuple(Previous(version=p['version'], backup=p['backup'], files=tuple(p['files']), at=p.get('at', '')) for p in data.get('previous', []))
    data['dependencies'] = tuple(tuple(x) for x in data.get('dependencies', []))
    data['conflicts'] = tuple(tuple(x) for x in data.get('conflicts', []))
    data['history'] = tuple(dict(h) for h in data.get('history', []))[-60:]
    return InstalledMod(**data)


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.mods-')
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    except OSError as error:
        raise InstallError(DISK, 'cannot write %s: %s' % (path.name, error)) from None
    finally:
        if os.path.exists(name):
            os.unlink(name)


class InstalledStore:
    def __init__(self, path):
        self.path = Path(path)
        self.problem = ''

    def load(self):
        """(mods dict keyed by (repository_id, mod_id), log list). A damaged file is reported in `problem`, not raised."""
        try:
            if self.path.stat().st_size > MAX_FILE:
                raise ValueError('file is too large')
            document = json.loads(self.path.read_text(encoding='utf-8'))
            if document.get('schema') != SCHEMA:
                raise ValueError('unknown schema')
            mods = {}
            for item in document.get('mods', []):
                mod = _mod_from(item)
                mods[mod.key] = mod
            return mods, list(document.get('log', []))[-MAX_LOG:]
        except FileNotFoundError:
            return {}, []
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
            self.problem = 'installed.json could not be read (%s)' % error
            return {}, []

    def save(self, mods, log):
        document = {'schema': SCHEMA, 'version': 1, 'mods': [asdict(m) for m in sorted(mods.values(), key=lambda m: (m.name.lower(), m.key))], 'log': log[-MAX_LOG:]}
        atomic_write(self.path, json.dumps(document, indent=2, ensure_ascii=False).encode('utf-8'))
