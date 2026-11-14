"""Read-only check of the stats engine against the real api.deadlock-api.com. Public endpoints only: no account number is sent.

    .venv/Scripts/python.exe scripts/dev/stats_live_check.py

Makes about ten requests (the limit is 200 a minute) and keeps the cache in a temporary folder.
"""
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from deadlock_fps.repos.transport import UrllibTransport                      # noqa: E402
from deadlock_fps.stats.api import USER_AGENT, DeadlockApi                      # noqa: E402
from deadlock_fps.stats.cache import Cache                                      # noqa: E402
from deadlock_fps.stats.source import StatsSource                               # noqa: E402

failures = []


def check(label, condition, detail=''):
    print(('ok    ' if condition else 'FAIL  ') + label + (('  ' + str(detail)) if detail != '' else ''))
    if not condition:
        failures.append(label)


with tempfile.TemporaryDirectory() as folder:
    source = StatsSource(DeadlockApi(UrllibTransport(USER_AGENT)), Cache(Path(folder) / 'stats'))
    started = time.time()

    names = source.hero_names()
    check('hero names', 20 <= len(names) <= 200, len(names))
    tiers = source.rank_names()
    check('rank names', tiers.get(1) == 'Initiate' and tiers.get(11) == 'Eternus', tiers)

    loaded = source.meta(14, 'ranked', 0)
    meta = loaded.value
    check('meta is fresh from the server', not loaded.cached and not loaded.stale)
    check('meta has heroes', len(meta.heroes) >= 20, len(meta.heroes))
    check('meta has matches', meta.total_matches > 1000, meta.total_matches)
    check('wins never exceed matches', all(h.wins <= h.matches for h in meta.heroes))
    check('pick rates add up to about twelve players a match', 10 < sum(meta.pick_rate(h) for h in meta.heroes) < 13, round(sum(meta.pick_rate(h) for h in meta.heroes), 2))
    check('no hero is called by a number', all(not h.name.startswith('#') for h in meta.heroes), [h.name for h in meta.heroes if h.name.startswith('#')])
    check('average win rate near one half', 0.45 < meta.average_win_rate < 0.55, round(meta.average_win_rate, 4))
    check('duration looks like a match', 600 < meta.average_duration_s < 7200, meta.average_duration_s)
    top = meta.heroes[0]
    print('      most played: %s  %d matches  %.1f %% win  KDA %.2f  net worth %d' % (top.name, top.matches, 100 * top.win_rate, top.kda, top.average_net_worth))

    again = source.meta(14, 'ranked', 0)
    check('the second ask comes from the cache', again.cached and again.value == meta)

    tier = source.meta(14, 'ranked', 5).value
    check('one rank tier has fewer matches than all ranks', 0 < tier.total_matches < meta.total_matches, (tier.total_matches, meta.total_matches))

    everything = source.meta(14, '', 0).value
    check('all modes have more matches than ranked only', everything.total_matches > meta.total_matches, (everything.total_matches, meta.total_matches))

    distribution = source.distribution(14, 'ranked').value
    check('distribution has many tiers', len(distribution.shares) >= 8, [s.name for s in distribution.shares])
    check('distribution players are counted', distribution.total_players > 1000, distribution.total_players)
    check('distribution tiers are named', all(not s.name.startswith('#') for s in distribution.shares))
    biggest = max(distribution.shares, key=lambda s: s.players)
    print('      biggest rank: %s  %.1f %% of players' % (biggest.name, 100 * biggest.players / distribution.total_players))

    check('finished in a sensible time', time.time() - started < 90, round(time.time() - started, 1))

print('\n%d failure(s)' % len(failures) if failures else '\nall checks passed')
sys.exit(1 if failures else 0)
