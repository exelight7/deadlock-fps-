"""HTTP access for repository providers.

Providers talk to a `Transport`, never to the network directly, so they can be
tested with a scripted fake and so a different HTTP stack can be swapped in.

`UrllibTransport` is the real implementation (standard library only). Its rules:

* HTTPS with certificate verification; no downgrade, no way to disable it.
* The host is resolved once, the answer must be a public address, and the
  socket connects to that exact address. A hostname that points at
  127.0.0.1 or a private network is refused, and so is DNS rebinding.
* Redirects are followed at most 5 times, and every hop passes the same URL
  checks as the original.
* The body is read in chunks and abandoned the moment it exceeds the limit.
* No compression is requested, so a small response cannot expand into a bomb.

Known limitation: system HTTP proxies are not used (a proxy would sit between
the app and the address check). Users behind a mandatory proxy cannot sync.
"""
import hashlib
import http.client
import ipaddress
import os
import socket
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin

from .errors import RepoError, NETWORK, TOO_LARGE, BAD_URL, DOWNLOAD_FAILED, CANCELLED
from .urls import check_https_url

USER_AGENT = 'DeadlockToolbox-RepositoryManager'
MAX_REDIRECTS = 5
DEFAULT_TIMEOUT = 15.0
DOWNLOAD_TIMEOUT = 30.0      # per socket operation: a stalled transfer fails, a slow one does not
TOTAL_DEADLINE = 45.0


@dataclass(frozen=True)
class Response:
    status: int
    body: bytes = b''
    headers: dict = field(default_factory=dict)   # lower-case header names
    url: str = ''                                  # final URL after redirects

    @property
    def ok(self):
        return self.status == 200

    def header(self, name, default=''):
        return self.headers.get(name.lower(), default)


@dataclass(frozen=True)
class DownloadResult:
    size: int
    sha256: str
    url: str                     # final URL after redirects


class Transport:
    """Interface. `get` returns a Response for every HTTP status; it raises RepoError only when no response could be had."""

    def get(self, url, *, max_bytes, headers=None, timeout=DEFAULT_TIMEOUT):
        raise NotImplementedError

    def download(self, url, destination, *, max_bytes, expected_size=None, progress=None, cancel=None, timeout=DOWNLOAD_TIMEOUT):
        """Stream to a new file and return a DownloadResult. Raises RepoError(too-large | download-failed | cancelled | network)."""
        raise NotImplementedError


def resolve_public(host, port=443, resolver=socket.getaddrinfo):
    """(family, sockaddr) of the first address for `host`; refuse when any answer is non-public."""
    try:
        answers = resolver(host, port, type=socket.SOCK_STREAM)
    except OSError as error:
        raise RepoError(NETWORK, 'cannot resolve %s: %s' % (host, error)) from None
    addresses = []
    for family, _, _, _, sockaddr in answers:
        address = ipaddress.ip_address(sockaddr[0].split('%')[0])
        if not address.is_global:
            # One private answer is enough to refuse: a mixed answer is how rebinding attacks work.
            raise RepoError(NETWORK, '%s resolves to a non-public address; refused' % host)
        addresses.append((family, sockaddr))
    if not addresses:
        raise RepoError(NETWORK, 'no address found for %s' % host)
    return addresses[0]


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Connects to the address validated by `resolve_public`, verifying TLS against the hostname."""

    def connect(self):
        family, sockaddr = resolve_public(self.host, self.port or 443)
        sock = socket.socket(family, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect(sockaddr)
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise


_CONTEXT = None


def _default_context():
    # Loading the system certificate store costs ~40 ms; the verified default context is built once and shared.
    global _CONTEXT
    if _CONTEXT is None:
        _CONTEXT = ssl.create_default_context()
    return _CONTEXT


class _PinnedHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self):
        super().__init__(context=_default_context())

    def https_open(self, request):
        return self.do_open(lambda host, **kw: _PinnedHTTPSConnection(host, **kw), request, context=self._context)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Redirects surface as HTTPError so `get` can validate every hop itself."""

    def redirect_request(self, *args, **kwargs):
        return None


def _build_opener():
    # Not build_opener(): that would add proxy, plain-HTTP, file and FTP handlers, any of which could bypass the pinning above.
    opener = urllib.request.OpenerDirector()
    for handler in (_PinnedHTTPSHandler(), urllib.request.HTTPDefaultErrorHandler(), _NoRedirect(), urllib.request.HTTPErrorProcessor()):
        opener.add_handler(handler)
    return opener


class UrllibTransport(Transport):
    def __init__(self, user_agent=USER_AGENT):
        self.user_agent = user_agent
        self._opener = _build_opener()

    def _follow(self, url, headers, timeout):
        """Open `url`, following at most MAX_REDIRECTS redirects that each pass the URL checks.

        Returns (reply, final_url); `reply` is a response or an HTTPError (which is also a readable response).
        The caller must close it.
        """
        current = check_https_url(url)
        for _ in range(MAX_REDIRECTS + 1):
            request = urllib.request.Request(current, headers={'User-Agent': self.user_agent, 'Accept-Encoding': 'identity', **(headers or {})})
            try:
                return self._opener.open(request, timeout=timeout), current
            except urllib.error.HTTPError as error:
                if error.code not in (301, 302, 303, 307, 308):
                    return error, current
                with error:
                    location = error.headers.get('Location')
                    if not location:
                        raise RepoError(NETWORK, 'redirect without a location') from None
                    try:
                        current = check_https_url(urljoin(current, location), what='redirect target')
                    except RepoError as bad:
                        raise RepoError(BAD_URL, 'refused redirect: %s' % bad.message) from None
            except RepoError:
                raise
            except (urllib.error.URLError, OSError, ssl.SSLError, http.client.HTTPException) as error:
                reason = getattr(error, 'reason', error)
                raise RepoError(NETWORK, 'cannot reach %s: %s' % (current.split('/')[2], reason)) from None
        raise RepoError(NETWORK, 'too many redirects')

    def get(self, url, *, max_bytes, headers=None, timeout=DEFAULT_TIMEOUT):
        deadline = time.monotonic() + TOTAL_DEADLINE
        reply, current = self._follow(url, headers, timeout)
        with reply:
            if isinstance(reply, urllib.error.HTTPError):
                body = reply.read(min(max_bytes, 65536) + 1)[:max_bytes]
                return Response(reply.code, body, {k.lower(): v for k, v in reply.headers.items()}, current)
            return self._read(reply, current, max_bytes, deadline)

    def download(self, url, destination, *, max_bytes, expected_size=None, progress=None, cancel=None, timeout=DOWNLOAD_TIMEOUT):
        """Stream a file to `destination` (a path that does not exist yet) while hashing it.

        Memory use is constant. The transfer is abandoned, and the partial file removed, the moment it exceeds
        `max_bytes` or `expected_size`, stalls, is cancelled, or ends short of `expected_size`.
        Returns a DownloadResult; raises RepoError otherwise.
        """
        reply, current = self._follow(url, {'Accept': 'application/octet-stream'}, timeout)
        with reply:
            status = reply.code if isinstance(reply, urllib.error.HTTPError) else reply.status
            if status != 200:
                raise RepoError(DOWNLOAD_FAILED, 'the server answered HTTP %d' % status)
            limit = min(max_bytes, expected_size) if expected_size else max_bytes
            declared = reply.headers.get('Content-Length')
            if declared and declared.isdigit() and int(declared) > limit:
                raise RepoError(TOO_LARGE, 'the file is larger than the allowed %d bytes' % limit)
            digest, total, last_data = hashlib.sha256(), 0, time.monotonic()
            destination = Path(destination)
            created = False
            try:
                with open(destination, 'xb') as out:
                    created = True            # only a file this call created may be removed on failure
                    while True:
                        if cancel is not None and cancel.is_set():
                            raise RepoError(CANCELLED, 'cancelled')
                        chunk = reply.read(256 * 1024)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > limit:
                            raise RepoError(TOO_LARGE, 'the file is larger than the allowed %d bytes' % limit)
                        digest.update(chunk)
                        out.write(chunk)
                        last_data = time.monotonic()
                        if progress:
                            progress(total, expected_size or int(declared or 0))
                    out.flush()
                    os.fsync(out.fileno())
                if expected_size and total != expected_size:
                    raise RepoError(DOWNLOAD_FAILED, 'the download ended after %d of %d bytes' % (total, expected_size))
                if not total:
                    raise RepoError(DOWNLOAD_FAILED, 'the server sent an empty file')
            except (OSError, ssl.SSLError, http.client.HTTPException) as error:
                if created:
                    destination.unlink(missing_ok=True)
                raise RepoError(DOWNLOAD_FAILED, 'the transfer failed: %s' % error) from None
            except BaseException:
                if created:
                    destination.unlink(missing_ok=True)
                raise
            return DownloadResult(total, digest.hexdigest(), current)

    @staticmethod
    def _read(reply, url, max_bytes, deadline):
        declared = reply.headers.get('Content-Length')
        if declared and declared.isdigit() and int(declared) > max_bytes:
            raise RepoError(TOO_LARGE, 'response is larger than %d bytes' % max_bytes)
        chunks, total = [], 0
        while True:
            if time.monotonic() > deadline:
                raise RepoError(NETWORK, 'the server was too slow')
            chunk = reply.read(64 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise RepoError(TOO_LARGE, 'response is larger than %d bytes' % max_bytes)
            chunks.append(chunk)
        return Response(reply.status, b''.join(chunks), {k.lower(): v for k, v in reply.headers.items()}, url)
