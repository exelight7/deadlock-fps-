"""URL safety and repository identity.

Every URL that enters the engine, whether typed by a user or read from a
remote index, passes `check_https_url` first. The rules are deliberately
strict because an index is untrusted input:

* HTTPS only, default port only, no embedded credentials;
* no `localhost`, single-label or non-public IP-literal hosts, so a remote
  index cannot aim the app at the user's own machine or home network;
* no control characters or whitespace, bounded length.
"""
import ipaddress
import re
from urllib.parse import urlsplit, urlunsplit, quote, unquote

from .errors import RepoError, BAD_URL

MAX_URL = 2048
_UNSAFE = re.compile(r'[\x00-\x20\x7f\\]')
_BLOCKED_SUFFIXES = ('.localhost', '.local', '.internal', '.lan', '.home.arpa')


def is_public_host(host):
    """Hostname or IP literal that could plausibly be a public server."""
    if not host or len(host) > 253:
        return False
    host = host.lower().rstrip('.')
    try:
        address = ipaddress.ip_address(host.strip('[]'))
        return address.is_global
    except ValueError:
        pass
    if host == 'localhost' or '.' not in host or host.endswith(_BLOCKED_SUFFIXES):
        return False
    if not re.fullmatch(r'[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+', host):
        return False
    return True


def check_https_url(value, *, what='URL'):
    """Return a normalised https URL (lower-case host, no fragment) or raise RepoError(BAD_URL)."""
    if not isinstance(value, str) or not value or len(value) > MAX_URL or _UNSAFE.search(value):
        raise RepoError(BAD_URL, '%s is empty, too long or contains unsafe characters' % what)
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError:
        raise RepoError(BAD_URL, '%s is not a valid address' % what) from None
    if parts.scheme != 'https':
        raise RepoError(BAD_URL, '%s must use https://' % what)
    if parts.username is not None or parts.password is not None:
        raise RepoError(BAD_URL, '%s must not contain credentials' % what)
    if port not in (None, 443):
        raise RepoError(BAD_URL, '%s must use the default HTTPS port' % what)
    host = (parts.hostname or '').lower()
    try:
        host = host.encode('idna').decode('ascii')
    except UnicodeError:
        raise RepoError(BAD_URL, '%s has an invalid host name' % what) from None
    if not is_public_host(host):
        raise RepoError(BAD_URL, '%s must point to a public host' % what)
    netloc = '[%s]' % host if ':' in host else host
    return urlunsplit(('https', netloc, parts.path or '/', parts.query, ''))


def host_of(url):
    return (urlsplit(url).hostname or '').lower()


# ---- repository identity -------------------------------------------------

_SEGMENT = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]*')
GITHUB_HOSTS = ('github.com', 'www.github.com')


def _segments(path):
    return [unquote(s) for s in path.split('/') if s]


def github_identity(url):
    """('owner', 'repo') for a github.com repository URL, or None."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if parts.scheme != 'https' or (parts.hostname or '').lower() not in GITHUB_HOSTS:
        return None
    segments = _segments(parts.path)
    if len(segments) < 2:
        return None
    owner, repo = segments[0], segments[1].removesuffix('.git')
    if not _SEGMENT.fullmatch(owner) or not _SEGMENT.fullmatch(repo) or repo in ('.', '..'):
        return None
    return owner, repo


def gitlab_identity(url, hosts=('gitlab.com', 'www.gitlab.com')):
    """(host, 'group/sub/project') for a GitLab project URL, or None."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    host = (parts.hostname or '').lower()
    if parts.scheme != 'https' or (hosts is not None and host not in hosts):
        return None
    segments = _segments(parts.path)
    if '-' in segments:
        segments = segments[:segments.index('-')]
    if len(segments) < 2:
        return None
    segments[-1] = segments[-1].removesuffix('.git')
    if not all(_SEGMENT.fullmatch(s) and s not in ('.', '..') for s in segments):
        return None
    return host.removeprefix('www.'), '/'.join(segments)


def canonical_https_id(url):
    """Stable identity of a custom HTTPS repository: host plus path, no query or trailing slash."""
    parts = urlsplit(check_https_url(url))
    return 'https:' + parts.hostname + (parts.path.rstrip('/') or '')


def quote_path(value):
    return quote(value, safe='')
