"""Turns a store mod and one of its files into what the installer understands.

The installer wants three things: a repository (who it came from, and how far to trust them), a mod, and a version
with a package. The store has no repository manifest, so this module builds all three from what GameBanana says:

* the "repository" is GameBanana, always UNVERIFIED: nobody on this project reviewed the content;
* one file of the mod becomes the single version. Its MD5 (GameBanana publishes no SHA-256) is checked by the
  installer, and the download must end on a GameBanana host whatever the redirects do;
* a `.zip` package is installed by *discovering* its `.vpk` files (there is no manifest to name them); a bare `.vpk`
  is installed as it is. Anything else (`.rar`, `.7z`, ...) is reported as unsupported with the reason, not guessed at.

Nothing here touches the network or the game; it only builds values. `Installer.prepare` does the rest.
"""
import re
from datetime import datetime, timezone
from pathlib import PurePosixPath

from ..installer.updates import STORE_PREFIX
from ..repos.errors import RepoError
from ..repos.model import (Compat, GameSupport, InstallSpec, Mod, ModVersion, Package, RepositoryInfo, RepositorySource, RepositoryView,
                           SyncState, Trust)
from ..repos.versions import Version

STORE_ID = STORE_PREFIX + 'gamebanana'
STORE_NAME = 'GameBanana'
HOSTS = ('gamebanana.com',)
MOD_PREFIX = 'gb-'
_FORMATS = {'.zip': 'zip', '.vpk': 'vpk'}
_UNSUPPORTED = {'.rar': 'rar', '.7z': '7z'}
_REASONS = {
    'rar': 'This file is a .rar archive. Toolbox can only unpack .zip archives and .vpk files so far.',
    '7z': 'This file is a .7z archive. Toolbox can only unpack .zip archives and .vpk files so far.',
    'other': 'Toolbox can only install .zip archives and .vpk files so far.',
}
NOTE = 'Community content from GameBanana. Nobody on this project reviewed it.'


def mod_id_of(submission_id):
    return '%s%d' % (MOD_PREFIX, submission_id)


def store_repository():
    source = RepositorySource(STORE_ID, 'https', 'https://gamebanana.com/', STORE_NAME, True)
    return RepositoryView(source, SyncState(status='ok', compat=Compat.TRANSLATED.value, display_name=STORE_NAME), Trust.UNVERIFIED, NOTE,
                          RepositoryInfo('gamebanana', STORE_NAME, 'The Deadlock catalogue on GameBanana', 'https://gamebanana.com/games/20948'))


def file_format(file):
    """('zip' | 'vpk', '') for a file Toolbox can install, or ('', code) when it cannot: code is 'rar', '7z' or 'other'."""
    suffix = PurePosixPath(file.name.lower()).suffix
    if suffix in _FORMATS:
        return _FORMATS[suffix], ''
    return '', _UNSUPPORTED.get(suffix, 'other')


def _iso(stamp):
    try:
        return datetime.fromtimestamp(stamp, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ') if stamp else ''
    except (ValueError, OSError, OverflowError):
        return ''


def version_text(submission, file):
    """The version the installer records: the author's own when it is a valid version number, otherwise the file's date."""
    candidate = re.sub(r'^[vV]\s*', '', submission.version or '').strip()
    try:
        return Version.parse(candidate).text
    except RepoError:
        pass
    try:
        when = datetime.fromtimestamp(file.added, timezone.utc) if file.added else None
    except (ValueError, OSError, OverflowError):
        when = None
    # No zero padding: version numbers may not have leading zeros ("2026.08.29" is refused, "2026.8.29" is fine and still sorts by date).
    return '%d.%d.%d' % (when.year, when.month, when.day) if when else '0.0.%d' % file.id       # the file id only when the date is missing


def build(profile, file):
    """(repository, mod, version) for installing `file` of the mod in `profile`. Raises ValueError when the file is not part of it."""
    if file not in profile.files:
        raise ValueError('that file does not belong to this mod')
    s = profile.submission
    kind, code = file_format(file)
    reason = _REASONS[code] if code else ''
    package = Package(kind or 'zip', file.url, file.size or None, None, (), file.md5, HOSTS)
    version = ModVersion(
        version=Version.parse(version_text(s, file)), published=_iso(file.added), changelog='', package=package,
        install=InstallSpec('vpk', (), discover=(kind == 'zip')), game=GameSupport(), unsupported_reason=reason)
    mod = Mod(
        id=mod_id_of(s.id), name=s.name, summary=profile.text[:200], description=profile.text, author=s.author, license=profile.license,
        categories=tuple(c for c in (s.category, s.subcategory) if c), tags=s.tags, homepage=s.url, source_url=s.url, screenshots=s.images,
        published=_iso(s.added), versions=(version,), derived=False)
    return store_repository(), mod, version
