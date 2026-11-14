"""The statistics the pages show: a fresh copy from disk when one is young, otherwise from the server, and an older
copy (marked as such) when the server cannot be reached.

Public numbers (the meta, the rank distribution, the hero and rank names) are cached. A player's own numbers are not:
they are fetched when the user asks and kept only in memory.
"""
import time
from dataclasses import dataclass

from ..repos.errors import RepoError
from .clean import clean, to_float, to_int
from .model import Distribution, HeroStat, Meta, Player, RankShare

TTL_ANALYTICS = 3600              # the meta moves slowly; an hour is fresh
TTL_ASSETS = 24 * 3600            # hero and rank names change with game updates only
STALE_LIMIT = 30 * 24 * 3600      # an older copy than this is not shown even when the server is down


@dataclass(frozen=True)
class Loaded:
    value: object
    error: object = None          # the RepoError that stopped a refresh, when `value` is an older copy
    cached: bool = False          # the value came from disk, not from the server just now

    @property
    def stale(self):
        return self.error is not None


# ---- what is written to disk, and how it is read back (the file is as untrusted as the server) -----------------

def _key(*parts):
    return '-'.join(str(p) if p != '' else 'all' for p in parts)


def _encode_meta(meta):
    return {'w': meta.window_days, 'm': meta.mode, 't': meta.tier, 'n': meta.total_matches, 'd': meta.average_duration_s, 'a': meta.abandon_rate,
            'h': [[h.hero_id, h.name, h.matches, h.wins, h.kills, h.deaths, h.assists, h.net_worth] for h in meta.heroes]}


def _decode_meta(data, saved):
    heroes = []
    for ident, name, matches, wins, kills, deaths, assists, net_worth in data['h'][:400]:
        ident, matches, wins = to_int(ident), to_int(matches), to_int(wins)
        if ident > 0 and matches > 0 and wins <= matches:
            heroes.append(HeroStat(ident, clean(name, 40) or '#%d' % ident, matches, wins, to_int(kills), to_int(deaths), to_int(assists), to_int(net_worth)))
    return Meta(to_int(data['w']), clean(data['m'], 12), to_int(data['t']), to_int(data['n']), to_float(data['d']), min(1.0, to_float(data['a'])), tuple(heroes), saved)


def _encode_distribution(distribution):
    return {'w': distribution.window_days, 'm': distribution.mode, 's': [[s.tier, s.name, s.matches, s.players] for s in distribution.shares]}


def _decode_distribution(data, saved):
    shares = [RankShare(to_int(t), clean(name, 30) or '#%d' % to_int(t), to_int(matches), to_int(players)) for t, name, matches, players in data['s'][:20] if to_int(t) > 0]
    return Distribution(to_int(data['w']), clean(data['m'], 12), tuple(shares), saved)


def _encode_names(names):
    return [[ident, name] for ident, name in sorted(names.items())]


def _decode_names(data, saved):
    names = {to_int(ident): clean(name, 40) for ident, name in data[:400]}
    names.pop(0, None)
    return {ident: name for ident, name in names.items() if name} or None


class StatsSource:
    def __init__(self, api, cache, clock=time.time):
        self.api = api
        self.cache = cache
        self.clock = clock

    def _through(self, key, ttl, fetch, encode, decode, refresh):
        if not refresh:
            fresh = self._read(key, ttl, decode)
            if fresh is not None:
                return Loaded(fresh, cached=True)
        try:
            value = fetch()
        except RepoError as error:
            old = self._read(key, STALE_LIMIT, decode)
            if old is None:
                raise
            return Loaded(old, error, cached=True)
        self.cache.put(key, encode(value))
        return Loaded(value)

    def _read(self, key, ttl, decode):
        hit = self.cache.get(key, ttl)
        if hit is None:
            return None
        try:
            return decode(*hit)
        except (KeyError, IndexError, TypeError, ValueError):
            return None

    # ---- names (small, cached for a day) ----

    def hero_names(self, refresh=False):
        return self._through('hero-names', TTL_ASSETS, self.api.heroes, _encode_names, _decode_names, refresh).value

    def rank_names(self, refresh=False):
        return self._through('rank-names', TTL_ASSETS, self.api.ranks, _encode_names, _decode_names, refresh).value

    # ---- the public numbers ----

    def meta(self, window_days, mode, tier, refresh=False):
        def fetch():
            names = self.hero_names(refresh)
            heroes = self.api.hero_stats(window_days, mode, tier, names)
            total, duration, abandon = self.api.game_summary(window_days, mode, tier)
            return Meta(window_days, mode, tier, total, duration, abandon, heroes, int(self.clock()))
        return self._through(_key('meta', window_days, mode, tier), TTL_ANALYTICS, fetch, _encode_meta, _decode_meta, refresh)

    def distribution(self, window_days, mode, refresh=False):
        def fetch():
            shares = self.api.rank_distribution(window_days, mode, self.rank_names(refresh))
            return Distribution(window_days, mode, shares, int(self.clock()))
        return self._through(_key('ranks', window_days, mode), TTL_ANALYTICS, fetch, _encode_distribution, _decode_distribution, refresh)

    # ---- what is already on disk: never touches the network, so a page can show it the moment it opens ----

    def cached_meta(self, window_days, mode, tier):
        value = self._read(_key('meta', window_days, mode, tier), TTL_ANALYTICS, _decode_meta)
        return Loaded(value, cached=True) if value is not None else None

    def cached_distribution(self, window_days, mode):
        value = self._read(_key('ranks', window_days, mode), TTL_ANALYTICS, _decode_distribution)
        return Loaded(value, cached=True) if value is not None else None

    def cached_rank_names(self):
        return self._read('rank-names', TTL_ASSETS, _decode_names) or {}

    # ---- one player (never written to disk) ----

    def player(self, account_id, window_days, mode):
        names = self.hero_names()
        rank = self.api.player_rank(account_id)
        heroes = self.api.player_heroes(account_id, window_days, mode, names)
        return Player(account_id, rank, heroes)
