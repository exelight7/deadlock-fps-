"""Providers (GitHub, GitLab, custom HTTPS) and the transport's network-safety rules."""
import io
import json
import unittest
import urllib.error
from email.message import Message

from deadlock_fps.repos.errors import RepoError
from deadlock_fps.repos.model import Compat, RepositorySource
from deadlock_fps.repos.providers import default_registry, ProviderRegistry, Provider
from deadlock_fps.repos.providers.github import GitHubProvider
from deadlock_fps.repos.providers.gitlab import GitLabProvider
from deadlock_fps.repos.providers.native import NativeHttpsProvider
from deadlock_fps.repos.transport import UrllibTransport, resolve_public, Response
from repo_fixtures import FakeTransport, ok, status, index, mod, version, gh_repo, gh_asset, gh_release, SHA

GH = 'https://api.github.com/repos/mira/skins'
RAW = 'https://raw.githubusercontent.com/mira/skins/main/deadlock-repo.json'


def github_source():
    return RepositorySource('github:mira/skins', 'github', 'https://github.com/mira/skins')


class Registry(unittest.TestCase):
    def test_identification_and_canonical_ids(self):
        r = default_registry()
        self.assertEqual(r.identify('https://github.com/Mira/Skins.git').id, 'github:mira/skins')
        self.assertEqual(r.identify('https://github.com/mira/skins/releases').kind, 'github')
        self.assertEqual(r.identify('https://gitlab.com/g/p').id, 'gitlab:gitlab.com/g/p')
        self.assertEqual(r.identify('https://mods.example.org/repo/').id, 'https:mods.example.org/repo')
        self.assertEqual(r.identify('https://gitlab.example.org/g/p', 'gitlab').id, 'gitlab:gitlab.example.org/g/p')
        with self.assertRaises(RepoError):
            r.identify('https://gitlab.example.org/g/p', 'nonsense')

    def test_a_new_provider_can_be_registered_without_touching_core(self):
        class Gitea(Provider):
            kind = 'gitea'

            def identify(self, url, hint=''):
                from deadlock_fps.repos.providers.base import Identity
                return Identity('gitea:' + url, self.kind, url) if 'gitea.example.org' in url else None

            def sync(self, source, transport, etag=''):
                raise NotImplementedError
        r = default_registry()
        r.register(Gitea(), first=True)
        self.assertEqual(r.identify('https://gitea.example.org/x/y').kind, 'gitea')
        with self.assertRaises(ValueError):
            r.register(Gitea())


class GitHub(unittest.TestCase):
    def test_native_manifest_in_default_branch(self):
        t = FakeTransport({GH: ok(gh_repo()), RAW: ok(index(), ETag='"v1"')})
        result = GitHubProvider().sync(github_source(), t)
        self.assertEqual(result.compat, Compat.NATIVE)
        self.assertEqual(result.index.info.name, 'Example Mods')
        self.assertEqual(result.etag, '"v1"')
        self.assertFalse(any('/releases' in u for u in t.urls()))        # no need to list releases

    def test_invalid_manifest_is_reported_not_silently_replaced_by_guessing(self):
        t = FakeTransport({GH: ok(gh_repo()), RAW: ok({'schema': 'deadlock-mod-repository', 'schema_version': '9.0'}),
                           GH + '/releases?per_page=30': ok([gh_release('v1.0.0', [gh_asset('mira', 'skins', 'v1.0.0', 'a.vpk')])])})
        result = GitHubProvider().sync(github_source(), t)
        self.assertEqual(result.compat, Compat.UNSUPPORTED)
        self.assertIn('not a usable repository index', result.reason)
        self.assertIsNone(result.index)

    def test_manifest_attached_to_a_release(self):
        asset = gh_asset('mira', 'skins', 'v2', 'deadlock-repo.json', digest=None)
        t = FakeTransport({GH: ok(gh_repo()), GH + '/releases?per_page=30': ok([gh_release('v2', [asset])]), asset['browser_download_url']: ok(index())})
        self.assertEqual(GitHubProvider().sync(github_source(), t).compat, Compat.NATIVE)

    def test_vpk_releases_are_translated_honestly(self):
        releases = [gh_release('v1.2.0', [gh_asset('mira', 'skins', 'v1.2.0', 'red-skin-v1.2.0.vpk'), gh_asset('mira', 'skins', 'v1.2.0', 'blue-skin-1.2.0.vpk', digest=None)]),
                    gh_release('v1.1.0', [gh_asset('mira', 'skins', 'v1.1.0', 'red-skin-v1.1.0.vpk')], prerelease=True),
                    gh_release('draft', [gh_asset('mira', 'skins', 'draft', 'x.vpk')], draft=True)]
        t = FakeTransport({GH: ok(gh_repo()), GH + '/releases?per_page=30': ok(releases)})
        result = GitHubProvider().sync(github_source(), t)
        self.assertEqual(result.compat, Compat.TRANSLATED)
        mods = {m.name: m for m in result.index.mods}
        self.assertEqual(sorted(mods), ['blue-skin', 'red-skin'])
        red = mods['red-skin']
        self.assertTrue(red.derived)
        self.assertEqual([str(v.version) for v in red.versions], ['1.2.0', '1.1.0'])
        self.assertTrue(red.versions[1].prerelease)
        self.assertEqual(str(red.latest().version), '1.2.0')
        self.assertEqual(red.versions[0].package.sha256, SHA)
        self.assertIsNone(mods['blue-skin'].versions[0].package.sha256)          # no hash is invented
        self.assertEqual(red.author, 'mira')
        self.assertEqual(red.license, 'MIT')
        self.assertIn('nobody has reviewed', result.reason)
        self.assertTrue(result.derived)
        self.assertTrue(json.loads(result.raw)['mods'])                           # cached document round-trips

    def test_zip_only_releases_need_manual_mapping_and_are_never_listed(self):
        rel = [gh_release('v3.5.5', [gh_asset('mira', 'skins', 'v3.5.5', 'App-windows-x64.zip'), gh_asset('mira', 'skins', 'v3.5.5', 'SHA256SUMS.txt')])]
        t = FakeTransport({GH: ok(gh_repo()), GH + '/releases?per_page=30': ok(rel)})
        result = GitHubProvider().sync(github_source(), t)
        self.assertEqual(result.compat, Compat.MANUAL)
        self.assertIsNone(result.index)
        self.assertIn('ZIP', result.reason)
        self.assertIn('mapping index', result.reason)

    def test_nothing_usable_and_missing_repositories(self):
        t = FakeTransport({GH: ok(gh_repo()), GH + '/releases?per_page=30': ok([])})
        self.assertEqual(GitHubProvider().sync(github_source(), t).compat, Compat.UNSUPPORTED)
        result = GitHubProvider().sync(github_source(), FakeTransport())
        self.assertEqual(result.compat, Compat.UNSUPPORTED)
        self.assertIn('no public repository', result.reason)

    def test_spoofed_asset_addresses_are_ignored(self):
        evil = gh_asset('mira', 'skins', 'v1.0.0', 'a.vpk')
        evil['browser_download_url'] = 'https://evil.example.org/mira/skins/releases/download/v1.0.0/a.vpk'
        other = gh_asset('mira', 'skins', 'v1.0.0', 'b.vpk')
        other['browser_download_url'] = 'https://github.com/someone/else/releases/download/v1.0.0/b.vpk'
        t = FakeTransport({GH: ok(gh_repo()), GH + '/releases?per_page=30': ok([gh_release('v1.0.0', [evil, other])])})
        self.assertEqual(GitHubProvider().sync(github_source(), t).compat, Compat.UNSUPPORTED)

    def test_oversized_incomplete_or_unversioned_assets_are_skipped(self):
        rel = [gh_release('v1.0.0', [gh_asset('mira', 'skins', 'v1.0.0', 'big.vpk', size=10 ** 12), gh_asset('mira', 'skins', 'v1.0.0', 'partial.vpk', state='new')]),
               gh_release('nightly', [gh_asset('mira', 'skins', 'nightly', 'n.vpk')])]
        t = FakeTransport({GH: ok(gh_repo()), GH + '/releases?per_page=30': ok(rel)})
        self.assertEqual(GitHubProvider().sync(github_source(), t).compat, Compat.UNSUPPORTED)

    def test_rate_limits_and_server_errors_are_errors_not_verdicts(self):
        for response, code in [(status(403, X_RateLimit_Remaining='0'), 'rate-limited'), (status(429), 'rate-limited'), (status(500), 'network')]:
            with self.assertRaises(RepoError) as caught:
                GitHubProvider().sync(github_source(), FakeTransport({GH: response}))
            self.assertEqual(caught.exception.code, code)
        with self.assertRaises(RepoError):
            GitHubProvider().sync(github_source(), FakeTransport({GH: RepoError('network', 'offline')}))


class GitLab(unittest.TestCase):
    API = 'https://gitlab.com/api/v4'
    SOURCE = RepositorySource('gitlab:gitlab.com/g/p', 'gitlab', 'https://gitlab.com/g/p')

    def routes(self, **extra):
        meta = {'id': 77, 'default_branch': 'main', 'description': 'Mods', 'web_url': 'https://gitlab.com/g/p'}
        return {self.API + '/projects/g%2Fp': ok(meta), **extra}

    def test_native_manifest(self):
        t = FakeTransport(self.routes(**{self.API + '/projects/77/repository/files/deadlock-repo.json/raw?ref=main': ok(index())}))
        self.assertEqual(GitLabProvider().sync(self.SOURCE, t).compat, Compat.NATIVE)

    def test_vpk_links_are_translated_without_size_or_hash(self):
        release = {'tag_name': 'v1.0.0', 'released_at': '2026-02-02T00:00:00Z', 'description': 'first', 'assets': {'links': [
            {'name': 'cool.vpk', 'direct_asset_url': 'https://gitlab.com/g/p/-/releases/v1.0.0/downloads/cool.vpk'},
            {'name': 'elsewhere.vpk', 'url': 'https://cdn.example.org/elsewhere.vpk'},
            {'name': 'insecure.vpk', 'url': 'http://gitlab.com/insecure.vpk'}]}}
        t = FakeTransport(self.routes(**{self.API + '/projects/77/releases?per_page=30': ok([release])}))
        result = GitLabProvider().sync(self.SOURCE, t)
        self.assertEqual(result.compat, Compat.TRANSLATED)
        self.assertEqual([m.name for m in result.index.mods], ['cool'])
        package = result.index.mods[0].versions[0].package
        self.assertIsNone(package.size)
        self.assertIsNone(package.sha256)
        self.assertEqual(len(result.warnings), 2)                                 # the other-host and http links, reported

    def test_zip_only_and_missing_project(self):
        release = {'tag_name': 'v1.0.0', 'assets': {'links': [{'name': 'pack.zip', 'url': 'https://gitlab.com/x/pack.zip'}]}}
        t = FakeTransport(self.routes(**{self.API + '/projects/77/releases?per_page=30': ok([release])}))
        self.assertEqual(GitLabProvider().sync(self.SOURCE, t).compat, Compat.MANUAL)
        self.assertEqual(GitLabProvider().sync(self.SOURCE, FakeTransport()).compat, Compat.UNSUPPORTED)

    def test_self_hosted_server_that_is_not_gitlab(self):
        source = RepositorySource('gitlab:git.example.org/g/p', 'gitlab', 'https://git.example.org/g/p', provider='gitlab')
        t = FakeTransport({'https://git.example.org/api/v4/projects/g%2Fp': ok({'hello': 'world'})})
        with self.assertRaises(RepoError):
            GitLabProvider().sync(source, t)


class CustomHttps(unittest.TestCase):
    def source(self, url):
        return RepositorySource('https:x', 'https', url)

    def test_direct_json_and_directory_urls(self):
        t = FakeTransport({'https://mods.example.org/idx.json': ok(index(), ETag='"a"'), 'https://mods.example.org/repo/deadlock-repo.json': ok(index())})
        provider = NativeHttpsProvider()
        self.assertEqual(provider.sync(self.source('https://mods.example.org/idx.json'), t).etag, '"a"')
        self.assertEqual(provider.sync(self.source('https://mods.example.org/repo/'), t).compat, Compat.NATIVE)
        self.assertEqual(t.urls()[-1], 'https://mods.example.org/repo/deadlock-repo.json')

    def test_conditional_request_and_not_modified(self):
        t = FakeTransport({'https://mods.example.org/idx.json': status(304)})
        result = NativeHttpsProvider().sync(self.source('https://mods.example.org/idx.json'), t, etag='"a"')
        self.assertTrue(result.not_modified)
        self.assertEqual(t.calls[0][1]['If-None-Match'], '"a"')

    def test_not_found_garbage_and_server_errors(self):
        provider = NativeHttpsProvider()
        self.assertEqual(provider.sync(self.source('https://mods.example.org/x.json'), FakeTransport()).compat, Compat.UNSUPPORTED)
        garbage = FakeTransport({'https://mods.example.org/x.json': ok(b'<html>hello</html>')})
        result = provider.sync(self.source('https://mods.example.org/x.json'), garbage)
        self.assertEqual(result.compat, Compat.UNSUPPORTED)
        self.assertIn('not valid', result.reason)
        with self.assertRaises(RepoError):
            provider.sync(self.source('https://mods.example.org/x.json'), FakeTransport({'https://mods.example.org/x.json': status(503)}))


class Reply:
    """Enough of an HTTP response for UrllibTransport._read."""

    def __init__(self, body, headers=None, status_code=200):
        self._body = io.BytesIO(body)
        self.headers = Message()
        for k, v in (headers or {}).items():
            self.headers[k] = v
        self.status = status_code

    def read(self, n=-1):
        return self._body.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class ScriptedOpener:
    def __init__(self, *steps):
        self.steps = list(steps)
        self.requested = []

    def open(self, request, timeout=None):
        self.requested.append(request.full_url)
        step = self.steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


def redirect(url, location, code=302):
    headers = Message()
    headers['Location'] = location
    return urllib.error.HTTPError(url, code, 'Found', headers, io.BytesIO(b''))


class TransportSafety(unittest.TestCase):
    def transport(self, *steps):
        t = UrllibTransport()
        t._opener = ScriptedOpener(*steps)
        return t

    def test_follows_https_redirects_and_returns_the_final_url(self):
        t = self.transport(redirect('https://a.example.org/x', 'https://b.example.org/y'), Reply(b'hello'))
        response = t.get('https://a.example.org/x', max_bytes=100)
        self.assertEqual((response.status, response.body, response.url), (200, b'hello', 'https://b.example.org/y'))

    def test_refuses_redirects_to_http_private_or_credentialed_targets(self):
        for target in ['http://b.example.org/', 'https://127.0.0.1/admin', 'https://10.1.1.1/', 'https://user:pw@b.example.org/', 'file:///etc/passwd', 'https://localhost/']:
            t = self.transport(redirect('https://a.example.org/x', target))
            with self.assertRaises(RepoError, msg=target) as caught:
                t.get('https://a.example.org/x', max_bytes=100)
            self.assertEqual(caught.exception.code, 'bad-url')

    def test_redirect_loops_stop(self):
        t = self.transport(*[redirect('https://a.example.org/x', 'https://a.example.org/x') for _ in range(10)])
        with self.assertRaises(RepoError) as caught:
            t.get('https://a.example.org/x', max_bytes=100)
        self.assertEqual(caught.exception.code, 'network')

    def test_size_limits_by_header_and_by_stream(self):
        with self.assertRaises(RepoError) as caught:
            self.transport(Reply(b'x', {'Content-Length': '5000'})).get('https://a.example.org/x', max_bytes=100)
        self.assertEqual(caught.exception.code, 'too-large')
        with self.assertRaises(RepoError) as caught:
            self.transport(Reply(b'x' * 5000)).get('https://a.example.org/x', max_bytes=100)
        self.assertEqual(caught.exception.code, 'too-large')

    def test_http_errors_are_returned_as_responses(self):
        error = urllib.error.HTTPError('https://a.example.org/x', 404, 'Not Found', Message(), io.BytesIO(b'{"message":"no"}'))
        self.assertEqual(self.transport(error).get('https://a.example.org/x', max_bytes=100).status, 404)

    def test_connection_failures_become_repo_errors(self):
        with self.assertRaises(RepoError) as caught:
            self.transport(urllib.error.URLError('timed out')).get('https://a.example.org/x', max_bytes=100)
        self.assertEqual(caught.exception.code, 'network')

    def test_initial_address_is_validated_before_any_request(self):
        t = self.transport()
        for bad in ['http://example.org/', 'https://127.0.0.1/', 'https://example.org:8080/']:
            with self.assertRaises(RepoError):
                t.get(bad, max_bytes=10)
        self.assertEqual(t._opener.requested, [])

    def test_only_https_is_reachable_through_the_opener(self):
        t = UrllibTransport()
        self.assertEqual(sorted(t._opener.handle_open), ['https'])

    def test_dns_answers_must_all_be_public(self):
        def resolver(answers):
            return lambda host, port, type=None: [(2, 1, 6, '', (a, port)) for a in answers]
        self.assertEqual(resolve_public('x.example.org', resolver=resolver(['93.184.216.34']))[1][0], '93.184.216.34')
        for answers in (['127.0.0.1'], ['10.0.0.8'], ['93.184.216.34', '192.168.0.1'], ['169.254.169.254'], ['0.0.0.0']):
            with self.assertRaises(RepoError, msg=str(answers)):
                resolve_public('x.example.org', resolver=resolver(answers))

        def failing(host, port, type=None):
            raise OSError('no such host')
        with self.assertRaises(RepoError):
            resolve_public('x.example.org', resolver=failing)


if __name__ == '__main__':
    unittest.main()
