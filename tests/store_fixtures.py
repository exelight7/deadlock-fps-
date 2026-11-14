"""Shared helpers for the mod-store tests: GameBanana-shaped documents and a fake server that pages like the real one."""
import json
import re
from urllib.parse import urlsplit, parse_qs

from deadlock_fps.repos.transport import Transport, Response

BASE_TIME = 1_700_000_000
IMAGES = 'https://images.gamebanana.com/img/ss/mods'


def image(ident, number=0):
    stem = '%x%d.jpg' % (ident, number)
    return {'_sType': 'screenshot', '_sBaseUrl': IMAGES, '_sFile': stem, '_sFile220': '220-90_' + stem, '_sFile530': '530-90_' + stem}


def record(ident, name=None, *, added=None, modified=None, category='Skins', sub='Doorman', author='Mira', files=True,
           obsolete=False, visibility='show', images=1, version='1.0', tags=None, model='Mod'):
    added = BASE_TIME + ident if added is None else added
    return {
        '_idRow': ident, '_sModelName': model, '_sName': name or 'Mod %d' % ident,
        '_sProfileUrl': 'https://gamebanana.com/mods/%d' % ident,
        '_tsDateAdded': added, '_tsDateModified': added if modified is None else modified,
        '_bHasFiles': files, '_aTags': list(tags or []),
        '_aPreviewMedia': {'_aImages': [image(ident, n) for n in range(images)]},
        '_aSubmitter': {'_idRow': 900 + ident % 7, '_sName': author},
        '_aRootCategory': {'_sName': category}, '_aSubCategory': {'_sName': sub},
        '_sVersion': version, '_bIsObsolete': obsolete, '_sInitialVisibility': visibility,
    }


def file_entry(ident=1801337, name='pak52_dir_ab12.zip', size=7493240, md5='03f6e9f9e25675d14521c84e010a33c2', av='clean', **extra):
    return {'_idRow': ident, '_sFile': name, '_nFilesize': size, '_sMd5Checksum': md5, '_sAvResult': av,
            '_sDownloadUrl': 'https://evil.example/ignored', '_nDownloadCount': 468, '_tsDateAdded': BASE_TIME, '_bIsArchived': False, **extra}


LICENSE_HTML = '<a rel="license" href="http://creativecommons.org/licenses/by-nc-nd/4.0/"><img alt="cc"></a> This work is licensed'


def profile_document(ident=711387, name='Pink Drifter', *, files=None, text='<p>Gives a <b>pink</b> retexture</p>', license_html=LICENSE_HTML):
    return {
        '_idRow': ident, '_sName': name, '_sVersion': '2.0', '_nLikeCount': 3, '_nViewCount': 988, '_nDownloadCount': 468,
        '_tsDateAdded': BASE_TIME, '_tsDateModified': BASE_TIME + 5, '_bIsObsolete': False, '_sInitialVisibility': 'show',
        '_aSuperCategory': {'_sName': 'Skins'}, '_aCategory': {'_sName': 'Drifter'},
        '_aSubmitter': {'_idRow': 55, '_sName': 'Mira'}, '_aPreviewMedia': {'_aImages': [image(ident)]},
        '_sText': text, '_sLicense': license_html, '_aFiles': [file_entry()] if files is None else files,
    }


def index_document(records, total=None):
    return {'_aMetadata': {'_nRecordCount': len(records) if total is None else total, '_nPerpage': 50, '_bIsComplete': False},
            '_aRecords': records}


def ok(payload):
    return Response(200, payload if isinstance(payload, bytes) else json.dumps(payload).encode('utf-8'), {}, '')


def status(code, **headers):
    return Response(code, b'{}', {k.lower().replace('_', '-'): v for k, v in headers.items()}, '')


class PagedGameBanana(Transport):
    """Serves Mod/Index, Mod/Categories and Mod/<id>/ProfilePage. Records are filtered by game, sorted and cut into pages.

    `hook(url, query)` runs first and may return a Response or an exception to raise (fault injection).
    """

    def __init__(self, records=(), *, game=20948):
        self.records = list(records)
        self.game = game
        self.profiles = {}
        self.categories = []
        self.hook = None
        self.calls = []

    def index_requests(self):
        """[(sort, page)] of every Mod/Index request, in order."""
        found = []
        for url in self.calls:
            parts = urlsplit(url)
            if parts.path.endswith('/Mod/Index'):
                query = {k: v[0] for k, v in parse_qs(parts.query).items()}
                found.append((query['_sSort'], int(query['_nPage'])))
        return found

    def get(self, url, *, max_bytes, headers=None, timeout=15.0):
        self.calls.append(url)
        parts = urlsplit(url)
        query = {k: v[0] for k, v in parse_qs(parts.query).items()}
        if self.hook:
            outcome = self.hook(url, query)
            if isinstance(outcome, Exception):
                raise outcome
            if outcome is not None:
                return outcome
        path = parts.path[len('/apiv11/'):]
        if path == 'Mod/Index':
            matching = self.records if query.get('_aFilters[Generic_Game]') == str(self.game) else []
            if query['_sSort'] == 'Generic_Oldest':
                ordered = sorted(matching, key=lambda r: (r['_tsDateAdded'], r['_idRow']))
            else:
                ordered = sorted(matching, key=lambda r: (r['_tsDateModified'], r['_idRow']), reverse=True)
            per, page = int(query['_nPerpage']), int(query['_nPage'])
            return ok(index_document(ordered[(page - 1) * per:page * per], total=len(matching)))
        if path == 'Mod/Categories':
            return ok(self.categories)
        match = re.fullmatch(r'Mod/(\d+)/ProfilePage', path)
        if match and int(match.group(1)) in self.profiles:
            return ok(self.profiles[int(match.group(1))])
        return Response(404, b'{}', {}, url)
