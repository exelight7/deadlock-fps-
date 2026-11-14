"""Errors raised by the repository engine.

Every failure carries a stable machine-readable `code` so the interface can
translate it, and a plain-English `message` for logs and diagnostics.
"""


class RepoError(Exception):
    """A repository operation failed. `code` is stable; `message` is for humans."""

    def __init__(self, code, message=''):
        super().__init__(message or code)
        self.code = code
        self.message = message or code

    def __str__(self):
        return self.message


# Codes (kept in one place so the UI and the docs can enumerate them).
BAD_URL = 'bad-url'                      # URL is not an acceptable HTTPS address
NETWORK = 'network'                      # connection, TLS, timeout or redirect failure
TOO_LARGE = 'too-large'                  # response exceeded the byte limit
RATE_LIMITED = 'rate-limited'            # provider asked us to slow down
INVALID_INDEX = 'invalid-index'          # JSON is not a valid repository index
UNSUPPORTED_SCHEMA = 'unsupported-schema'  # index uses a schema major we do not know
DUPLICATE = 'duplicate'                  # repository already added
NOT_FOUND = 'not-found'                  # no such repository in the store
STORE = 'store'                          # persisting state failed
DOWNLOAD_FAILED = 'download-failed'      # a package transfer failed or ended short
CANCELLED = 'cancelled'                  # the user cancelled
