"""Versions, URL safety, the manifest specification and game-fit evaluation."""
import json
import unittest

from deadlock_fps.repos import spec
from deadlock_fps.repos.compat import fit
from deadlock_fps.repos.errors import RepoError
from deadlock_fps.repos.model import GameFit, GameSupport
from deadlock_fps.repos.urls import check_https_url, github_identity, gitlab_identity, canonical_https_id, is_public_host
from deadlock_fps.repos.versions import Version, satisfies, parse_range
from repo_fixtures import index, mod, version, clone, SHA


class Versions(unittest.TestCase):
    def test_ordering_including_prereleases_and_short_forms(self):
        ordered = ['0.9', '1.0.0-alpha', '1.0.0-alpha.1', '1.0.0-beta', '1.0.0-beta.2', '1.0.0-beta.11', '1.0.0-rc.1', '1.0', '1.0.1', '1.0.10', '1.2', '2']
        parsed = [Version.parse(v) for v in ordered]
        self.assertEqual(sorted(reversed(parsed)), parsed)
        self.assertEqual(Version.parse('1.4'), Version.parse('v1.4.0'))
        self.assertEqual(hash(Version.parse('1.4')), hash(Version.parse('1.4.0')))

    def test_rejects_garbage(self):
        for bad in ['', 'latest', '1..2', '01.2', '1.2.3.4.5', '1.0-', None, 12, '../1.0', 'x' * 80, '1.0-01']:
            with self.assertRaises(RepoError, msg=repr(bad)):
                Version.parse(bad)

    def test_ranges(self):
        v = Version.parse
        self.assertTrue(satisfies(v('1.5'), '>=1.2 <2'))
        self.assertTrue(satisfies(v('1.5'), '>= 1.2 < 2'))
        self.assertFalse(satisfies(v('2.0'), '>=1.2 <2'))
        self.assertTrue(satisfies(v('3'), '*'))
        self.assertTrue(satisfies(v('3'), ''))
        self.assertTrue(satisfies(v('1.0'), '=1.0.0'))
        self.assertFalse(satisfies(v('1.3'), '!=1.3'))
        self.assertFalse(satisfies(v('1.0.0-beta'), '>=1.0.0'))
        for bad in ['>=', '>=abc', 'a b', '~1.2']:
            with self.assertRaises(RepoError, msg=bad):
                parse_range(bad)


class Urls(unittest.TestCase):
    def test_accepts_plain_https_and_normalises(self):
        self.assertEqual(check_https_url('https://Example.ORG/a/b?x=1#frag'), 'https://example.org/a/b?x=1')
        self.assertEqual(check_https_url('https://example.org:443/x'), 'https://example.org/x')

    def test_rejects_unsafe_addresses(self):
        for bad in ['http://example.org/x', 'ftp://example.org', 'file:///etc/passwd', 'https://user:pw@example.org/', 'https://user@example.org/',
                    'https://example.org:8443/x', 'https://localhost/x', 'https://app.localhost/x', 'https://127.0.0.1/x', 'https://10.0.0.5/x',
                    'https://192.168.1.1/x', 'https://169.254.169.254/latest/meta-data', 'https://[::1]/x', 'https://printer/x', 'https://nas.local/x',
                    'https://example.org/a b', 'https://example.org/\x00', 'https://example.org/a\\b', '', None, 'https://' + 'a' * 300 + '.example.org/',
                    'https://example.org/' + 'a' * 3000, '//example.org/x', 'javascript:alert(1)']:
            with self.assertRaises(RepoError, msg=repr(bad)):
                check_https_url(bad)

    def test_public_ip_literals_pass(self):
        self.assertTrue(is_public_host('8.8.8.8'))
        self.assertFalse(is_public_host('100.64.0.1'))   # carrier-grade NAT

    def test_identity(self):
        self.assertEqual(github_identity('https://github.com/Owner/Repo.git'), ('Owner', 'Repo'))
        self.assertEqual(github_identity('https://github.com/owner/repo/releases/tag/v1'), ('owner', 'repo'))
        self.assertEqual(github_identity('https://www.github.com/owner/repo'), ('owner', 'repo'))
        for bad in ['https://github.com/owner', 'https://github.com.evil.test/o/r', 'http://github.com/o/r', 'https://github.com/o/..', 'https://gist.github.com/o/r']:
            self.assertIsNone(github_identity(bad), bad)
        self.assertEqual(gitlab_identity('https://gitlab.com/group/sub/proj/-/releases'), ('gitlab.com', 'group/sub/proj'))
        self.assertIsNone(gitlab_identity('https://gitlab.example.org/g/p'))
        self.assertEqual(gitlab_identity('https://gitlab.example.org/g/p.git', hosts=None), ('gitlab.example.org', 'g/p'))
        self.assertEqual(canonical_https_id('https://Mods.Example.org/repo/?q=1'), 'https:mods.example.org/repo')


class Specification(unittest.TestCase):
    def test_valid_index_is_parsed_with_versions_newest_first(self):
        result = spec.parse_index(json.dumps(index()).encode())
        self.assertEqual(result.info.name, 'Example Mods')
        self.assertEqual(result.warnings, ())
        crimson = result.get('crimson-skin')
        self.assertEqual([str(v.version) for v in crimson.versions], ['1.1.0', '1.0.0'])
        self.assertEqual(str(crimson.latest().version), '1.1.0')
        self.assertTrue(crimson.latest().installable)
        self.assertEqual(crimson.categories, ('skins', 'characters'))
        self.assertFalse(crimson.derived)

    def test_future_minor_and_unknown_fields_are_tolerated(self):
        doc = index(schema_version='1.7')
        doc['future_field'] = {'anything': True}
        doc['mods'][0]['new_thing'] = 5
        doc['mods'][0]['versions'][0]['package']['compression'] = 'zstd'
        self.assertEqual(len(spec.parse_index(doc).mods), 1)

    def test_other_major_is_refused_with_its_own_code(self):
        with self.assertRaises(RepoError) as caught:
            spec.parse_index(index(schema_version='2.0'))
        self.assertEqual(caught.exception.code, 'unsupported-schema')

    def test_structural_problems_raise(self):
        for doc in [[], {}, index(schema='something-else'), index(schema_version='one'), index(repository='x'), index(mods='x'),
                    {**index(), 'repository': {'id': 'x'}}]:
            with self.assertRaises(RepoError, msg=str(doc)[:60]):
                spec.parse_index(doc)
        for raw in [b'not json', b'\xff\xfe', b'[1,2]']:
            with self.assertRaises(RepoError):
                spec.parse_index(raw)

    def test_size_limits(self):
        with self.assertRaises(RepoError) as caught:
            spec.parse_index(b' ' * (spec.MAX_INDEX_BYTES + 1))
        self.assertEqual(caught.exception.code, 'too-large')
        many = index(*[mod('mod-%04d' % i, versions=[version()]) for i in range(spec.MAX_MODS + 1)])
        with self.assertRaises(RepoError):
            spec.parse_index(many)

    def test_one_bad_mod_does_not_poison_the_rest(self):
        bad_id = mod('Bad ID!')
        no_versions = mod('empty-one', versions=[])
        good = mod('good-one')
        result = spec.parse_index(index(bad_id, no_versions, good))
        self.assertEqual([m.id for m in result.mods], ['good-one'])
        self.assertEqual(len(result.warnings), 2)
        self.assertIn('mod #1 skipped', result.warnings[0])

    def test_bad_version_is_skipped_but_mod_survives(self):
        m = mod(versions=[version('1.0.0'), version('not-a-version'), version('1.1.0', package={'format': 'vpk', 'url': 'http://insecure.example.org/a.vpk', 'size': 10})])
        result = spec.parse_index(index(m))
        self.assertEqual([str(v.version) for v in result.mods[0].versions], ['1.0.0'])
        self.assertEqual(len(result.warnings), 2)

    def test_security_fields_are_enforced(self):
        def rejected(**changes):
            package = {'format': 'vpk', 'url': 'https://files.example.org/a.vpk', 'size': 10, 'sha256': SHA}
            package.update(changes.pop('package', {}))
            m = mod(versions=[version('1.0.0', package=package, **changes)])
            return spec.parse_index(index(m)).mods == ()
        self.assertTrue(rejected(package={'url': 'http://files.example.org/a.vpk'}))
        self.assertTrue(rejected(package={'url': 'https://127.0.0.1/a.vpk'}))
        self.assertTrue(rejected(package={'url': 'https://user:pw@files.example.org/a.vpk'}))
        self.assertTrue(rejected(package={'sha256': 'zz'}))
        self.assertTrue(rejected(package={'sha256': 'a' * 63}))
        self.assertTrue(rejected(package={'size': 0}))
        self.assertTrue(rejected(package={'size': -5}))
        self.assertTrue(rejected(package={'size': '10'}))
        self.assertTrue(rejected(package={'size': True}))
        self.assertTrue(rejected(package={'size': spec.MAX_PACKAGE_BYTES + 1}))
        self.assertTrue(rejected(package={'mirrors': ['http://m.example.org/a']}))
        self.assertTrue(rejected(package={'size': None}))                    # native indexes must declare a size
        self.assertFalse(rejected())

    def test_install_paths_cannot_escape_or_install_anything_but_vpk(self):
        def survives(fmt, files):
            m = mod(versions=[version('1.0.0', package={'format': fmt, 'url': 'https://f.example.org/a.zip', 'size': 10}, install={'type': 'vpk', 'files': files})])
            return bool(spec.parse_index(index(m)).mods)
        self.assertTrue(survives('zip', [{'source': 'pak/skin.vpk'}]))
        for source in ['../evil.vpk', '/etc/passwd.vpk', 'a/../../b.vpk', 'C:/x.vpk', 'a\\b.vpk', 'run.exe', 'setup.bat', 'readme.txt', 'a:stream.vpk', '.hidden.vpk', 'x' * 300 + '.vpk', 'sp ace/\x00.vpk']:
            self.assertFalse(survives('zip', [{'source': source}]), source)
        self.assertFalse(survives('zip', []))                                 # a zip must say which files to install
        self.assertFalse(survives('vpk', [{'source': ''}, {'source': 'second.vpk'}]))

    def test_unknown_format_or_install_type_is_kept_but_not_installable(self):
        m = mod(versions=[version('2.0.0', package={'format': '7z', 'url': 'https://f.example.org/a.7z', 'size': 10}),
                          version('1.0.0', install={'type': 'script', 'files': []})])
        parsed = spec.parse_index(index(m)).mods[0]
        self.assertEqual(len(parsed.versions), 2)
        self.assertTrue(all(not v.installable for v in parsed.versions))
        self.assertIn('not supported', parsed.versions[0].unsupported_reason)
        self.assertFalse(parsed.latest().installable)

    def test_yanked_and_prerelease_selection(self):
        m = mod(versions=[version('2.0.0-beta.1'), version('1.5.0', yanked=True), version('1.4.0'), version('1.3.0', prerelease=True)])
        parsed = spec.parse_index(index(m)).mods[0]
        self.assertEqual(str(parsed.latest().version), '1.4.0')
        self.assertEqual(str(parsed.latest(include_prerelease=True).version), '1.4.0')
        only_pre = spec.parse_index(index(mod(versions=[version('1.0.0-rc.1')]))).mods[0]
        self.assertIsNone(only_pre.latest())
        self.assertEqual(str(only_pre.latest(include_prerelease=True).version), '1.0.0-rc.1')

    def test_duplicates_are_reported_not_merged(self):
        result = spec.parse_index(index(mod('same-id'), mod('same-id', name='Other'),))
        self.assertEqual([m.name for m in result.mods], ['Crimson Skin'])
        m = mod(versions=[version('1.0.0'), version('1.0')])
        self.assertEqual(len(spec.parse_index(index(m)).mods[0].versions), 1)

    def test_text_fields_reject_control_characters_and_overlong_values(self):
        for changes in [{'name': 'Bad\x00name'}, {'name': 'x' * 121}, {'name': ''}, {'summary': 'line\nbreak'}, {'description': 'x' * 16001}, {'categories': 'skins'},
                        {'screenshots': ['http://x.example.org/a.png']}, {'published': 'yesterday'}, {'published': '2026-13-45'}]:
            result = spec.parse_index(index(mod(**changes)))
            self.assertEqual(result.mods, (), changes)
        result = spec.parse_index(index(mod(description='Line one\nLine two\ttabbed')))
        self.assertIn('Line two', result.mods[0].description)

    def test_publisher_cannot_declare_trust(self):
        doc = index()
        doc['trust'] = 'OFFICIAL'
        doc['repository']['trust'] = 'VERIFIED'
        doc['mods'][0]['verified'] = True
        result = spec.parse_index(doc)
        self.assertFalse(any(hasattr(result.info, name) for name in ('trust', 'verified')))
        self.assertFalse(hasattr(result.mods[0], 'verified'))

    def test_derived_documents_may_omit_size_and_author(self):
        m = mod(author='', versions=[version('1.0.0', package={'format': 'vpk', 'url': 'https://github.com/o/r/releases/download/1.0.0/a.vpk'})])
        self.assertEqual(spec.parse_index(index(m)).mods, ())
        parsed = spec.parse_index(index(m), derived=True).mods[0]
        self.assertTrue(parsed.derived)
        self.assertIsNone(parsed.versions[0].package.size)

    def test_repository_list_documents(self):
        doc = {'schema': 'deadlock-mod-repository-list', 'schema_version': '1.0',
               'repositories': [{'url': 'https://github.com/a/b', 'name': 'AB'}, {'url': 'https://mods.example.org/idx.json'}]}
        entries = spec.parse_repository_list(doc)
        self.assertEqual([e['url'] for e in entries], ['https://github.com/a/b', 'https://mods.example.org/idx.json'])
        doc['repositories'].append({'url': 'http://nope.example.org'})
        with self.assertRaises(RepoError):
            spec.parse_repository_list(doc)
        self.assertEqual(spec.kind_of(json.dumps(doc).encode()), 'list')
        self.assertEqual(spec.kind_of(json.dumps(index()).encode()), 'index')
        self.assertIsNone(spec.kind_of(b'[]'))


class GameFitRules(unittest.TestCase):
    def test_fit(self):
        F = GameFit
        self.assertIs(fit(GameSupport(100, 200, None), 150), F.COMPATIBLE)
        self.assertIs(fit(GameSupport(100, 200, None), 99), F.INCOMPATIBLE)
        self.assertIs(fit(GameSupport(100, 200, None), 201), F.INCOMPATIBLE)
        self.assertIs(fit(GameSupport(100, None, 150), 150), F.COMPATIBLE)
        self.assertIs(fit(GameSupport(100, None, 150), 400), F.UNTESTED)
        self.assertIs(fit(GameSupport(None, None, None), 400), F.UNKNOWN)
        self.assertIs(fit(GameSupport(100, 200, None), None), F.UNKNOWN)


if __name__ == '__main__':
    unittest.main()
