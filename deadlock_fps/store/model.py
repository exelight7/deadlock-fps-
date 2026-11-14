"""Plain data shapes of the mod store. Immutable values with no network or disk behaviour."""
from dataclasses import dataclass

MODEL_MOD = 'Mod'


@dataclass(frozen=True)
class Submission:
    """One mod listing as the store knows it. Everything here came from an untrusted server and was cleaned on the way in."""
    id: int
    name: str
    model: str = MODEL_MOD
    category: str = ''
    subcategory: str = ''
    author: str = ''
    author_id: int = 0
    version: str = ''
    added: int = 0                 # unix seconds
    modified: int = 0
    has_files: bool = False
    obsolete: bool = False
    nsfw: bool = False             # GameBanana hides or warns on this listing for its content ratings
    thumbnail: str = ''            # https URL on a GameBanana host, or ''
    images: tuple = ()
    tags: tuple = ()
    likes: int = 0                 # the index omits counts; they arrive with a profile fetch
    views: int = 0
    downloads: int = 0
    hydrated_at: int = 0           # when the counts were last fetched; 0 = never

    @property
    def url(self):
        return 'https://gamebanana.com/mods/%d' % self.id


@dataclass(frozen=True)
class StoreFile:
    """One downloadable file of a submission. GameBanana publishes MD5 only, never SHA-256."""
    id: int
    name: str
    size: int
    md5: str                       # 32 lower-case hex digits, or ''
    added: int = 0
    downloads: int = 0
    av_clean: object = None        # True: GameBanana's scan said clean; False: it said something else; None: unknown
    archived: bool = False

    @property
    def url(self):
        return 'https://gamebanana.com/dl/%d' % self.id


@dataclass(frozen=True)
class Profile:
    submission: Submission
    text: str = ''                 # description as plain text (the HTML is never kept)
    license: str = ''              # e.g. 'CC BY-NC-ND 4.0', or '' when the page does not say
    files: tuple = ()


@dataclass(frozen=True)
class Category:
    id: int
    name: str
    items: int = 0
    children: int = 0
    obsolete: bool = False


@dataclass(frozen=True)
class IndexPage:
    submissions: tuple             # the valid Mod listings of this page
    total: int                     # what the server says the whole listing holds
    raw_count: int                 # records the page contained, valid or not
    skipped: int                   # records dropped because they were malformed or not mods


@dataclass(frozen=True)
class QueryResult:
    rows: tuple
    total: int
