"""Plain data types shared by providers, the manager, the interface and (later) the installer.

Nothing here performs I/O. Every type is immutable so a cached index can be
shared between threads without copying.
"""
from dataclasses import dataclass, field
from enum import Enum

from .versions import Version


class Compat(str, Enum):
    """How well the application understands a repository. Shown to the user as-is."""
    NATIVE = 'native'            # publishes the application's own manifest specification
    TRANSLATED = 'translated'    # a provider integration derived the catalogue from release metadata
    MANUAL = 'manual'            # recognised, but only a hand-written mapping can make it installable
    UNSUPPORTED = 'unsupported'  # nothing usable; `reason` explains why


class Trust(str, Enum):
    """Review status. Never inferred from the hosting provider and never self-declared by a repository."""
    OFFICIAL = 'OFFICIAL'
    VERIFIED = 'VERIFIED'
    COMMUNITY = 'COMMUNITY'
    UNVERIFIED = 'UNVERIFIED'


class GameFit(str, Enum):
    COMPATIBLE = 'compatible'
    UNTESTED = 'untested'
    INCOMPATIBLE = 'incompatible'
    UNKNOWN = 'unknown'


@dataclass(frozen=True)
class Package:
    format: str                  # 'vpk' or 'zip'; anything else makes the version unsupported
    url: str                     # normalised https URL
    size: int | None             # bytes; required for native indexes
    sha256: str | None           # lower-case hex; optional but strongly recommended
    mirrors: tuple = ()
    md5: str = ''                # weaker checksum some publishers give instead (GameBanana): catches a damaged download, not tampering
    hosts: tuple = ()            # when set, the download must end on one of these domains or their subdomains, whatever the redirects did


@dataclass(frozen=True)
class InstallFile:
    source: str                  # path inside the package ('' means the package itself, for format 'vpk')


@dataclass(frozen=True)
class InstallSpec:
    type: str                    # 'vpk' in spec 1.0
    files: tuple = ()
    discover: bool = False       # zip packages: install the .vpk files the archive contains instead of a manifest's list (store packages)


@dataclass(frozen=True)
class GameSupport:
    min_build: int | None = None
    max_build: int | None = None
    tested_build: int | None = None


@dataclass(frozen=True)
class Relation:
    id: str
    range: str = '*'
    reason: str = ''


@dataclass(frozen=True)
class ModVersion:
    version: Version
    published: str               # ISO 8601 date or datetime, as published ('' when unknown)
    changelog: str
    package: Package | None
    install: InstallSpec | None
    game: GameSupport
    dependencies: tuple = ()
    conflicts: tuple = ()
    prerelease: bool = False
    yanked: bool = False
    unsupported_reason: str = ''  # set when this app cannot install the version (unknown format, newer install type…)

    @property
    def installable(self):
        return not self.yanked and not self.unsupported_reason and self.package is not None and self.install is not None


@dataclass(frozen=True)
class Mod:
    id: str
    name: str
    summary: str
    description: str
    author: str
    license: str
    categories: tuple
    tags: tuple
    homepage: str
    source_url: str
    screenshots: tuple
    published: str
    versions: tuple              # newest first
    derived: bool = False        # True when a provider translated release metadata (nothing was declared by the author)

    def latest(self, include_prerelease=False):
        """Newest version that is not yanked; stable unless only pre-releases exist and asked for."""
        usable = [v for v in self.versions if not v.yanked]
        stable = [v for v in usable if not v.prerelease and not v.version.is_prerelease]
        pool = stable or (usable if include_prerelease else [])
        return pool[0] if pool else None

    def find(self, version):
        version = Version.parse(version) if isinstance(version, str) else version
        return next((v for v in self.versions if v.version == version), None)


@dataclass(frozen=True)
class RepositoryInfo:
    id: str                      # id the publisher gave it (not our canonical identity)
    name: str
    description: str = ''
    homepage: str = ''
    maintainer: str = ''
    updated: str = ''


@dataclass(frozen=True)
class RepositoryIndex:
    info: RepositoryInfo
    mods: tuple
    schema_version: str
    warnings: tuple = ()         # problems with individual entries that were skipped, never silently

    def get(self, mod_id):
        return next((m for m in self.mods if m.id == mod_id), None)


@dataclass(frozen=True)
class RepositorySource:
    """A repository the user added. `id` is the canonical identity used for trust and de-duplication."""
    id: str
    kind: str                    # 'github' | 'gitlab' | 'https' | 'local'
    url: str                     # what the user gave us ('' for local imports)
    name: str = ''               # optional user-chosen display name
    enabled: bool = True
    added: float = 0.0
    provider: str = ''           # explicit provider choice, e.g. a self-hosted GitLab

    @property
    def uid(self):
        import hashlib
        return hashlib.sha256(self.id.encode('utf-8')).hexdigest()[:16]


@dataclass(frozen=True)
class SyncState:
    """What we last learned about a repository. Persisted next to its cached index."""
    status: str = 'new'          # 'new' | 'ok' | 'error' | 'unsupported'
    compat: str = Compat.UNSUPPORTED.value
    reason: str = ''
    error_code: str = ''
    error_message: str = ''
    last_sync: float = 0.0       # last successful sync
    last_attempt: float = 0.0
    etag: str = ''
    mod_count: int = 0
    warnings: tuple = ()
    display_name: str = ''


@dataclass(frozen=True)
class RepositoryView:
    """Everything the interface needs to draw one row of the Repository Manager."""
    source: RepositorySource
    state: SyncState
    trust: Trust
    trust_note: str = ''
    info: RepositoryInfo | None = None

    @property
    def name(self):
        return self.source.name or (self.info.name if self.info else '') or self.state.display_name or self.source.url or self.source.id

    @property
    def compat(self):
        return Compat(self.state.compat)


@dataclass(frozen=True)
class SearchHit:
    repository: RepositoryView
    mod: Mod
    latest: ModVersion | None
    score: float = 0.0
