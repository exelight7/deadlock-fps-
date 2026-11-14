"""RepositoryManager: lifecycle, persistence, status, trust, import/export and cross-repository search."""
import json
import tempfile
import unittest
from pathlib import Path

from deadlock_fps.repos import RepositoryManager, RepositoryStore, TrustRegistry, RepoError, Compat, Trust
from deadlock_fps.repos.providers import default_registry, Provider
from deadlock_fps.repos.providers.base import SyncResult
from deadlock_fps.repos.search import search
from repo_fixtures import FakeTransport, ok, status, index, mod, version, clone, gh_repo, gh_asset, gh_release

IDX = 'https://mods.example.org/index.json'
OTHER = 'https://other.example.net/deadlock-repo.json'
GH = 'https://api.github.com/repos/mira/skins'


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        self.now += 10
        return self.now


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.transport = FakeTransport({IDX: ok(index(), ETag='"e1"')})
        self.clock = Clock()
        self.manager = self.make()

    def tearDown(self):
        self.temp.cleanup()

    def make(self, trust=None):
        return RepositoryManager(RepositoryStore(self.folder), self.transport, trust=trust or TrustRegistry({}), clock=self.clock)


class Lifecycle(Base):
    def test_add_does_not_fetch_and_starts_unverified_and_new(self):
        view = self.manager.add(IDX)
        self.assertEqual(self.transport.calls, [])
        self.assertEqual(view.state.status, 'new')
        self.assertEqual(view.trust, Trust.UNVERIFIED)
        self.assertTrue(view.source.enabled)

    def test_refresh_loads_catalogue_and_metadata(self):
        rid = self.manager.add(IDX).source.id
        view = self.manager.refresh(rid)
        self.assertEqual(view.state.status, 'ok')
        self.assertEqual(view.compat, Compat.NATIVE)
        self.assertEqual(view.state.mod_count, 1)
        self.assertEqual(view.name, 'Example Mods')
        self.assertGreater(view.state.last_sync, 0)
        self.assertEqual(view.state.etag, '"e1"')
        self.assertEqual(view.info.maintainer, 'Mira')
        self.assertEqual(self.manager.index(rid).mods[0].id, 'crimson-skin')

    def test_duplicate_detection_uses_canonical_identity(self):
        self.manager.add('https://github.com/Mira/Skins')
        for again in ['https://github.com/mira/skins.git', 'https://github.com/MIRA/skins/releases']:
            with self.assertRaises(RepoError) as caught:
                self.manager.add(again)
            self.assertEqual(caught.exception.code, 'duplicate')

    def test_bad_addresses_are_refused_before_anything_is_stored(self):
        for bad in ['http://example.org/x', 'https://127.0.0.1/x', 'not a url', '']:
            with self.assertRaises(RepoError):
                self.manager.add(bad)
        self.assertEqual(self.manager.list(), [])
        self.assertFalse((self.folder / 'sources.json').exists())

    def test_enable_disable_rename_remove(self):
        rid = self.manager.add(IDX).source.id
        self.manager.refresh(rid)
        self.assertEqual(len(self.manager.search()), 1)
        self.assertFalse(self.manager.set_enabled(rid, False).source.enabled)
        self.assertEqual(self.manager.search(), [])
        self.manager.set_enabled(rid, True)
        self.assertEqual(self.manager.rename(rid, '  My mods  ').name, 'My mods')
        uid = self.manager.get(rid).source.uid
        self.assertTrue((self.folder / 'index' / (uid + '.json')).exists())
        self.manager.remove(rid)
        self.assertEqual(self.manager.list(), [])
        self.assertFalse((self.folder / 'index' / (uid + '.json')).exists())
        self.assertFalse((self.folder / 'state' / (uid + '.json')).exists())
        with self.assertRaises(RepoError):
            self.manager.get(rid)

    def test_everything_survives_a_restart(self):
        rid = self.manager.add(IDX, name='Mine').source.id
        self.manager.refresh(rid)
        self.manager.set_enabled(rid, False)
        again = self.make()
        view = again.get(rid)
        self.assertEqual((view.name, view.source.enabled, view.state.status, view.state.mod_count), ('Mine', False, 'ok', 1))
        again.set_enabled(rid, True)
        self.assertEqual(again.search('crimson')[0].mod.id, 'crimson-skin')

    def test_damaged_files_are_survivable(self):
        rid = self.manager.add(IDX).source.id
        self.manager.refresh(rid)
        uid = self.manager.get(rid).source.uid
        (self.folder / 'index' / (uid + '.json')).write_bytes(b'{broken')
        (self.folder / 'state' / (uid + '.json')).write_text('[]')
        again = self.make()
        view = again.get(rid)
        self.assertEqual(view.state.status, 'new')                  # state lost, repository still listed
        self.assertTrue(again.refresh(rid).state.status == 'ok')    # and a refresh repairs it
        (self.folder / 'sources.json').write_text('not json')
        broken = self.make()
        self.assertEqual(broken.list(), [])
        self.assertTrue(broken.store.problems)


class Sync(Base):
    def test_unreachable_server_is_a_status_and_keeps_the_last_good_catalogue(self):
        rid = self.manager.add(IDX).source.id
        self.manager.refresh(rid)
        self.transport.routes[IDX] = RepoError('network', 'cannot reach mods.example.org: timed out')
        view = self.manager.refresh(rid)
        self.assertEqual(view.state.status, 'error')
        self.assertEqual(view.state.error_code, 'network')
        self.assertIn('timed out', view.state.error_message)
        self.assertEqual(view.state.mod_count, 1)
        self.assertGreater(view.state.last_sync, 0)                 # the last success is still known
        self.assertGreater(view.state.last_attempt, view.state.last_sync)
        self.assertEqual(len(self.manager.search('crimson')), 1)    # stale but usable
        self.transport.routes[IDX] = ok(index())
        self.assertEqual(self.manager.refresh(rid).state.status, 'ok')
        self.assertEqual(self.manager.get(rid).state.error_code, '')

    def test_conditional_refresh_uses_etag_and_keeps_data(self):
        rid = self.manager.add(IDX).source.id
        self.manager.refresh(rid)
        self.transport.routes[IDX] = status(304)
        view = self.manager.refresh(rid)
        self.assertEqual(self.transport.calls[-1][1].get('If-None-Match'), '"e1"')
        self.assertEqual((view.state.status, view.state.mod_count), ('ok', 1))

    def test_etag_is_not_sent_when_the_cache_is_gone(self):
        rid = self.manager.add(IDX).source.id
        self.manager.refresh(rid)
        uid = self.manager.get(rid).source.uid
        (self.folder / 'index' / (uid + '.json')).unlink()
        again = self.make()
        again.refresh(rid)
        self.assertNotIn('If-None-Match', self.transport.calls[-1][1])
        self.assertEqual(len(again.search()), 1)

    def test_a_repository_that_stops_being_compatible_loses_its_catalogue(self):
        rid = self.manager.add(IDX).source.id
        self.manager.refresh(rid)
        self.transport.routes[IDX] = ok(index(schema_version='3.0'))
        view = self.manager.refresh(rid)
        self.assertEqual((view.state.status, view.compat), ('unsupported', Compat.UNSUPPORTED))
        self.assertIn('3.0', view.state.reason)
        self.assertEqual(self.manager.search(), [])

    def test_unsupported_repositories_explain_themselves_and_are_not_searched(self):
        rid = self.manager.add('https://github.com/mira/skins').source.id
        rel = [gh_release('v1', [gh_asset('mira', 'skins', 'v1', 'tool.zip')])]
        self.transport.routes.update({GH: ok(gh_repo()), GH + '/releases?per_page=30': ok(rel)})
        view = self.manager.refresh(rid)
        self.assertEqual(view.compat, Compat.MANUAL)
        self.assertIn('ZIP', view.state.reason)
        self.assertEqual(self.manager.search(), [])

    def test_a_crashing_provider_cannot_take_the_others_down(self):
        class Broken(Provider):
            kind = 'broken'

            def identify(self, url, hint=''):
                from deadlock_fps.repos.providers.base import Identity
                return Identity('broken:' + url, 'broken', url) if 'broken.example.org' in url else None

            def sync(self, source, transport, etag=''):
                raise ZeroDivisionError('boom')
        registry = default_registry()
        registry.register(Broken(), first=True)
        manager = RepositoryManager(RepositoryStore(self.folder), self.transport, registry=registry, trust=TrustRegistry({}), clock=self.clock)
        bad = manager.add('https://broken.example.org/x').source.id
        good = manager.add(IDX).source.id
        views = {v.source.id: v for v in manager.refresh_all()}
        self.assertEqual(views[bad].state.error_code, 'internal')
        self.assertEqual(views[good].state.status, 'ok')

    def test_refresh_all_skips_disabled_and_reports_progress(self):
        a = self.manager.add(IDX).source.id
        self.transport.routes[OTHER] = ok(index(mod('other-mod'), name='Other', ident='other'))
        b = self.manager.add(OTHER).source.id
        self.manager.set_enabled(b, False)
        steps = []
        views = self.manager.refresh_all(progress=lambda done, total, view: steps.append((done, total)))
        self.assertEqual([v.source.id for v in views], [a])
        self.assertEqual(steps, [(1, 1)])
        self.assertEqual(self.manager.get(b).state.status, 'new')
        self.assertEqual(len(self.manager.refresh_all(only_enabled=False)), 2)

    def test_translated_catalogue_is_cached_and_reloaded_as_derived(self):
        rid = self.manager.add('https://github.com/mira/skins').source.id
        rel = [gh_release('v1.0.0', [gh_asset('mira', 'skins', 'v1.0.0', 'red-v1.0.0.vpk')])]
        self.transport.routes.update({GH: ok(gh_repo()), GH + '/releases?per_page=30': ok(rel)})
        self.assertEqual(self.manager.refresh(rid).compat, Compat.TRANSLATED)
        again = self.make()
        mods = again.index(rid).mods
        self.assertTrue(mods[0].derived)
        self.assertEqual(again.search('red')[0].repository.compat, Compat.TRANSLATED)


class Trusting(Base):
    def test_label_comes_only_from_the_registry(self):
        self.transport.routes[IDX] = ok(clone(index(trust='OFFICIAL')))
        rid = self.manager.add(IDX).source.id
        self.assertEqual(self.manager.refresh(rid).trust, Trust.UNVERIFIED)
        registry = TrustRegistry({'https:mods.example.org/index.json': (Trust.VERIFIED, 'Reviewed 2026-11')})
        verified = self.make(registry).get(rid)
        self.assertEqual((verified.trust, verified.trust_note), (Trust.VERIFIED, 'Reviewed 2026-11'))

    def test_hosting_provider_confers_nothing(self):
        view = self.manager.add('https://github.com/anyone/anything')
        self.assertEqual(view.trust, Trust.UNVERIFIED)
        self.assertIn('Nobody has reviewed', view.trust_note)

    def test_fork_or_lookalike_does_not_inherit_official(self):
        registry = TrustRegistry.load()
        manager = RepositoryManager(RepositoryStore(self.folder), self.transport, trust=registry, clock=self.clock)
        self.assertEqual(manager.add('https://github.com/exelight7/deadlock-fps-').trust, Trust.OFFICIAL)
        self.assertEqual(manager.add('https://github.com/exelight7/deadlock-fps').trust, Trust.UNVERIFIED)
        self.assertEqual(manager.add('https://github.com/someone-else/deadlock-fps-').trust, Trust.UNVERIFIED)

    def test_registry_failure_is_safe(self):
        folder = Path(tempfile.mkdtemp())
        try:
            self.assertIn('not found', TrustRegistry.load(folder / 'missing.json').problem)
            (folder / 'bad.json').write_text('{"schema": "x"}')
            self.assertEqual(len(TrustRegistry.load(folder / 'bad.json')), 0)
            (folder / 'sneaky.json').write_text(json.dumps({'schema': 'deadlock-trust-registry', 'version': 1, 'entries': [
                {'repository': 'github:a/b', 'label': 'GOLD'}]}))
            self.assertEqual(len(TrustRegistry.load(folder / 'sneaky.json')), 0)
            self.assertEqual(TrustRegistry.load(folder / 'bad.json').label_for('github:a/b')[0], Trust.UNVERIFIED)
        finally:
            import shutil
            shutil.rmtree(folder, ignore_errors=True)

    def test_shipped_registry_loads(self):
        registry = TrustRegistry.load()
        self.assertEqual(registry.problem, '')
        self.assertEqual(registry.label_for('github:exelight7/deadlock-fps-')[0], Trust.OFFICIAL)


class ConfigImportExport(Base):
    def test_importing_an_index_file_creates_a_local_repository(self):
        result = self.manager.import_config(json.dumps(index(name='Hand Mapped', ident='hand-mapped')).encode())
        self.assertEqual(result.kind, 'index')
        view = result.added[0]
        self.assertEqual((view.source.kind, view.source.id, view.compat, view.state.status), ('local', 'local:hand-mapped', Compat.NATIVE, 'ok'))
        self.assertEqual(self.manager.search('crimson')[0].repository.source.id, 'local:hand-mapped')
        self.assertEqual(self.manager.refresh('local:hand-mapped').state.status, 'ok')       # nothing to fetch
        self.assertEqual(self.transport.calls, [])
        with self.assertRaises(RepoError) as caught:
            self.manager.import_config(json.dumps(index(ident='hand-mapped')).encode())
        self.assertEqual(caught.exception.code, 'duplicate')
        updated = index(mod('another'), ident='hand-mapped')
        self.manager.import_config(json.dumps(updated).encode(), replace_existing=True)
        self.assertEqual([h.mod.id for h in self.manager.search()], ['another'])
        self.assertTrue(self.make().get('local:hand-mapped').state.status == 'ok')

    def test_local_import_can_never_claim_a_remote_identity_or_trust(self):
        registry = TrustRegistry({'github:exelight7/deadlock-fps-': (Trust.OFFICIAL, '')})
        manager = self.make(registry)
        view = manager.import_config(json.dumps(index(ident='github:exelight7/deadlock-fps-')).encode()).added[0]
        self.assertTrue(view.source.id.startswith('local:'))
        self.assertEqual(view.trust, Trust.UNVERIFIED)

    def test_invalid_files_are_rejected_cleanly(self):
        for data in [b'garbage', b'[]', json.dumps({'schema': 'other'}).encode(), json.dumps(index(schema_version='2.0')).encode()]:
            with self.assertRaises(RepoError):
                self.manager.import_config(data)
        self.assertEqual(self.manager.list(), [])

    def test_repository_lists_round_trip_and_report_what_was_skipped(self):
        self.manager.add('https://github.com/mira/skins', name='Skins')
        self.manager.add(IDX)
        exported = self.manager.export_config()
        fresh_folder = tempfile.TemporaryDirectory()
        try:
            other = RepositoryManager(RepositoryStore(fresh_folder.name), self.transport, trust=TrustRegistry({}), clock=self.clock)
            result = other.import_config(exported)
            self.assertEqual((result.kind, len(result.added), result.skipped), ('list', 2, []))
            again = other.import_config(exported)
            self.assertEqual(len(again.added), 0)
            self.assertEqual({reason for _, reason in again.skipped}, {'this repository is already in the list'})
            self.assertEqual({v.source.id for v in other.list()}, {'github:mira/skins', 'https:mods.example.org/index.json'})
            self.assertEqual(self.transport.calls, [])                                    # importing a list never fetches
        finally:
            fresh_folder.cleanup()

    def test_local_repositories_are_not_exported(self):
        self.manager.import_config(json.dumps(index()).encode())
        self.assertEqual(json.loads(self.manager.export_config())['repositories'], [])


class Searching(Base):
    def setUp(self):
        super().setUp()
        self.transport.routes[IDX] = ok(index(
            mod('crimson-skin', name='Crimson Skin', author='Mira', categories=['skins'], versions=[version('1.0.0', package={'format': 'vpk', 'url': 'https://f.example.org/a.vpk', 'size': 900})]),
            mod('hud-tweak', name='HUD Tweak', summary='Cleaner crimson interface', author='Ian', categories=['hud'], published='2026-06-01',
                versions=[version('2.0.0', published='2026-06-01', package={'format': 'vpk', 'url': 'https://f.example.org/h.vpk', 'size': 100})]),
            mod('night-map', name='Night Map', author='Zed', categories=['maps'], versions=[version('1.0.0-beta.1')])))
        self.transport.routes[OTHER] = ok(index(mod('crimson-skin', name='Crimson Skin (fork)', author='Other', categories=['skins']), name='Other', ident='other'))
        for url in (IDX, OTHER):
            self.manager.refresh(self.manager.add(url).source.id)

    def test_searches_across_repositories_with_weighted_relevance(self):
        hits = self.manager.search('crimson')
        self.assertEqual([h.mod.name for h in hits], ['Crimson Skin', 'Crimson Skin (fork)', 'HUD Tweak'])    # name beats summary
        self.assertEqual({h.repository.name for h in hits}, {'Example Mods', 'Other'})
        self.assertEqual(self.manager.search('crimson mira')[0].mod.author, 'Mira')                         # every word must match
        self.assertEqual(self.manager.search('crimson nonexistent'), [])
        self.assertEqual(len(self.manager.search('')), 4)

    def test_filters_and_sorting(self):
        self.assertEqual([h.mod.id for h in self.manager.search(category='hud')], ['hud-tweak'])
        self.assertEqual(len(self.manager.search(category='SKINS')), 2)
        only_other = self.manager.search(repository='https:other.example.net/deadlock-repo.json')
        self.assertEqual([h.repository.name for h in only_other], ['Other'])
        self.assertEqual([h.mod.id for h in self.manager.search(sort='name')][:2], ['crimson-skin', 'crimson-skin'])
        self.assertEqual(self.manager.search(sort='updated')[0].mod.id, 'hud-tweak')
        self.assertEqual(self.manager.search(sort='size')[0].mod.id, 'crimson-skin')
        self.assertEqual(self.manager.search(trust=Trust.OFFICIAL), [])
        ids = [h.mod.id for h in self.manager.search(installable_only=True)]
        self.assertNotIn('night-map', ids)                                                                  # only a pre-release exists

    def test_categories_are_counted_over_enabled_repositories(self):
        self.assertEqual(self.manager.categories()['skins'], 2)
        self.manager.set_enabled('https:other.example.net/deadlock-repo.json', False)
        self.assertEqual(self.manager.categories()['skins'], 1)

    def test_find_mod_returns_the_exact_repository_entry(self):
        view, found = self.manager.find_mod('https:other.example.net/deadlock-repo.json', 'crimson-skin')
        self.assertEqual((view.name, found.name), ('Other', 'Crimson Skin (fork)'))
        self.assertIsNone(self.manager.find_mod('https:mods.example.org/index.json', 'missing'))


if __name__ == '__main__':
    unittest.main()
