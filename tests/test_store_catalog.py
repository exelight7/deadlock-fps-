"""The local catalogue: persistence, safe full-text search, filters, sorting, and recovery from a damaged file."""
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from deadlock_fps.repos.errors import RepoError
from deadlock_fps.store import Catalog
from deadlock_fps.store.gamebanana import parse_submission, parse_profile
from store_fixtures import record, profile_document


def listing(ident, name=None, **kwargs):
    return parse_submission(record(ident, name, **kwargs))


class CatalogCase(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / 'store' / 'catalog.sqlite'
        self.catalog = Catalog(self.path)

    def fill(self, *items):
        self.catalog.save_page(items, 1)

    def names(self, **query):
        return [s.name for s in self.catalog.query(**query).rows]


class Storage(CatalogCase):
    def test_round_trip_keeps_every_field(self):
        original = listing(7, 'Pink Doorman', category='Skins', sub='Doorman', author='Mira', tags=['pink', 'vfx'], images=2, version='1.2')
        self.fill(original)
        self.assertEqual(self.catalog.get(7), original)
        self.assertIsNone(self.catalog.get(8))

    def test_survives_reopening(self):
        self.fill(listing(1), listing(2))
        self.catalog.set_meta(crawl_done=123)
        reopened = Catalog(self.path)
        self.assertEqual((reopened.count(), reopened.meta_int('crawl_done')), (2, 123))

    def test_an_update_replaces_listing_facts_but_never_the_counts(self):
        self.fill(listing(1, 'Old name', version='1.0'))
        self.catalog.apply_profile(parse_profile(profile_document(1, 'Old name')), now=500)
        self.fill(listing(1, 'New name', version='2.0'))          # the index carries no counts: zeros must not erase them
        s = self.catalog.get(1)
        self.assertEqual((s.name, s.version), ('New name', '2.0'))
        self.assertEqual((s.likes, s.views, s.downloads, s.hydrated_at), (3, 988, 468, 500))
        self.assertEqual(self.catalog.count(), 1)

    def test_an_update_refreshes_the_search_index(self):
        self.fill(listing(1, 'Alpha'))
        self.fill(listing(1, 'Omega'))
        self.assertEqual(self.names(text='alpha'), [])
        self.assertEqual(self.names(text='omega'), ['Omega'])

    def test_page_and_cursor_are_saved_together(self):
        self.catalog.save_page([listing(1)], 1, crawl_next=2, crawl_total=100)
        self.assertEqual((self.catalog.count(), self.catalog.meta_int('crawl_next')), (1, 2))

    def test_meta_defaults_and_garbage(self):
        self.assertEqual(self.catalog.meta('missing', 'fallback'), 'fallback')
        self.catalog.set_meta(a='not a number', b='')
        self.assertEqual((self.catalog.meta_int('a', 9), self.catalog.meta_int('b', 4), self.catalog.meta_int('zzz', 3)), (9, 4, 3))

    def test_clear_empties_everything_including_search(self):
        self.fill(listing(1, 'Alpha'))
        self.catalog.set_meta(crawl_done=1)
        self.catalog.clear()
        self.assertEqual((self.catalog.count(), self.catalog.meta('crawl_done'), self.names(text='alpha')), (0, '', []))


class Search(CatalogCase):
    def setUp(self):
        super().setUp()
        self.fill(listing(1, 'Pink Doorman', author='Mira', category='Skins', sub='Doorman', tags=['pink']),
                  listing(2, 'Crimson Wraith', author='Zed', category='Skins', sub='Wraith'),
                  listing(3, 'Clean HUD', author='Mira', category='HUD', sub=''),
                  listing(4, 'سكن رائع', author='علي', category='Skins', sub='Wraith'))

    def test_prefix_and_case_insensitive(self):
        self.assertEqual(self.names(text='PIN', sort='name'), ['Pink Doorman'])

    def test_every_word_must_match(self):
        self.assertEqual(self.names(text='pink doorman'), ['Pink Doorman'])
        self.assertEqual(self.names(text='pink wraith'), [])

    def test_author_category_subcategory_and_tags_are_searchable(self):
        self.assertEqual(sorted(self.names(text='mira')), ['Clean HUD', 'Pink Doorman'])
        self.assertEqual(self.names(text='hud'), ['Clean HUD'])
        self.assertEqual(sorted(self.names(text='wraith')), ['Crimson Wraith', 'سكن رائع'])

    def test_arabic_text(self):
        self.assertEqual(self.names(text='رائع'), ['سكن رائع'])
        self.assertEqual(self.names(text='علي'), ['سكن رائع'])

    def test_search_syntax_is_inert(self):
        for hostile in ('"', '*', 'pink OR wraith', 'NEAR(pink wraith)', 'name:pink', 'pink)', '" OR 1=1 --', "'; DROP TABLE submission; --", '^pink'):
            try:
                self.catalog.query(text=hostile)
            except Exception as error:      # noqa: BLE001
                self.fail('%r raised %r' % (hostile, error))
        self.assertEqual(self.catalog.count(), 4)
        self.assertEqual(self.names(text='pink OR wraith'), [], 'OR is a word to match, not an operator')
        self.assertEqual(len(self.names(text='"')), 4, 'text with no words filters nothing')

    def test_like_fallback_matches_the_same_listings(self):
        self.catalog.fts = False
        self.assertEqual(self.names(text='pin'), ['Pink Doorman'])
        self.assertEqual(sorted(self.names(text='wraith')), ['Crimson Wraith', 'سكن رائع'])
        self.assertEqual(self.names(text='pink wraith'), [])

    def test_filters_combine_with_search(self):
        self.assertEqual(self.names(text='mira', category='HUD'), ['Clean HUD'])
        self.assertEqual(self.names(category='Skins', subcategory='Wraith', sort='name'), ['Crimson Wraith', 'سكن رائع'])


class Filters(CatalogCase):
    def setUp(self):
        super().setUp()
        self.fill(listing(1, 'Visible'), listing(2, 'Adult', visibility='hide'), listing(3, 'Warned', visibility='warn'),
                  listing(4, 'Old', obsolete=True), listing(5, 'No files', files=False))

    def test_default_hides_adult_obsolete_and_fileless(self):
        self.assertEqual(self.names(), ['Visible'])

    def test_each_switch_widens_the_result(self):
        self.assertEqual(sorted(self.names(include_nsfw=True)), ['Adult', 'Visible', 'Warned'])
        self.assertEqual(sorted(self.names(include_obsolete=True)), ['Old', 'Visible'])
        self.assertEqual(sorted(self.names(downloadable_only=False)), ['No files', 'Visible'])
        self.assertEqual(len(self.names(include_nsfw=True, include_obsolete=True, downloadable_only=False)), 5)

    def test_totals_ignore_paging(self):
        result = self.catalog.query(include_nsfw=True, limit=1)
        self.assertEqual((len(result.rows), result.total), (1, 3))


class Ordering(CatalogCase):
    def setUp(self):
        super().setUp()
        self.fill(listing(1, 'bravo', added=100, modified=300), listing(2, 'Alpha', added=300, modified=100), listing(3, 'charlie', added=200, modified=200))

    def test_sorts(self):
        self.assertEqual(self.names(sort='updated'), ['bravo', 'charlie', 'Alpha'])
        self.assertEqual(self.names(sort='newest'), ['Alpha', 'charlie', 'bravo'])
        self.assertEqual(self.names(sort='name'), ['Alpha', 'bravo', 'charlie'])

    def test_popularity_uses_fetched_counts(self):
        for ident, downloads in ((1, 5), (2, 50), (3, 20)):
            doc = profile_document(ident, 'x')
            doc['_nDownloadCount'], doc['_nLikeCount'] = downloads, 0
            self.catalog.apply_profile(parse_profile(doc))
        self.assertEqual(self.names(sort='popular'), ['Alpha', 'charlie', 'bravo'])

    def test_unknown_sort_falls_back_instead_of_reaching_sql(self):
        self.assertEqual(self.names(sort='name; DROP TABLE submission'), self.names(sort='updated'))
        self.assertEqual(self.catalog.count(), 3)

    def test_paging(self):
        self.assertEqual(self.names(sort='name', limit=2), ['Alpha', 'bravo'])
        self.assertEqual(self.names(sort='name', limit=2, offset=2), ['charlie'])
        self.assertEqual(self.names(sort='name', offset=99), [])
        self.assertEqual(len(self.names(limit=0)), 1, 'a limit is at least one row')
        self.assertEqual(len(self.names(limit=10 ** 9)), 3)


class Facets(CatalogCase):
    def test_counts_respect_the_default_filters(self):
        self.fill(listing(1, category='Skins', sub='Doorman'), listing(2, category='Skins', sub='Doorman'), listing(3, category='Skins', sub='Wraith'),
                  listing(4, category='HUD', sub=''), listing(5, category='Skins', sub='Wraith', visibility='hide'),
                  listing(6, category='Maps', sub='', files=False))
        self.assertEqual(self.catalog.categories(), [('Skins', 3), ('HUD', 1)])
        self.assertEqual(self.catalog.categories(include_nsfw=True), [('Skins', 4), ('HUD', 1)])
        self.assertEqual(self.catalog.subcategories('Skins'), [('Doorman', 2), ('Wraith', 1)])
        self.assertEqual(self.catalog.subcategories('HUD'), [])

    def test_latest_modified(self):
        self.assertEqual(self.catalog.latest_modified(), 0)
        self.fill(listing(1, added=5, modified=50), listing(2, added=6, modified=70))
        self.assertEqual(self.catalog.latest_modified(), 70)


class Recovery(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / 'catalog.sqlite'

    def damaged(self):
        return list(Path(self.folder.name).glob('catalog.sqlite.damaged-*'))

    def test_a_file_that_is_not_a_database_is_set_aside_and_rebuilt(self):
        self.path.write_bytes(b'this is not sqlite ' * 100)
        catalog = Catalog(self.path)
        self.assertEqual(catalog.count(), 0)
        self.assertEqual(len(self.damaged()), 1)
        catalog.save_page([listing(1)], 1)
        self.assertEqual(Catalog(self.path).count(), 1)

    def test_an_unknown_schema_version_is_set_aside_too(self):
        Catalog(self.path)
        with closing(sqlite3.connect(str(self.path))) as connection:     # a plain `with` would leave the file open (and unmovable on Windows)
            connection.execute('PRAGMA user_version = 99')
        catalog = Catalog(self.path)
        self.assertEqual(catalog.count(), 0)
        self.assertEqual(len(self.damaged()), 1)

    def test_an_unwritable_location_is_a_clean_error(self):
        blocker = Path(self.folder.name) / 'file'
        blocker.write_bytes(b'x')
        with self.assertRaises(RepoError):
            Catalog(blocker / 'inside' / 'catalog.sqlite')


if __name__ == '__main__':
    unittest.main()
