"""GitLab projects and GitLab Releases (gitlab.com, or any self-hosted GitLab when the user names the provider).

Classification mirrors the GitHub provider: a `deadlock-repo.json` in the
default branch is NATIVE; otherwise `.vpk` links on releases are TRANSLATED;
ZIP-only releases are MANUAL; anything else is UNSUPPORTED. GitLab reports
neither sizes nor hashes for release links, so translated packages carry
neither and the interface says so.
"""
import json
from urllib.parse import quote, urlsplit

from .base import Provider, Identity, SyncResult, INDEX_FILENAME, get_json, native_result, check_status, slug
from ..errors import RepoError, NETWORK
from ..model import Compat
from ..spec import parse_index, SCHEMA, MAX_INDEX_BYTES
from ..urls import gitlab_identity, check_https_url, host_of
from ..versions import Version

RELEASE_PAGE = 30


class GitLabProvider(Provider):
    kind = 'gitlab'
    label = 'GitLab project'

    def identify(self, url, hint=''):
        try:
            clean = check_https_url(url)
        except RepoError:
            return None
        found = gitlab_identity(clean, hosts=None if hint == 'gitlab' else ('gitlab.com', 'www.gitlab.com'))
        if not found:
            return None
        host, path = found
        return Identity('gitlab:%s/%s' % (host, path.lower()), self.kind, 'https://%s/%s' % (host, path), path)

    def sync(self, source, transport, etag=''):
        host, path = gitlab_identity(source.url, hosts=None)
        api = 'https://%s/api/v4' % host
        response, meta = get_json(transport, '%s/projects/%s' % (api, quote(path, safe='')))
        check_status(response, host)
        if response.status == 404:
            return SyncResult(Compat.UNSUPPORTED, reason='%s reports no public project %s (it may be private, renamed or not a GitLab server).' % (host, path))
        if not isinstance(meta, dict) or type(meta.get('id')) is not int:
            raise RepoError(NETWORK, '%s did not answer like a GitLab server' % host)
        project, branch = meta['id'], meta.get('default_branch') if isinstance(meta.get('default_branch'), str) else 'main'

        raw = '%s/projects/%d/repository/files/%s/raw?ref=%s' % (api, project, INDEX_FILENAME, quote(branch, safe=''))
        manifest = transport.get(raw, max_bytes=MAX_INDEX_BYTES, headers={'Accept': 'application/json'})
        check_status(manifest, host)
        if manifest.status == 200:
            result = native_result(manifest, derived_from=INDEX_FILENAME)
            result.display_name = result.display_name or path
            return result

        response, releases = get_json(transport, '%s/projects/%d/releases?per_page=%d' % (api, project, RELEASE_PAGE))
        check_status(response, host)
        releases = [r for r in releases if isinstance(r, dict)] if response.status == 200 and isinstance(releases, list) else []
        translated = self._translate(meta, host, path, releases)
        if translated:
            return translated
        archives = sum(1 for r in releases for link in self._links(r) if str(link.get('name', '')).lower().endswith('.zip'))
        if archives:
            return SyncResult(Compat.MANUAL, display_name=path, reason=(
                'This project publishes %d ZIP archive(s) but no %s. A ZIP can contain anything, so Toolbox does not guess '
                'what is installable. Write a mapping index for it (see docs/REPOSITORY_SPEC.md) and import it.' % (archives, INDEX_FILENAME)))
        return SyncResult(Compat.UNSUPPORTED, display_name=path, reason='No %s in the default branch and no .vpk links on a release.' % INDEX_FILENAME)

    @staticmethod
    def _links(release):
        assets = release.get('assets')
        links = assets.get('links') if isinstance(assets, dict) else None
        return [l for l in links if isinstance(l, dict)] if isinstance(links, list) else []

    def _translate(self, meta, host, path, releases):
        groups, notes = {}, []
        for release in releases:
            tag = release.get('tag_name')
            try:
                version = Version.parse(tag)
            except RepoError:
                notes.append('release %r skipped: the tag is not a version number' % str(tag)[:40])
                continue
            for link in self._links(release):
                name = link.get('name')
                url = link.get('direct_asset_url') or link.get('url')
                if not isinstance(name, str) or not name.lower().endswith('.vpk') or not isinstance(url, str):
                    continue
                try:
                    url = check_https_url(url)
                except RepoError:
                    notes.append('link %s skipped: unsafe address' % name[:60])
                    continue
                if host_of(url) != host:
                    notes.append('link %s skipped: hosted on a different server (%s)' % (name[:60], host_of(url)))
                    continue
                stem = name[:-4].replace(tag, '').replace(str(version), '').strip(' ._-') or path.rsplit('/', 1)[-1]
                groups.setdefault(stem, []).append({
                    'version': str(version), 'published': (release.get('released_at') or '')[:25],
                    'changelog': release.get('description') if isinstance(release.get('description'), str) else '',
                    'prerelease': release.get('upcoming_release') is True,
                    'package': {'format': 'vpk', 'url': url, 'size': None, 'sha256': None},
                    'install': {'type': 'vpk', 'files': [{'source': ''}]}})
        if not groups:
            return None
        description = meta.get('description') if isinstance(meta.get('description'), str) else ''
        web = meta.get('web_url') if isinstance(meta.get('web_url'), str) else 'https://%s/%s' % (host, path)
        owner = path.split('/')[0]
        mods = [{'id': slug('gl-%s-%s' % (path.replace('/', '-'), stem)), 'name': stem.replace('_', ' '),
                 'summary': description[:300], 'description': description, 'author': owner,
                 'homepage': web, 'source_url': web, 'versions': versions} for stem, versions in groups.items()]
        document = {'schema': SCHEMA, 'schema_version': '1.0',
                    'repository': {'id': slug('gl-' + path.replace('/', '-')), 'name': path, 'description': description[:1000], 'homepage': web, 'maintainer': owner},
                    'mods': mods}
        index = parse_index(document, derived=True)
        reason = ('Derived from the .vpk links on GitLab releases because the author published no %s. '
                  'File sizes and hashes are not provided by GitLab, game compatibility is unknown, and nobody has reviewed these files.' % INDEX_FILENAME)
        return SyncResult(Compat.TRANSLATED, index, raw=json.dumps(document).encode('utf-8'), derived=True, reason=reason, display_name=path, warnings=tuple(notes) + index.warnings)
