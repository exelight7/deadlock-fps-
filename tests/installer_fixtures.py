"""Fixtures for the installation-engine tests: a throwaway game folder, a transport that serves real bytes, a VPK builder."""
import hashlib
import io
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from deadlock_fps.core import ASSETS
from deadlock_fps.installer import Installer
from deadlock_fps.repos import spec
from deadlock_fps.repos.errors import RepoError
from deadlock_fps.repos.model import RepositorySource, RepositoryView, SyncState, Trust
from deadlock_fps.repos.transport import DownloadResult
from repo_fixtures import FakeTransport, index, mod as mod_doc, version as version_doc

HOST = 'https://files.example.org/'


def make_vpk(paths=('materials/shared/skin.vmat',), payload=b'DATA'):
    """A valid single-file VPK providing `paths`."""
    by_extension = {}
    for path in paths:
        directory, _, filename = path.rpartition('/')
        stem, _, extension = filename.rpartition('.')
        by_extension.setdefault(extension, {}).setdefault(directory or ' ', []).append(stem)
    tree, data = b'', b''
    for extension, directories in by_extension.items():
        tree += extension.encode() + b'\0'
        for directory, stems in directories.items():
            tree += directory.encode() + b'\0'
            for stem in stems:
                chunk = payload + stem.encode()
                tree += stem.encode() + b'\0' + struct.pack('<IHHIIH', 0, 0, 0x7FFF, len(data), len(chunk), 0xFFFF)
                data += chunk
            tree += b'\0'
        tree += b'\0'
    tree += b'\0'
    return struct.pack('<III', 0x55AA1234, 1, len(tree)) + tree + data


def make_zip(members, extra=None):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in {**members, **(extra or {})}.items():
            archive.writestr(name, data)
    return buffer.getvalue()


class ServingTransport(FakeTransport):
    """FakeTransport that also implements download() from an in-memory table, with the real transport's limits."""

    def __init__(self, files=None):
        super().__init__()
        self.files = dict(files or {})
        self.downloads = []
        self.fail_first = {}

    def download(self, url, destination, *, max_bytes, expected_size=None, progress=None, cancel=None, timeout=30.0):
        self.downloads.append(url)
        if self.fail_first.get(url):
            self.fail_first[url] -= 1
            raise RepoError('download-failed', 'the server answered HTTP 503')
        data = self.files.get(url)
        if data is None:
            raise RepoError('download-failed', 'the server answered HTTP 404')
        limit = min(max_bytes, expected_size) if expected_size else max_bytes
        if len(data) > limit:
            raise RepoError('too-large', 'the file is larger than the allowed %d bytes' % limit)
        if cancel is not None and cancel.is_set():
            raise RepoError('cancelled', 'cancelled')
        Path(destination).write_bytes(data)
        if progress:
            progress(len(data), len(data))
        if expected_size and len(data) != expected_size:
            Path(destination).unlink()
            raise RepoError('download-failed', 'the download ended after %d of %d bytes' % (len(data), expected_size))
        return DownloadResult(len(data), hashlib.sha256(data).hexdigest(), url)


def view(repository_id='https:mods.example.org/index.json', trust=Trust.COMMUNITY, enabled=True, name='Example Mods'):
    source = RepositorySource(repository_id, 'https', 'https://mods.example.org/index.json', name, enabled)
    return RepositoryView(source, SyncState(status='ok', compat='native'), trust, '')


def mod_document(ident, versions, **extra):
    """The index entry (a dict) for one mod. `versions`: dicts with version, data (bytes), format, install, and overrides."""
    docs = []
    for spec_ in versions:
        data = spec_['data']
        fmt = spec_.get('format', 'vpk')
        url = spec_.get('url', '%s%s-%s.%s' % (HOST, ident, spec_['version'], fmt))
        package = {'format': fmt, 'url': url, 'size': spec_.get('size', len(data))}
        if spec_.get('hash', True):
            package['sha256'] = spec_.get('sha256', hashlib.sha256(data).hexdigest())
        package.update(spec_.get('package', {}))
        entry = version_doc(spec_['version'], package=package, install=spec_.get('install', {'type': 'vpk', 'files': [{'source': ''}] if fmt == 'vpk' else []}))
        for key in ('dependencies', 'conflicts', 'game', 'yanked', 'prerelease', 'published', 'changelog'):
            if key in spec_:
                entry[key] = spec_[key]
        docs.append(entry)
    return mod_doc(ident, name=extra.pop('name', ident.title()), versions=docs, author='Mira', **extra)


def catalogue_mod(ident, versions, **extra):
    """Parse a real Mod from `mod_document`."""
    parsed = spec.parse_index(index(mod_document(ident, versions, **extra)))
    assert parsed.mods, parsed.warnings
    return parsed.mods[0]


class GameCase(unittest.TestCase):
    """A fake Deadlock folder without an addons path (as Valve ships it), a serving transport, and an Installer on them."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'Deadlock'
        self.gi = self.root / 'game/citadel/gameinfo.gi'
        self.gi.parent.mkdir(parents=True)
        text = (ASSETS / 'reference/gameinfo.gi').read_text(encoding='utf-8').replace('            Game          "citadel/addons"\n', '')
        self.gi.write_text(text, encoding='utf-8')
        self.original_gi = self.gi.read_bytes()
        self.addons = self.root / 'game/citadel/addons'
        for target in ('deadlock_fps.core.ensure_closed',):
            patcher = patch(target)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.transport = ServingTransport()
        self.running = False
        self.installer = self.new_installer()

    def new_installer(self, **kwargs):
        def guard():
            if self.running:
                raise ValueError('Close Deadlock first.')
        return Installer(self.root, self.transport, guard=guard, **kwargs)

    def serve(self, mod):
        for v in mod.versions:
            pass

    def offer(self, ident, versions, **extra):
        """Create a catalogue mod and put its package bytes on the serving transport."""
        for spec_ in versions:
            fmt = spec_.get('format', 'vpk')
            url = spec_.get('url', '%s%s-%s.%s' % (HOST, ident, spec_['version'], fmt))
            self.transport.files[url] = spec_['data']
        return catalogue_mod(ident, versions, **extra)

    def install(self, mod, version=None, repo=None, ack=True):
        repo = repo or view()
        chosen = mod.find(version) if version else mod.latest()
        plan = self.installer.prepare(repo, mod, chosen)
        return self.installer.commit(plan, acknowledged=ack)

    def game_snapshot(self):
        return {str(p.relative_to(self.root / 'game')): p.read_bytes() for p in (self.root / 'game').rglob('*') if p.is_file()}

    def addon_names(self):
        return sorted(p.name for p in self.addons.glob('*')) if self.addons.exists() else []
