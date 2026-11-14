"""Any HTTPS server that publishes a repository index.

This is the independent-hosting path: a static file on a web server, object
storage, GitHub Pages, or a purpose-built mod server. The URL may name the
index file directly, or a directory-like address, in which case
`deadlock-repo.json` is requested beneath it.
"""
from urllib.parse import urlsplit, urlunsplit

from .base import Provider, Identity, SyncResult, INDEX_FILENAME, native_result, check_status
from ..errors import RepoError, BAD_URL
from ..model import Compat
from ..spec import MAX_INDEX_BYTES
from ..urls import check_https_url, canonical_https_id


class NativeHttpsProvider(Provider):
    kind = 'https'
    label = 'Custom HTTPS repository'

    def identify(self, url, hint=''):
        try:
            clean = check_https_url(url)
        except RepoError:
            return None
        return Identity(canonical_https_id(clean), self.kind, clean)

    @staticmethod
    def candidates(url):
        parts = urlsplit(url)
        if parts.path.lower().endswith('.json'):
            return [url]
        base = parts.path.rstrip('/')
        return [urlunsplit(('https', parts.netloc, base + '/' + INDEX_FILENAME, parts.query, ''))]

    def sync(self, source, transport, etag=''):
        last = None
        for candidate in self.candidates(source.url):
            headers = {'Accept': 'application/json'}
            if etag:
                headers['If-None-Match'] = etag
            response = transport.get(candidate, max_bytes=MAX_INDEX_BYTES, headers=headers)
            if response.status == 304:
                return SyncResult(Compat.NATIVE, not_modified=True, etag=etag, reason='Index unchanged since the last sync.')
            check_status(response, candidate.split('/')[2])
            if response.status == 404:
                last = candidate
                continue
            return native_result(response, derived_from=candidate.rsplit('/', 1)[-1])
        return SyncResult(Compat.UNSUPPORTED, reason='No repository index was found at %s (HTTP 404).' % last)
