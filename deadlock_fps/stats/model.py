"""Plain data shapes of the stats engine. Immutable values; the arithmetic lives in maths.py."""
from dataclasses import dataclass

from .maths import kda, rate, wilson


@dataclass(frozen=True)
class HeroStat:
    """One hero's totals over a window of matches, for everyone (the meta) or for one player."""
    hero_id: int
    name: str
    matches: int
    wins: int
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    net_worth: int = 0             # total over all matches; 0 when the source has none

    @property
    def win_rate(self):
        return rate(self.wins, self.matches)

    @property
    def kda(self):
        return kda(self.kills, self.deaths, self.assists)

    @property
    def average_net_worth(self):
        return rate(self.net_worth, self.matches)

    @property
    def interval(self):
        """The 95 % range the true win rate is likely in (a fraction pair)."""
        return wilson(self.wins, self.matches)


@dataclass(frozen=True)
class Meta:
    """What every player did on every hero in a window: the numbers behind "which heroes are strong right now"."""
    window_days: int
    mode: str                      # 'ranked', 'unranked' or '' for every mode
    tier: int                      # 1..11 for one rank tier, 0 for every rank
    total_matches: int
    average_duration_s: float
    abandon_rate: float
    heroes: tuple                  # HeroStat
    fetched_at: int                # unix seconds

    def pick_rate(self, hero):
        """The share of matches the hero was played in. Twelve players share a match, so all heroes together add up to 12 (1200 %)."""
        return rate(hero.matches, self.total_matches)

    @property
    def average_win_rate(self):
        """Over every pick: close to one half, because each match has one winning team."""
        return rate(sum(h.wins for h in self.heroes), sum(h.matches for h in self.heroes))


@dataclass(frozen=True)
class RankShare:
    tier: int
    name: str
    matches: int
    players: int


@dataclass(frozen=True)
class Distribution:
    window_days: int
    mode: str
    shares: tuple                  # RankShare, tier 1 upward
    fetched_at: int

    @property
    def total_players(self):
        return sum(s.players for s in self.shares)


@dataclass(frozen=True)
class PlayerRank:
    badge: int                     # tier * 10 + subrank
    tier: int
    subrank: int


@dataclass(frozen=True)
class Player:
    account_id: int
    rank: object                   # PlayerRank or None when the player has no ranked data
    heroes: tuple                  # HeroStat, most played first
