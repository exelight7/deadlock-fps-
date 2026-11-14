"""GameBanana API v11 client for the Deadlock mod catalogue.

Everything GameBanana sends is untrusted data. This module is the only place that reads its JSON: it checks the
types, bounds every string, strips control and bidirectional-override characters, turns HTML into plain text,
and builds every URL itself from numeric ids (it never follows a link out of a response). Image addresses are
kept only when they are https on a GameBanana host.

Rate limits are strict, so pages are as large as the index allows (50) and the caller (`sync`) paces requests.
"""
import json
import re
from dataclasses import replace
from html.parser import HTMLParser
from urllib.parse import urlencode, urlsplit

from ..repos.errors import RepoError, NETWORK, NOT_FOUND, RATE_LIMITED
from ..repos.urls import check_https_url
from .model import Category, IndexPage, MODEL_MOD, Profile, StoreFile, Submission

BASE = 'https://gamebanana.com/apiv11/'
GAME_ID = 20948                        # Deadlock on GameBanana
PAGE_SIZE = 50                         # the largest page the index serves
MAX_PAGE = 250
MAX_RESPONSE = 4 * 1024 * 1024
USER_AGENT = 'DeadlockToolbox-ModStore'
BAD_RESPONSE = 'bad-response'          # the server answered with something that is not the expected JSON

MAX_IMAGES = 12
MAX_TAGS = 12
MAX_FILES = 40
MAX_TEXT = 20000

SORT_OLDEST = 'Generic_Oldest'          # stable while new uploads only append: used for full crawls
SORT_LATEST_MODIFIED = 'Generic_LatestModified'

# Control characters plus the bidirectional overrides and isolates that can make a name display as something else.
# LRM/RLM marks stay: legitimate Arabic and Hebrew text uses them.
_CONTROL = re.compile(r'[\x00-\x08\x0b-\x1f\x7f‪-‮⁦-⁩]')
_SPACES = re.compile(r'\s+')
_IMAGE_FILE = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,120}\.(?:jpe?g|png|webp|gif)')
_MD5 = re.compile(r'[0-9a-fA-F]{32}')
_LICENSE = re.compile(r'creativecommons\.org/licenses/([a-z-]+)/(\d(?:\.\d)?)', re.IGNORECASE)
_HIDDEN_VISIBILITY = ('hide', 'warn')


# ---- cleaning ---------------------------------------------------------------------------------------------

def clean(value, limit=200):
    """A single-line, bounded, control-free string; '' for anything that is not text."""
    if not isinstance(value, str):
        return ''
    return _SPACES.sub(' ', _CONTROL.sub('', value)).strip()[:limit]


def to_int(value, default=0, high=2 ** 53):
    if isinstance(value, bool):
        return default
    if isinstance(value, str) and value.isascii() and value.isdigit():
        value = int(value)
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, int) and 0 <= value <= high:
        return value
    return default


def safe_url(value):
    """The normalised URL when it is https on gamebanana.com or one of its subdomains, else ''."""
    try:
        url = check_https_url(value)
    except RepoError:
        return ''
    host = (urlsplit(url).hostname or '').lower()
    return url if host == 'gamebanana.com' or host.endswith('.gamebanana.com') else ''


class _TextExtractor(HTMLParser):
    _BREAKS = frozenset(('br', 'p', 'div', 'li', 'tr', 'ul', 'ol', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr'))

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self._skip += 1
        elif tag in self._BREAKS:
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self._skip = max(0, self._skip - 1)
        elif tag in self._BREAKS:
            self.parts.append('\n')

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def plain_text(value, limit=MAX_TEXT):
    """HTML (or plain text) reduced to readable plain text: tags dropped, scripts ignored, blank runs collapsed."""
    if not isinstance(value, str) or not value:
        return ''
    extractor = _TextExtractor()
    try:
        extractor.feed(value[:limit * 4])
        extractor.close()
    except Exception:       # a malformed document must not break a listing
        return clean(value, limit)
    lines = [_SPACES.sub(' ', _CONTROL.sub('', line)).strip() for line in ''.join(extractor.parts).split('\n')]
    text = re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()
    return text[:limit]


# ---- normalisation ----------------------------------------------------------------------------------------

def _name_of(node, limit=80):
    return clean(node.get('_sName'), limit) if isinstance(node, dict) else ''


def _image_urls(media):
    """(thumbnail, images): display-size URLs, https on GameBanana only."""
    thumbnail, images = '', []
    entries = media.get('_aImages') if isinstance(media, dict) else None
    for entry in (entries if isinstance(entries, list) else [])[:MAX_IMAGES]:
        if not isinstance(entry, dict):
            continue
        base = entry.get('_sBaseUrl')
        if not isinstance(base, str):
            continue

        def build(key):
            name = entry.get(key)
            if isinstance(name, str) and _IMAGE_FILE.fullmatch(name):
                return safe_url(base.rstrip('/') + '/' + name)
            return ''

        shown = build('_sFile530') or build('_sFile')
        small = build('_sFile220') or build('_sFile100') or build('_sFile')
        if shown:
            images.append(shown)
            thumbnail = thumbnail or small or shown
    return thumbnail, tuple(images)


def _tags(raw):
    tags = []
    for tag in (raw if isinstance(raw, list) else [])[:MAX_TAGS * 2]:
        text = clean(tag.get('_sValue') or tag.get('_sName') if isinstance(tag, dict) else tag, 40)
        if text and text not in tags:
            tags.append(text)
    return tuple(tags[:MAX_TAGS])


def parse_submission(record, *, model=MODEL_MOD):
    """A Submission from one index record or profile document, or None when it is unusable."""
    if not isinstance(record, dict):
        return None
    ident = to_int(record.get('_idRow'))
    declared = record.get('_sModelName')
    if ident <= 0 or (isinstance(declared, str) and declared != model):
        return None
    name = clean(record.get('_sName'))
    if not name:
        return None
    root = record.get('_aRootCategory') or record.get('_aSuperCategory')
    sub = record.get('_aSubCategory') or record.get('_aCategory')
    submitter = record.get('_aSubmitter') if isinstance(record.get('_aSubmitter'), dict) else {}
    thumbnail, images = _image_urls(record.get('_aPreviewMedia'))
    modified = to_int(record.get('_tsDateModified'))
    added = to_int(record.get('_tsDateAdded'))
    return Submission(
        id=ident, name=name, model=model,
        category=_name_of(root), subcategory=_name_of(sub),
        author=clean(submitter.get('_sName'), 60), author_id=to_int(submitter.get('_idRow')),
        version=clean(record.get('_sVersion'), 40),
        added=added, modified=modified or added,
        has_files=record.get('_bHasFiles') is not False,   # the profile document has no flag: it lists files instead
        obsolete=record.get('_bIsObsolete') is True,
        nsfw=record.get('_sInitialVisibility') in _HIDDEN_VISIBILITY,
        thumbnail=thumbnail, images=images, tags=_tags(record.get('_aTags')),
        likes=to_int(record.get('_nLikeCount')), views=to_int(record.get('_nViewCount')),
        downloads=to_int(record.get('_nDownloadCount')))


def parse_file(entry):
    if not isinstance(entry, dict):
        return None
    ident = to_int(entry.get('_idRow'))
    name = clean(entry.get('_sFile'), 160).replace('/', '_').replace('\\', '_')
    if ident <= 0 or not name:
        return None
    md5 = entry.get('_sMd5Checksum')
    verdict = clean(entry.get('_sAvResult'), 20).lower()
    return StoreFile(
        id=ident, name=name, size=to_int(entry.get('_nFilesize')),
        md5=md5.lower() if isinstance(md5, str) and _MD5.fullmatch(md5) else '',
        added=to_int(entry.get('_tsDateAdded')), downloads=to_int(entry.get('_nDownloadCount')),
        av_clean=None if not verdict else verdict == 'clean', archived=entry.get('_bIsArchived') is True)


def _license_of(document):
    raw = document.get('_sLicense')
    match = _LICENSE.search(raw) if isinstance(raw, str) else None
    if not match:
        return ''
    return 'CC %s %s' % (match.group(1).upper(), match.group(2))


def parse_profile(document, *, model=MODEL_MOD):
    submission = parse_submission(document, model=model)
    if submission is None:
        raise RepoError(BAD_RESPONSE, 'the profile page is not a usable mod')
    raw_files = document.get('_aFiles')
    files = tuple(f for f in (parse_file(e) for e in (raw_files[:MAX_FILES] if isinstance(raw_files, list) else ())) if f)
    submission = replace(submission, has_files=bool(files))   # a profile lists its files instead of carrying a flag
    return Profile(submission, plain_text(document.get('_sText') or document.get('_sDescription')), _license_of(document), files)


def parse_categories(document):
    if not isinstance(document, list):
        raise RepoError(BAD_RESPONSE, 'the category list is not a list')
    found = []
    for entry in document[:200]:
        if not isinstance(entry, dict):
            continue
        ident, name = to_int(entry.get('_idRow')), _name_of(entry)
        if ident > 0 and name:
            found.append(Category(ident, name, to_int(entry.get('_nItemCount')), to_int(entry.get('_nCategoryCount')),
                                  entry.get('_bIsObsolete') is True))
    return tuple(found)


# ---- client -----------------------------------------------------------------------------------------------

class GameBananaClient:
    def __init__(self, transport, *, base=BASE, user_agent=USER_AGENT):
        self.transport = transport
        self.base = base
        self.user_agent = user_agent

    def _get_json(self, path, params=None):
        url = self.base + path + ('?' + urlencode(params) if params else '')
        response = self.transport.get(url, max_bytes=MAX_RESPONSE, headers={'Accept': 'application/json', 'User-Agent': self.user_agent})
        if response.status == 429:
            raise RepoError(RATE_LIMITED, 'GameBanana is rate limiting requests (retry after %s)' % (response.header('retry-after') or 'a while'))
        if response.status == 404:
            raise RepoError(NOT_FOUND, 'GameBanana has no such page')
        if response.status != 200:
            raise RepoError(NETWORK, 'GameBanana answered with HTTP %d' % response.status)
        try:
            return json.loads(response.body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            raise RepoError(BAD_RESPONSE, 'GameBanana did not return JSON') from None

    def index_page(self, page, *, newest=False):
        """One page of Deadlock mods. `newest` orders by last modification (for refreshes); the default is oldest first."""
        if not 1 <= page <= MAX_PAGE:
            raise ValueError('page must be between 1 and %d' % MAX_PAGE)
        document = self._get_json(MODEL_MOD + '/Index', {
            '_nPerpage': PAGE_SIZE, '_aFilters[Generic_Game]': GAME_ID, '_nPage': page,
            '_sSort': SORT_LATEST_MODIFIED if newest else SORT_OLDEST})
        records = document.get('_aRecords') if isinstance(document, dict) else None
        if not isinstance(records, list):
            raise RepoError(BAD_RESPONSE, 'the mod index has no record list')
        metadata = document.get('_aMetadata') if isinstance(document.get('_aMetadata'), dict) else {}
        parsed = tuple(s for s in (parse_submission(r) for r in records) if s)
        return IndexPage(parsed, to_int(metadata.get('_nRecordCount')), len(records), len(records) - len(parsed))

    def categories(self, parent=None):
        """Root categories of Deadlock, or the children of category `parent`."""
        scope = {'_idCategoryRow': parent} if parent else {'_idGameRow': GAME_ID}
        return parse_categories(self._get_json(MODEL_MOD + '/Categories', {**scope, '_sSort': 'a_to_z', '_bShowEmpty': 'true'}))

    def profile(self, mod_id):
        ident = to_int(mod_id)
        if ident <= 0:
            raise ValueError('a mod id is a positive number')
        document = self._get_json('%s/%d/ProfilePage' % (MODEL_MOD, ident))
        if not isinstance(document, dict):
            raise RepoError(BAD_RESPONSE, 'the profile page is not an object')
        profile = parse_profile(document)
        if profile.submission.id != ident:
            raise RepoError(BAD_RESPONSE, 'GameBanana answered with a different mod than requested')
        return profile
