"""The disk cache and the source that combines it with the client: freshness, stale fallback, corrupt files, no personal data on disk."""
import json
import tempfile
import unittest
from pathlib import Path

from deadlock_fps.repos.errors import RepoError, NETWORK
from deadlock_fps.stats.api import DeadlockApi
from deadlock_fps.stats.cache import Cache
from deadlock_fps.stats.source import STALE_LIMIT, TTL_ANALYTICS, TTL_ASSETS, StatsSource
from stats_fixtures import FakeServer, player_row

NOW = 1_790_000_000


class Clock:
    def __init__(self, now=NOW):
        self.now = now

    def __call__(self):
        return self.now


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.clock = Clock()
        self.cache = Cache(Path(self.directory.name) / 'stats', self.clock)

    def test_a_missing_key_is_a_miss(self):
        self.assertIsNone(self.cache.get('nothing', 100))

    def test_round_trip_with_the_saved_time(self):
        self.cache.put('meta-14', {'a': [1, 2]})
        self.assertEqual(self.cache.get('meta-14', 100), ({'a': [1, 2]}, NOW))

    def test_a_copy_older_than_the_limit_is_a_miss(self):
        self.cache.put('k', 1)
        self.clock.now += 100
        self.assertEqual(self.cache.get('k', 100), (1, NOW))
        self.clock.now += 1
        self.assertIsNone(self.cache.get('k', 100))

    def test_a_copy_from_the_future_is_a_miss(self):
        self.cache.put('k', 1)
        self.clock.now -= 5
        self.assertIsNone(self.cache.get('k', 100))

    def test_unreadable_files_are_misses(self):
        self.cache.put('k', 1)
        path = self.cache.folder / 'k.json'
        for content in (b'', b'not json', b'[]', b'{"at": "x", "data": 1}', b'{"data": 1}', b'\xff\xfe', b'{"at": 1.5e400, "data": 1}'):
            path.write_bytes(content)
            self.assertIsNone(self.cache.get('k', 10 ** 12), content)

    def test_an_oversized_file_is_a_miss(self):
        self.cache.put('k', 1)
        valid_but_huge = b'{"at": %d, "data": "' % NOW + b'x' * (8 * 1024 * 1024) + b'"}'      # parses fine: only the size rule can refuse it
        (self.cache.folder / 'k.json').write_bytes(valid_but_huge)
        self.assertIsNone(self.cache.get('k', 10 ** 12))
        (self.cache.folder / 'k.json').write_bytes(b'{"at": %d, "data": "small"}' % NOW)
        self.assertEqual(self.cache.get('k', 10 ** 12), ('small', NOW))

    def test_keys_cannot_leave_the_folder(self):
        for key in ('../x', 'a/b', 'a\\b', '', '.hidden', 'A', 'x' * 100, 'a b'):
            with self.assertRaises(ValueError, msg=key):
                self.cache.get(key, 10)
            with self.assertRaises(ValueError, msg=key):
                self.cache.put(key, 1)

    def test_a_failed_write_is_silent_and_leaves_no_temporary_file(self):
        self.cache.put('k', object())                 # not JSON-serialisable
        self.assertIsNone(self.cache.get('k', 100))
        self.assertEqual([p.name for p in self.cache.folder.iterdir()], [])

    def test_a_folder_that_cannot_be_created_is_silent(self):
        blocker = Path(self.directory.name) / 'file'
        blocker.write_bytes(b'x')
        Cache(blocker / 'inside', self.clock).put('k', 1)          # no exception

    def test_writes_replace_the_old_copy_and_leave_one_file(self):
        self.cache.put('k', 1)
        self.cache.put('k', 2)
        self.assertEqual(self.cache.get('k', 100)[0], 2)
        self.assertEqual([p.name for p in self.cache.folder.iterdir()], ['k.json'])

    def test_clear_removes_every_copy(self):
        self.cache.put('a', 1)
        self.cache.put('b', 2)
        self.cache.clear()
        self.assertEqual(list(self.cache.folder.iterdir()), [])


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.clock = Clock()
        self.server = FakeServer()
        self.folder = Path(self.directory.name) / 'stats'
        self.source = StatsSource(DeadlockApi(self.server, clock=self.clock), Cache(self.folder, self.clock), self.clock)

    def test_the_first_meta_comes_from_the_server_and_has_everything(self):
        loaded = self.source.meta(14, 'ranked', 0)
        meta = loaded.value
        self.assertFalse(loaded.cached)
        self.assertFalse(loaded.stale)
        self.assertEqual((meta.window_days, meta.mode, meta.tier, meta.total_matches, meta.fetched_at), (14, 'ranked', 0, 1800, NOW))
        self.assertEqual([h.name for h in meta.heroes], ['Infernus', 'Seven', 'Vindicta'])
        self.assertAlmostEqual(meta.average_duration_s, 2100.5)
        self.assertEqual(self.server.count('/v1/assets/heroes'), 1)

    def test_a_second_ask_within_the_hour_costs_no_request(self):
        first = self.source.meta(14, 'ranked', 0).value
        calls = len(self.server.calls)
        self.clock.now += TTL_ANALYTICS - 1
        second = self.source.meta(14, 'ranked', 0)
        self.assertTrue(second.cached)
        self.assertEqual(len(self.server.calls), calls)
        self.assertEqual(second.value, first)
        self.assertEqual(second.value.fetched_at, NOW)         # shows when it was really fetched

    def test_after_the_hour_the_server_is_asked_again_but_hero_names_stay_cached(self):
        self.source.meta(14, 'ranked', 0)
        self.clock.now += TTL_ANALYTICS + 1
        self.source.meta(14, 'ranked', 0)
        self.assertEqual(self.server.count('/v1/analytics/hero-stats'), 2)
        self.assertEqual(self.server.count('/v1/assets/heroes'), 1)

    def test_hero_names_are_asked_again_after_a_day(self):
        self.source.meta(14, 'ranked', 0)
        self.clock.now += TTL_ASSETS + 1
        self.source.meta(14, 'ranked', 0)
        self.assertEqual(self.server.count('/v1/assets/heroes'), 2)

    def test_refresh_skips_the_cache(self):
        self.source.meta(14, 'ranked', 0)
        loaded = self.source.meta(14, 'ranked', 0, refresh=True)
        self.assertFalse(loaded.cached)
        self.assertEqual(self.server.count('/v1/analytics/hero-stats'), 2)

    def test_each_question_has_its_own_copy(self):
        self.source.meta(14, 'ranked', 0)
        self.source.meta(14, 'ranked', 5)
        self.source.meta(7, 'ranked', 0)
        self.source.meta(14, '', 0)
        self.assertEqual(self.server.count('/v1/analytics/hero-stats'), 4)
        self.assertEqual(self.source.meta(14, 'ranked', 5).cached, True)

    def test_the_server_down_with_an_old_copy_shows_the_copy_marked_stale(self):
        first = self.source.meta(14, 'ranked', 0).value
        self.clock.now += 5 * 86400
        self.server.hook = lambda url, query: RepoError(NETWORK, 'down')
        loaded = self.source.meta(14, 'ranked', 0)
        self.assertTrue(loaded.stale)
        self.assertEqual(loaded.error.code, NETWORK)
        self.assertEqual(loaded.value.heroes, first.heroes)
        self.assertEqual(loaded.value.fetched_at, NOW)

    def test_the_server_down_without_a_copy_is_an_error(self):
        self.server.hook = lambda url, query: RepoError(NETWORK, 'down')
        with self.assertRaises(RepoError):
            self.source.meta(14, 'ranked', 0)

    def test_a_copy_older_than_thirty_days_is_not_shown(self):
        self.source.meta(14, 'ranked', 0)
        self.clock.now += STALE_LIMIT + 10
        self.server.hook = lambda url, query: RepoError(NETWORK, 'down')
        with self.assertRaises(RepoError):
            self.source.meta(14, 'ranked', 0)

    def test_a_failed_refresh_does_not_overwrite_the_good_copy(self):
        self.source.meta(14, 'ranked', 0)
        self.server.hook = lambda url, query: RepoError(NETWORK, 'down')
        self.source.meta(14, 'ranked', 0, refresh=True)
        self.server.hook = None
        self.assertTrue(self.source.meta(14, 'ranked', 0).cached)

    def test_a_corrupt_cache_file_means_a_fresh_request_not_a_crash(self):
        self.source.meta(14, 'ranked', 0)
        (self.folder / 'meta-14-ranked-0.json').write_text('{"at": %d, "data": {"h": 5}}' % NOW)
        loaded = self.source.meta(14, 'ranked', 0)
        self.assertFalse(loaded.cached)
        self.assertEqual(len(loaded.value.heroes), 3)

    def test_a_tampered_cache_file_is_cleaned_when_read(self):
        self.source.meta(14, 'ranked', 0)
        path = self.folder / 'meta-14-ranked-0.json'
        document = json.loads(path.read_text())
        document['data']['h'] = [[1, 'In‮fernus\n', 10, 5, -1, 'x', None, 9], [2, 'Seven', 10, 11, 0, 0, 0, 0], [0, 'Zero', 5, 1, 0, 0, 0, 0], [3, 'Vindicta', 20, 10, 0, 0, 0, 0]]
        document['data']['a'] = 99
        path.write_text(json.dumps(document))
        meta = self.source.meta(14, 'ranked', 0).value
        self.assertEqual([h.hero_id for h in meta.heroes], [1, 3])
        self.assertEqual(meta.heroes[0].name, 'Infernus')
        self.assertEqual((meta.heroes[0].kills, meta.heroes[0].deaths), (0, 0))
        self.assertEqual(meta.abandon_rate, 1.0)

    def test_the_distribution_is_cached_like_the_meta(self):
        first = self.source.distribution(14, '').value
        self.assertEqual([s.name for s in first.shares], ['Initiate', 'Seeker', 'Eternus'])
        calls = len(self.server.calls)
        second = self.source.distribution(14, '')
        self.assertTrue(second.cached)
        self.assertEqual(second.value, first)
        self.assertEqual(len(self.server.calls), calls)

    def test_the_distribution_falls_back_to_a_stale_copy(self):
        self.source.distribution(14, 'ranked')
        self.clock.now += 2 * TTL_ANALYTICS
        self.server.hook = lambda url, query: RepoError(NETWORK, 'down')
        self.assertTrue(self.source.distribution(14, 'ranked').stale)


class PlayerPrivacyTests(unittest.TestCase):
    ACCOUNT = 123456789

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.clock = Clock()
        self.server = FakeServer()
        self.server.ranked[self.ACCOUNT] = {'badge': 63, 'rank': 6, 'subrank': 3}
        self.server.players[self.ACCOUNT] = [player_row(self.ACCOUNT, 1, 40, 25, kills=300, deaths=150, assists=200)]
        self.folder = Path(self.directory.name) / 'stats'
        self.source = StatsSource(DeadlockApi(self.server, clock=self.clock), Cache(self.folder, self.clock), self.clock)

    def test_a_player_has_a_rank_and_hero_rows(self):
        player = self.source.player(self.ACCOUNT, 0, '')
        self.assertEqual((player.account_id, player.rank.tier, player.rank.subrank), (self.ACCOUNT, 6, 3))
        self.assertEqual([(h.name, h.matches, h.wins) for h in player.heroes], [('Infernus', 40, 25)])

    def test_the_account_number_is_not_written_to_disk(self):
        self.source.player(self.ACCOUNT, 30, 'ranked')
        self.source.meta(14, '', 0)
        for path in self.folder.iterdir():
            self.assertNotIn(str(self.ACCOUNT), path.name)
            self.assertNotIn(str(self.ACCOUNT).encode(), path.read_bytes(), path.name)

    def test_the_account_number_is_sent_only_by_player_calls(self):
        self.source.meta(14, 'ranked', 5)
        self.source.distribution(14, '')
        self.assertFalse([u for u in self.server.calls if str(self.ACCOUNT) in u])
        self.source.player(self.ACCOUNT, 0, '')
        self.assertEqual(len([u for u in self.server.calls if str(self.ACCOUNT) in u]), 2)

    def test_a_player_without_data_is_empty_not_an_error(self):
        player = self.source.player(987654321, 0, '')
        self.assertIsNone(player.rank)
        self.assertEqual(player.heroes, ())

    def test_player_numbers_are_asked_again_every_time(self):
        self.source.player(self.ACCOUNT, 0, '')
        self.source.player(self.ACCOUNT, 0, '')
        self.assertEqual(self.server.count('/v1/players/hero-stats'), 2)


if __name__ == '__main__':
    unittest.main()
