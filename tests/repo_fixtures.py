"""Shared helpers for the repository-engine tests: a scripted transport and sample documents."""
import copy
import json

from deadlock_fps.repos.errors import RepoError, NETWORK
from deadlock_fps.repos.transport import Transport, Response

SHA = 'a' * 64


class FakeTransport(Transport):
    """Maps exact URLs to a Response, an exception to raise, or a callable(url, headers). Unknown URLs are 404."""

    def __init__(self, routes=None):
        self.routes = dict(routes or {})
        self.calls = []

    def get(self, url, *, max_bytes, headers=None, timeout=15.0):
        self.calls.append((url, dict(headers or {})))
        target = self.routes.get(url)
        if callable(target):
            target = target(url, headers or {})
        if isinstance(target, Exception):
            raise target
        if target is None:
            return Response(404, b'{}', {}, url)
        if len(target.body) > max_bytes:
            raise RepoError('too-large', 'response is larger than the limit')
        return target

    def urls(self):
        return [c[0] for c in self.calls]


def ok(payload, **headers):
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode('utf-8')
    return Response(200, body, {k.lower().replace('_', '-'): v for k, v in headers.items()}, '')


def status(code, **headers):
    return Response(code, b'{}', {k.lower().replace('_', '-'): v for k, v in headers.items()}, '')


def version(number='1.0.0', **overrides):
    entry = {
        'version': number, 'published': '2026-03-18', 'changelog': 'Initial release.',
        'game': {'min_build': 100, 'tested_build': 150},
        'package': {'format': 'vpk', 'url': 'https://files.example.org/mods/skin-%s.vpk' % number, 'size': 4096, 'sha256': SHA},
        'install': {'type': 'vpk', 'files': [{'source': ''}]},
    }
    entry.update(overrides)
    return entry


def mod(ident='crimson-skin', **overrides):
    entry = {
        'id': ident, 'name': 'Crimson Skin', 'summary': 'A red recolour.', 'description': 'Long text.',
        'author': 'Mira', 'license': 'CC-BY-4.0', 'categories': ['Skins', 'characters'], 'tags': ['red'],
        'homepage': 'https://example.org/crimson', 'source_url': 'https://github.com/mira/crimson',
        'screenshots': ['https://example.org/crimson/1.png'], 'published': '2026-03-18',
        'versions': [version('1.0.0'), version('1.1.0', published='2026-04-01')],
    }
    entry.update(overrides)
    return entry


def index(*mods, name='Example Mods', ident='example-mods', **overrides):
    document = {
        'schema': 'deadlock-mod-repository', 'schema_version': '1.0',
        'repository': {'id': ident, 'name': name, 'description': 'Community mods.', 'homepage': 'https://example.org', 'maintainer': 'Mira'},
        'mods': list(mods) or [mod()],
    }
    document.update(overrides)
    return document


def clone(value):
    return copy.deepcopy(value)


# ---- GitHub API payloads ----------------------------------------------------

def gh_repo(branch='main', description='Skins for Deadlock', license_id='MIT'):
    return {'default_branch': branch, 'description': description, 'license': {'spdx_id': license_id}}


def gh_asset(owner, repo, tag, name, size=2048, digest=SHA, state='uploaded'):
    asset = {'name': name, 'state': state, 'size': size,
             'browser_download_url': 'https://github.com/%s/%s/releases/download/%s/%s' % (owner, repo, tag, name)}
    if digest:
        asset['digest'] = 'sha256:' + digest
    return asset


def gh_release(tag, assets, prerelease=False, draft=False, body='Notes'):
    return {'tag_name': tag, 'draft': draft, 'prerelease': prerelease, 'published_at': '2026-05-01T10:00:00Z', 'body': body, 'assets': assets}
