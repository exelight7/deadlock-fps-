"""Client for the public Deadlock API (api.deadlock-api.com), written from its published OpenAPI description.

Everything the server sends is untrusted data: this module is the only place that reads its JSON. Types and sizes are
checked, text is cleaned, rows that contradict themselves (more wins than matches) are dropped, and the host is fixed in
code: no address from a response is ever fetched. The requests use the shared pinned-HTTPS transport (public addresses
only, size limits) and ask for nothing that identifies the user except, for the player calls, the account number the
user chose to look up.

Rate limits are documented as 200 requests a minute for the analytics calls and 100 a second for the player calls; one
refresh here makes at most four requests.
"""
import json
import time
from urllib.parse import urlencode

from ..repos.errors import RepoError, NETWORK, NOT_FOUND, RATE_LIMITED
from .clean import clean, to_float, to_int
from .model import HeroStat, PlayerRank, RankShare
from .steam import MAX_ACCOUNT

BASE = 'https://api.deadlock-api.com'
USER_AGENT = 'DeadlockToolbox-Stats'
MAX_RESPONSE = 4 * 1024 * 1024
BAD_RESPONSE = 'bad-response'
WINDOWS = (7, 14, 30)                  # days of matches the meta is computed over
MODES = ('', 'ranked', 'unranked')     # '' means every mode
TIERS = tuple(range(0, 12))            # 0 means every rank; 1..11 are Initiate to Eternus
MAX_ROWS = 400                         # a response never holds more heroes than this; a longer list is cut, not trusted


def badge_range(tier):
    """The average-badge range that makes up one whole rank tier (badge = tier * 10 + sub-rank, sub-ranks 1 to 6)."""
    return tier * 10 + 1, tier * 10 + 6


# ---- reading responses ----------------------------------------------------------------------------------------

def _rows(document):
    if not isinstance(document, list):
        raise RepoError(BAD_RESPONSE, 'the server answered with something that is not a list')
    return [row for row in document[:MAX_ROWS] if isinstance(row, dict)]


def parse_heroes(document):
    """{hero id: name}"""
    names = {}
    for row in _rows(document):
        ident, name = to_int(row.get('id')), clean(row.get('name'), 40)
        if ident > 0 and name:
            names[ident] = name
    return names


def parse_ranks(document):
    """{tier: name}"""
    return {tier: name for tier, name in ((to_int(r.get('tier'), -1), clean(r.get('name'), 30)) for r in _rows(document)) if tier >= 0 and name}


def hero_name(names, ident):
    return names.get(ident) or '#%d' % ident


def parse_hero_rows(document, names):
    """HeroStat rows of the whole player base. A row with more wins than matches, or none at all, is dropped."""
    heroes = {}
    for row in _rows(document):
        ident, matches, wins = to_int(row.get('hero_id')), to_int(row.get('matches')), to_int(row.get('wins'))
        if ident <= 0 or matches <= 0 or wins > matches or ident in heroes:
            continue
        heroes[ident] = HeroStat(ident, hero_name(names, ident), matches, wins, to_int(row.get('total_kills')), to_int(row.get('total_deaths')),
                                 to_int(row.get('total_assists')), to_int(row.get('total_net_worth')))
    return tuple(sorted(heroes.values(), key=lambda h: (-h.matches, h.hero_id)))


def parse_game(document):
    """(total matches, average duration in seconds, abandon rate) from the one-row game summary."""
    rows = document if isinstance(document, list) else [document]
    row = next((r for r in rows if isinstance(r, dict)), {})
    return to_int(row.get('total_matches')), to_float(row.get('avg_duration_s'), high=86400 * 2), min(1.0, to_float(row.get('abandon_rate')))


def parse_distribution(document, tier_names):
    """RankShare per tier from the per-badge rows (a tier is 6 badges: tier * 10 + 1 to tier * 10 + 6)."""
    matches, players = {}, {}
    for row in _rows(document):
        badge = to_int(row.get('badge_level'))
        tier = badge // 10
        if 1 <= tier <= 11 and 1 <= badge % 10 <= 6:
            matches[tier] = matches.get(tier, 0) + to_int(row.get('total_matches'))
            players[tier] = players.get(tier, 0) + to_int(row.get('unique_players'))
    return tuple(RankShare(t, tier_names.get(t) or '#%d' % t, matches[t], players[t]) for t in sorted(matches))


def parse_player_rank(document):
    row = document[0] if isinstance(document, list) and document else document
    if not isinstance(row, dict):
        return None
    badge, tier, sub = to_int(row.get('badge')), to_int(row.get('rank')), to_int(row.get('subrank'))
    if tier <= 0 and badge >= 10:
        tier, sub = badge // 10, badge % 10
    return PlayerRank(badge, tier, sub) if tier > 0 else None


def parse_player_heroes(document, names, account_id):
    """The player's own HeroStat rows, most played first. Rows about someone else, or with more wins than matches, are dropped."""
    heroes = {}
    for row in _rows(document):
        ident, matches, wins = to_int(row.get('hero_id')), to_int(row.get('matches_played')), to_int(row.get('wins'))
        if to_int(row.get('account_id'), -1) != account_id or ident <= 0 or matches <= 0 or wins > matches or ident in heroes:
            continue
        heroes[ident] = HeroStat(ident, hero_name(names, ident), matches, wins, to_int(row.get('kills')), to_int(row.get('deaths')), to_int(row.get('assists')))
    return tuple(sorted(heroes.values(), key=lambda h: (-h.matches, h.hero_id)))


# ---- the client -----------------------------------------------------------------------------------------------

class DeadlockApi:
    def __init__(self, transport, *, clock=time.time, base=BASE, user_agent=USER_AGENT):
        self.transport = transport
        self.clock = clock
        self.base = base
        self.user_agent = user_agent

    def _get(self, path, params=None):
        url = self.base + path + ('?' + urlencode(params) if params else '')
        response = self.transport.get(url, max_bytes=MAX_RESPONSE, headers={'Accept': 'application/json', 'User-Agent': self.user_agent})
        if response.status == 429:
            raise RepoError(RATE_LIMITED, 'the statistics server is rate limiting requests (retry after %s)' % (response.header('retry-after') or 'a while'))
        if response.status == 404:
            raise RepoError(NOT_FOUND, 'the statistics server has nothing for this request')
        if response.status != 200:
            raise RepoError(NETWORK, 'the statistics server answered with HTTP %d' % response.status)
        try:
            return json.loads(response.body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError, RecursionError):      # RecursionError: a body made of thousands of '['
            raise RepoError(BAD_RESPONSE, 'the statistics server did not return JSON') from None

    def _scope(self, window_days, mode, tier):
        if window_days not in WINDOWS or mode not in MODES or tier not in TIERS:
            raise ValueError('unknown window, mode or tier')
        # Rounded to the hour so the same question gives the same address (and the answer can be cached).
        params = {'min_unix_timestamp': int(self.clock()) // 3600 * 3600 - window_days * 86400, 'game_mode': 'normal'}
        if mode:
            params['match_mode'] = mode
        if tier:
            params['min_average_badge'], params['max_average_badge'] = badge_range(tier)
        return params

    # -- public numbers: nothing about the user is sent --

    def heroes(self):
        return parse_heroes(self._get('/v1/assets/heroes', {'only_active': 'true'}))

    def ranks(self):
        return parse_ranks(self._get('/v1/assets/ranks'))

    def hero_stats(self, window_days, mode, tier, names):
        return parse_hero_rows(self._get('/v1/analytics/hero-stats', self._scope(window_days, mode, tier)), names)

    def game_summary(self, window_days, mode, tier):
        return parse_game(self._get('/v1/analytics/game-stats', self._scope(window_days, mode, tier)))

    def rank_distribution(self, window_days, mode, tier_names):
        params = self._scope(window_days, mode, 0)
        return parse_distribution(self._get('/v1/analytics/badge-distribution', params), tier_names)

    # -- one player: the account number is sent, because that is the question --

    @staticmethod
    def _account(account_id):
        if not isinstance(account_id, int) or isinstance(account_id, bool) or not 1 <= account_id <= MAX_ACCOUNT:
            raise ValueError('an account number is a whole number between 1 and %d' % MAX_ACCOUNT)
        return account_id

    def player_rank(self, account_id):
        try:
            return parse_player_rank(self._get('/v1/players/%d/rank' % self._account(account_id)))
        except RepoError as error:
            if error.code == NOT_FOUND:
                return None                 # a player with no ranked data is not an error
            raise

    def player_heroes(self, account_id, window_days, mode, names):
        """The player's hero totals over the last `window_days` days (0 for every match they have)."""
        if window_days and window_days not in WINDOWS or mode not in MODES:
            raise ValueError('unknown window or mode')
        params = {'account_ids': self._account(account_id), 'game_mode': 'normal'}
        if window_days:
            params['min_unix_timestamp'] = int(self.clock()) // 3600 * 3600 - window_days * 86400
        if mode:
            params['match_mode'] = mode
        return parse_player_heroes(self._get('/v1/players/hero-stats', params), names, account_id)
