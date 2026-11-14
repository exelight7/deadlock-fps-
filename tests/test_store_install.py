"""Installing from the Mod Store: the adapter, discovery inside zip packages, MD5 and host checks, and the whole path through the real engine."""
import hashlib
import io
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from deadlock_fps.graph import Graph, build_catalogue
from deadlock_fps.installer import InstallError, update_status
from deadlock_fps.installer import archive
from deadlock_fps.installer.records import InstalledMod
from deadlock_fps.repos import RepositoryManager, RepositoryStore
from deadlock_fps.repos.model import Trust
from deadlock_fps.repos.transport import DownloadResult
from deadlock_fps.store.gamebanana import parse_profile
from deadlock_fps.store.install import STORE_ID, build, file_format, mod_id_of, store_repository, version_text
from installer_fixtures import GameCase, ServingTransport, make_vpk, make_zip
from repo_fixtures import FakeTransport
from store_fixtures import profile_document, file_entry, BASE_TIME

URL = 'https://gamebanana.com/dl/%d'


def md5(data):
    return hashlib.md5(data).hexdigest()


class Adapter(unittest.TestCase):
    def profile(self, **kwargs):
        return parse_profile(profile_document(**kwargs))

    def test_builds_the_three_things_the_installer_wants(self):
        profile = self.profile()
        repository, mod, version = build(profile, profile.files[0])
        self.assertEqual((repository.source.id, repository.name, repository.trust), (STORE_ID, 'GameBanana', Trust.UNVERIFIED))
        self.assertEqual((mod.id, mod.name, mod.author, mod.license, mod.derived), ('gb-711387', 'Pink Drifter', 'Mira', 'CC BY-NC-ND 4.0', False))
        self.assertEqual((mod.homepage, mod.source_url), ('https://gamebanana.com/mods/711387',) * 2)
        self.assertEqual(mod.categories, ('Skins', 'Drifter'))
        package = version.package
        self.assertEqual((package.format, package.url, package.size, package.sha256, package.md5, package.hosts),
                         ('zip', URL % 1801337, 7493240, None, '03f6e9f9e25675d14521c84e010a33c2', ('gamebanana.com',)))
        self.assertTrue(version.install.discover and version.installable)

    def test_the_store_repository_is_always_unverified_and_carries_the_store_prefix(self):
        self.assertEqual(store_repository().trust, Trust.UNVERIFIED)
        self.assertTrue(STORE_ID.startswith('store:'))
        self.assertEqual(mod_id_of(42), 'gb-42')

    def test_file_kinds(self):
        def kind(name):
            return file_format(self.profile(files=[file_entry(name=name)]).files[0])
        self.assertEqual([kind(n) for n in ('a.zip', 'A.ZIP', 'x.vpk', 'a.rar', 'a.7z', 'a.exe', 'noext')],
                         [('zip', ''), ('zip', ''), ('vpk', ''), ('', 'rar'), ('', '7z'), ('', 'other'), ('', 'other')])

    def test_unsupported_files_are_not_installable_and_say_why(self):
        for name in ('mod.rar', 'mod.7z', 'tool.exe'):
            profile = self.profile(files=[file_entry(name=name)])
            _, _, version = build(profile, profile.files[0])
            self.assertFalse(version.installable, name)
            self.assertIn('.zip', version.unsupported_reason)

    def test_a_bare_vpk_is_installed_as_it_is(self):
        profile = self.profile(files=[file_entry(name='pak01_dir.vpk')])
        _, _, version = build(profile, profile.files[0])
        self.assertEqual((version.package.format, version.install.discover, version.installable), ('vpk', False, True))

    def test_a_file_of_another_mod_is_refused(self):
        other = self.profile(files=[file_entry(ident=5)])
        mine = self.profile()
        with self.assertRaises(ValueError):
            build(mine, other.files[0])

    def test_version_text(self):
        def text(version, added=BASE_TIME):
            document = profile_document(files=[file_entry(ident=77)])
            document['_sVersion'] = version
            document['_aFiles'][0]['_tsDateAdded'] = added
            profile = parse_profile(document)
            return version_text(profile.submission, profile.files[0])
        self.assertEqual([text('1.2'), text('v2.0.1'), text('V 3'), text('1.0.0-beta.1')], ['1.2', '2.0.1', '3', '1.0.0-beta.1'])
        self.assertEqual(text('Beta 2'), '2023.11.14', 'an author text that is not a version falls back to the file date')
        self.assertEqual(text(''), '2023.11.14')
        self.assertEqual(text('', added=0), '0.0.77', 'and to the file id when even the date is missing')
        self.assertEqual(text('1.02'), '2023.11.14', 'a leading zero is not a valid version either')

    def test_every_day_of_a_year_gives_a_version_the_installer_accepts(self):
        """Found by the first real download: 2026-08-29 became '2026.08.29', which the version rules refuse."""
        from datetime import datetime, timedelta, timezone
        from deadlock_fps.repos.versions import Version
        start = datetime(2024, 1, 1, 12, tzinfo=timezone.utc)          # a leap year: every month and day shape occurs
        seen = []
        for offset in range(366):
            stamp = int((start + timedelta(days=offset)).timestamp())
            document = profile_document(files=[file_entry(ident=77)])
            document['_sVersion'] = 'Beta'
            document['_aFiles'][0]['_tsDateAdded'] = stamp
            profile = parse_profile(document)
            text = version_text(profile.submission, profile.files[0])
            Version.parse(text)                                          # raises when the text is not a valid version
            build(profile, profile.files[0])                             # and so does the whole adapter
            seen.append(Version.parse(text))
        self.assertEqual(seen, sorted(seen), 'later files always get later versions')
        self.assertEqual(len(set(seen)), 366)
        real = profile_document(files=[file_entry(ident=1801337)])          # the file that broke it: uploaded 2026-08-29
        real['_sVersion'] = ''
        real['_aFiles'][0]['_tsDateAdded'] = int(datetime(2026, 8, 29, 12, tzinfo=timezone.utc).timestamp())
        profile = parse_profile(real)
        self.assertEqual(version_text(profile.submission, profile.files[0]), '2026.8.29')


def raw_zip(members):
    """A zip whose member names are stored exactly as given. `ZipFile.writestr(name)` rewrites os.sep (a backslash on Windows) to '/', which would hide the very names these tests are about."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as handle:
        for name, data in members.items():
            info = zipfile.ZipInfo('placeholder')
            info.filename = name                # assigned after construction: no normalisation
            handle.writestr(info, data)
    return buffer.getvalue()


class Discovery(unittest.TestCase):
    def inspect(self, members, **kwargs):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'x.zip'
            path.write_bytes(raw_zip(members))
            return archive.inspect_zip(path, kwargs.pop('wanted', []), discover=True)

    def test_finds_every_vpk_at_any_depth_and_ignores_the_rest(self):
        report = self.inspect({'readme.txt': b'hi', 'mod/pak03_dir.vpk': b'x', 'pak01_dir.vpk': b'x', 'deep/er/other.VPK': b'x', 'setup.exe': b'MZ'})
        self.assertEqual(report.members, ('deep/er/other.VPK', 'mod/pak03_dir.vpk', 'pak01_dir.vpk'))
        self.assertEqual(report.ignored, ('readme.txt', 'setup.exe'))
        self.assertEqual(report.risky, ('setup.exe',))

    def test_nothing_to_install_is_an_error(self):
        for members in ({'readme.txt': b'x'}, {'a.rar': b'x'}, {'notes/vpk': b'x'}):
            with self.assertRaises(InstallError) as caught:
                self.inspect(members)
            self.assertEqual(caught.exception.code, 'bad-package')
            self.assertIn('no .vpk', caught.exception.message)

    def test_too_many_files_without_a_manifest_are_refused(self):
        self.assertEqual(len(self.inspect({'p%d_dir.vpk' % i: b'x' for i in range(8)}).members), 8)
        with self.assertRaises(InstallError) as caught:
            self.inspect({'p%d_dir.vpk' % i: b'x' for i in range(9)})
        self.assertIn('at most 8', caught.exception.message)

    def test_every_safety_check_still_covers_the_whole_archive(self):
        names = ['../evil.vpk', '/abs.vpk', 'C:/x.vpk', 'ok/./x.vpk']
        if os.sep == '/':
            # zipfile itself turns a backslash into '/' when it reads the member list on Windows, so only other systems ever see one.
            # Either way the name is never used as a path: members are streamed to a staging name the installer picks.
            names.append('a\\b.vpk')
        for name in names:
            with self.assertRaises(InstallError, msg=name):
                self.inspect({'good_dir.vpk': b'x', name: b'x'})
        with self.assertRaises(InstallError):               # a case collision, even between files that would not be installed
            self.inspect({'good_dir.vpk': b'x', 'Notes.txt': b'a', 'notes.txt': b'b'})

    def test_a_manifest_list_is_ignored_when_discovering(self):
        report = self.inspect({'a_dir.vpk': b'x', 'b.txt': b'y'}, wanted=['b.txt'])
        self.assertEqual(report.members, ('a_dir.vpk',))


class StoreInstall(GameCase):
    """Real engine, throwaway game folder, a fake GameBanana that serves real zip bytes."""

    def offer_file(self, data, name='mod.zip', ident=1801337, md5_value=None, mod_id=711387, size=None, **entry):
        profile = parse_profile(profile_document(mod_id, 'Pink Drifter', files=[file_entry(
            ident=ident, name=name, size=len(data) if size is None else size, md5=md5(data) if md5_value is None else md5_value, **entry)]))
        self.transport.files[URL % ident] = data
        return profile

    def prepare(self, profile, **kwargs):
        repository, mod, version = build(profile, profile.files[0])
        return self.installer.prepare(repository, mod, version, **kwargs)

    def install(self, profile, ack=True):
        return self.installer.commit(self.prepare(profile), acknowledged=ack)

    def staging_clean(self):
        staging = self.installer.store_dir / 'staging'
        return not staging.exists() or not any(staging.iterdir())

    # ---- the good path -------------------------------------------------------------

    def test_a_zip_is_downloaded_checked_inspected_and_installed(self):
        data = make_zip({'readme.txt': b'hi', 'pak52_dir.vpk': make_vpk(['materials/a.vmat'])})
        plan = self.prepare(self.offer_file(data))
        self.assertEqual((plan.verified, plan.md5_verified, plan.requires_ack, plan.trust, plan.repository_id), (False, True, True, 'UNVERIFIED', STORE_ID))
        self.assertTrue(any('MD5 checksum and the download matched it' in w for w in plan.warnings))
        self.assertFalse(any('published no SHA-256' in w for w in plan.warnings))
        self.assertEqual([f.source for f in plan.files], ['pak52_dir.vpk'])
        self.assertEqual(self.addon_names(), [], 'preparing never touches the game folder')
        installed = self.installer.commit(plan, acknowledged=True)
        self.assertEqual(installed.key, (STORE_ID, 'gb-711387'))
        self.assertEqual((installed.trust, installed.repository_name, installed.package_verified), ('UNVERIFIED', 'GameBanana', False))
        self.assertEqual(installed.package_url, URL % 1801337)
        self.assertEqual(installed.source_url, 'https://gamebanana.com/mods/711387')
        self.assertEqual(self.addon_names(), ['pak01_dir.vpk'], 'renamed into the first free pak slot, whatever the archive called it')

    def test_the_acknowledgement_is_enforced_by_the_engine(self):
        plan = self.prepare(self.offer_file(make_zip({'a_dir.vpk': make_vpk()})))
        with self.assertRaises(InstallError) as caught:
            self.installer.commit(plan, acknowledged=False)
        self.assertEqual(caught.exception.code, 'ack-required')
        self.assertEqual(self.addon_names(), [])

    def test_several_vpks_become_several_paks(self):
        data = make_zip({'one_dir.vpk': make_vpk(['materials/a.vmat']), 'sub/two_dir.vpk': make_vpk(['materials/b.vmat'])})
        installed = self.install(self.offer_file(data))
        self.assertEqual(self.addon_names(), ['pak01_dir.vpk', 'pak02_dir.vpk'])
        self.assertEqual(len(installed.files), 2)

    def test_a_bare_vpk_installs(self):
        profile = self.offer_file(make_vpk(), name='pak09_dir.vpk')
        self.assertEqual(self.install(profile).file_names(), ['pak01_dir.vpk'])

    def test_executables_inside_the_archive_are_reported_and_never_installed(self):
        plan = self.prepare(self.offer_file(make_zip({'a_dir.vpk': make_vpk(), 'setup.exe': b'MZ'})))
        self.assertTrue(any('setup.exe' in w and 'will not be installed or run' in w for w in plan.warnings))
        self.installer.commit(plan, acknowledged=True)
        self.assertEqual(self.addon_names(), ['pak01_dir.vpk'])

    def test_installing_again_is_an_update_and_uninstalling_leaves_a_way_back(self):
        profile = self.offer_file(make_zip({'a_dir.vpk': make_vpk()}))
        self.install(profile)
        plan = self.prepare(profile)
        self.assertEqual((plan.action, plan.replaces), ('update', plan.version))
        self.installer.commit(plan, acknowledged=True)
        self.assertEqual(self.addon_names(), ['pak01_dir.vpk'])
        self.installer.uninstall(STORE_ID, 'gb-711387')
        self.assertEqual((self.addon_names(), self.installer.installed()), ([], []))
        self.assertTrue(any((self.installer.store_dir / 'trash').rglob('*.vpk')), 'removed files go to the recovery folder, not the void')

    # ---- integrity -----------------------------------------------------------------

    def test_a_wrong_md5_discards_the_download_and_changes_nothing(self):
        before = self.game_snapshot()
        with self.assertRaises(InstallError) as caught:
            self.prepare(self.offer_file(make_zip({'a_dir.vpk': make_vpk()}), md5_value='a' * 32))
        self.assertEqual(caught.exception.code, 'hash-mismatch')
        self.assertIn('MD5', caught.exception.message)
        self.assertEqual((self.game_snapshot(), self.staging_clean()), (before, True))
        self.assertEqual(list((self.installer.store_dir / 'downloads').glob('*')), [], 'no partial file is left behind')

    def test_the_md5_comparison_ignores_case(self):
        data = make_zip({'a_dir.vpk': make_vpk()})
        # the profile parser lower-cases, so an upper-case value is given to the engine directly
        profile = self.offer_file(data)
        repository, mod, version = build(profile, profile.files[0])
        shouted = version.__class__(**{**version.__dict__, 'package': version.package.__class__(**{**version.package.__dict__, 'md5': md5(data).upper()})})
        self.assertTrue(self.installer.prepare(repository, mod, shouted).md5_verified)

    def test_without_any_checksum_the_old_warning_stays(self):
        plan = self.prepare(self.offer_file(make_zip({'a_dir.vpk': make_vpk()}), md5_value=''))
        self.assertEqual((plan.md5_verified, plan.verified), (False, False))
        self.assertTrue(any('published no SHA-256' in w for w in plan.warnings))

    # ---- where the bytes may come from -----------------------------------------------

    def serve_from(self, final_url):
        """A transport whose downloads claim to have ended on `final_url`, as a redirect chain would."""
        outer = self.transport

        class Redirecting(ServingTransport):
            def download(self, url, destination, **kwargs):
                result = outer.download(url, destination, **kwargs)
                return DownloadResult(result.size, result.sha256, final_url)
        redirecting = Redirecting()
        redirecting.files = outer.files
        self.installer.transport = redirecting

    def test_gamebanana_subdomains_are_accepted_as_the_final_host(self):
        profile = self.offer_file(make_zip({'a_dir.vpk': make_vpk()}))
        for final in ('https://files.gamebanana.com/mods/x.zip', 'https://filecache46.gamebanana.com/mods/x.zip', 'https://gamebanana.com/dl/1'):
            self.serve_from(final)
            self.assertTrue(self.prepare(profile).md5_verified, final)
            self.installer.discard(self.prepare(profile))

    def test_any_other_final_host_is_refused_and_leaves_nothing(self):
        profile = self.offer_file(make_zip({'a_dir.vpk': make_vpk()}))
        before = self.game_snapshot()
        for final in ('https://evil.example.net/x.zip', 'https://gamebanana.com.evil.net/x.zip', 'https://notgamebanana.com/x.zip', 'https://gamebanana.com.example/x.zip'):
            self.serve_from(final)
            with self.assertRaises(InstallError, msg=final) as caught:
                self.prepare(profile)
            self.assertEqual(caught.exception.code, 'download')
            self.assertIn('expected hosts', caught.exception.message)
        self.assertEqual((self.game_snapshot(), self.staging_clean(), list((self.installer.store_dir / 'downloads').glob('*'))), (before, True, []))

    def test_repository_packages_without_a_host_list_are_unaffected(self):
        mod = self.offer('plain', [{'version': '1.0.0', 'data': make_vpk()}])
        self.serve_from('https://anywhere.example.net/x.vpk')
        plan = self.installer.prepare(__import__('installer_fixtures').view(), mod, mod.latest())
        self.assertTrue(plan.verified)

    # ---- refusals --------------------------------------------------------------------

    def test_a_vpk_that_is_not_a_vpk_is_refused_inside_a_zip(self):
        before = self.game_snapshot()
        with self.assertRaises(InstallError) as caught:
            self.prepare(self.offer_file(make_zip({'a_dir.vpk': b'this is not a package'})))
        self.assertEqual(caught.exception.code, 'bad-package')
        self.assertEqual((self.game_snapshot(), self.staging_clean()), (before, True))

    def test_a_zip_with_no_vpk_and_an_archive_that_is_not_a_zip(self):
        for data, fragment in ((make_zip({'readme.txt': b'x'}), 'no .vpk'), (b'Rar!\x1a\x07\x00 not a zip', 'not a valid ZIP')):
            with self.assertRaises(InstallError) as caught:
                self.prepare(self.offer_file(data, ident=900 + len(data)))
            self.assertIn(fragment, caught.exception.message)

    def test_an_unsupported_file_never_reaches_the_network(self):
        profile = self.offer_file(b'Rar!', name='mod.rar')
        with self.assertRaises(InstallError) as caught:
            self.prepare(profile)
        self.assertEqual(caught.exception.code, 'not-installable')
        self.assertEqual(self.transport.downloads, [])

    def test_a_download_larger_than_announced_is_cut_off(self):
        profile = self.offer_file(make_zip({'a_dir.vpk': make_vpk()}), size=10)
        with self.assertRaises(InstallError) as caught:
            self.prepare(profile)
        self.assertIn(caught.exception.code, ('download', 'size-mismatch'))
        self.assertTrue(self.staging_clean())

    def test_the_game_must_be_closed(self):
        plan = self.prepare(self.offer_file(make_zip({'a_dir.vpk': make_vpk()})))
        self.running = True
        with self.assertRaises(InstallError) as caught:
            self.installer.commit(plan, acknowledged=True)
        self.assertEqual(caught.exception.code, 'game-running')
        self.assertEqual(self.addon_names(), [])


class AroundTheEngine(GameCase):
    def installed_store_mod(self):
        data = make_zip({'a_dir.vpk': make_vpk()})
        profile = parse_profile(profile_document(files=[file_entry(size=len(data), md5=md5(data))]))
        self.transport.files[URL % 1801337] = data
        repository, mod, version = build(profile, profile.files[0])
        return self.installer.commit(self.installer.prepare(repository, mod, version), acknowledged=True)

    def test_update_status_does_not_claim_the_repository_was_removed(self):
        have = self.installed_store_mod()
        (status,) = update_status([have], None)
        self.assertEqual(status.state, 'unavailable')
        self.assertIn('Mod Store', status.note)
        self.assertNotIn('removed', status.note)
        self.assertFalse(status.updatable)

    def test_the_graph_shows_store_mods_as_such(self):
        have = self.installed_store_mod()
        with tempfile.TemporaryDirectory() as folder:
            from deadlock_fps.store.install import STORE_ID as sid
            manager = RepositoryManager(RepositoryStore(Path(folder)), FakeTransport())
            graph = build_catalogue(Graph(), manager, [have])
        node = graph.nodes['mod:%s|gb-711387' % sid]
        self.assertEqual((node.status, node.installed), ('MOD STORE', True))
        self.assertIn('Mod Store', ' '.join(node.lines))

    def test_the_analysis_and_repair_tools_cope_with_store_mods(self):
        self.installed_store_mod()
        self.assertEqual([i for i in self.installer.analyze() if i.severity == 'error'], [])


if __name__ == '__main__':
    unittest.main()
