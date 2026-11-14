"""Live, read-only check of the mod-store engine against GameBanana. Usage: store_live_check.py <repo root>

Runs one full catalogue download into a throwaway folder (about 125 requests, 26 MB, paced at 0.6 s), prints what it
found, then runs a second sync to show the cheap refresh path. Nothing is installed and no personal data is sent.
Use it after changing `deadlock_fps/store/`, or when GameBanana's API seems to have changed.
"""
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, sys.argv[1])

from deadlock_fps.repos import UrllibTransport
from deadlock_fps.store import Catalog, GameBananaClient, StoreSync

folder = Path(tempfile.mkdtemp(prefix='store-crawl-'))
catalog = Catalog(folder / 'catalog.sqlite')
sync = StoreSync(GameBananaClient(UrllibTransport(user_agent='DeadlockToolbox-ModStore')), catalog)
started = time.time()
last = [0]


def progress(done, total):
    if done - last[0] >= 20 or done == total:
        last[0] = done
        print('  page %d of about %d (%.0fs)' % (done, total, time.time() - started), flush=True)


print('first sync (full crawl)...', flush=True)
report = sync.sync(progress=progress)
print('report:', report)
print('elapsed: %.0fs' % (time.time() - started))
print('rows in catalogue:', catalog.count(), '| high water:', catalog.meta_int('high_water'), '| crawl_done set:', bool(catalog.meta('crawl_done')))
print('visible by default:', catalog.query(limit=1).total, '| with adult:', catalog.query(include_nsfw=True, limit=1).total,
      '| with outdated too:', catalog.query(include_nsfw=True, include_obsolete=True, limit=1).total,
      '| fileless included:', catalog.query(include_nsfw=True, include_obsolete=True, downloadable_only=False, limit=1).total)
print('categories:', catalog.categories(include_nsfw=True, include_obsolete=True))
print('top Skins subcategories:', catalog.subcategories('Skins')[:6])
print('search "doorman":', catalog.query(text='doorman', limit=1).total, '| "hud":', catalog.query(text='hud', limit=1).total)
before = time.time()
again = sync.sync()
print('second sync: mode=%s pages=%d fetched=%d complete=%s in %.1fs' % (again.mode, again.pages, again.fetched, again.complete, time.time() - before))
print('catalogue file size: %.1f MB' % ((folder / 'catalog.sqlite').stat().st_size / 1048576))
