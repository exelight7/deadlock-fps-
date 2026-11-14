"""Keeps the local catalogue in step with GameBanana.

* `crawl` walks the whole listing oldest-first (new uploads only append, so pages do not shift under it). The page
  and the cursor are saved in one transaction, so an interruption, a rate limit or a closed window resumes at the
  next page instead of starting over.
* `refresh` reads newest-modified-first and stops at the first page that reaches what is already known. When more
  than `refresh_page_limit` pages changed (the app was not opened for a long time) it falls back to a new crawl.
* `sync` picks one of the two.

Requests are paced (`pause` seconds apart) because GameBanana's limits are strict. A 429 stops the run cleanly and
reports `stopped == 'rate-limited'`; nothing is lost and the next call continues.
"""
import math
import time
from dataclasses import dataclass

from ..repos.errors import RepoError, RATE_LIMITED
from .gamebanana import MAX_PAGE, PAGE_SIZE


@dataclass
class SyncReport:
    mode: str
    pages: int = 0
    fetched: int = 0
    skipped: int = 0
    total: int = 0
    complete: bool = False
    stopped: str = ''            # '', 'cancelled', 'rate-limited', 'page-limit'


class StoreSync:
    def __init__(self, client, catalog, *, clock=time.time, sleep=time.sleep, pause=0.6, refresh_page_limit=20):
        self.client = client
        self.catalog = catalog
        self.clock = clock
        self.sleep = sleep
        self.pause = pause
        self.refresh_page_limit = refresh_page_limit

    @property
    def needs_crawl(self):
        return not self.catalog.meta('crawl_done')

    def sync(self, progress=None, cancel=None):
        if self.needs_crawl:
            return self.crawl(progress, cancel)
        report = self.refresh(progress, cancel)
        if report.stopped == 'page-limit':
            return self.crawl(progress, cancel, restart=True)
        return report

    # ---- full crawl -------------------------------------------------------------------------------------

    def crawl(self, progress=None, cancel=None, restart=False):
        catalog = self.catalog
        if restart:
            catalog.set_meta(crawl_snapshot='', crawl_next='')
        snapshot = catalog.meta_int('crawl_snapshot')
        page = catalog.meta_int('crawl_next', 1) if snapshot else 1
        snapshot = snapshot or int(self.clock())
        report = SyncReport('crawl')
        while page <= MAX_PAGE:
            if cancel is not None and cancel.is_set():
                report.stopped = 'cancelled'
                return report
            try:
                result = self.client.index_page(page)
            except RepoError as error:
                if error.code != RATE_LIMITED:
                    raise
                report.stopped = 'rate-limited'
                return report
            last = result.raw_count < PAGE_SIZE
            catalog.save_page(result.submissions, snapshot, crawl_snapshot=snapshot, crawl_next=page + 1, crawl_total=result.total)
            report.pages += 1
            report.fetched += len(result.submissions)
            report.skipped += result.skipped
            report.total = result.total
            if progress:
                progress(page, max(page, math.ceil(result.total / PAGE_SIZE)))
            if last:
                catalog.set_meta(crawl_done=int(self.clock()), high_water=catalog.latest_modified(), crawl_snapshot='', crawl_next='')
                report.complete = True
                return report
            page += 1
            self.sleep(self.pause)
        report.stopped = 'page-limit'
        return report

    # ---- incremental refresh ----------------------------------------------------------------------------

    def refresh(self, progress=None, cancel=None):
        catalog = self.catalog
        known = catalog.meta_int('high_water')
        newest = known
        report = SyncReport('refresh')
        for page in range(1, self.refresh_page_limit + 1):
            if cancel is not None and cancel.is_set():
                report.stopped = 'cancelled'
                return report
            try:
                result = self.client.index_page(page, newest=True)
            except RepoError as error:
                if error.code != RATE_LIMITED:
                    raise
                report.stopped = 'rate-limited'
                return report
            catalog.save_page(result.submissions, int(self.clock()))
            report.pages += 1
            report.fetched += len(result.submissions)
            report.skipped += result.skipped
            report.total = result.total
            stamps = [s.modified for s in result.submissions]
            newest = max([newest, *stamps])
            if progress:
                progress(page, self.refresh_page_limit)
            ordered = all(a >= b for a, b in zip(stamps, stamps[1:]))
            if result.raw_count < PAGE_SIZE or not stamps or (ordered and min(stamps) < known):
                catalog.set_meta(high_water=newest, refreshed_at=int(self.clock()))
                report.complete = True
                return report
            self.sleep(self.pause)
        report.stopped = 'page-limit'
        return report
