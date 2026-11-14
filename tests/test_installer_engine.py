"""The installation engine against a throwaway game folder: pipeline, safety, rollback, recovery."""
import json
import os
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from deadlock_fps import kv
from deadlock_fps.installer import Installer, InstallError
from deadlock_fps.installer.records import InstalledStore
from deadlock_fps.installer.vpk import sha256_file
from deadlock_fps.repos.model import GameFit, Trust
from installer_fixtures import GameCase, make_vpk, make_zip, view, HOST

SKIN = make_vpk(['materials/shared/skin.vmat'], b'v1')
SKIN2 = make_vpk(['materials/shared/skin.vmat', 'materials/shared/extra.vmat'], b'v2')
HUD = make_vpk(['panorama/hud.css'], b'hud')


class Pipeline(GameCase):
    def test_prepare_downloads_verifies_and_stages_without_touching_the_game(self):
        mod = self.offer('crimson', [{'version': '1.0.0', 'data': SKIN}])
        before = self.game_snapshot()
        steps = []
        plan = self.installer.prepare(view(), mod, mod.latest(), progress=lambda a, b: steps.append((a, b)))
        self.assertEqual(self.game_snapshot(), before)
        self.assertFalse(self.addons.exists())
        self.assertEqual((plan.action, plan.version, plan.verified, plan.can_install), ('install', '1.0.0', True, True))
        self.assertEqual([f.name for f in plan.files], ['pak01_dir.vpk'])
        self.assertEqual(plan.files[0].entries, 1)
        self.assertEqual(plan.actual_sha256, plan.declared_sha256)
        self.assertEqual(steps[-1][0], len(SKIN))
        self.assertTrue(Path(plan.files[0].staged).is_file())
        self.installer.discard(plan)
        self.assertFalse(Path(plan.staging).exists())

    def test_commit_installs_verifies_records_and_registers_the_search_path(self):
        mod = self.offer('crimson', [{'version': '1.0.0', 'data': SKIN}])
        installed = self.install(mod)
        self.assertEqual((self.addons / 'pak01_dir.vpk').read_bytes(), SKIN)
        self.assertTrue(kv.has_addons_path(self.gi.read_text(encoding='utf-8')))
        self.assertEqual((installed.version, installed.enabled, installed.package_verified, installed.trust), ('1.0.0', True, True, 'COMMUNITY'))
        self.assertEqual(installed.files[0].sha256, sha256_file(self.addons / 'pak01_dir.vpk'))
        self.assertFalse(self.installer.journal_path.exists())
        self.assertFalse((self.installer.store_dir / 'staging').exists() and any((self.installer.store_dir / 'staging').iterdir()))
        again = self.new_installer()
        self.assertEqual([m.name for m in again.installed()], ['Crimson'])
        self.assertEqual(again.history()[0]['action'], 'install')

    def test_zip_packages_install_only_the_listed_vpk_files(self):
        data = make_zip({'pak/a.vpk': SKIN, 'pak/b.vpk': HUD, 'extra.vpk': b'ignored'}, {'setup.exe': b'MZ'})
        mod = self.offer('pack', [{'version': '1.0.0', 'data': data, 'format': 'zip', 'install': {'type': 'vpk', 'files': [{'source': 'pak/a.vpk'}, {'source': 'pak/b.vpk'}]}}])
        plan = self.installer.prepare(view(), mod, mod.latest())
        self.assertTrue(any('setup.exe' in w and 'will not be installed or run' in w for w in plan.warnings))
        self.installer.commit(plan, acknowledged=True)
        self.assertEqual(self.addon_names(), ['pak01_dir.vpk', 'pak02_dir.vpk'])
        self.assertEqual((self.addons / 'pak01_dir.vpk').read_bytes(), SKIN)
        self.assertEqual((self.addons / 'pak02_dir.vpk').read_bytes(), HUD)
        self.assertFalse(any(p.suffix == '.exe' for p in self.root.rglob('*')))

    def test_a_tampered_download_is_discarded(self):
        mod = self.offer('crimson', [{'version': '1.0.0', 'data': SKIN}])
        self.transport.files[HOST + 'crimson-1.0.0.vpk'] = SKIN[:-1] + b'X'
        with self.assertRaises(InstallError) as caught:
            self.installer.prepare(view(), mod, mod.latest())
        self.assertEqual(caught.exception.code, 'hash-mismatch')
        self.assertEqual(self.leftovers(), [])

    def leftovers(self):
        base = self.installer.store_dir
        return [p for sub in ('staging', 'downloads') for p in (base / sub).rglob('*') if p.is_file()] if base.exists() else []

    def test_wrong_size_truncated_and_unavailable_downloads_fail_cleanly(self):
        mod = self.offer('crimson', [{'version': '1.0.0', 'data': SKIN}])
        for data in (SKIN + b'extra', SKIN[:10], None):
            if data is None:
                self.transport.files.pop(HOST + 'crimson-1.0.0.vpk')
            else:
                self.transport.files[HOST + 'crimson-1.0.0.vpk'] = data
            with self.assertRaises(InstallError) as caught:
                self.installer.prepare(view(), mod, mod.latest())
            self.assertEqual(caught.exception.code, 'download')
            self.assertEqual(self.leftovers(), [])

    def test_mirrors_are_tried_when_the_primary_fails(self):
        mod = self.offer('crimson', [{'version': '1.0.0', 'data': SKIN, 'package': {'mirrors': ['https://mirror.example.net/c.vpk']}}])
        self.transport.files['https://mirror.example.net/c.vpk'] = SKIN
        self.transport.files.pop(HOST + 'crimson-1.0.0.vpk')
        plan = self.installer.prepare(view(), mod, mod.latest())
        self.assertEqual(self.transport.downloads, [HOST + 'crimson-1.0.0.vpk', 'https://mirror.example.net/c.vpk'])
        self.assertTrue(plan.verified)

    def test_a_package_that_is_not_a_vpk_is_refused_after_a_good_hash(self):
        mod = self.offer('fake', [{'version': '1.0.0', 'data': b'MZ this is an executable pretending to be a mod'}])
        with self.assertRaises(InstallError) as caught:
            self.installer.prepare(view(), mod, mod.latest())
        self.assertEqual(caught.exception.code, 'bad-package')
        self.assertEqual(self.leftovers(), [])
        self.assertFalse(self.addons.exists())

    def test_withdrawn_and_unsupported_versions_cannot_be_prepared(self):
        mod = self.offer('old', [{'version': '1.0.0', 'data': SKIN, 'yanked': True}, {'version': '2.0.0', 'data': SKIN, 'format': '7z'}])
        for v in mod.versions:
            with self.assertRaises(InstallError) as caught:
                self.installer.prepare(view(), mod, v)
            self.assertEqual(caught.exception.code, 'not-installable')
        self.assertEqual(self.transport.downloads, [])

    def test_free_disk_space_is_checked_before_downloading(self):
        installer = self.new_installer(free_space=lambda path: 1024)
        mod = self.offer('crimson', [{'version': '1.0.0', 'data': SKIN}])
        with self.assertRaises(InstallError) as caught:
            installer.prepare(view(), mod, mod.latest())
        self.assertEqual(caught.exception.code, 'disk')
        self.assertEqual(self.transport.downloads, [])

    def test_cancelling_during_download_leaves_nothing_behind(self):
        mod = self.offer('crimson', [{'version': '1.0.0', 'data': SKIN}])
        event = threading.Event()
        event.set()
        with self.assertRaises(InstallError) as caught:
            self.installer.prepare(view(), mod, mod.latest(), cancel=event)
        self.assertEqual(caught.exception.code, 'cancelled')
        self.assertEqual(self.leftovers(), [])


class Acknowledgement(GameCase):
    def plan(self, trust=Trust.COMMUNITY, **version):
        mod = self.offer('crimson', [{'version': '1.0.0', 'data': SKIN, **version}])
        return self.installer.prepare(view(trust=trust), mod, mod.latest())

    def test_a_verified_hash_from_a_reviewed_source_needs_no_acknowledgement(self):
        for trust in (Trust.OFFICIAL, Trust.VERIFIED, Trust.COMMUNITY):
            plan = self.plan(trust)
            self.assertFalse(plan.requires_ack, trust)
            self.installer.discard(plan)

    def test_unverified_sources_and_missing_hashes_must_be_acknowledged_by_the_engine_itself(self):
        for trust, hash_published in ((Trust.UNVERIFIED, True), (Trust.COMMUNITY, False), (Trust.UNVERIFIED, False)):
            plan = self.plan(trust, hash=hash_published)
            self.assertTrue(plan.requires_ack)
            self.assertTrue(any('UNVERIFIED' in w or 'SHA-256' in w for w in plan.warnings))
            with self.assertRaises(InstallError) as caught:
                self.installer.commit(plan)
            self.assertEqual(caught.exception.code, 'ack-required')
            self.assertFalse(self.addons.exists())
            self.installer.discard(plan)
        plan = self.plan(Trust.UNVERIFIED, hash=False)
        self.assertFalse(plan.verified)
        self.installer.commit(plan, acknowledged=True)
        self.assertFalse(self.installer.installed()[0].package_verified)


class Slots(GameCase):
    def test_slots_skip_files_that_already_exist_whoever_owns_them(self):
        self.addons.mkdir(parents=True)
        (self.addons / 'pak01_dir.vpk').write_bytes(make_vpk(['other/file.txt']))
        (self.addons / 'pak03_dir.vpk').write_bytes(make_vpk(['other/file2.txt']))
        self.install(self.offer('mod-a', [{'version': '1.0.0', 'data': make_vpk(['a/a.txt'])}]))
        self.install(self.offer('mod-b', [{'version': '1.0.0', 'data': make_vpk(['b/b.txt'])}]))
        self.assertEqual(self.addon_names(), ['pak01_dir.vpk', 'pak02_dir.vpk', 'pak03_dir.vpk', 'pak04_dir.vpk'])
        self.assertEqual([f.name for m in self.installer.installed() for f in m.files], ['pak02_dir.vpk', 'pak04_dir.vpk'])

    def test_a_freed_slot_is_reused_and_unmanaged_files_are_never_touched(self):
        self.addons.mkdir(parents=True)
        foreign = make_vpk(['other/file.txt'])
        (self.addons / 'pak01_dir.vpk').write_bytes(foreign)
        a = self.install(self.offer('mod-a', [{'version': '1.0.0', 'data': make_vpk(['a/a.txt'])}]))
        self.installer.uninstall(*a.key)
        self.install(self.offer('mod-b', [{'version': '1.0.0', 'data': make_vpk(['b/b.txt'])}]))
        self.assertEqual(self.installer.installed()[0].files[0].name, 'pak02_dir.vpk')
        self.assertEqual((self.addons / 'pak01_dir.vpk').read_bytes(), foreign)
        self.assertEqual([p.name for p in self.installer.unmanaged()], ['pak01_dir.vpk'])

    def test_running_out_of_slots_is_an_error_not_an_overwrite(self):
        self.addons.mkdir(parents=True)
        for n in range(1, 100):
            (self.addons / ('pak%02d_dir.vpk' % n)).write_bytes(make_vpk(['f/%d.txt' % n]))
        mod = self.offer('late', [{'version': '1.0.0', 'data': SKIN}])
        with self.assertRaises(InstallError):
            self.installer.prepare(view(), mod, mod.latest())
        self.assertEqual((self.addons / 'pak99_dir.vpk').read_bytes(), make_vpk(['f/99.txt']))


class Relationships(GameCase):
    def test_overlaps_with_installed_and_foreign_files_are_reported_with_the_winner(self):
        self.addons.mkdir(parents=True)
        (self.addons / 'pak01_dir.vpk').write_bytes(make_vpk(['materials/shared/skin.vmat'], b'foreign'))
        plan = self.installer.prepare(view(), *self.mod_and_version('crimson', SKIN))
        self.assertEqual(len(plan.overlaps), 1)
        overlap = plan.overlaps[0]
        self.assertEqual((overlap.count, overlap.wins), (1, 'other'))
        self.assertIn('not installed by Toolbox', overlap.other)
        self.assertTrue(any('takes priority' in w for w in plan.warnings))
        self.assertTrue(plan.can_install)

    def mod_and_version(self, ident, data, **kw):
        mod = self.offer(ident, [{'version': '1.0.0', 'data': data, **kw}])
        return mod, mod.latest()

    def test_missing_dependencies_block_and_installing_the_dependency_first_unblocks(self):
        needs = self.offer('needs-lib', [{'version': '1.0.0', 'data': HUD, 'dependencies': [{'id': 'the-lib', 'range': '>=1.2 <2'}]}])
        plan = self.installer.prepare(view(), needs, needs.latest())
        self.assertFalse(plan.can_install)
        self.assertIn('the-lib', plan.blockers[0])
        with self.assertRaises(InstallError) as caught:
            self.installer.commit(plan, acknowledged=True)
        self.assertEqual(caught.exception.code, 'blocked')
        self.assertFalse(self.addons.exists())
        old = self.offer('the-lib', [{'version': '1.1.0', 'data': SKIN}])
        self.install(old)
        self.assertFalse(self.installer.prepare(view(), needs, needs.latest()).can_install)          # 1.1.0 is outside the range
        newer = self.offer('the-lib', [{'version': '1.5.0', 'data': SKIN2}])
        self.install(newer)
        self.assertTrue(self.installer.prepare(view(), needs, needs.latest()).can_install)

    def test_declared_conflicts_block_in_both_directions(self):
        self.install(self.offer('first', [{'version': '1.0.0', 'data': SKIN}]))
        second = self.offer('second', [{'version': '1.0.0', 'data': HUD, 'conflicts': [{'id': 'first', 'range': '*', 'reason': 'both recolour the hero'}]}])
        plan = self.installer.prepare(view(), second, second.latest())
        self.assertFalse(plan.can_install)
        self.assertIn('both recolour the hero', plan.blockers[0])
        self.install(self.offer('third', [{'version': '1.0.0', 'data': make_vpk(['x/y.txt']), 'conflicts': [{'id': 'fourth', 'range': '*'}]}]))
        fourth = self.offer('fourth', [{'version': '1.0.0', 'data': make_vpk(['z/w.txt'])}])
        plan = self.installer.prepare(view(), fourth, fourth.latest())
        self.assertFalse(plan.can_install)
        self.assertIn('declares a conflict', plan.blockers[0])

    def test_a_mod_that_others_need_cannot_be_uninstalled_without_force(self):
        lib = self.install(self.offer('the-lib', [{'version': '1.5.0', 'data': SKIN}]))
        self.install(self.offer('needs-lib', [{'version': '1.0.0', 'data': HUD, 'dependencies': [{'id': 'the-lib', 'range': '*'}]}]))
        with self.assertRaises(InstallError) as caught:
            self.installer.uninstall(*lib.key)
        self.assertEqual(caught.exception.code, 'in-use')
        self.assertTrue((self.addons / 'pak01_dir.vpk').exists())
        self.installer.uninstall(*lib.key, force=True)
        self.assertTrue(any(i.code == 'dependency' for i in self.installer.analyze()))


class Updates(GameCase):
    def setUp(self):
        super().setUp()
        self.mod = self.offer('crimson', [{'version': '1.0.0', 'data': SKIN}, {'version': '2.0.0', 'data': SKIN2}])
        self.v1 = self.install(self.mod, '1.0.0')

    def test_an_update_replaces_files_in_the_same_slot_and_keeps_the_old_version(self):
        updated = self.install(self.mod, '2.0.0')
        self.assertEqual((updated.version, [f.name for f in updated.files]), ('2.0.0', ['pak01_dir.vpk']))
        self.assertEqual((self.addons / 'pak01_dir.vpk').read_bytes(), SKIN2)
        self.assertEqual(len(updated.previous), 1)
        self.assertEqual(updated.previous[0].version, '1.0.0')
        backup = self.installer.store_dir / 'backups' / updated.previous[0].backup / 'pak01_dir.vpk'
        self.assertEqual(backup.read_bytes(), SKIN)
        self.assertEqual([h['action'] for h in updated.history], ['install', 'update'])

    def test_restore_previous_swaps_back_and_the_swap_is_itself_reversible(self):
        self.install(self.mod, '2.0.0')
        back = self.installer.restore_previous(*self.v1.key)
        self.assertEqual((back.version, (self.addons / 'pak01_dir.vpk').read_bytes()), ('1.0.0', SKIN))
        self.assertEqual(back.previous[-1].version, '2.0.0')
        again = self.installer.restore_previous(*self.v1.key)
        self.assertEqual((again.version, (self.addons / 'pak01_dir.vpk').read_bytes()), ('2.0.0', SKIN2))
        self.assertFalse(self.installer.journal_path.exists())

    def test_a_version_with_fewer_or_more_files_adds_and_removes_slots_safely(self):
        two = self.offer('multi', [{'version': '1.0.0', 'data': make_zip({'a.vpk': SKIN, 'b.vpk': HUD}), 'format': 'zip', 'install': {'type': 'vpk', 'files': [{'source': 'a.vpk'}, {'source': 'b.vpk'}]}},
                                   {'version': '2.0.0', 'data': make_zip({'a.vpk': SKIN2}), 'format': 'zip', 'install': {'type': 'vpk', 'files': [{'source': 'a.vpk'}]}},
                                   {'version': '3.0.0', 'data': make_zip({'a.vpk': SKIN, 'b.vpk': HUD, 'c.vpk': make_vpk(['c/c.txt'])}), 'format': 'zip',
                                    'install': {'type': 'vpk', 'files': [{'source': 'a.vpk'}, {'source': 'b.vpk'}, {'source': 'c.vpk'}]}}])
        self.install(two, '1.0.0')
        self.assertEqual(self.addon_names(), ['pak01_dir.vpk', 'pak02_dir.vpk', 'pak03_dir.vpk'])      # pak01 belongs to 'crimson'
        shrunk = self.install(two, '2.0.0')
        self.assertEqual([f.name for f in shrunk.files], ['pak02_dir.vpk'])
        self.assertEqual(self.addon_names(), ['pak01_dir.vpk', 'pak02_dir.vpk'])
        self.assertEqual(shrunk.previous[-1].files, ('pak02_dir.vpk', 'pak03_dir.vpk'))
        grown = self.install(two, '3.0.0')
        self.assertEqual([f.name for f in grown.files], ['pak02_dir.vpk', 'pak03_dir.vpk', 'pak04_dir.vpk'])

    def test_only_the_last_three_previous_versions_keep_their_backups(self):
        versions = [{'version': '%d.0.0' % n, 'data': make_vpk(['v/%d.txt' % n], b'%d' % n)} for n in range(1, 7)]
        mod = self.offer('many', versions)
        for n in range(1, 7):
            current = self.install(mod, '%d.0.0' % n)
        self.assertEqual([p.version for p in current.previous], ['3.0.0', '4.0.0', '5.0.0'])
        self.assertEqual(len(list((self.installer.store_dir / 'backups').iterdir())), 3)

    def test_update_status_compares_against_the_catalogue_and_never_crosses_repositories(self):
        from deadlock_fps.installer import update_status
        from deadlock_fps.repos import RepositoryManager, RepositoryStore, TrustRegistry
        from repo_fixtures import ok, index, mod as mod_doc, version as version_doc
        transport = self.transport
        document = index(mod_doc('crimson', versions=[version_doc('2.0.0', game={'min_build': 100, 'max_build': 120}), version_doc('1.0.0')]), mod_doc('gone-soon', versions=[version_doc('1.0.0')]))
        transport.routes['https://mods.example.org/index.json'] = ok(document)
        manager = RepositoryManager(RepositoryStore(Path(self.temp.name) / 'repos'), transport, trust=TrustRegistry({}))
        rid = manager.add('https://mods.example.org/index.json').source.id
        manager.refresh(rid)
        mine = self.installer.get(self.v1.repository_id, 'crimson')
        # The installed record points at the fixture's repository id, which is the one we added.
        self.assertEqual(rid, mine.repository_id)
        [status] = update_status([mine], manager, game_build=150)
        self.assertEqual((status.state, status.latest, status.fit), ('update', '2.0.0', GameFit.INCOMPATIBLE))
        self.assertFalse(status.updatable)                           # built for builds 100-120, the game is 150
        [status] = update_status([mine], manager, game_build=110)
        self.assertTrue(status.updatable)
        manager.set_enabled(rid, False)
        self.assertEqual(update_status([mine], manager)[0].state, 'unavailable')
        manager.set_enabled(rid, True)
        manager.remove(rid)
        self.assertEqual(update_status([mine], manager)[0].state, 'unavailable')


class Failures(GameCase):
    """Whatever goes wrong, the game folder ends exactly as it started."""

    def setUp(self):
        super().setUp()
        self.mod = self.offer('crimson', [{'version': '1.0.0', 'data': SKIN}, {'version': '2.0.0', 'data': SKIN2}])

    def assert_untouched(self, snapshot):
        self.assertEqual(self.game_snapshot(), snapshot)
        self.assertFalse(self.installer.journal_path.exists())

    def test_a_failed_verification_rolls_back_a_first_install_completely(self):
        plan = self.installer.prepare(view(), self.mod, self.mod.find('1.0.0'))
        before = self.game_snapshot()
        with patch.object(Installer, '_verify', side_effect=InstallError('verify', 'simulated')):
            with self.assertRaises(InstallError):
                self.installer.commit(plan, acknowledged=True)
        after = self.game_snapshot()
        self.assertNotIn('citadel/addons/pak01_dir.vpk'.replace('/', os.sep), after)
        self.assertEqual({k: v for k, v in after.items() if 'addons' in k or 'mods' in k}, {})
        self.assertEqual(self.installer.installed(), [])
        self.assertFalse(self.installer.journal_path.exists())
        self.assertEqual(self.new_installer().installed(), [])
        self.assertEqual(before.keys() - after.keys(), set())

    def test_a_failed_update_restores_the_previous_version_byte_for_byte(self):
        self.install(self.mod, '1.0.0')
        plan = self.installer.prepare(view(), self.mod, self.mod.find('2.0.0'))
        snapshot = {k: v for k, v in self.game_snapshot().items() if 'staging' not in k}
        with patch.object(Installer, '_record_install', side_effect=OSError('disk full while recording')):
            with self.assertRaises(InstallError):
                self.installer.commit(plan, acknowledged=True)
        self.assertEqual((self.addons / 'pak01_dir.vpk').read_bytes(), SKIN)
        self.assertEqual({k: v for k, v in self.game_snapshot().items() if 'staging' not in k}, snapshot)
        self.assertEqual(self.installer.installed()[0].version, '1.0.0')
        self.assertFalse(self.installer.journal_path.exists())

    def test_a_failure_in_the_middle_of_the_moves_is_undone(self):
        self.install(self.mod, '1.0.0')
        plan = self.installer.prepare(view(), self.mod, self.mod.find('2.0.0'))
        real = os.replace
        failed = []

        def flaky(src, dst):
            if not failed and 'addons' in str(dst) and 'pak01' in str(dst):     # once: placing the new file, after the old one was backed up
                failed.append(dst)
                raise OSError('simulated I/O error')
            return real(src, dst)
        with patch('deadlock_fps.installer.engine.os.replace', side_effect=flaky):
            with self.assertRaises(OSError):
                self.installer.commit(plan, acknowledged=True)
        self.assertEqual((self.addons / 'pak01_dir.vpk').read_bytes(), SKIN)
        self.assertFalse(self.installer.journal_path.exists())
        self.assertEqual(self.installer.installed()[0].version, '1.0.0')

    def test_when_even_the_rollback_fails_the_journal_survives_and_recovery_finishes_the_job(self):
        self.install(self.mod, '1.0.0')
        plan = self.installer.prepare(view(), self.mod, self.mod.find('2.0.0'))
        real = os.replace

        def always_failing_into_addons(src, dst):
            if 'addons' in str(dst):
                raise OSError('the disk is gone')
            return real(src, dst)
        with patch('deadlock_fps.installer.engine.os.replace', side_effect=always_failing_into_addons):
            with self.assertRaises(InstallError) as caught:
                self.installer.commit(plan, acknowledged=True)
        self.assertEqual(caught.exception.code, 'journal')
        self.assertTrue(self.installer.journal_path.exists())
        self.assertFalse((self.addons / 'pak01_dir.vpk').exists())              # the old file is in the backup, not lost
        notes = self.new_installer().recover()                                 # the disk is back
        self.assertTrue(notes)
        self.assertEqual((self.addons / 'pak01_dir.vpk').read_bytes(), SKIN)
        self.assertFalse(self.installer.journal_path.exists())

    def test_a_file_that_changes_after_installation_fails_verification_and_is_rolled_back(self):
        plan = self.installer.prepare(view(), self.mod, self.mod.find('1.0.0'))
        real = os.replace

        def corrupting(src, dst):
            real(src, dst)
            if 'addons' in str(dst):
                Path(dst).write_bytes(b'corrupted by a failing disk')
        with patch('deadlock_fps.installer.engine.os.replace', side_effect=corrupting):
            with self.assertRaises(InstallError) as caught:
                self.installer.commit(plan, acknowledged=True)
        self.assertEqual(caught.exception.code, 'verify')
        self.assertEqual(self.addon_names(), [])
        self.assertEqual(self.installer.installed(), [])

    def test_the_game_must_be_closed(self):
        plan = self.installer.prepare(view(), self.mod, self.mod.find('1.0.0'))
        snapshot = self.game_snapshot()
        self.running = True
        with self.assertRaises(InstallError) as caught:
            self.installer.commit(plan, acknowledged=True)
        self.assertEqual(caught.exception.code, 'game-running')
        self.assertEqual(self.game_snapshot(), snapshot)
        self.running = False
        self.installer.commit(plan, acknowledged=True)
        self.running = True
        for action in (lambda: self.installer.uninstall('https:mods.example.org/index.json', 'crimson'),
                       lambda: self.installer.set_enabled('https:mods.example.org/index.json', 'crimson', False),
                       self.installer.repair):
            with self.assertRaises(InstallError) as caught:
                action()
            self.assertEqual(caught.exception.code, 'game-running')

    def test_staged_files_changed_after_the_preview_are_refused(self):
        plan = self.installer.prepare(view(), self.mod, self.mod.find('1.0.0'))
        Path(plan.files[0].staged).write_bytes(HUD)
        with self.assertRaises(InstallError) as caught:
            self.installer.commit(plan, acknowledged=True)
        self.assertEqual(caught.exception.code, 'stale-plan')
        self.assertFalse(self.addons.exists())

    def test_a_same_size_change_to_a_staged_file_is_caught_by_its_hash(self):
        plan = self.installer.prepare(view(), self.mod, self.mod.find('1.0.0'))
        staged = Path(plan.files[0].staged)
        data = bytearray(staged.read_bytes())
        data[-1] ^= 0xFF                                                       # same length, one byte different
        staged.write_bytes(bytes(data))
        with self.assertRaises(InstallError) as caught:
            self.installer.commit(plan, acknowledged=True)
        self.assertEqual(caught.exception.code, 'stale-plan')
        self.assertFalse(self.addons.exists())

    def test_a_move_never_overwrites_its_destination(self):
        self.addons.mkdir(parents=True)
        source, target = self.addons / 'src.bin', self.addons / 'dst.bin'
        source.write_bytes(b'new')
        target.write_bytes(b'precious')
        with self.assertRaises(InstallError) as caught:
            self.installer._run_moves('tx-guard', [(source, target)], 'test')
        self.assertEqual(caught.exception.code, 'stale-plan')
        self.assertEqual((source.read_bytes(), target.read_bytes()), (b'new', b'precious'))
        self.assertFalse(self.installer.journal_path.exists())

    def test_a_foreign_file_that_appears_in_the_target_slot_is_never_overwritten(self):
        plan = self.installer.prepare(view(), self.mod, self.mod.find('1.0.0'))
        self.addons.mkdir(parents=True)
        (self.addons / 'pak01_dir.vpk').write_bytes(b'someone else installed this meanwhile')
        with self.assertRaises(InstallError) as caught:
            self.installer.commit(plan, acknowledged=True)
        self.assertEqual(caught.exception.code, 'stale-plan')
        self.assertEqual((self.addons / 'pak01_dir.vpk').read_bytes(), b'someone else installed this meanwhile')
        self.assertEqual(self.installer.installed(), [])

    def test_a_malformed_gameinfo_stops_before_any_mod_file_is_placed(self):
        plan = self.installer.prepare(view(), self.mod, self.mod.find('1.0.0'))
        self.gi.write_text('"GameInfo" { broken', encoding='utf-8')
        with self.assertRaises(InstallError) as caught:
            self.installer.commit(plan, acknowledged=True)
        self.assertEqual(caught.exception.code, 'gameinfo')
        self.assertFalse(self.addons.exists())
        self.assertEqual(self.gi.read_text(encoding='utf-8'), '"GameInfo" { broken')


class Recovery(GameCase):
    def test_an_interrupted_install_is_rolled_back_on_the_next_start(self):
        old = self.offer('crimson', [{'version': '1.0.0', 'data': SKIN}, {'version': '2.0.0', 'data': SKIN2}])
        self.install(old, '1.0.0')
        plan = self.installer.prepare(view(), old, old.find('2.0.0'))
        # Simulate a power cut: perform the journaled moves, then "die" before anything is recorded or the journal cleared.
        backup = self.installer.store_dir / 'backups' / plan.tx
        self.installer._run_moves(plan.tx, [(self.addons / 'pak01_dir.vpk', backup / 'pak01_dir.vpk'), (plan.files[0].staged, self.addons / 'pak01_dir.vpk')], 'update Crimson 2.0.0')
        self.assertEqual((self.addons / 'pak01_dir.vpk').read_bytes(), SKIN2)
        fresh = self.new_installer()
        with self.assertRaises(InstallError) as caught:
            fresh.prepare(view(), old, old.find('2.0.0'))
        self.assertEqual(caught.exception.code, 'journal')
        notes = fresh.recover()
        self.assertTrue(any('rolled back' in n for n in notes))
        self.assertEqual((self.addons / 'pak01_dir.vpk').read_bytes(), SKIN)
        self.assertFalse(fresh.journal_path.exists())
        self.assertEqual(fresh.installed()[0].version, '1.0.0')
        self.assertEqual(fresh.recover(), [])

    def test_leftover_downloads_and_staging_are_cleaned_on_start(self):
        leftover = self.installer.store_dir / 'downloads'
        leftover.mkdir(parents=True)
        (leftover / 'x.part').write_bytes(b'half')
        stage = self.installer.store_dir / 'staging' / 'old'
        stage.mkdir(parents=True)
        (stage / 'pak01_dir.vpk').write_bytes(b'x')
        self.new_installer().recover()
        self.assertFalse(leftover.exists() or stage.exists())

    def test_a_damaged_record_file_is_kept_not_overwritten(self):
        self.install(self.offer('crimson', [{'version': '1.0.0', 'data': SKIN}]))
        path = self.installer.records.path
        path.write_text('{ not json', encoding='utf-8')
        fresh = self.new_installer()
        self.assertEqual(fresh.installed(), [])
        self.assertTrue(fresh.records.problem)
        self.install_with(fresh, self.offer('hud', [{'version': '1.0.0', 'data': HUD}]))
        saved = list(path.parent.glob('installed.damaged-*.json'))
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0].read_text(encoding='utf-8'), '{ not json')
        self.assertEqual([m.name for m in self.new_installer().installed()], ['Hud'])

    def install_with(self, installer, mod):
        installer.commit(installer.prepare(view(), mod, mod.latest()), acknowledged=True)


class Lifecycle(GameCase):
    def setUp(self):
        super().setUp()
        self.mod = self.offer('crimson', [{'version': '1.0.0', 'data': SKIN}])
        self.record = self.install(self.mod)
        self.key = self.record.key

    def test_uninstall_moves_files_to_the_recovery_folder_and_forgets_the_mod(self):
        trash = self.installer.uninstall(*self.key)
        self.assertEqual(self.addon_names(), [])
        self.assertEqual((trash / 'pak01_dir.vpk').read_bytes(), SKIN)
        self.assertEqual(self.installer.installed(), [])
        self.assertEqual([h['action'] for h in self.installer.history()][:1], ['uninstall'])
        self.assertTrue(self.installer.addons.parent.exists() and kv.has_addons_path(self.gi.read_text(encoding='utf-8')))
        with self.assertRaises(InstallError):
            self.installer.uninstall(*self.key)

    def test_only_the_last_few_uninstalled_copies_are_kept(self):
        for n in range(8):
            mod = self.offer('m%d' % n, [{'version': '1.0.0', 'data': make_vpk(['f/%d.txt' % n])}])
            self.installer.uninstall(*self.install(mod).key)
        self.assertEqual(len(list((self.installer.store_dir / 'trash').iterdir())), 5)

    def test_disable_removes_the_file_from_the_load_path_and_enable_brings_it_back(self):
        disabled = self.installer.set_enabled(*self.key, False)
        self.assertFalse(disabled.enabled)
        self.assertEqual(self.addon_names(), [])
        self.assertEqual(self.installer.unmanaged(), [])
        self.assertTrue(self.installer.set_enabled(*self.key, False).enabled is False)           # idempotent
        enabled = self.installer.set_enabled(*self.key, True)
        self.assertEqual((enabled.enabled, (self.addons / 'pak01_dir.vpk').read_bytes()), (True, SKIN))
        self.assertEqual([h['action'] for h in enabled.history], ['install', 'disable', 'enable'])

    def test_a_disabled_mods_slot_stays_reserved_and_is_reallocated_if_someone_takes_it(self):
        self.installer.set_enabled(*self.key, False)
        other = self.install(self.offer('hud', [{'version': '1.0.0', 'data': HUD}]))
        self.assertEqual(other.files[0].name, 'pak02_dir.vpk')                                    # pak01 is reserved for crimson
        (self.addons / 'pak01_dir.vpk').write_bytes(make_vpk(['intruder/file.txt']))              # but a foreign file takes it anyway
        back = self.installer.set_enabled(*self.key, True)
        self.assertEqual(back.files[0].name, 'pak03_dir.vpk')
        self.assertEqual((self.addons / 'pak03_dir.vpk').read_bytes(), SKIN)
        self.assertEqual((self.addons / 'pak01_dir.vpk').read_bytes(), make_vpk(['intruder/file.txt']))

    def test_updating_a_disabled_mod_installs_the_new_version_enabled(self):
        newer = self.offer('crimson', [{'version': '1.0.0', 'data': SKIN}, {'version': '1.1.0', 'data': SKIN2}])
        self.installer.set_enabled(*self.key, False)
        updated = self.install(newer, '1.1.0')
        self.assertEqual((updated.enabled, updated.version), (True, '1.1.0'))
        self.assertEqual((self.addons / 'pak01_dir.vpk').read_bytes(), SKIN2)
        self.assertEqual(updated.previous[-1].version, '1.0.0')

    def test_reinstalling_the_same_version_is_allowed_and_flagged(self):
        plan = self.installer.prepare(view(), self.mod, self.mod.latest())
        self.assertTrue(any('already installed' in w for w in plan.warnings))
        self.installer.commit(plan, acknowledged=True)
        self.assertEqual(len(self.installer.installed()), 1)


class Health(GameCase):
    def setUp(self):
        super().setUp()
        self.a = self.install(self.offer('crimson', [{'version': '1.0.0', 'data': SKIN}]))

    def codes(self):
        return sorted(i.code for i in self.installer.analyze())

    def test_a_healthy_install_has_no_problems(self):
        self.assertEqual(self.codes(), [])

    def test_missing_and_modified_files_are_reported(self):
        (self.addons / 'pak01_dir.vpk').write_bytes(SKIN2)
        self.assertEqual(self.codes(), ['modified'])
        (self.addons / 'pak01_dir.vpk').unlink()
        self.assertEqual(self.codes(), ['missing'])

    def test_a_steam_reset_of_gameinfo_is_detected_and_repaired(self):
        self.gi.write_bytes(self.original_gi)
        issues = self.installer.analyze()
        self.assertEqual([i.code for i in issues], ['inactive'])
        self.assertEqual(issues[0].severity, 'error')
        self.installer.repair()
        self.assertEqual(self.codes(), [])
        self.assertTrue(kv.has_addons_path(self.gi.read_text(encoding='utf-8')))

    def test_overlaps_between_installed_and_unmanaged_mods_are_listed_with_the_winner(self):
        (self.addons / 'pak05_dir.vpk').write_bytes(make_vpk(['materials/shared/skin.vmat'], b'other'))
        issues = self.installer.analyze()
        overlap = [i for i in issues if i.code == 'overlap'][0]
        self.assertIn('Crimson', overlap.subject)
        self.assertIn('pak01_dir.vpk', overlap.detail)
        self.assertIn('wins', overlap.detail)
        self.assertTrue(any(i.code == 'unmanaged' for i in issues))

    def test_unreadable_unmanaged_files_are_warned_about_not_crashed_on(self):
        (self.addons / 'pak07_dir.vpk').write_bytes(b'not a vpk')
        self.assertIn('unreadable', self.codes())


if __name__ == '__main__':
    unittest.main()
