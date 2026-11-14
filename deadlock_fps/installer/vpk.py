"""Structural validation of Valve package (VPK) files, without loading them into memory.

A mod VPK can be hundreds of megabytes, so only the header and the directory tree are read. What is checked:

* the magic number and version (1 or 2);
* the tree fits inside the file and is not absurdly large;
* every entry's bytes live *inside this file* (archive index 0x7fff) and inside its bounds. A `_dir` VPK that points at
  numbered sibling files (`pak01_000.vpk`, ...) is refused with an explicit reason: this version installs single-file
  packages only;
* the terminator of every entry, and valid UTF-8 names.

The result is the set of virtual paths the package provides, which is what conflict detection compares.
"""
import hashlib
import struct
from dataclasses import dataclass
from pathlib import Path

from .errors import InstallError, BAD_PACKAGE

MAGIC = 0x55AA1234
MAX_TREE = 32 * 1024 * 1024
MAX_ENTRIES = 500_000
EXTERNAL = 0x7FFF               # archive index meaning "data follows the tree in this file"


@dataclass(frozen=True)
class VpkInfo:
    version: int
    size: int
    paths: frozenset            # virtual paths such as "materials/shared/skin.vmat"

    @property
    def entries(self):
        return len(self.paths)


def inspect_vpk(path):
    """Validate `path` and return VpkInfo. Raises InstallError(BAD_PACKAGE) with a human reason."""
    path = Path(path)
    if path.is_symlink():
        raise InstallError(BAD_PACKAGE, '%s is a symbolic link' % path.name)
    try:
        size = path.stat().st_size
        with open(path, 'rb') as handle:
            head = handle.read(12)
            if len(head) < 12:
                raise InstallError(BAD_PACKAGE, '%s is too short to be a VPK' % path.name)
            magic, version, tree_size = struct.unpack('<III', head)
            if magic != MAGIC:
                raise InstallError(BAD_PACKAGE, '%s is not a VPK file (wrong signature)' % path.name)
            if version not in (1, 2):
                raise InstallError(BAD_PACKAGE, '%s uses VPK version %d, which is not supported' % (path.name, version))
            offset = 12 if version == 1 else 28
            if version == 2:
                rest = handle.read(16)
                if len(rest) < 16:
                    raise InstallError(BAD_PACKAGE, '%s has a truncated VPK header' % path.name)
            if tree_size > MAX_TREE or offset + tree_size > size:
                raise InstallError(BAD_PACKAGE, '%s has an invalid directory tree size' % path.name)
            tree = handle.read(tree_size)
            if len(tree) != tree_size:
                raise InstallError(BAD_PACKAGE, '%s is truncated' % path.name)
    except OSError as error:
        raise InstallError(BAD_PACKAGE, 'cannot read %s: %s' % (path.name, error)) from None
    return VpkInfo(version, size, _walk(tree, offset + tree_size, size, path.name))


def _walk(tree, data_start, file_size, name):
    position, found = 0, set()

    def string():
        nonlocal position
        stop = tree.find(b'\0', position)
        if stop < 0:
            raise InstallError(BAD_PACKAGE, '%s has an unterminated name in its directory' % name)
        try:
            text = tree[position:stop].decode('utf-8')
        except UnicodeDecodeError:
            raise InstallError(BAD_PACKAGE, '%s has a file name that is not valid UTF-8' % name) from None
        position = stop + 1
        return text

    while True:
        extension = string()
        if not extension:
            break
        while True:
            directory = string()
            if not directory:
                break
            while True:
                stem = string()
                if not stem:
                    break
                if position + 18 > len(tree):
                    raise InstallError(BAD_PACKAGE, '%s has a truncated entry' % name)
                crc, preload, archive, start, length, terminator = struct.unpack_from('<IHHIIH', tree, position)
                position += 18
                if terminator != 0xFFFF:
                    raise InstallError(BAD_PACKAGE, '%s has a damaged entry (bad terminator)' % name)
                if archive != EXTERNAL:
                    raise InstallError(BAD_PACKAGE, '%s refers to separate data files (multi-file VPK); only single-file VPKs can be installed by this version' % name)
                if position + preload > len(tree):
                    raise InstallError(BAD_PACKAGE, '%s has an entry whose preload data is out of bounds' % name)
                position += preload
                if data_start + start + length > file_size:
                    raise InstallError(BAD_PACKAGE, '%s has an entry whose data lies beyond the end of the file' % name)
                directory_part = '' if directory == ' ' else directory + '/'
                stem_part = '' if stem == ' ' else stem
                suffix = '' if extension == ' ' else '.' + extension
                found.add(directory_part + stem_part + suffix)
                if len(found) > MAX_ENTRIES:
                    raise InstallError(BAD_PACKAGE, '%s lists too many files' % name)
    if not found:
        raise InstallError(BAD_PACKAGE, '%s contains no files' % name)
    return frozenset(found)


def md5_file(path, chunk=1024 * 1024):
    """MD5 of a file, for publishers (GameBanana) that give nothing stronger. Never used as a security boundary."""
    digest = hashlib.md5(usedforsecurity=False)
    with open(path, 'rb') as handle:
        while block := handle.read(chunk):
            digest.update(block)
    return digest.hexdigest()


def sha256_file(path, chunk=1024 * 1024):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        while block := handle.read(chunk):
            digest.update(block)
    return digest.hexdigest()
