"""A tiny on-disk cache for public answers, so opening the page costs nothing and the server is asked rarely.

One JSON file per key under the folder, written atomically. A file that is unreadable, too large or from the future is
treated as missing (it is a cache: wrong is worse than empty). Personal data is never put here.
"""
import json
import os
import re
import tempfile
import time
from pathlib import Path

MAX_FILE = 8 * 1024 * 1024
_KEY = re.compile(r'[a-z0-9][a-z0-9._-]{0,79}')


class Cache:
    def __init__(self, folder, clock=time.time):
        self.folder = Path(folder)
        self.clock = clock

    def _path(self, key):
        if not _KEY.fullmatch(key):
            raise ValueError('bad cache key')
        return self.folder / (key + '.json')

    def get(self, key, ttl):
        """(data, saved_at) when a copy younger than `ttl` seconds exists, else None."""
        path = self._path(key)
        try:
            if path.stat().st_size > MAX_FILE:
                return None
            document = json.loads(path.read_text(encoding='utf-8'))
            saved, data = int(document['at']), document['data']
        except (OSError, ValueError, KeyError, TypeError, OverflowError, RecursionError):
            return None
        now = self.clock()
        return (data, saved) if 0 <= now - saved <= ttl else None

    def put(self, key, data):
        """Save `data` (JSON-serialisable). A failure to write is not an error: the cache just stays empty."""
        path = self._path(key)
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
            handle, temporary = tempfile.mkstemp(dir=str(self.folder), prefix=key + '.', suffix='.tmp')
            with os.fdopen(handle, 'w', encoding='utf-8') as out:
                json.dump({'at': int(self.clock()), 'data': data}, out)
            os.replace(temporary, path)
        except (OSError, TypeError, ValueError):
            try:
                os.unlink(temporary)
            except (OSError, UnboundLocalError):
                pass

    def clear(self):
        for path in self.folder.glob('*.json'):
            try:
                path.unlink()
            except OSError:
                pass
