"""Local SQLite catalogue of store listings.

The store crawls GameBanana once into this file and answers every search, filter and sort locally, so browsing is
instant and costs the server nothing. The file is a cache: if it is unreadable it is moved aside and rebuilt.

All values reach SQL as bound parameters. User text reaches the full-text index only as quoted `\\w` tokens, so it
cannot inject FTS syntax. Without FTS5 the search falls back to LIKE with escaped wildcards.
"""
import json
import re
import sqlite3
import threading
import time
from contextlib import closing
from pathlib import Path

from ..repos.errors import RepoError, STORE
from .model import MODEL_MOD, QueryResult, Submission

SCHEMA_VERSION = 1
SORTS = {
    'updated': 'modified DESC, id DESC',
    'newest': 'added DESC, id DESC',
    'name': 'name COLLATE NOCASE ASC, id ASC',
    'popular': 'downloads DESC, likes DESC, modified DESC',
}
_TOKEN = re.compile(r'\w+')
_COLUMNS = ('id', 'model', 'name', 'category', 'subcategory', 'author', 'author_id', 'version', 'added', 'modified',
            'has_files', 'obsolete', 'nsfw', 'thumbnail', 'images', 'tags', 'likes', 'views', 'downloads', 'hydrated_at')

_TABLES = '''
CREATE TABLE submission (
    model TEXT NOT NULL, id INTEGER NOT NULL, name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT '', subcategory TEXT NOT NULL DEFAULT '',
    author TEXT NOT NULL DEFAULT '', author_id INTEGER NOT NULL DEFAULT 0, version TEXT NOT NULL DEFAULT '',
    added INTEGER NOT NULL DEFAULT 0, modified INTEGER NOT NULL DEFAULT 0,
    has_files INTEGER NOT NULL DEFAULT 0, obsolete INTEGER NOT NULL DEFAULT 0, nsfw INTEGER NOT NULL DEFAULT 0,
    thumbnail TEXT NOT NULL DEFAULT '', images TEXT NOT NULL DEFAULT '[]', tags TEXT NOT NULL DEFAULT '[]',
    likes INTEGER NOT NULL DEFAULT 0, views INTEGER NOT NULL DEFAULT 0, downloads INTEGER NOT NULL DEFAULT 0,
    hydrated_at INTEGER NOT NULL DEFAULT 0, seen INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (model, id));
CREATE INDEX submission_modified ON submission (modified DESC);
CREATE INDEX submission_added ON submission (added DESC);
CREATE INDEX submission_category ON submission (category, subcategory);
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
'''
_FTS = "CREATE VIRTUAL TABLE submission_fts USING fts5(name, author, category, subcategory, tags, tokenize='unicode61 remove_diacritics 2')"


def _error(error):
    return RepoError(STORE, 'the store catalogue failed: %s' % error)


class Catalog:
    def __init__(self, path):
        self.path = Path(path)
        self._lock = threading.RLock()
        self.fts = False
        self._ensure()

    # ---- connection and schema ------------------------------------------------------------------------

    def _connect(self):
        connection = sqlite3.connect(str(self.path), timeout=20)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure(self):
        with self._lock:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self._open_or_create()
            except sqlite3.DatabaseError:
                # A cache: move the unreadable file aside (kept for inspection) and start over.
                aside = self.path.with_name('%s.damaged-%d' % (self.path.name, int(time.time())))
                try:
                    self.path.replace(aside)
                    self._open_or_create()
                except (OSError, sqlite3.Error) as error:
                    raise _error(error) from None
            except OSError as error:
                raise _error(error) from None

    def _open_or_create(self):
        with closing(self._connect()) as connection:
            version = connection.execute('PRAGMA user_version').fetchone()[0]
            if version == 0:
                with connection:
                    connection.executescript(_TABLES)
                    try:
                        connection.execute(_FTS)
                    except sqlite3.OperationalError:
                        pass                      # this SQLite build has no FTS5: search falls back to LIKE
                    connection.execute('PRAGMA user_version = %d' % SCHEMA_VERSION)
            elif version != SCHEMA_VERSION:
                raise sqlite3.DatabaseError('unknown catalogue schema %d' % version)
            self.fts = connection.execute("SELECT 1 FROM sqlite_master WHERE name = 'submission_fts'").fetchone() is not None
            connection.execute('SELECT COUNT(*) FROM submission').fetchone()    # raises on a file that is not a database

    # ---- meta ------------------------------------------------------------------------------------------

    def meta(self, key, default=''):
        with self._lock, closing(self._connect()) as connection:
            row = connection.execute('SELECT value FROM meta WHERE key = ?', (key,)).fetchone()
            return row['value'] if row else default

    def set_meta(self, **values):
        with self._lock, closing(self._connect()) as connection, connection:
            for key, value in values.items():
                connection.execute('INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value',
                                   (key, str(value)))

    def meta_int(self, key, default=0):
        value = self.meta(key)
        return int(value) if value.isascii() and value.isdigit() else default

    # ---- writing ---------------------------------------------------------------------------------------

    def save_page(self, submissions, snapshot, **meta):
        """Upsert listings and the cursor values in `meta` in one transaction, so an interruption never leaves one without the other."""
        try:
            with self._lock, closing(self._connect()) as connection, connection:
                for submission in submissions:
                    self._upsert(connection, submission, snapshot)
                for key, value in meta.items():
                    connection.execute('INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value',
                                       (key, str(value)))
        except sqlite3.Error as error:
            raise _error(error) from None

    def _upsert(self, connection, s, snapshot):
        # Counts and hydrated_at are deliberately absent from the update: the index carries none, and zeros must not erase them.
        connection.execute(
            'INSERT INTO submission (model, id, name, category, subcategory, author, author_id, version, added, modified, '
            'has_files, obsolete, nsfw, thumbnail, images, tags, seen) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) '
            'ON CONFLICT(model, id) DO UPDATE SET name=excluded.name, category=excluded.category, subcategory=excluded.subcategory, '
            'author=excluded.author, author_id=excluded.author_id, version=excluded.version, added=excluded.added, '
            'modified=excluded.modified, has_files=excluded.has_files, obsolete=excluded.obsolete, nsfw=excluded.nsfw, '
            'thumbnail=excluded.thumbnail, images=excluded.images, tags=excluded.tags, seen=excluded.seen',
            (s.model, s.id, s.name, s.category, s.subcategory, s.author, s.author_id, s.version, s.added, s.modified,
             int(s.has_files), int(s.obsolete), int(s.nsfw), s.thumbnail, json.dumps(list(s.images)), json.dumps(list(s.tags)), snapshot))
        if self.fts:
            rowid = connection.execute('SELECT rowid FROM submission WHERE model = ? AND id = ?', (s.model, s.id)).fetchone()[0]
            connection.execute('DELETE FROM submission_fts WHERE rowid = ?', (rowid,))
            connection.execute('INSERT INTO submission_fts (rowid, name, author, category, subcategory, tags) VALUES (?,?,?,?,?,?)',
                               (rowid, s.name, s.author, s.category, s.subcategory, ' '.join(s.tags)))

    def apply_profile(self, profile, now=None):
        """Store the counts and refreshed facts from a profile fetch."""
        s = profile.submission
        try:
            with self._lock, closing(self._connect()) as connection, connection:
                connection.execute('UPDATE submission SET likes = ?, views = ?, downloads = ?, version = ?, has_files = ?, hydrated_at = ? '
                                   'WHERE model = ? AND id = ?',
                                   (s.likes, s.views, s.downloads, s.version, int(s.has_files), int(now if now is not None else time.time()), s.model, s.id))
        except sqlite3.Error as error:
            raise _error(error) from None

    def clear(self):
        try:
            with self._lock, closing(self._connect()) as connection, connection:
                connection.execute('DELETE FROM submission')
                connection.execute('DELETE FROM meta')
                if self.fts:
                    connection.execute('DELETE FROM submission_fts')
        except sqlite3.Error as error:
            raise _error(error) from None

    # ---- reading ---------------------------------------------------------------------------------------

    @staticmethod
    def _submission(row):
        return Submission(
            id=row['id'], name=row['name'], model=row['model'], category=row['category'], subcategory=row['subcategory'],
            author=row['author'], author_id=row['author_id'], version=row['version'], added=row['added'], modified=row['modified'],
            has_files=bool(row['has_files']), obsolete=bool(row['obsolete']), nsfw=bool(row['nsfw']), thumbnail=row['thumbnail'],
            images=tuple(json.loads(row['images'])), tags=tuple(json.loads(row['tags'])),
            likes=row['likes'], views=row['views'], downloads=row['downloads'], hydrated_at=row['hydrated_at'])

    def count(self):
        with self._lock, closing(self._connect()) as connection:
            return connection.execute('SELECT COUNT(*) FROM submission').fetchone()[0]

    def get(self, ident, model=MODEL_MOD):
        with self._lock, closing(self._connect()) as connection:
            row = connection.execute('SELECT * FROM submission WHERE model = ? AND id = ?', (model, ident)).fetchone()
            return self._submission(row) if row else None

    def _where(self, text, category, subcategory, include_nsfw, include_obsolete, downloadable_only):
        clauses, params = ['model = ?'], [MODEL_MOD]
        if not include_nsfw:
            clauses.append('nsfw = 0')
        if not include_obsolete:
            clauses.append('obsolete = 0')
        if downloadable_only:
            clauses.append('has_files = 1')
        if category:
            clauses.append('category = ?')
            params.append(category)
        if subcategory:
            clauses.append('subcategory = ?')
            params.append(subcategory)
        tokens = _TOKEN.findall(text or '')[:8]
        if tokens and self.fts:
            clauses.append('rowid IN (SELECT rowid FROM submission_fts WHERE submission_fts MATCH ?)')
            params.append(' '.join('"%s"*' % token for token in tokens))
        elif tokens:
            for token in tokens:
                clauses.append("(name || ' ' || author || ' ' || category || ' ' || subcategory || ' ' || tags) LIKE ? ESCAPE '\\'")
                params.append('%' + token.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%')
        return ' AND '.join(clauses), params

    def query(self, *, text='', category='', subcategory='', include_nsfw=False, include_obsolete=False,
              downloadable_only=True, sort='updated', limit=50, offset=0):
        where, params = self._where(text, category, subcategory, include_nsfw, include_obsolete, downloadable_only)
        order = SORTS.get(sort, SORTS['updated'])
        limit, offset = max(1, min(int(limit), 500)), max(0, int(offset))
        try:
            with self._lock, closing(self._connect()) as connection:
                total = connection.execute('SELECT COUNT(*) FROM submission WHERE ' + where, params).fetchone()[0]
                rows = connection.execute('SELECT * FROM submission WHERE %s ORDER BY %s LIMIT ? OFFSET ?' % (where, order), [*params, limit, offset]).fetchall()
        except sqlite3.Error as error:
            raise _error(error) from None
        return QueryResult(tuple(self._submission(row) for row in rows), total)

    def categories(self, *, include_nsfw=False, include_obsolete=False):
        """[(name, count)] for the root categories, largest first."""
        return self._facet('category', '', include_nsfw, include_obsolete)

    def subcategories(self, category, *, include_nsfw=False, include_obsolete=False):
        """[(name, count)] inside one root category (for Skins these are the heroes)."""
        return self._facet('subcategory', category, include_nsfw, include_obsolete)

    def _facet(self, column, category, include_nsfw, include_obsolete):
        where, params = self._where('', category, '', include_nsfw, include_obsolete, True)
        with self._lock, closing(self._connect()) as connection:
            rows = connection.execute("SELECT %s AS name, COUNT(*) AS n FROM submission WHERE %s AND %s != '' GROUP BY %s ORDER BY n DESC, name"
                                      % (column, where, column, column), params).fetchall()
        return [(row['name'], row['n']) for row in rows]

    def latest_modified(self):
        with self._lock, closing(self._connect()) as connection:
            return connection.execute('SELECT COALESCE(MAX(modified), 0) FROM submission').fetchone()[0]
