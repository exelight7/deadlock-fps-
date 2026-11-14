"""The repository provider contract.

A provider knows one hosting convention. It can

* `identify` a URL it understands, producing the canonical identity that trust
  and de-duplication are based on, and
* `sync` a repository, returning a `SyncResult` that says how compatible the
  repository is and, when it is, the validated catalogue.

Providers never install anything and never touch the game folder. They return
data; the manager stores it and the installer (a separate module) consumes it.
Adding a new hosting source means writing one class and registering it; no
other module changes.
"""
import json
import re
from dataclasses import dataclass, field

from ..errors import RepoError, NETWORK, RATE_LIMITED, INVALID_INDEX, UNSUPPORTED_SCHEMA, TOO_LARGE
from ..model import Compat
from ..spec import parse_index, MAX_INDEX_BYTES

INDEX_FILENAME = 'deadlock-repo.json'
API_LIMIT = 4 * 1024 * 1024


@dataclass(frozen=True)
class Identity:
    id: str            # canonical, e.g. 'github:owner/repo'
    kind: str          # provider kind
    url: str           # normalised URL to keep
    name_hint: str = ''


@dataclass
class SyncResult:
    compat: Compat
    index: object = None           # RepositoryIndex when compat is NATIVE or TRANSLATED
    reason: str = ''               # human-readable explanation, always set when not NATIVE
    etag: str = ''
    not_modified: bool = False     # server confirmed the cached index is current
    display_name: str = ''
    warnings: tuple = field(default_factory=tuple)
    raw: bytes = b''               # the exact validated document, cached and re-validated on load
    derived: bool = False          # True when a provider generated the document from release metadata


class Provider:
    kind = ''
    label = ''

    def identify(self, url, hint=''):
        """Return an Identity when this provider handles `url`, else None. Must not touch the network."""
        raise NotImplementedError

    def sync(self, source, transport, etag=''):
        """Fetch and classify the repository. Raise RepoError only for failures that say nothing about compatibility (network, rate limit)."""
        raise NotImplementedError


class ProviderRegistry:
    """Ordered list of providers; the first that recognises a URL wins."""

    def __init__(self, providers=()):
        self._providers = list(providers)

    def register(self, provider, *, first=False):
        if any(p.kind == provider.kind for p in self._providers):
            raise ValueError('provider %r is already registered' % provider.kind)
        self._providers.insert(0 if first else len(self._providers), provider)

    @property
    def kinds(self):
        return [p.kind for p in self._providers]

    def get(self, kind):
        return next((p for p in self._providers if p.kind == kind), None)

    def identify(self, url, hint=''):
        if hint:
            provider = self.get(hint)
            if not provider:
                raise RepoError('bad-provider', 'unknown provider %r (known: %s)' % (hint, ', '.join(self.kinds)))
            identity = provider.identify(url, hint)
            if identity:
                return identity
        else:
            for provider in self._providers:
                identity = provider.identify(url, '')
                if identity:
                    return identity
        raise RepoError('bad-url', 'no provider understands this address')


# ---- helpers shared by providers ----------------------------------------

def slug(text, limit=63):
    text = re.sub(r'[^a-z0-9._-]+', '-', text.lower()).strip('-._')
    return text[:limit].strip('-._')


def get_json(transport, url, headers=None, limit=API_LIMIT):
    """(Response, parsed JSON or None). The body is only parsed for 200 responses."""
    response = transport.get(url, max_bytes=limit, headers=headers)
    if response.status != 200:
        return response, None
    try:
        return response, json.loads(response.body.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        raise RepoError(NETWORK, 'the server did not return JSON for %s' % url.split('/')[2]) from None


def native_result(response, *, derived_from=''):
    """Parse a fetched index. A malformed index is a compatibility answer (UNSUPPORTED), not a crash."""
    try:
        index = parse_index(response.body)
    except RepoError as error:
        if error.code in (INVALID_INDEX, UNSUPPORTED_SCHEMA, TOO_LARGE):
            return SyncResult(Compat.UNSUPPORTED, reason='%s is not a usable repository index: %s' % (derived_from or 'The file', error.message))
        raise
    return SyncResult(Compat.NATIVE, index, reason='Publishes the Deadlock mod repository specification %s.' % index.schema_version,
                      etag=response.header('etag'), display_name=index.info.name, warnings=index.warnings, raw=response.body)


def check_status(response, what):
    """Translate unexpected HTTP statuses into RepoErrors; 200 and 404 are handled by callers."""
    if response.status == 429 or (response.status == 403 and response.header('x-ratelimit-remaining') == '0'):
        raise RepoError(RATE_LIMITED, '%s is rate limiting requests; try again later' % what)
    if response.status not in (200, 404):
        raise RepoError(NETWORK, '%s answered with HTTP %d' % (what, response.status))
