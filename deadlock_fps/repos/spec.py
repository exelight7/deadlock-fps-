"""Reader and validator for the Deadlock Mod Repository specification, version 1.

The full specification for repository authors is docs/REPOSITORY_SPEC.md. This
module is its executable form: an index is untrusted input, so nothing is used
that was not checked here.

Compatibility rules:

* `schema_version` is "MAJOR.MINOR". Any 1.x index is accepted; a newer minor
  may add fields, which are ignored. A different major is refused outright.
* One bad mod or version never poisons the whole index: it is skipped and
  reported in `RepositoryIndex.warnings`.
* A version that is well formed but uses something this build does not know
  (a new package format, a new install type) is kept and marked unsupported,
  so the interface can say "needs a newer Toolbox" instead of hiding it.
* Fields that grant trust are not part of the specification. A repository
  cannot label itself verified; see trust.py.
"""
import json
import re
from datetime import datetime

from .errors import RepoError, INVALID_INDEX, UNSUPPORTED_SCHEMA, BAD_URL, TOO_LARGE
from .model import (Package, InstallFile, InstallSpec, GameSupport, Relation, ModVersion, Mod,
                    RepositoryInfo, RepositoryIndex)
from .urls import check_https_url
from .versions import Version, parse_range

SCHEMA = 'deadlock-mod-repository'
LIST_SCHEMA = 'deadlock-mod-repository-list'
SUPPORTED_MAJOR = 1

# Hard limits: an index that exceeds them is rejected or trimmed, never partially trusted.
MAX_INDEX_BYTES = 8 * 1024 * 1024
MAX_MODS = 5000
MAX_VERSIONS = 200
MAX_PACKAGE_BYTES = 2 * 1024 ** 3
MAX_SCREENSHOTS = 12
MAX_LIST = 32
KNOWN_FORMATS = ('vpk', 'zip')
KNOWN_INSTALL_TYPES = ('vpk',)

_ID = re.compile(r'[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])')
_SHA256 = re.compile(r'[0-9a-fA-F]{64}')
_DATE = re.compile(r'\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?')
_CONTROL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
_SOURCE_PATH = re.compile(r'[A-Za-z0-9][A-Za-z0-9 ._()+-]*(?:/[A-Za-z0-9][A-Za-z0-9 ._()+-]*)*')


class _Skip(Exception):
    """Internal: this entry is unusable. The message becomes a warning."""


def _text(value, field, limit, *, required=False, multiline=False):
    if value is None or value == '':
        if required:
            raise _Skip('%s is required' % field)
        return ''
    if not isinstance(value, str):
        raise _Skip('%s must be text' % field)
    value = value.replace('\r\n', '\n').strip()
    if len(value) > limit:
        raise _Skip('%s is longer than %d characters' % (field, limit))
    if _CONTROL.search(value) or (not multiline and '\n' in value):
        raise _Skip('%s contains control characters' % field)
    if required and not value:
        raise _Skip('%s is required' % field)
    return value


def _url(value, field, *, required=False):
    if value in (None, ''):
        if required:
            raise _Skip('%s is required' % field)
        return ''
    try:
        return check_https_url(value, what=field)
    except RepoError as error:
        raise _Skip(error.message) from None


def _date(value, field):
    if value in (None, ''):
        return ''
    if not isinstance(value, str) or not _DATE.fullmatch(value.strip()):
        raise _Skip('%s must be an ISO 8601 date such as 2026-03-18' % field)
    text = value.strip()
    try:
        datetime.fromisoformat(text.replace('Z', '+00:00'))
    except ValueError:
        raise _Skip('%s is not a real date' % field) from None
    return text


def _int(value, field, *, lo=0, hi=2 ** 53, allow_none=True):
    if value is None and allow_none:
        return None
    if type(value) is not int or not lo <= value <= hi:
        raise _Skip('%s must be a whole number between %d and %d' % (field, lo, hi))
    return value


def _list(value, field, limit):
    if value in (None, ''):
        return []
    if not isinstance(value, list) or len(value) > limit:
        raise _Skip('%s must be a list of at most %d items' % (field, limit))
    return value


def _words(value, field):
    items = []
    for item in _list(value, field, MAX_LIST):
        item = _text(item, field + ' item', 40, required=True)
        if item.lower() not in items:
            items.append(item.lower())
    return tuple(items)


def _relations(value, field, with_reason):
    result = []
    for item in _list(value, field, MAX_LIST):
        if not isinstance(item, dict):
            raise _Skip('%s entries must be objects' % field)
        ident = _text(item.get('id'), field + ' id', 64, required=True)
        if not _ID.fullmatch(ident):
            raise _Skip('%s id %r is not a valid mod id' % (field, ident[:40]))
        rng = _text(item.get('range', '*'), field + ' range', 128) or '*'
        try:
            parse_range(rng)
        except RepoError as error:
            raise _Skip(error.message) from None
        reason = _text(item.get('reason'), field + ' reason', 300) if with_reason else ''
        result.append(Relation(ident, rng, reason))
    return tuple(result)


def _package(raw, *, derived):
    if not isinstance(raw, dict):
        raise _Skip('package must be an object')
    fmt = _text(raw.get('format'), 'package.format', 24, required=True).lower()
    url = _url(raw.get('url'), 'package.url', required=True)
    size = raw.get('size')
    if size is None and not derived:
        raise _Skip('package.size is required')
    size = _int(size, 'package.size', lo=1, hi=MAX_PACKAGE_BYTES)
    digest = raw.get('sha256')
    if digest is not None:
        if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            raise _Skip('package.sha256 must be 64 hexadecimal characters')
        digest = digest.lower()
    mirrors = tuple(_url(m, 'package.mirrors item', required=True) for m in _list(raw.get('mirrors'), 'package.mirrors', 8))
    return Package(fmt, url, size, digest, mirrors)


def _install(raw, package):
    if not isinstance(raw, dict):
        raise _Skip('install must be an object')
    kind = _text(raw.get('type'), 'install.type', 24, required=True).lower()
    files = []
    for item in _list(raw.get('files'), 'install.files', 64):
        if not isinstance(item, dict):
            raise _Skip('install.files entries must be objects')
        source = item.get('source', '')
        source = _text(source, 'install.files.source', 200)
        # A path inside the package. Never absolute, never climbing, never a Windows drive or stream.
        if source and (not _SOURCE_PATH.fullmatch(source) or '..' in source.split('/') or source.startswith('/')):
            raise _Skip('install.files.source %r is not a safe relative path' % source[:60])
        files.append(InstallFile(source))
    return InstallSpec(kind, tuple(files))


def _version(raw, *, derived):
    if not isinstance(raw, dict):
        raise _Skip('version entry must be an object')
    try:
        version = Version.parse(raw.get('version'))
    except RepoError as error:
        raise _Skip(error.message) from None
    game_raw = raw.get('game') or {}
    if not isinstance(game_raw, dict):
        raise _Skip('game must be an object')
    game = GameSupport(_int(game_raw.get('min_build'), 'game.min_build'),
                       _int(game_raw.get('max_build'), 'game.max_build'),
                       _int(game_raw.get('tested_build'), 'game.tested_build'))
    if game.min_build is not None and game.max_build is not None and game.min_build > game.max_build:
        raise _Skip('game.min_build is greater than game.max_build')
    package = _package(raw.get('package'), derived=derived)
    install = _install(raw.get('install') or {'type': 'vpk', 'files': [{'source': ''}]} if derived else raw.get('install'), package)
    reason = ''
    if package.format not in KNOWN_FORMATS:
        reason = 'package format %r is not supported by this version of Toolbox' % package.format
    elif install.type not in KNOWN_INSTALL_TYPES:
        reason = 'install type %r is not supported by this version of Toolbox' % install.type
    elif install.type == 'vpk' and package.format == 'zip' and not install.files:
        raise _Skip('a zip package must list the .vpk files to install in install.files')
    elif install.type == 'vpk' and any(f.source and not f.source.lower().endswith('.vpk') for f in install.files):
        # Only Valve package files are ever copied into the game. Scripts and executables are not installable.
        raise _Skip('only .vpk files can be installed')
    elif install.type == 'vpk' and package.format == 'vpk' and any(f.source for f in install.files[1:]):
        raise _Skip('a vpk package installs exactly itself')
    return ModVersion(
        version=version,
        published=_date(raw.get('published'), 'published'),
        changelog=_text(raw.get('changelog'), 'changelog', 16000, multiline=True),
        package=package, install=install, game=game,
        dependencies=_relations(raw.get('dependencies'), 'dependencies', False),
        conflicts=_relations(raw.get('conflicts'), 'conflicts', True),
        prerelease=raw.get('prerelease', False) is True or version.is_prerelease,
        yanked=raw.get('yanked', False) is True,
        unsupported_reason=reason)


def _mod(raw, *, derived):
    if not isinstance(raw, dict):
        raise _Skip('mod entry must be an object')
    ident = _text(raw.get('id'), 'id', 64, required=True)
    if not _ID.fullmatch(ident):
        raise _Skip('id %r must be 2-64 lower-case letters, digits, dot, dash or underscore' % ident[:40])
    where = 'mod %s' % ident
    try:
        screenshots = tuple(_url(s, 'screenshots item', required=True) for s in _list(raw.get('screenshots'), 'screenshots', MAX_SCREENSHOTS))
        fields = dict(
            name=_text(raw.get('name'), 'name', 120, required=True),
            summary=_text(raw.get('summary'), 'summary', 300),
            description=_text(raw.get('description'), 'description', 16000, multiline=True),
            author=_text(raw.get('author'), 'author', 120, required=not derived),
            license=_text(raw.get('license'), 'license', 120),
            categories=_words(raw.get('categories'), 'categories'),
            tags=_words(raw.get('tags'), 'tags'),
            homepage=_url(raw.get('homepage'), 'homepage'),
            source_url=_url(raw.get('source_url'), 'source_url'),
            published=_date(raw.get('published'), 'published'))
    except _Skip as error:
        raise _Skip('%s: %s' % (where, error)) from None
    raw_versions = raw.get('versions')
    if not isinstance(raw_versions, list) or not raw_versions:
        raise _Skip('%s: versions must be a non-empty list' % where)
    if len(raw_versions) > MAX_VERSIONS:
        raise _Skip('%s: more than %d versions' % (where, MAX_VERSIONS))
    versions, warnings, seen = [], [], set()
    for position, item in enumerate(raw_versions):
        try:
            version = _version(item, derived=derived)
        except _Skip as error:
            warnings.append('%s version #%d skipped: %s' % (where, position + 1, error))
            continue
        if version.version in seen:
            warnings.append('%s version %s is listed twice; the first entry is used' % (where, version.version))
            continue
        seen.add(version.version)
        versions.append(version)
    if not versions:
        raise _Skip('%s: no valid versions (%s)' % (where, '; '.join(warnings)[:300]))
    versions.sort(key=lambda v: v.version, reverse=True)
    return Mod(id=ident, screenshots=screenshots, versions=tuple(versions), derived=derived, **fields), warnings


def decode(data):
    """Bytes or dict → dict, enforcing the size limit before parsing."""
    if isinstance(data, dict):
        return data
    if len(data) > MAX_INDEX_BYTES:
        raise RepoError(TOO_LARGE, 'index is larger than %d MiB' % (MAX_INDEX_BYTES >> 20))
    try:
        document = json.loads(bytes(data).decode('utf-8-sig'))
    except (ValueError, UnicodeDecodeError) as error:
        raise RepoError(INVALID_INDEX, 'not valid UTF-8 JSON: %s' % str(error)[:120]) from None
    if not isinstance(document, dict):
        raise RepoError(INVALID_INDEX, 'the top level must be a JSON object')
    return document


def check_schema(document, expected=SCHEMA):
    if document.get('schema') != expected:
        raise RepoError(INVALID_INDEX, 'schema must be %r' % expected)
    version = document.get('schema_version')
    if not isinstance(version, str) or not re.fullmatch(r'\d{1,3}\.\d{1,3}', version):
        raise RepoError(INVALID_INDEX, 'schema_version must look like "1.0"')
    major = int(version.split('.')[0])
    if major != SUPPORTED_MAJOR:
        raise RepoError(UNSUPPORTED_SCHEMA,
                        'this index uses specification %s; this version of Toolbox reads %d.x' % (version, SUPPORTED_MAJOR))
    return version


def parse_index(data, *, derived=False):
    """Validate an index document and return a RepositoryIndex. Raises RepoError for structural problems."""
    document = decode(data)
    version = check_schema(document)
    raw_info = document.get('repository')
    if not isinstance(raw_info, dict):
        raise RepoError(INVALID_INDEX, '"repository" must be an object')
    try:
        info = RepositoryInfo(
            id=_text(raw_info.get('id'), 'repository.id', 64, required=True),
            name=_text(raw_info.get('name'), 'repository.name', 120, required=True),
            description=_text(raw_info.get('description'), 'repository.description', 1000, multiline=True),
            homepage=_url(raw_info.get('homepage'), 'repository.homepage'),
            maintainer=_text(raw_info.get('maintainer'), 'repository.maintainer', 120),
            updated=_date(raw_info.get('updated'), 'repository.updated'))
    except _Skip as error:
        raise RepoError(INVALID_INDEX, str(error)) from None
    raw_mods = document.get('mods')
    if not isinstance(raw_mods, list):
        raise RepoError(INVALID_INDEX, '"mods" must be a list')
    if len(raw_mods) > MAX_MODS:
        raise RepoError(TOO_LARGE, 'index lists more than %d mods' % MAX_MODS)
    mods, warnings, seen = [], [], set()
    for position, item in enumerate(raw_mods):
        try:
            mod, notes = _mod(item, derived=derived)
        except _Skip as error:
            warnings.append('mod #%d skipped: %s' % (position + 1, error))
            continue
        warnings.extend(notes)
        if mod.id in seen:
            warnings.append('mod %s is listed twice; the first entry is used' % mod.id)
            continue
        seen.add(mod.id)
        mods.append(mod)
    return RepositoryIndex(info, tuple(mods), version, tuple(warnings[:200]))


def parse_repository_list(data):
    """A shareable list of repositories: [{'url', 'name'?}]. URLs are validated; nothing is fetched."""
    document = decode(data)
    check_schema(document, LIST_SCHEMA)
    entries = []
    for position, item in enumerate(_list(document.get('repositories'), 'repositories', 200)):
        try:
            if not isinstance(item, dict):
                raise _Skip('entry must be an object')
            entries.append({'url': _url(item.get('url'), 'url', required=True),
                            'name': _text(item.get('name'), 'name', 120),
                            'provider': _text(item.get('provider'), 'provider', 24).lower()})
        except _Skip as error:
            raise RepoError(BAD_URL, 'repository #%d: %s' % (position + 1, error)) from None
    return entries


def kind_of(data):
    """Which known document is this? 'index', 'list' or None, without validating the rest."""
    try:
        schema = decode(data).get('schema')
    except RepoError:
        return None
    return {SCHEMA: 'index', LIST_SCHEMA: 'list'}.get(schema)
