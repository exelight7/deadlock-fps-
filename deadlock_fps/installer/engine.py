"""The installation engine for repository mods. Qt-free, so it is testable against temporary game folders.

    prepare()  Download → Verify → Inspect → Stage        touches only the private store, never the game
    commit()   Backup → Install → Verify → Commit         one journaled transaction, rolled back on any failure

Every change to the game folder is a *move* recorded in a write-ahead journal before it happens. A move never
overwrites: the destination must not exist. Replaced and removed files are moved into the store (backups/, trash/),
not deleted, so every operation has a way back, including after a crash (`recover()` replays the journal backwards).

Mods are installed as `pakNN_dir.vpk` into `game/citadel/addons`, the folder every Deadlock mod manager uses. When two
mods provide the same file the lowest number wins, which is how the game loads them.
"""
import json
import os
import shutil
import threading
import time
import uuid
from dataclasses import dataclass, field, replace
from pathlib import Path

from ..core import game_root, ensure_closed, Studio
from urllib.parse import urlsplit

from ..repos.errors import RepoError, CANCELLED as REPO_CANCELLED, DOWNLOAD_FAILED
from ..repos.versions import Version, satisfies
from . import archive
from .errors import (InstallError, NO_GAME, GAME_RUNNING, NOT_INSTALLABLE, DOWNLOAD, HASH_MISMATCH, BAD_PACKAGE, DISK, BLOCKED,
                     ACK_REQUIRED, VERIFY, STALE, NOT_FOUND, IN_USE, CANCELLED, JOURNAL)
from .records import InstalledStore, InstalledMod, InstalledFile, Previous, atomic_write, pak_name, pak_slot, PAK
from .vpk import inspect_vpk, md5_file, sha256_file

MAX_PACKAGE = 2 * 1024 ** 3
UNKNOWN_SIZE_RESERVE = 512 * 1024 ** 2
FREE_MARGIN = 64 * 1024 ** 2
KEEP_PREVIOUS = 3
KEEP_TRASH = 5
GAMEINFO = 'gameinfo'                  # extra code: gameinfo.gi could not be updated


@dataclass(frozen=True)
class PlannedFile:
    name: str                          # final file name in addons, e.g. pak04_dir.vpk
    source: str                        # path inside the package ('' = the package itself)
    size: int
    sha256: str
    entries: int                       # files the VPK provides
    staged: str                        # absolute path in the private staging folder


@dataclass(frozen=True)
class Overlap:
    other: str                         # who else provides these files
    count: int
    sample: tuple
    wins: str                          # 'this' or 'other': lower pak number wins


@dataclass
class InstallPlan:
    tx: str
    repository_id: str
    repository_name: str
    trust: str
    mod_id: str
    mod_name: str
    author: str
    version: str
    action: str                        # 'install' or 'update'
    replaces: str
    package_url: str
    package_size: int
    declared_sha256: str | None
    actual_sha256: str
    verified: bool                     # the published SHA-256 matched the downloaded bytes
    files: tuple
    removed: tuple                     # old file names that the new version no longer provides
    warnings: tuple
    blockers: tuple
    overlaps: tuple
    source_url: str
    dependencies: tuple
    conflicts: tuple
    staging: str
    requires_ack: bool
    derived: bool
    md5_verified: bool = False         # no SHA-256 was published, but the publisher's MD5 matched (damage check only)

    @property
    def can_install(self):
        return not self.blockers


@dataclass(frozen=True)
class Issue:
    severity: str                      # 'error' | 'warning' | 'info'
    code: str
    subject: str
    detail: str


def _now():
    return time.strftime('%Y-%m-%dT%H:%M:%S%z')


class Installer:
    def __init__(self, root, transport, *, guard=None, studio=None, clock=time.time, free_space=None):
        try:
            self.root = game_root(root)
        except ValueError as error:
            raise InstallError(NO_GAME, str(error)) from None
        self.transport = transport
        self.addons = self.root / 'game/citadel/addons'
        self.store_dir = self.root / '.deadlock-fps-studio' / 'mods'
        self.journal_path = self.store_dir / 'journal.json'
        self.records = InstalledStore(self.store_dir / 'installed.json')
        self._guard = guard or ensure_closed
        self._studio = studio or (lambda: Studio(self.root))
        self.clock = clock
        self._free = free_space or (lambda path: shutil.disk_usage(path).free)
        self._lock = threading.RLock()
        self._mods, self._log = self.records.load()

    # ---- state -----------------------------------------------------------------

    def installed(self):
        with self._lock:
            return sorted(self._mods.values(), key=lambda m: (m.name.lower(), m.key))

    def get(self, repository_id, mod_id):
        return self._mods.get((repository_id, mod_id))

    def history(self):
        return list(reversed(self._log))

    def _save(self):
        if self.records.problem and self.records.path.exists():
            # Never overwrite a file we could not read: keep it for the user, then start a fresh one.
            self.records.path.replace(self.records.path.with_name('installed.damaged-%d.json' % int(self.clock())))
            self.records.problem = ''
        self.records.save(self._mods, self._log)

    def _record_log(self, action, mod, version, result, note=''):
        self._log.append({'at': _now(), 'action': action, 'repository_id': mod[0], 'mod_id': mod[1], 'name': mod[2], 'version': version, 'result': result, 'note': note[:300]})

    def _tx(self):
        return '%010d-%s' % (int(self.clock()), uuid.uuid4().hex[:6])

    def _check_game_closed(self):
        try:
            self._guard()
        except ValueError as error:
            raise InstallError(GAME_RUNNING, str(error)) from None

    @staticmethod
    def _uid(repository_id, mod_id):
        import hashlib
        return hashlib.sha256(('%s|%s' % (repository_id, mod_id)).encode('utf-8')).hexdigest()[:12]

    def _disabled_dir(self, mod):
        return self.store_dir / 'disabled' / self._uid(*mod.key)

    def _location(self, mod, name):
        return (self.addons if mod.enabled else self._disabled_dir(mod)) / name

    # ---- journal and moves -------------------------------------------------------

    def _write_journal(self, tx, moves, label):
        atomic_write(self.journal_path, json.dumps({'tx': tx, 'label': label, 'moves': moves}, indent=1).encode('utf-8'))

    def _run_moves(self, tx, moves, label):
        """Perform (src, dst) moves in order, journaled. Any failure undoes the moves already made, then re-raises."""
        done = []
        self._write_journal(tx, done, label)
        try:
            for src, dst in moves:
                src, dst = Path(src), Path(dst)
                if not src.exists():
                    raise InstallError(STALE, 'expected file is missing: %s' % src.name)
                if dst.exists():
                    raise InstallError(STALE, 'refusing to overwrite %s' % dst.name)
                dst.parent.mkdir(parents=True, exist_ok=True)
                done.append([str(src), str(dst)])
                self._write_journal(tx, done, label)          # write-ahead: recorded before it happens
                os.replace(src, dst)
        except BaseException as failure:
            problems = self._undo(done)
            if problems:
                raise InstallError(JOURNAL, 'the operation failed and could not be fully undone (%s); restart the app to retry the recovery' % '; '.join(problems)) from failure
            self.journal_path.unlink(missing_ok=True)
            raise
        return done

    @staticmethod
    def _undo(done):
        problems = []
        for src, dst in reversed(done):
            src, dst = Path(src), Path(dst)
            try:
                if dst.exists() and not src.exists():
                    os.replace(dst, src)
            except OSError as error:
                problems.append('%s: %s' % (dst.name, error))
        return problems

    def _finish(self):
        self.journal_path.unlink(missing_ok=True)

    def recover(self):
        """Undo an interrupted transaction and clear leftovers of an interrupted download. Returns notes for the user."""
        notes = []
        with self._lock:
            if self.journal_path.exists():
                try:
                    journal = json.loads(self.journal_path.read_text(encoding='utf-8'))
                    problems = self._undo(journal.get('moves', []))
                except (OSError, ValueError) as error:
                    raise InstallError(JOURNAL, 'the recovery journal is unreadable: %s' % error) from None
                if problems:
                    raise InstallError(JOURNAL, 'recovery could not move some files back: %s' % '; '.join(problems))
                self.journal_path.unlink(missing_ok=True)
                notes.append('An interrupted operation (%s) was rolled back.' % journal.get('label', 'unknown'))
            for leftover in ('downloads', 'staging'):
                shutil.rmtree(self.store_dir / leftover, ignore_errors=True)
        return notes

    # ---- inspecting the addons folder ------------------------------------------------

    def _addon_files(self):
        try:
            return sorted(p for p in self.addons.iterdir() if p.is_file() and PAK.fullmatch(p.name))
        except OSError:
            return []

    def unmanaged(self):
        """Files in addons that this app did not install (other tools, or the user)."""
        mine = {n for m in self._mods.values() if m.enabled for n in m.file_names()}
        return [p for p in self._addon_files() if p.name not in mine]

    def _used_slots(self):
        used = {pak_slot(p.name) for p in self._addon_files()}
        for mod in self._mods.values():
            used.update(pak_slot(n) for n in mod.file_names())          # disabled mods keep their numbers
        used.discard(None)
        return used

    def _allocate(self, count, taken):
        slots, n = [], 1
        while len(slots) < count:
            if n > 99:
                raise InstallError(DISK, 'there are no free pak slots left (01-99) in the addons folder')
            if n not in taken:
                slots.append(n)
            n += 1
        return [pak_name(s) for s in slots]

    # ---- prepare -------------------------------------------------------------------------

    def prepare(self, repository, mod, version, *, progress=None, cancel=None):
        """Download, verify, inspect and stage `version` of `mod`. The game folder is not touched."""
        if not version.installable:
            raise InstallError(NOT_INSTALLABLE, version.unsupported_reason or 'this version cannot be installed' + (' (withdrawn by its author)' if version.yanked else ''))
        package = version.package
        key = (repository.source.id, mod.id)
        tx = self._tx()
        staging = self.store_dir / 'staging' / tx
        downloads = self.store_dir / 'downloads'
        with self._lock:
            if self.journal_path.exists():
                raise InstallError(JOURNAL, 'an earlier operation was interrupted; restart the app so it can be rolled back first')
            existing = self._mods.get(key)
        staging.mkdir(parents=True)
        downloads.mkdir(parents=True, exist_ok=True)
        part = downloads / (tx + '.part')
        try:
            need = (package.size or UNKNOWN_SIZE_RESERVE) * 2 + FREE_MARGIN
            if self._free(self.store_dir) < need:
                raise InstallError(DISK, 'not enough free disk space: about %d MB are needed' % (need >> 20))
            result = self._download(package, part, progress, cancel)
            verified = md5_verified = False
            if package.sha256:
                if result.sha256 != package.sha256:
                    raise InstallError(HASH_MISMATCH, 'the downloaded file does not match the SHA-256 published in the repository index; it was discarded')
                verified = True
            elif package.md5:
                if md5_file(part) != package.md5.lower():
                    raise InstallError(HASH_MISMATCH, 'the downloaded file does not match the MD5 checksum the publisher gave; it was discarded')
                md5_verified = True
            staged, risky = self._stage(version, part, staging, cancel)
            existing_names = existing.file_names() if existing else []
            names = [existing_names[i] if i < len(existing_names) else None for i in range(len(staged))]
            taken = self._used_slots() - {pak_slot(n) for n in existing_names}
            fresh = iter(self._allocate(sum(1 for n in names if n is None), taken | {pak_slot(n) for n in names if n}))
            names = [n or next(fresh) for n in names]
            files = []
            for name, (source, path) in zip(names, staged):
                final = staging / name
                os.replace(path, final)
                info = inspect_vpk(final)
                files.append(PlannedFile(name, source, final.stat().st_size, sha256_file(final), info.entries, str(final)))
            removed = tuple(n for n in existing_names[len(files):])
            return self._plan(tx, repository, mod, version, existing, package, result, verified, tuple(files), removed, risky, staging, md5_verified)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        finally:
            part.unlink(missing_ok=True)

    def _download(self, package, part, progress, cancel):
        failure = None
        for url in (package.url, *package.mirrors):
            try:
                result = self.transport.download(url, part, max_bytes=min(package.size or MAX_PACKAGE, MAX_PACKAGE), expected_size=package.size, progress=progress, cancel=cancel)
            except RepoError as error:
                if error.code == REPO_CANCELLED:
                    raise InstallError(CANCELLED, 'cancelled') from None
                failure = error
                Path(part).unlink(missing_ok=True)
                continue
            if package.hosts and not self._on_hosts(result.url, package.hosts):
                # Redirects may lead anywhere public; a package that names its hosts is only accepted from them.
                Path(part).unlink(missing_ok=True)
                failure = RepoError(DOWNLOAD_FAILED, 'the download ended on %s, which is not one of the expected hosts' % (urlsplit(result.url).hostname or 'an unknown host'))
                continue
            return result
        raise InstallError(DOWNLOAD, failure.message if failure else 'the download failed') from None

    @staticmethod
    def _on_hosts(url, hosts):
        host = (urlsplit(url).hostname or '').lower()
        return any(host == h or host.endswith('.' + h) for h in hosts)

    def _stage(self, version, part, staging, cancel):
        """[(source path in package, staged path)], risky extra files. Everything is inspected before anything is kept."""
        if version.package.format == 'vpk':
            target = staging / 'single.vpk'
            os.replace(part, target)
            return [('', target)], ()
        wanted = [f.source for f in version.install.files]
        report = archive.inspect_zip(part, wanted, discover=version.install.discover)
        staged = []
        for position, name in enumerate(report.members):
            target = staging / ('member%d.vpk' % position)
            archive.extract_member(part, name, target, cancel=cancel)
            staged.append((name, target))
        return staged, report.risky

    def _plan(self, tx, repository, mod, version, existing, package, result, verified, files, removed, risky, staging, md5_verified=False):
        warnings, blockers = [], []
        installed = [m for m in self._mods.values() if m.key != (repository.source.id, mod.id)]
        for relation in version.dependencies:
            have = [m for m in installed if m.mod_id == relation.id and m.enabled and self._satisfies(m.version, relation.range)]
            if not have:
                blockers.append('Requires %s (%s), which is not installed or is disabled.' % (relation.id, relation.range))
        for relation in version.conflicts:
            for other in installed:
                if other.mod_id == relation.id and self._satisfies(other.version, relation.range):
                    blockers.append('Conflicts with the installed mod %s%s' % (other.name, ': ' + relation.reason if relation.reason else '.'))
        for other in installed:
            for conflict in other.conflicts:
                if conflict[0] == mod.id and self._satisfies(version.version.text, conflict[1]):
                    blockers.append('The installed mod %s declares a conflict with this mod%s' % (other.name, ': ' + conflict[2] if len(conflict) > 2 and conflict[2] else '.'))
        overlaps = self._overlaps(files, existing)
        for overlap in overlaps:
            warnings.append('%d files are also provided by %s; %s.' % (overlap.count, overlap.other, 'this mod takes priority' if overlap.wins == 'this' else 'the other takes priority'))
        if md5_verified:
            warnings.append('The publisher gave only an MD5 checksum and the download matched it. That detects a damaged download, not one that was deliberately changed.')
        elif not verified:
            warnings.append('The repository published no SHA-256 for this file, so its integrity could not be checked against the publisher.')
        trust = repository.trust.value
        if trust == 'UNVERIFIED':
            warnings.append('This repository is UNVERIFIED: nobody has reviewed it.')
        if mod.derived:
            warnings.append('This entry was derived from release files; the author provided no description or compatibility information.')
        for name in risky:
            warnings.append('The archive also contains %s. It will not be installed or run.' % name)
        if existing and existing.version == version.version.text:
            warnings.append('This version is already installed; installing again replaces its files.')
        return InstallPlan(
            tx=tx, repository_id=repository.source.id, repository_name=repository.name, trust=trust, mod_id=mod.id, mod_name=mod.name, author=mod.author,
            version=version.version.text, action='update' if existing else 'install', replaces=existing.version if existing else '',
            package_url=package.url, package_size=result.size, declared_sha256=package.sha256, actual_sha256=result.sha256, verified=verified,
            files=files, removed=removed, warnings=tuple(warnings), blockers=tuple(blockers), overlaps=overlaps,
            source_url=mod.source_url or mod.homepage, dependencies=tuple((r.id, r.range) for r in version.dependencies),
            conflicts=tuple((r.id, r.range, r.reason) for r in version.conflicts), staging=str(staging),
            requires_ack=(not verified) or trust == 'UNVERIFIED' or mod.derived, derived=mod.derived, md5_verified=md5_verified)

    @staticmethod
    def _satisfies(installed_version, version_range):
        try:
            return satisfies(Version.parse(installed_version), version_range)
        except RepoError:
            return False

    def _overlaps(self, files, existing):
        own = set(existing.file_names()) if existing else set()
        names = {m_file: m for m in self._mods.values() for m_file in m.file_names()}
        found = []
        planned = {f.name: inspect_vpk(f.staged).paths for f in files}
        for path in self._addon_files():
            if path.name in own:
                continue
            try:
                other = inspect_vpk(path).paths
            except InstallError:
                continue
            owner = names.get(path.name)
            label = '%s (%s)' % (owner.name, path.name) if owner else '%s (not installed by Toolbox)' % path.name
            for name, paths in planned.items():
                shared = paths & other
                if shared:
                    wins = 'this' if pak_slot(name) < pak_slot(path.name) else 'other'
                    found.append(Overlap(label, len(shared), tuple(sorted(shared)[:5]), wins))
        return tuple(found)

    def discard(self, plan):
        shutil.rmtree(plan.staging, ignore_errors=True)

    # ---- commit ----------------------------------------------------------------------------------

    def commit(self, plan, *, acknowledged=False):
        """Install a prepared plan. Returns the InstalledMod. On any failure the game folder is exactly as it was."""
        if plan.blockers:
            raise InstallError(BLOCKED, ' '.join(plan.blockers))
        if plan.requires_ack and not acknowledged:
            raise InstallError(ACK_REQUIRED, 'the warnings in the preview must be acknowledged before installing')
        with self._lock:
            self._check_game_closed()
            if self.journal_path.exists():
                raise InstallError(JOURNAL, 'an earlier operation was interrupted; restart the app so it can be rolled back first')
            for planned in plan.files:
                staged = Path(planned.staged)
                if not staged.is_file() or staged.stat().st_size != planned.size or sha256_file(staged) != planned.sha256:
                    raise InstallError(STALE, 'the staged files changed after the preview; prepare the installation again')
            key = (plan.repository_id, plan.mod_id)
            existing = self._mods.get(key)
            try:
                self._studio().enable_addons(str(self.store_dir))
            except (ValueError, OSError) as error:
                raise InstallError(GAMEINFO, 'gameinfo.gi could not be prepared: %s' % error) from None
            backup = self.store_dir / 'backups' / plan.tx
            moves, backed_up = [], []
            owned = set(existing.file_names()) if existing else set()
            for name in sorted(owned):
                source = self._location(existing, name)
                if source.exists():
                    moves.append((source, backup / name))
                    backed_up.append(name)
            for planned in plan.files:
                if planned.name not in owned and (self.addons / planned.name).exists():
                    raise InstallError(STALE, '%s appeared in the addons folder after the preview; prepare the installation again' % planned.name)
                moves.append((planned.staged, self.addons / planned.name))
            self.addons.mkdir(parents=True, exist_ok=True)
            label = '%s %s %s' % (plan.action, plan.mod_name, plan.version)
            self._run_moves(plan.tx, moves, label)
            try:
                self._verify(plan)
                mod = self._record_install(plan, existing, backup, backed_up)
                self._save()
            except BaseException as failure:
                done = json.loads(self.journal_path.read_text(encoding='utf-8'))['moves']
                problems = self._undo(done)
                self._mods, self._log = self.records.load()
                if problems:
                    raise InstallError(JOURNAL, 'verification failed and the rollback was incomplete (%s)' % '; '.join(problems)) from failure
                self._finish()
                if isinstance(failure, InstallError):
                    raise
                raise InstallError(VERIFY, 'the installed files could not be recorded: %s' % failure) from failure
            self._finish()
            shutil.rmtree(plan.staging, ignore_errors=True)
            if not backed_up:
                shutil.rmtree(backup, ignore_errors=True)
            self._prune(mod)
            return self._mods[mod.key]

    def _verify(self, plan):
        for planned in plan.files:
            target = self.addons / planned.name
            if not target.is_file() or target.stat().st_size != planned.size or sha256_file(target) != planned.sha256:
                raise InstallError(VERIFY, '%s did not verify after installation' % planned.name)
            inspect_vpk(target)

    def _record_install(self, plan, existing, backup, backed_up):
        now = _now()
        files = tuple(InstalledFile(f.name, f.sha256, f.size, f.source) for f in plan.files)
        previous = tuple(existing.previous) if existing else ()
        history = tuple(existing.history) if existing else ()
        if existing and backed_up:
            previous += (Previous(existing.version, plan.tx, tuple(backed_up), now),)
        mod = InstalledMod(
            repository_id=plan.repository_id, mod_id=plan.mod_id, name=plan.mod_name, version=plan.version, files=files, enabled=True, author=plan.author,
            repository_name=plan.repository_name, trust=plan.trust, source_url=plan.source_url, package_url=plan.package_url, package_sha256=plan.actual_sha256,
            package_verified=plan.verified, installed_at=existing.installed_at if existing else now, updated_at=now, dependencies=plan.dependencies,
            conflicts=plan.conflicts, previous=previous, history=history + ({'at': now, 'action': plan.action, 'version': plan.version, 'note': 'verified' if plan.verified else 'no publisher hash'},))
        self._mods[mod.key] = mod
        self._record_log(plan.action, (plan.repository_id, plan.mod_id, plan.mod_name), plan.version, 'ok')
        return mod

    def _prune(self, mod):
        keep = mod.previous[-KEEP_PREVIOUS:]
        for old in mod.previous[:-KEEP_PREVIOUS]:
            shutil.rmtree(self.store_dir / 'backups' / old.backup, ignore_errors=True)
        if keep != mod.previous:
            self._mods[mod.key] = replace(mod, previous=tuple(keep))
            self._save()

    # ---- other operations --------------------------------------------------------------------------

    def _require(self, repository_id, mod_id):
        mod = self._mods.get((repository_id, mod_id))
        if not mod:
            raise InstallError(NOT_FOUND, 'that mod is not installed')
        return mod

    def dependents(self, mod):
        return [m for m in self._mods.values() if m.key != mod.key and m.enabled and any(d[0] == mod.mod_id for d in m.dependencies)]

    def uninstall(self, repository_id, mod_id, *, force=False):
        """Remove a mod. Its files are kept in the store's trash for recovery, not deleted."""
        with self._lock:
            mod = self._require(repository_id, mod_id)
            users = self.dependents(mod)
            if users and not force:
                raise InstallError(IN_USE, 'required by: %s' % ', '.join(sorted(m.name for m in users)))
            self._check_game_closed()
            tx = self._tx()
            trash = self.store_dir / 'trash' / tx
            moves = [(self._location(mod, n), trash / n) for n in mod.file_names() if self._location(mod, n).exists()]
            self._run_moves(tx, moves, 'uninstall %s' % mod.name)
            try:
                del self._mods[mod.key]
                self._record_log('uninstall', (mod.repository_id, mod.mod_id, mod.name), mod.version, 'ok', 'files kept in the recovery folder')
                self._save()
            except BaseException:
                self._undo(json.loads(self.journal_path.read_text(encoding='utf-8'))['moves'])
                self._mods, self._log = self.records.load()
                self._finish()
                raise
            self._finish()
            for old in mod.previous:
                shutil.rmtree(self.store_dir / 'backups' / old.backup, ignore_errors=True)
            shutil.rmtree(self._disabled_dir(mod), ignore_errors=True)
            self._prune_trash()
            return trash

    def _prune_trash(self):
        base = self.store_dir / 'trash'
        for old in sorted(p for p in base.iterdir() if p.is_dir())[:-KEEP_TRASH] if base.exists() else []:
            shutil.rmtree(old, ignore_errors=True)

    def set_enabled(self, repository_id, mod_id, enabled):
        """Disable moves the files out of the load path (the game then cannot see them); enable moves them back."""
        with self._lock:
            mod = self._require(repository_id, mod_id)
            if mod.enabled == bool(enabled):
                return mod
            self._check_game_closed()
            tx = self._tx()
            if enabled:
                try:
                    self._studio().enable_addons(str(self.store_dir))
                except (ValueError, OSError) as error:
                    raise InstallError(GAMEINFO, 'gameinfo.gi could not be prepared: %s' % error) from None
                taken = {p.name for p in self._addon_files()}
                # Every slot in use is off limits, this mod's own reserved ones included: a name is only kept when its file is free.
                names, fresh = [], iter(self._allocate(len(mod.files), self._used_slots() | {pak_slot(n) for n in taken}))
                for f in mod.files:
                    names.append(f.name if f.name not in taken else next(fresh))
                moves = [(self._disabled_dir(mod) / f.name, self.addons / new) for f, new in zip(mod.files, names)]
                files = tuple(replace(f, name=new) for f, new in zip(mod.files, names))
                updated = replace(mod, enabled=True, files=files)
            else:
                moves = [(self.addons / n, self._disabled_dir(mod) / n) for n in mod.file_names()]
                updated = replace(mod, enabled=False)
            self._run_moves(tx, moves, '%s %s' % ('enable' if enabled else 'disable', mod.name))
            return self._commit_record(updated, 'enable' if enabled else 'disable', mod)

    def _commit_record(self, updated, action, before):
        try:
            history = tuple(updated.history) + ({'at': _now(), 'action': action, 'version': updated.version, 'note': ''},)
            self._mods[updated.key] = replace(updated, history=history, updated_at=_now())
            self._record_log(action, (updated.repository_id, updated.mod_id, updated.name), updated.version, 'ok')
            self._save()
        except BaseException:
            self._undo(json.loads(self.journal_path.read_text(encoding='utf-8'))['moves'])
            self._mods, self._log = self.records.load()
            self._finish()
            raise
        self._finish()
        return self._mods[updated.key]

    def restore_previous(self, repository_id, mod_id):
        """Go back to the version that was installed before the last update. The current version becomes the new 'previous'."""
        with self._lock:
            mod = self._require(repository_id, mod_id)
            if not mod.previous:
                raise InstallError(NOT_FOUND, 'there is no earlier version to restore')
            self._check_game_closed()
            target = mod.previous[-1]
            folder = self.store_dir / 'backups' / target.backup
            infos = []
            for name in target.files:
                path = folder / name
                if not path.is_file():
                    raise InstallError(NOT_FOUND, 'the saved copy of version %s is no longer available' % target.version)
                inspect_vpk(path)
                infos.append(InstalledFile(name, sha256_file(path), path.stat().st_size))
            tx = self._tx()
            new_backup = self.store_dir / 'backups' / tx
            moves = [(self._location(mod, n), new_backup / n) for n in mod.file_names() if self._location(mod, n).exists()]
            destination = self.addons if mod.enabled else self._disabled_dir(mod)
            moves += [(folder / n, destination / n) for n in target.files]
            self._run_moves(tx, moves, 'restore %s %s' % (mod.name, target.version))
            now = _now()
            previous = tuple(p for p in mod.previous if p is not target) + (Previous(mod.version, tx, tuple(mod.file_names()), now),)
            updated = replace(mod, version=target.version, files=tuple(infos), previous=previous[-KEEP_PREVIOUS:], package_sha256='', package_verified=False)
            result = self._commit_record(updated, 'restore', mod)
            shutil.rmtree(folder, ignore_errors=True)
            return result

    # ---- health ---------------------------------------------------------------------------------------

    def analyze(self):
        """Read-only health check of everything Toolbox installed, and of the addons folder as a whole."""
        issues = []
        studio = self._studio()
        if self._mods and not studio.addons_enabled():
            issues.append(Issue('error', 'inactive', 'gameinfo.gi', 'gameinfo.gi does not list citadel/addons, so the game ignores every installed mod. Steam probably restored the file; use Repair.'))
        trees = {}
        for mod in sorted(self._mods.values(), key=lambda m: m.name.lower()):
            if not mod.enabled:
                continue
            for f in mod.files:
                path = self.addons / f.name
                if not path.is_file():
                    issues.append(Issue('error', 'missing', mod.name, '%s is missing from the addons folder.' % f.name))
                    continue
                if path.stat().st_size != f.size or sha256_file(path) != f.sha256:
                    issues.append(Issue('error', 'modified', mod.name, '%s was changed after installation.' % f.name))
                    continue
                try:
                    trees[f.name] = (mod.name, inspect_vpk(path).paths)
                except InstallError as error:
                    issues.append(Issue('error', 'damaged', mod.name, error.message))
        for path in self.unmanaged():
            try:
                trees[path.name] = ('%s (not installed by Toolbox)' % path.name, inspect_vpk(path).paths)
                issues.append(Issue('info', 'unmanaged', path.name, 'Not installed by Toolbox; it is loaded but not tracked.'))
            except InstallError as error:
                issues.append(Issue('warning', 'unreadable', path.name, error.message))
        names = sorted(trees, key=lambda n: pak_slot(n))
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                shared = trees[a][1] & trees[b][1]
                if shared:
                    issues.append(Issue('warning', 'overlap', '%s + %s' % (trees[a][0], trees[b][0]),
                                        '%d shared files; %s (%s) wins over %s (%s).' % (len(shared), trees[a][0], a, trees[b][0], b)))
        for mod in self._mods.values():
            for dep in mod.dependencies:
                if not any(m.mod_id == dep[0] and m.enabled and self._satisfies(m.version, dep[1]) for m in self._mods.values() if m.key != mod.key):
                    issues.append(Issue('warning', 'dependency', mod.name, 'Requires %s (%s), which is not installed or is disabled.' % (dep[0], dep[1])))
        return issues

    def repair(self):
        """Re-register citadel/addons (for example after Steam restored gameinfo.gi)."""
        with self._lock:
            self._check_game_closed()
            try:
                return self._studio().enable_addons(str(self.store_dir))
            except (ValueError, OSError) as error:
                raise InstallError(GAMEINFO, 'gameinfo.gi could not be repaired: %s' % error) from None
