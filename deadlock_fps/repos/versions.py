"""Mod version numbers and the small range language used by dependencies.

Versions are dotted numbers with an optional SemVer pre-release, e.g. `1.4`,
`2.0.1`, `1.0.0-beta.2`. One to four numeric components are accepted and
missing components count as zero, so `1.4` equals `1.4.0`.

Ranges are space-separated comparators that must all hold: `>=1.2 <2`,
`=1.0.0`, `!=1.3`, or `*` for any version.
"""
import re
from functools import total_ordering

from .errors import RepoError, INVALID_INDEX

_VERSION = re.compile(
    r'v?(0|[1-9][0-9]*)(?:\.(0|[1-9][0-9]*))?(?:\.(0|[1-9][0-9]*))?(?:\.(0|[1-9][0-9]*))?'
    r'(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?')
_COMPARATOR = re.compile(r'(>=|<=|!=|>|<|=)?\s*(\S+)')


@total_ordering
class Version:
    __slots__ = ('numbers', 'pre', 'text')

    def __init__(self, numbers, pre, text):
        self.numbers = numbers
        self.pre = pre
        self.text = text

    @classmethod
    def parse(cls, value):
        if not isinstance(value, str) or not 1 <= len(value) <= 64:
            raise RepoError(INVALID_INDEX, 'version must be a short string')
        match = _VERSION.fullmatch(value.strip())
        if not match:
            raise RepoError(INVALID_INDEX, 'unsupported version number: %r' % value[:40])
        numbers = tuple(int(part or 0) for part in match.group(1, 2, 3, 4))
        pre = tuple(match.group(5).split('.')) if match.group(5) else ()
        if any(part.isdigit() and len(part) > 1 and part[0] == '0' for part in pre):
            raise RepoError(INVALID_INDEX, 'invalid pre-release in version: %r' % value[:40])
        return cls(numbers, pre, value.strip().removeprefix('v'))

    @property
    def is_prerelease(self):
        return bool(self.pre)

    def _key(self):
        return self.numbers, self.pre

    def __eq__(self, other):
        return isinstance(other, Version) and self.numbers == other.numbers and self.pre == other.pre

    def __hash__(self):
        return hash((self.numbers, self.pre))

    def __lt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        if self.numbers != other.numbers:
            return self.numbers < other.numbers
        # A pre-release sorts before the release it precedes.
        if bool(self.pre) != bool(other.pre):
            return bool(self.pre)
        for a, b in zip(self.pre, other.pre):
            if a == b:
                continue
            if a.isdigit() and b.isdigit():
                return int(a) < int(b)
            if a.isdigit() != b.isdigit():
                return a.isdigit()
            return a < b
        return len(self.pre) < len(other.pre)

    def __repr__(self):
        return 'Version(%s)' % self.text

    def __str__(self):
        return self.text


def valid_version(value):
    try:
        Version.parse(value)
        return True
    except RepoError:
        return False


def parse_range(text):
    """Return a list of (operator, Version) pairs; an empty list means any version."""
    if not isinstance(text, str) or len(text) > 128:
        raise RepoError(INVALID_INDEX, 'version range must be a short string')
    text = text.strip()
    if text in ('', '*'):
        return []
    parts = []
    # Tokenise on whitespace but allow `>= 1.2` (operator separated from number).
    tokens = re.findall(r'(?:>=|<=|!=|>|<|=)\s*[^\s]+|[^\s]+', text)
    if ''.join(tokens).replace(' ', '') != re.sub(r'\s+', '', text):
        raise RepoError(INVALID_INDEX, 'unreadable version range: %r' % text[:40])
    for token in tokens:
        match = _COMPARATOR.fullmatch(token)
        if not match:
            raise RepoError(INVALID_INDEX, 'unreadable version range: %r' % text[:40])
        parts.append((match.group(1) or '=', Version.parse(match.group(2))))
    return parts


def satisfies(version, version_range):
    """True when `version` (a Version) meets every comparator of `version_range` (a string)."""
    for operator, bound in parse_range(version_range):
        if operator == '=' and not version == bound:
            return False
        if operator == '!=' and version == bound:
            return False
        if operator == '>' and not version > bound:
            return False
        if operator == '>=' and not version >= bound:
            return False
        if operator == '<' and not version < bound:
            return False
        if operator == '<=' and not version <= bound:
            return False
    return True
