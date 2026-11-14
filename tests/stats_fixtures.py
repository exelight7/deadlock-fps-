"""A scripted stand-in for api.deadlock-api.com, shaped from its published OpenAPI description (fields, types, status codes)."""
import json
import re
from urllib.parse import parse_qs, urlsplit

from deadlock_fps.repos.transport import Response, Transport

HEROES = [{'id': 1, 'name': 'Infernus', 'class_name': 'hero_inferno'}, {'id': 2, 'name': 'Seven', 'class_name': 'hero_gigawatt'},
          {'id': 3, 'name': 'Vindicta', 'class_name': 'hero_hornet'}]
RANKS = [{'tier': tier, 'name': name} for tier, name in enumerate(
    ['Obscurus', 'Initiate', 'Seeker', 'Alchemist', 'Arcanist', 'Ritualist', 'Emissary', 'Archon', 'Oracle', 'Phantom', 'Ascendant', 'Eternus'])]


def ok(payload):
    return Response(200, payload if isinstance(payload, bytes) else json.dumps(payload).encode('utf-8'), {}, '')


def status(code, **headers):
    return Response(code, b'{}', {k.lower().replace('_', '-'): v for k, v in headers.items()}, '')


def hero_row(hero_id, matches, wins, *, kills=0, deaths=0, assists=0, net_worth=0):
    return {'hero_id': hero_id, 'bucket': None, 'matches': matches, 'wins': wins, 'losses': matches - wins, 'total_kills': kills,
            'total_deaths': deaths, 'total_assists': assists, 'total_net_worth': net_worth}


def player_row(account_id, hero_id, matches, wins, *, kills=0, deaths=0, assists=0):
    return {'account_id': account_id, 'hero_id': hero_id, 'matches_played': matches, 'wins': wins, 'kills': kills, 'deaths': deaths,
            'assists': assists, 'last_played': 1790000000, 'time_played': 3600 * matches, 'matches': list(range(matches))}


def badge_row(badge, matches, players):
    return {'badge_level': badge, 'total_matches': matches, 'unique_players': players}


class FakeServer(Transport):
    """Serves the endpoints the stats engine uses. `hook(url, query)` runs first and may return a Response or an exception to raise."""

    def __init__(self):
        self.heroes = list(HEROES)
        self.ranks = list(RANKS)
        self.hero_rows = [hero_row(1, 1000, 520, kills=7000, deaths=5000, assists=9000, net_worth=30_000_000),
                          hero_row(2, 600, 270, kills=3000, deaths=3000, assists=3000, net_worth=18_000_000),
                          hero_row(3, 200, 110, kills=1500, deaths=900, assists=700, net_worth=7_000_000)]
        self.game = [{'total_matches': 1800, 'avg_duration_s': 2100.5, 'abandon_rate': 0.07, 'avg_kills': 7.0}]
        self.badges = [badge_row(11, 100, 80), badge_row(16, 50, 40), badge_row(21, 70, 60), badge_row(116, 5, 4)]
        self.ranked = {}              # account id -> rank document or an int status
        self.players = {}             # account id -> list of rows
        self.hook = None
        self.calls = []

    def queries(self, path):
        """The parsed query of every request to `path`, in order."""
        found = []
        for url in self.calls:
            parts = urlsplit(url)
            if parts.path == path:
                found.append({k: v[0] for k, v in parse_qs(parts.query, keep_blank_values=True).items()})
        return found

    def count(self, path):
        return len(self.queries(path))

    def get(self, url, *, max_bytes, headers=None, timeout=15.0):
        self.calls.append(url)
        parts = urlsplit(url)
        query = {k: v[0] for k, v in parse_qs(parts.query, keep_blank_values=True).items()}
        if self.hook:
            outcome = self.hook(url, query)
            if isinstance(outcome, Exception):
                raise outcome
            if outcome is not None:
                return outcome
        path = parts.path
        if path == '/v1/assets/heroes':
            return ok(self.heroes)
        if path == '/v1/assets/ranks':
            return ok(self.ranks)
        if path == '/v1/analytics/hero-stats':
            return ok(self.hero_rows)
        if path == '/v1/analytics/game-stats':
            return ok(self.game)
        if path == '/v1/analytics/badge-distribution':
            return ok(self.badges)
        if path == '/v1/players/hero-stats':
            rows = []
            for ident in query['account_ids'].split(','):
                rows.extend(self.players.get(int(ident), []))
            return ok(rows)
        match = re.fullmatch(r'/v1/players/(\d+)/rank', path)
        if match:
            reply = self.ranked.get(int(match.group(1)))
            if isinstance(reply, int):
                return status(reply)
            return ok(reply if reply is not None else {'badge': 0, 'rank': 0, 'subrank': 0, 'last_match': None})
        return Response(404, b'{}', {}, url)
