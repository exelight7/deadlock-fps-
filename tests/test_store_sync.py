"""Synchronisation: resumable crawl, incremental refresh, rate limits, cancellation and pacing."""
import tempfile
import threading
import unittest
from pathlib import Path

from deadlock_fps.repos.errors import RepoError, NETWORK
from deadlock_fps.store import Catalog, GameBananaClient, StoreSync
from store_fixtures import PagedGameBanana, record, status, ok, index_document, BASE_TIME

NOW = 1_800_000_000.0


class SyncCase(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.catalog = Catalog(Path(folder.name) / 'catalog.sqlite')
        self.pauses = []
        self.server = PagedGameBanana()
        self.stamp = NOW

    def make(self, count=120):
        self.server.records = [record(i) for i in range(1, count + 1)]
        return self.sync()

    def sync(self, **options):
        return StoreSync(GameBananaClient(self.server), self.catalog, clock=lambda: self.stamp, sleep=self.pauses.append, pause=0.25, **options)


class FullCrawl(SyncCase):
    def test_walks_every_page_oldest_first_and_records_completion(self):
        sync = self.make(120)
        self.assertTrue(sync.needs_crawl)
        report = sync.crawl()
        self.assertEqual((report.mode, report.complete, report.stopped, report.pages, report.fetched, report.total), ('crawl', True, '', 3, 120, 120))
        self.assertEqual(self.server.index_requests(), [('Generic_Oldest', 1), ('Generic_Oldest', 2), ('Generic_Oldest', 3)])
        self.assertEqual(self.catalog.count(), 120)
        self.assertFalse(sync.needs_crawl)
        self.assertEqual(self.catalog.meta_int('high_water'), BASE_TIME + 120)
        self.assertEqual(self.catalog.meta('crawl_next'), '', 'the cursor is cleared once the crawl is complete')

    def test_requests_are_paced_but_not_after_the_last_page(self):
        self.make(120).crawl()
        self.assertEqual(self.pauses, [0.25, 0.25])

    def test_an_exact_multiple_of_the_page_size_ends_on_the_empty_page(self):
        report = self.make(100).crawl()
        self.assertEqual((report.complete, report.pages, self.catalog.count()), (True, 3, 100))

    def test_an_empty_catalogue_completes_immediately(self):
        report = self.make(0).crawl()
        self.assertEqual((report.complete, report.pages, report.fetched), (True, 1, 0))

    def test_progress_reports_page_and_expected_pages(self):
        seen = []
        self.make(120).crawl(progress=lambda done, total: seen.append((done, total)))
        self.assertEqual(seen, [(1, 3), (2, 3), (3, 3)])

    def test_malformed_records_are_counted_not_fatal(self):
        sync = self.make(10)
        self.server.records.append({'_idRow': 'x'})
        self.server.records[-1].update({'_tsDateAdded': BASE_TIME + 999})
        report = sync.crawl()
        self.assertEqual((report.fetched, report.skipped, self.catalog.count()), (10, 1, 10))


class Interruptions(SyncCase):
    def test_a_rate_limit_stops_cleanly_and_the_next_call_resumes(self):
        sync = self.make(120)
        blocked = {'on': True}
        self.server.hook = lambda url, query: status(429, retry_after='60') if blocked['on'] and query['_nPage'] == '2' else None
        report = sync.crawl()
        self.assertEqual((report.stopped, report.complete, report.pages, self.catalog.count()), ('rate-limited', False, 1, 50))
        self.assertEqual(self.catalog.meta_int('crawl_next'), 2)
        self.assertTrue(sync.needs_crawl)

        blocked['on'] = False
        self.server.calls.clear()
        report = sync.crawl()
        self.assertEqual((report.complete, report.pages, self.catalog.count()), (True, 2, 120))
        self.assertEqual([page for _, page in self.server.index_requests()], [2, 3], 'resumes at page 2, never refetching page 1')

    def test_resuming_works_from_a_new_sync_object(self):
        sync = self.make(120)
        self.server.hook = lambda url, query: status(429) if query['_nPage'] == '3' else None
        self.assertEqual(sync.crawl().stopped, 'rate-limited')
        self.server.hook = None
        self.server.calls.clear()
        again = self.sync()                       # a new run of the program
        self.assertEqual(again.crawl().complete, True)
        self.assertEqual([page for _, page in self.server.index_requests()], [3])

    def test_cancel_before_start_makes_no_request(self):
        stop = threading.Event()
        stop.set()
        report = self.make(60).crawl(cancel=stop)
        self.assertEqual((report.stopped, self.server.calls, self.catalog.count()), ('cancelled', [], 0))

    def test_cancel_between_pages_keeps_what_was_saved(self):
        stop = threading.Event()
        sync = self.make(120)
        report = sync.crawl(progress=lambda done, total: stop.set(), cancel=stop)
        self.assertEqual((report.stopped, report.pages, self.catalog.count(), self.catalog.meta_int('crawl_next')), ('cancelled', 1, 50, 2))
        self.assertTrue(sync.crawl().complete)
        self.assertEqual(self.catalog.count(), 120)

    def test_other_errors_propagate_and_keep_earlier_pages(self):
        sync = self.make(120)
        self.server.hook = lambda url, query: status(503) if query['_nPage'] == '2' else None
        with self.assertRaises(RepoError) as caught:
            sync.crawl()
        self.assertEqual(caught.exception.code, NETWORK)
        self.assertEqual((self.catalog.count(), self.catalog.meta_int('crawl_next')), (50, 2))

    def test_restart_discards_the_old_cursor(self):
        sync = self.make(120)
        self.server.hook = lambda url, query: status(429) if query['_nPage'] == '2' else None
        sync.crawl()
        self.server.hook = None
        self.server.calls.clear()
        sync.crawl(restart=True)
        self.assertEqual([page for _, page in self.server.index_requests()], [1, 2, 3])


class Refresh(SyncCase):
    def crawled(self, count=120):
        sync = self.make(count)
        sync.crawl()
        self.server.calls.clear()
        self.pauses.clear()
        return sync

    def test_nothing_changed_costs_one_request(self):
        sync = self.crawled()
        report = sync.refresh()
        self.assertEqual((report.complete, report.pages, self.server.index_requests()), (True, 1, [('Generic_LatestModified', 1)]))

    def test_new_and_edited_listings_arrive_and_the_mark_advances(self):
        sync = self.crawled()
        self.server.records[4]['_sName'] = 'Renamed'
        self.server.records[4]['_tsDateModified'] = BASE_TIME + 500
        self.server.records.append(record(121, 'Brand new', added=BASE_TIME + 600))
        report = sync.refresh()
        self.assertEqual((report.complete, report.pages), (True, 1))
        self.assertEqual(self.catalog.get(5).name, 'Renamed')
        self.assertEqual(self.catalog.get(121).name, 'Brand new')
        self.assertEqual(self.catalog.meta_int('high_water'), BASE_TIME + 600)
        self.assertEqual(self.catalog.meta_int('refreshed_at'), int(NOW))

    def test_a_second_refresh_after_that_finds_nothing_new(self):
        sync = self.crawled()
        self.server.records.append(record(121, added=BASE_TIME + 600))
        sync.refresh()
        self.server.calls.clear()
        sync.refresh()
        self.assertEqual(len(self.server.index_requests()), 1)

    def test_many_changes_walk_several_pages(self):
        sync = self.crawled()
        for r in self.server.records[:70]:
            r['_tsDateModified'] = BASE_TIME + 1000 + r['_idRow']
        report = sync.refresh()
        self.assertEqual((report.complete, report.pages), (True, 2))
        self.assertEqual(self.pauses, [0.25])

    def test_too_many_changes_stop_the_refresh_and_sync_falls_back_to_a_crawl(self):
        sync = self.crawled(120)
        for r in self.server.records:
            r['_tsDateModified'] = BASE_TIME + 5000 + r['_idRow']
        limited = self.sync(refresh_page_limit=2)
        self.assertEqual((limited.refresh().stopped, limited.refresh().complete), ('page-limit', False))
        self.server.calls.clear()
        report = limited.sync()
        self.assertEqual((report.mode, report.complete), ('crawl', True))
        crawl_requests = [r for r in self.server.index_requests() if r[0] == 'Generic_Oldest']
        self.assertEqual(crawl_requests, [('Generic_Oldest', 1), ('Generic_Oldest', 2), ('Generic_Oldest', 3)], 'the restarted crawl begins at page 1')
        self.assertEqual(self.server.index_requests()[0][0], 'Generic_LatestModified', 'sync tries the cheap refresh first')
        self.assertEqual(self.catalog.meta_int('high_water'), BASE_TIME + 5120)

    def test_an_unordered_page_never_stops_the_walk_early(self):
        sync = self.crawled(10)
        known = self.catalog.meta_int('high_water')
        pages = {
            '1': [record(1, modified=known + 50), record(2, modified=known - 10), record(3, modified=known + 20)] + [record(i) for i in range(4, 51)],
            '2': [record(60, modified=known + 99)],
        }
        self.server.hook = lambda url, query: ok(index_document(pages[query['_nPage']], total=51)) if query['_sSort'] == 'Generic_LatestModified' else None
        report = sync.refresh()
        self.assertEqual((report.complete, report.pages), (True, 2), 'page 1 had a stale entry in the middle but was not sorted')
        self.assertEqual(self.catalog.meta_int('high_water'), known + 99)

    def test_a_rate_limit_leaves_the_mark_where_it_was(self):
        sync = self.crawled()
        before = self.catalog.meta_int('high_water')
        self.server.records.append(record(121, added=BASE_TIME + 600))
        self.server.hook = lambda url, query: status(429)
        report = sync.refresh()
        self.assertEqual((report.stopped, self.catalog.meta_int('high_water')), ('rate-limited', before))


class Entry(SyncCase):
    def test_sync_crawls_first_then_refreshes(self):
        sync = self.make(60)
        self.assertEqual(sync.sync().mode, 'crawl')
        self.assertEqual(sync.sync().mode, 'refresh')

    def test_an_interrupted_first_crawl_is_continued_by_sync(self):
        sync = self.make(120)
        self.server.hook = lambda url, query: status(429) if query['_nPage'] == '2' else None
        self.assertEqual(sync.sync().stopped, 'rate-limited')
        self.server.hook = None
        self.assertEqual((sync.sync().mode, self.catalog.count()), ('crawl', 120))


if __name__ == '__main__':
    unittest.main()
