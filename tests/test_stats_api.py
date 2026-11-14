"""The Deadlock API client: the addresses it builds, what it sends, how it reads answers (hostile ones included) and how it fails."""
import unittest

from deadlock_fps.repos.errors import RepoError, NETWORK, NOT_FOUND, RATE_LIMITED
from deadlock_fps.repos.transport import Response
from deadlock_fps.stats import api as stats_api
from deadlock_fps.stats.api import BAD_RESPONSE, DeadlockApi, badge_range
from stats_fixtures import FakeServer, badge_row, hero_row, ok, player_row, status

NOW = 1_790_000_000 + 1234          # not on an hour boundary
HOUR_FLOOR = NOW // 3600 * 3600
NAMES = {1: 'Infernus', 2: 'Seven', 3: 'Vindicta'}


def make(server=None):
    server = server or FakeServer()
    return server, DeadlockApi(server, clock=lambda: NOW)


class AddressTests(unittest.TestCase):
    def test_the_host_is_fixed_and_https(self):
        self.assertEqual(stats_api.BASE, 'https://api.deadlock-api.com')
        server, api = make()
        api.heroes()
        self.assertTrue(server.calls[0].startswith('https://api.deadlock-api.com/v1/assets/heroes?'))

    def test_hero_names_ask_for_active_heroes_only(self):
        server, api = make()
        self.assertEqual(api.heroes(), {1: 'Infernus', 2: 'Seven', 3: 'Vindicta'})
        self.assertEqual(server.queries('/v1/assets/heroes'), [{'only_active': 'true'}])

    def test_rank_names(self):
        _, api = make()
        names = api.ranks()
        self.assertEqual((names[0], names[1], names[11]), ('Obscurus', 'Initiate', 'Eternus'))

    def test_hero_stats_scope_for_every_rank_and_mode(self):
        server, api = make()
        api.hero_stats(14, '', 0, NAMES)
        self.assertEqual(server.queries('/v1/analytics/hero-stats'), [{'min_unix_timestamp': str(HOUR_FLOOR - 14 * 86400), 'game_mode': 'normal'}])

    def test_hero_stats_scope_for_a_mode_and_a_rank(self):
        server, api = make()
        api.hero_stats(7, 'ranked', 5, NAMES)
        query = server.queries('/v1/analytics/hero-stats')[0]
        self.assertEqual((query['match_mode'], query['min_average_badge'], query['max_average_badge']), ('ranked', '51', '56'))
        self.assertEqual(query['min_unix_timestamp'], str(HOUR_FLOOR - 7 * 86400))

    def test_the_same_question_gives_the_same_address_within_an_hour(self):
        server, api = make()
        api.hero_stats(14, 'ranked', 0, NAMES)
        api.clock = lambda: NOW + 600
        api.hero_stats(14, 'ranked', 0, NAMES)
        self.assertEqual(server.calls[0], server.calls[1])

    def test_a_rank_tier_is_six_badges_wide(self):
        self.assertEqual(badge_range(1), (11, 16))
        self.assertEqual(badge_range(11), (111, 116))

    def test_game_summary_and_distribution_use_the_same_scope(self):
        server, api = make()
        api.game_summary(30, 'unranked', 2)
        api.rank_distribution(30, 'unranked', {})
        game = server.queries('/v1/analytics/game-stats')[0]
        badges = server.queries('/v1/analytics/badge-distribution')[0]
        self.assertEqual((game['match_mode'], game['min_average_badge']), ('unranked', '21'))
        self.assertNotIn('min_average_badge', badges)          # the distribution is across all ranks
        self.assertEqual(badges['match_mode'], 'unranked')

    def test_unknown_scope_is_refused_before_any_request(self):
        server, api = make()
        for args in ((3, '', 0), (14, 'bogus', 0), (14, '', 12), (14, '', -1)):
            with self.assertRaises(ValueError):
                api.hero_stats(*args, NAMES)
        self.assertEqual(server.calls, [])

    def test_user_agent_is_generic(self):
        sent = {}

        class Spy(FakeServer):
            def get(self, url, *, max_bytes, headers=None, timeout=15.0):
                sent.update(headers or {}, max_bytes=max_bytes)
                return super().get(url, max_bytes=max_bytes, headers=headers, timeout=timeout)
        _, api = make(Spy())
        api.heroes()
        self.assertEqual(sent['User-Agent'], 'DeadlockToolbox-Stats')
        self.assertEqual(sent['max_bytes'], stats_api.MAX_RESPONSE)


class ReadingTests(unittest.TestCase):
    def test_hero_rows_become_sorted_stats(self):
        _, api = make()
        heroes = api.hero_stats(14, '', 0, NAMES)
        self.assertEqual([h.name for h in heroes], ['Infernus', 'Seven', 'Vindicta'])
        top = heroes[0]
        self.assertEqual((top.matches, top.wins, top.kills, top.deaths, top.assists, top.net_worth), (1000, 520, 7000, 5000, 9000, 30_000_000))

    def test_an_unknown_hero_gets_a_numbered_name(self):
        server, api = make()
        server.hero_rows = [hero_row(77, 10, 5)]
        self.assertEqual(api.hero_stats(14, '', 0, NAMES)[0].name, '#77')

    def test_contradicting_or_empty_rows_are_dropped(self):
        server, api = make()
        server.hero_rows = [hero_row(1, 10, 11), hero_row(2, 0, 0), hero_row(0, 5, 2), hero_row(3, 20, 10), hero_row(3, 99, 1),
                            {'hero_id': 'x', 'matches': 5, 'wins': 1}, 'junk', None, 7, [1]]
        heroes = api.hero_stats(14, '', 0, NAMES)
        self.assertEqual([(h.hero_id, h.matches) for h in heroes], [(3, 20)])      # the first row for a hero wins

    def test_negative_fractional_and_boolean_numbers_are_ignored(self):
        server, api = make()
        server.hero_rows = [{'hero_id': 1, 'matches': 10, 'wins': 5, 'total_kills': -4, 'total_deaths': 2.5, 'total_assists': True, 'total_net_worth': 'x'}]
        hero = api.hero_stats(14, '', 0, NAMES)[0]
        self.assertEqual((hero.kills, hero.deaths, hero.assists, hero.net_worth), (0, 0, 0, 0))

    def test_hostile_hero_names_are_cleaned(self):
        server, api = make()
        server.heroes = [{'id': 1, 'name': 'In‮fernus\n<b>x</b>' + 'y' * 200}, {'id': 2, 'name': 5}, {'id': -3, 'name': 'Neg'}, {'id': 4}]
        names = api.heroes()
        self.assertEqual(list(names), [1])
        self.assertNotIn('‮', names[1])
        self.assertNotIn('\n', names[1])
        self.assertLessEqual(len(names[1]), 40)

    def test_a_response_that_is_not_a_list_is_a_bad_response(self):
        server, api = make()
        for body in ({'a': 1}, 'text', 5, None):
            server.hero_rows = body
            with self.assertRaises(RepoError) as caught:
                api.hero_stats(14, '', 0, NAMES)
            self.assertEqual(caught.exception.code, BAD_RESPONSE)

    def test_a_huge_list_is_cut_not_trusted(self):
        server, api = make()
        server.hero_rows = [hero_row(i, 10, 5) for i in range(1, 1500)]
        self.assertEqual(len(api.hero_stats(14, '', 0, {})), stats_api.MAX_ROWS)

    def test_game_summary(self):
        _, api = make()
        self.assertEqual(api.game_summary(14, '', 0), (1800, 2100.5, 0.07))

    def test_game_summary_accepts_one_object_and_clamps_nonsense(self):
        server, api = make()
        server.game = {'total_matches': 5, 'avg_duration_s': -4, 'abandon_rate': 7}
        self.assertEqual(api.game_summary(14, '', 0), (5, 0.0, 1.0))
        server.game = []
        self.assertEqual(api.game_summary(14, '', 0), (0, 0.0, 0.0))

    def test_distribution_groups_badges_into_tiers(self):
        _, api = make()
        shares = api.rank_distribution(14, '', api.ranks())
        self.assertEqual([(s.tier, s.name, s.matches, s.players) for s in shares],
                         [(1, 'Initiate', 150, 120), (2, 'Seeker', 70, 60), (11, 'Eternus', 5, 4)])

    def test_distribution_ignores_impossible_badges(self):
        server, api = make()
        server.badges = [badge_row(10, 5, 5), badge_row(17, 5, 5), badge_row(0, 5, 5), badge_row(121, 5, 5), badge_row(-4, 5, 5), badge_row(33, 9, 7)]
        self.assertEqual([(s.tier, s.matches) for s in api.rank_distribution(14, '', {})], [(3, 9)])

    def test_a_tier_without_a_name_gets_a_number(self):
        _, api = make()
        self.assertEqual(api.rank_distribution(14, '', {})[0].name, '#1')


class PlayerTests(unittest.TestCase):
    ACCOUNT = 123456789

    def test_rank(self):
        server, api = make()
        server.ranked[self.ACCOUNT] = {'badge': 63, 'rank': 6, 'subrank': 3, 'last_match': None}
        rank = api.player_rank(self.ACCOUNT)
        self.assertEqual((rank.badge, rank.tier, rank.subrank), (63, 6, 3))
        self.assertEqual(server.calls, ['https://api.deadlock-api.com/v1/players/123456789/rank'])

    def test_rank_derived_from_the_badge_when_the_tier_is_missing(self):
        server, api = make()
        server.ranked[self.ACCOUNT] = {'badge': 63, 'rank': 0, 'subrank': 0}
        self.assertEqual((api.player_rank(self.ACCOUNT).tier, api.player_rank(self.ACCOUNT).subrank), (6, 3))

    def test_a_player_without_a_rank_gives_none(self):
        server, api = make()
        self.assertIsNone(api.player_rank(self.ACCOUNT))            # the server answers with zeros
        server.ranked[self.ACCOUNT] = 404
        self.assertIsNone(api.player_rank(self.ACCOUNT))
        server.ranked[self.ACCOUNT] = [1, 2]
        self.assertIsNone(api.player_rank(self.ACCOUNT))

    def test_player_heroes(self):
        server, api = make()
        server.players[self.ACCOUNT] = [player_row(self.ACCOUNT, 2, 10, 4, kills=50, deaths=40, assists=30), player_row(self.ACCOUNT, 1, 30, 20)]
        heroes = api.player_heroes(self.ACCOUNT, 30, 'ranked', NAMES)
        self.assertEqual([(h.name, h.matches, h.wins) for h in heroes], [('Infernus', 30, 20), ('Seven', 10, 4)])
        query = server.queries('/v1/players/hero-stats')[0]
        self.assertEqual((query['account_ids'], query['match_mode'], query['game_mode']), ('123456789', 'ranked', 'normal'))
        self.assertEqual(query['min_unix_timestamp'], str(HOUR_FLOOR - 30 * 86400))

    def test_every_match_has_no_time_limit(self):
        server, api = make()
        api.player_heroes(self.ACCOUNT, 0, '', NAMES)
        self.assertEqual(set(server.queries('/v1/players/hero-stats')[0]), {'account_ids', 'game_mode'})

    def test_rows_about_other_players_are_dropped(self):
        server, api = make()
        server.players[self.ACCOUNT] = [player_row(self.ACCOUNT + 1, 1, 10, 5), player_row(self.ACCOUNT, 2, 10, 5), player_row('x', 3, 4, 1), player_row(self.ACCOUNT, 3, 4, 9)]
        self.assertEqual([h.hero_id for h in api.player_heroes(self.ACCOUNT, 0, '', NAMES)], [2])

    def test_account_numbers_are_checked_before_any_request(self):
        server, api = make()
        for bad in (0, -1, 2 ** 32, True, '123', 1.5, None):
            with self.assertRaises(ValueError):
                api.player_rank(bad)
            with self.assertRaises(ValueError):
                api.player_heroes(bad, 0, '', NAMES)
        self.assertEqual(server.calls, [])

    def test_unknown_window_or_mode_for_a_player(self):
        _, api = make()
        for window, mode in ((5, ''), (14, 'bogus')):
            with self.assertRaises(ValueError):
                api.player_heroes(self.ACCOUNT, window, mode, NAMES)


class FailureTests(unittest.TestCase):
    def fail_with(self, outcome):
        server, api = make()
        server.hook = lambda url, query: outcome
        return api

    def test_rate_limit(self):
        api = self.fail_with(status(429, retry_after='30'))
        with self.assertRaises(RepoError) as caught:
            api.heroes()
        self.assertEqual(caught.exception.code, RATE_LIMITED)
        self.assertIn('30', str(caught.exception))

    def test_not_found_and_server_errors(self):
        for code, expected in ((404, NOT_FOUND), (400, NETWORK), (500, NETWORK), (503, NETWORK), (301, NETWORK)):
            with self.assertRaises(RepoError, msg=str(code)) as caught:
                self.fail_with(status(code)).heroes()
            self.assertEqual(caught.exception.code, expected, code)

    def test_a_body_that_is_not_json(self):
        for body in (b'<html>nope</html>', b'', b'\xff\xfe\x00', b'{"a":'):
            with self.assertRaises(RepoError) as caught:
                self.fail_with(Response(200, body, {}, '')).heroes()
            self.assertEqual(caught.exception.code, BAD_RESPONSE)

    def test_transport_errors_pass_through(self):
        with self.assertRaises(RepoError) as caught:
            self.fail_with(RepoError(NETWORK, 'down')).heroes()
        self.assertEqual(caught.exception.code, NETWORK)

    def test_a_json_nesting_bomb_is_a_bad_response_not_a_crash(self):
        api = self.fail_with(Response(200, b'[' * 100000, {}, ''))
        with self.assertRaises(RepoError) as caught:
            api.heroes()
        self.assertEqual(caught.exception.code, BAD_RESPONSE)


if __name__ == '__main__':
    unittest.main()
