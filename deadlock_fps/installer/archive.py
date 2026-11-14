"""Hardened ZIP handling for downloaded mod packages.

The archive is untrusted. It is inspected completely before anything is written, and then only the members the
manifest listed are extracted, by streaming, with the byte count measured as it is written (never trusting the sizes
in the archive's own headers).

An archive is refused outright when *any* entry is unsafe, even one that would never be extracted:

* absolute paths, `..` segments, empty segments, backslashes, drive letters or NTFS stream markers (`:`);
* control characters, names ending in a dot or space (Windows silently rewrites them);
* symbolic links; encrypted entries;
* two names that differ only by case (they collide on Windows and macOS);
* too many entries, a huge declared expansion, or a suspicious compression ratio (a zip bomb).

Files that are not on the install list are never extracted. Executables and scripts that the archive carries are
reported so the user can see they exist, and they are still not installed or run.
"""
import os
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .errors import InstallError, BAD_PACKAGE, CANCELLED

MAX_ENTRIES = 4096
MAX_DECLARED_TOTAL = 8 * 1024 ** 3
MAX_MEMBER = 2 * 1024 ** 3
MAX_DISCOVERED = 8
RATIO_LIMIT = 1000                      # uncompressed : compressed
RATIO_MIN_SIZE = 10 * 1024 * 1024       # ratios on tiny files mean nothing
RISKY = {'.exe', '.dll', '.bat', '.cmd', '.ps1', '.sh', '.js', '.vbs', '.msi', '.scr', '.com', '.jar', '.lnk', '.py', '.so', '.dylib', '.appimage'}


@dataclass(frozen=True)
class ZipReport:
    members: tuple               # the wanted members, as stored in the archive
    ignored: tuple               # names present but not installed
    risky: tuple                 # ignored names that look executable


def _unsafe_name(name):
    if not name or '\\' in name or ':' in name or name.startswith('/') or any(ord(c) < 32 or ord(c) == 127 for c in name):
        return True
    # Split literally: pathlib would silently collapse `a//b` and `./x`, hiding exactly what we want to see.
    parts = (name[:-1] if name.endswith('/') else name).split('/')
    return any(p in ('', '.', '..') or p.endswith(('.', ' ')) for p in parts)


def inspect_zip(path, wanted, discover=False):
    """Validate the archive and that every name in `wanted` is present exactly once as a regular `.vpk` file.

    With `discover`, `wanted` is ignored and every regular `.vpk` the archive holds is wanted instead (a store package
    has no manifest). Every safety check below still covers all entries, and a handful of files at most is accepted.
    """
    path = Path(path)
    try:
        archive = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as error:
        raise InstallError(BAD_PACKAGE, 'the download is not a valid ZIP archive: %s' % error) from None
    with archive:
        entries = archive.infolist()
        if len(entries) > MAX_ENTRIES:
            raise InstallError(BAD_PACKAGE, 'the archive has %d entries; the limit is %d' % (len(entries), MAX_ENTRIES))
        if sum(e.file_size for e in entries) > MAX_DECLARED_TOTAL:
            raise InstallError(BAD_PACKAGE, 'the archive claims to expand to more than %d GiB' % (MAX_DECLARED_TOTAL >> 30))
        seen = {}
        for entry in entries:
            if _unsafe_name(entry.filename):
                raise InstallError(BAD_PACKAGE, 'the archive contains an unsafe path: %r' % entry.filename[:80])
            if stat.S_ISLNK(entry.external_attr >> 16):
                raise InstallError(BAD_PACKAGE, 'the archive contains a symbolic link: %r' % entry.filename[:80])
            if entry.flag_bits & 0x1:
                raise InstallError(BAD_PACKAGE, 'the archive contains an encrypted entry: %r' % entry.filename[:80])
            folded = entry.filename.rstrip('/').casefold()
            if folded in seen:
                raise InstallError(BAD_PACKAGE, 'the archive has two entries that differ only by case or repeat a name: %r' % entry.filename[:80])
            seen[folded] = entry
            if entry.compress_size and entry.file_size > RATIO_MIN_SIZE and entry.file_size / entry.compress_size > RATIO_LIMIT:
                raise InstallError(BAD_PACKAGE, 'suspicious compression ratio for %r (possible zip bomb)' % entry.filename[:80])
        if discover:
            wanted = sorted(e.filename for e in entries if not e.is_dir() and e.filename.lower().endswith('.vpk'))
            if not wanted:
                raise InstallError(BAD_PACKAGE, 'the archive contains no .vpk file')
            if len(wanted) > MAX_DISCOVERED:
                raise InstallError(BAD_PACKAGE, 'the archive contains %d .vpk files; at most %d are accepted without a manifest' % (len(wanted), MAX_DISCOVERED))
        members = []
        for name in wanted:
            entry = next((e for e in entries if e.filename == name), None)
            if entry is None or entry.is_dir():
                raise InstallError(BAD_PACKAGE, 'the archive does not contain %r, which the repository says to install' % name)
            if not name.lower().endswith('.vpk'):
                raise InstallError(BAD_PACKAGE, 'only .vpk files can be installed (%r)' % name)
            if entry.file_size > MAX_MEMBER:
                raise InstallError(BAD_PACKAGE, '%r is larger than the %d GiB limit' % (name, MAX_MEMBER >> 30))
            members.append(name)
        ignored = tuple(e.filename for e in entries if not e.is_dir() and e.filename not in members)
        risky = tuple(n for n in ignored if os.path.splitext(n)[1].lower() in RISKY)
        return ZipReport(tuple(members), ignored, risky)


def extract_member(path, name, destination, *, limit=MAX_MEMBER, cancel=None):
    """Stream one member to a new file. The bytes actually written are counted, not the sizes the archive declares."""
    destination = Path(destination)
    written = 0
    created = False
    try:
        with zipfile.ZipFile(path) as archive, archive.open(name) as source, open(destination, 'xb') as out:
            created = True
            while True:
                if cancel is not None and cancel.is_set():
                    raise InstallError(CANCELLED, 'cancelled')
                chunk = source.read(256 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > limit:
                    raise InstallError(BAD_PACKAGE, '%r expands beyond the %d byte limit' % (name, limit))
                out.write(chunk)
            out.flush()
            os.fsync(out.fileno())
    except (zipfile.BadZipFile, OSError, RuntimeError, EOFError) as error:
        if created:
            destination.unlink(missing_ok=True)
        raise InstallError(BAD_PACKAGE, 'cannot extract %r: %s' % (name, error)) from None
    except BaseException:
        if created:
            destination.unlink(missing_ok=True)
        raise
    return written
