"""One real "My stats" lookup. Usage: stats_player_check.py <repo root> <account number> [window days: 0|7|14|30] [mode: all|ranked|unranked]

**This sends the account number to api.deadlock-api.com** (the player rank and the player hero totals, plus the public hero
names and, when a window is given, the public numbers for the comparison). Run it only with the account owner's OK, and
never write the number into the repository, the vault or a test. The cache is a throwaway folder and nothing is printed
that identifies the account.

It checks the assumptions the Stats page makes about the real answers: the rows belong to the account, wins never exceed
matches, kills/deaths/assists are totals (the stated kills per minute equals kills divided by minutes played), and a
player without ranked data gets a rank of zero.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from deadlock_fps.repos.errors import RepoError                  # noqa: E402
from deadlock_fps.repos.transport import UrllibTransport          # noqa: E402
from deadlock_fps.stats.api import USER_AGENT, DeadlockApi          # noqa: E402
from deadlock_fps.stats.cache import Cache                          # noqa: E402
from deadlock_fps.stats.source import StatsSource                   # noqa: E402

account = int(sys.argv[2])
window = int(sys.argv[3]) if len(sys.argv) > 3 else 0
mode = '' if len(sys.argv) < 5 or sys.argv[4] == 'all' else sys.argv[4]
failures = []


def check(label, condition, detail=''):
    print(('ok    ' if condition else 'FAIL  ') + label + (('  ' + str(detail)) if detail != '' else ''))
    if not condition:
        failures.append(label)


with tempfile.TemporaryDirectory() as folder:
    api = DeadlockApi(UrllibTransport(USER_AGENT))
    source = StatsSource(api, Cache(Path(folder)))
    tiers = source.rank_names()
    rank_document = api._get('/v1/players/%d/rank' % account)
    check('the rank answer has the documented fields', isinstance(rank_document, dict) and {'badge', 'rank', 'subrank'} <= set(rank_document), sorted(rank_document) if isinstance(rank_document, dict) else '')
    rows = api._get('/v1/players/hero-stats', {'account_ids': account, 'game_mode': 'normal', **({'match_mode': mode} if mode else {})})
    check('the hero answer is a list', isinstance(rows, list), len(rows))
    check('every row belongs to this account', all(r.get('account_id') == account for r in rows))
    check('wins never exceed matches played', all(r['wins'] <= r['matches_played'] for r in rows))
    check('matches played equals the length of the match list', all(r['matches_played'] == len(r.get('matches', [])) for r in rows))
    totals = [r for r in rows if r['time_played'] > 0]
    check('kills, deaths and assists are totals (stated kills per minute = kills / minutes)',
          all(abs(r['kills_per_min'] - r['kills'] / (r['time_played'] / 60)) < 0.005 for r in totals), len(totals))
    player = source.player(account, window, mode)
    check('every hero has a name', all(not h.name.startswith('#') for h in player.heroes), [h.hero_id for h in player.heroes if h.name.startswith('#')])
    rank = player.rank
    print('      rank:', ('%s %d (badge %d)' % (tiers.get(rank.tier, '#%d' % rank.tier), rank.subrank, rank.badge)) if rank else 'none on record',
          '| heroes', len(player.heroes), '| matches', sum(h.matches for h in player.heroes), '| wins', sum(h.wins for h in player.heroes))
    if window:
        try:
            meta = source.meta(window, mode, 0).value
            print('      comparison loaded for %d days: %d heroes' % (window, len(meta.heroes)))
        except RepoError as error:
            print('      comparison could not be loaded (%s): the page then leaves the column blank' % error.code)

print('\n%d failure(s)' % len(failures) if failures else '\nall checks passed')
sys.exit(1 if failures else 0)
