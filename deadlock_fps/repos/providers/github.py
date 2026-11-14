"""GitHub repositories and GitHub Releases.

Classification, strongest first. The first rule that applies wins.

1. NATIVE      `deadlock-repo.json` in the root of the default branch, or attached
               to the newest release that has one. The publisher wrote a manifest.
2. TRANSLATED  No manifest, but releases attach `.vpk` files. A VPK is Valve's own
               package format and is validated structurally before install, so a
               catalogue can be derived from release metadata. The result is
               honest about what it is: generic descriptions, no declared game
               compatibility, hashes only when GitHub reports them.
3. MANUAL      Releases attach only `.zip` archives. A zip can contain anything,
               so it is never interpreted automatically. A mapping index must be
               written by hand and imported.
4. UNSUPPORTED Nothing usable; the reason says why.

Only the first page (30) of releases is read.
"""
import json
import re
from urllib.parse import quote, unquote, urlsplit

from .base import Provider, Identity, SyncResult, INDEX_FILENAME, get_json, native_result, check_status, slug
from ..errors import RepoError, NETWORK
from ..model import Compat
from ..spec import parse_index, SCHEMA, MAX_INDEX_BYTES, MAX_PACKAGE_BYTES
from ..urls import github_identity
from ..versions import Version

API = 'https://api.github.com'
RAW = 'https://raw.githubusercontent.com'
HEADERS = {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
RELEASE_PAGE = 30


def _download_url_ok(url, owner, repo, tag, name):
    """GitHub's asset URL must be exactly the documented download path of this repository."""
    if not isinstance(url, str):
        return False
    parts = urlsplit(url)
    expected = '/%s/%s/releases/download/%s/%s' % (owner, repo, tag, name)
    return parts.scheme == 'https' and (parts.hostname or '').lower() == 'github.com' and not parts.query \
        and unquote(parts.path).lower() == expected.lower()


class GitHubProvider(Provider):
    kind = 'github'
    label = 'GitHub repository'

    def identify(self, url, hint=''):
        found = github_identity(url)
        if not found:
            return None
        owner, repo = found
        return Identity('github:%s/%s' % (owner.lower(), repo.lower()), self.kind, 'https://github.com/%s/%s' % (owner, repo), '%s/%s' % (owner, repo))

    def sync(self, source, transport, etag=''):
        owner, repo = github_identity(source.url)
        base = '%s/repos/%s/%s' % (API, owner, repo)
        response, meta = get_json(transport, base, HEADERS)
        check_status(response, 'GitHub')
        if response.status == 404:
            return SyncResult(Compat.UNSUPPORTED, reason='GitHub reports no public repository %s/%s (it may be private, renamed or misspelled).' % (owner, repo))
        if not isinstance(meta, dict):
            raise RepoError(NETWORK, 'GitHub returned an unexpected answer')
        branch = meta.get('default_branch') if isinstance(meta.get('default_branch'), str) else 'main'
        name = '%s/%s' % (owner, repo)

        # 1a. Manifest in the default branch.
        raw = '%s/%s/%s/%s/%s' % (RAW, owner, repo, quote(branch, safe='/'), INDEX_FILENAME)
        manifest = transport.get(raw, max_bytes=MAX_INDEX_BYTES, headers={'Accept': 'application/json'})
        check_status(manifest, 'raw.githubusercontent.com')
        if manifest.status == 200:
            result = native_result(manifest, derived_from=INDEX_FILENAME)
            result.display_name = result.display_name or name
            return result

        # 1b / 2 / 3. Releases.
        response, releases = get_json(transport, '%s/releases?per_page=%d' % (base, RELEASE_PAGE), HEADERS)
        check_status(response, 'GitHub')
        if response.status == 404 or not isinstance(releases, list):
            releases = []
        releases = [r for r in releases if isinstance(r, dict) and r.get('draft') is False]

        for release in releases:
            for asset in release.get('assets') or []:
                if isinstance(asset, dict) and asset.get('name') == INDEX_FILENAME and asset.get('state') == 'uploaded' \
                        and _download_url_ok(asset.get('browser_download_url'), owner, repo, release.get('tag_name'), INDEX_FILENAME):
                    fetched = transport.get(asset['browser_download_url'], max_bytes=MAX_INDEX_BYTES, headers={'Accept': 'application/octet-stream'})
                    check_status(fetched, 'GitHub')
                    if fetched.status == 200:
                        result = native_result(fetched, derived_from='the release copy of ' + INDEX_FILENAME)
                        result.display_name = result.display_name or name
                        return result

        translated = self._translate(meta, owner, repo, releases)
        if translated:
            return translated
        archives = sum(1 for r in releases for a in (r.get('assets') or []) if isinstance(a, dict) and str(a.get('name', '')).lower().endswith('.zip'))
        if archives:
            return SyncResult(Compat.MANUAL, display_name=name, reason=(
                'This repository publishes %d ZIP archive(s) but no %s. A ZIP can contain anything, so Toolbox does not guess '
                'what is installable. Write a mapping index for it (see docs/REPOSITORY_SPEC.md) and import it, or ask the author to publish one.' % (archives, INDEX_FILENAME)))
        return SyncResult(Compat.UNSUPPORTED, display_name=name, reason='No %s in the default branch and no .vpk files attached to a release.' % INDEX_FILENAME)

    def _translate(self, meta, owner, repo, releases):
        groups = {}
        notes = []
        for release in releases:
            tag = release.get('tag_name')
            if not isinstance(tag, str):
                continue
            try:
                version = Version.parse(tag)
            except RepoError:
                notes.append('release %r skipped: the tag is not a version number' % tag[:40])
                continue
            for asset in release.get('assets') or []:
                if not isinstance(asset, dict):
                    continue
                file = asset.get('name')
                size = asset.get('size')
                if not isinstance(file, str) or not file.lower().endswith('.vpk') or asset.get('state') != 'uploaded':
                    continue
                if type(size) is not int or not 0 < size <= MAX_PACKAGE_BYTES or not _download_url_ok(asset.get('browser_download_url'), owner, repo, tag, file):
                    notes.append('asset %s of %s skipped: unexpected size or address' % (file[:60], tag[:30]))
                    continue
                stem = file[:-4]
                for text in (tag, tag.lstrip('v'), str(version)):
                    stem = stem.replace(text, '')
                stem = re.sub(r'[\s._-]+$|^[\s._-]+', '', re.sub(r'[\s._-]{2,}', '-', stem)) or repo
                digest = asset.get('digest') if isinstance(asset.get('digest'), str) and re.fullmatch(r'sha256:[0-9a-fA-F]{64}', asset['digest']) else None
                entry = {
                    'version': str(version), 'published': (release.get('published_at') or '')[:25],
                    'changelog': release.get('body') if isinstance(release.get('body'), str) else '',
                    'prerelease': release.get('prerelease') is True,
                    'package': {'format': 'vpk', 'url': asset['browser_download_url'], 'size': size, 'sha256': digest[7:] if digest else None},
                    'install': {'type': 'vpk', 'files': [{'source': ''}]},
                }
                groups.setdefault(stem, []).append(entry)
        if not groups:
            return None
        description = meta.get('description') if isinstance(meta.get('description'), str) else ''
        license_id = (meta.get('license') or {}).get('spdx_id') if isinstance(meta.get('license'), dict) else ''
        html = 'https://github.com/%s/%s' % (owner, repo)
        mods = []
        for stem, versions in groups.items():
            mods.append({
                'id': slug('gh-%s-%s-%s' % (owner, repo, stem)) or slug('gh-%s-%s' % (owner, repo)),
                'name': stem.replace('_', ' '), 'summary': description[:300], 'description': description,
                'author': owner, 'license': license_id if license_id and license_id != 'NOASSERTION' else '',
                'homepage': html, 'source_url': html, 'versions': versions})
        document = {'schema': SCHEMA, 'schema_version': '1.0',
                    'repository': {'id': slug('gh-%s-%s' % (owner, repo)), 'name': '%s/%s' % (owner, repo), 'description': description[:1000], 'homepage': html, 'maintainer': owner},
                    'mods': mods}
        index = parse_index(document, derived=True)
        reason = ('Derived from the .vpk files attached to GitHub releases because the author published no %s. '
                  'Descriptions are generic, game compatibility is unknown, and nobody has reviewed these files.' % INDEX_FILENAME)
        return SyncResult(Compat.TRANSLATED, index, raw=json.dumps(document).encode('utf-8'), derived=True, reason=reason, display_name='%s/%s' % (owner, repo), warnings=tuple(notes) + index.warnings)
