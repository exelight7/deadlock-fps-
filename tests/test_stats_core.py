"""Stats engine, pure parts: the readers for untrusted values, the formulas, the Steam id spellings, the data shapes."""
import math
import unittest

from deadlock_fps.stats.clean import clean, to_float, to_int
from deadlock_fps.stats.maths import kda, rate, wilson
from deadlock_fps.stats.model import Distribution, HeroStat, Meta, RankShare
from deadlock_fps.stats.steam import MAX_ACCOUNT, STEAM64_BASE, SteamIdError, account_id, from_userdata_path


class CleanTests(unittest.TestCase):
    def test_text_is_single_line_bounded_and_free_of_control_and_bidi_characters(self):
        self.assertEqual(clean('  Dyna\u202emo\n\tX  '), 'Dynamo X')
        self.assertEqual(clean('a\x00b\x1bc'), 'abc')
        self.assertEqual(len(clean('x' * 500, 40)), 40)

    def test_text_keeps_arabic_and_direction_marks(self):
        self.assertEqual(clean('\u200fعربي\u200f'), '\u200fعربي\u200f')

    def test_anything_that_is_not_text_gives_empty(self):
        for value in (None, 5, 1.5, ['x'], {'a': 1}, b'x'):
            self.assertEqual(clean(value), '')

    def test_integers_accept_plain_numbers_only(self):
        self.assertEqual(to_int(7), 7)
        self.assertEqual(to_int('42'), 42)
        self.assertEqual(to_int(5.0), 5)
        for bad in (True, False, -1, 2.5, '4.2', '-3', '١٢', None, [], float('nan'), float('inf'), 2 ** 60):
            self.assertEqual(to_int(bad, -9), -9, repr(bad))

    def test_integer_upper_bound(self):
        self.assertEqual(to_int(101, 0, 100), 0)
        self.assertEqual(to_int(100, 0, 100), 100)

    def test_floats_are_finite_and_non_negative(self):
        self.assertEqual(to_float(3), 3.0)
        self.assertEqual(to_float(0.25), 0.25)
        for bad in (True, -0.5, float('nan'), float('inf'), '1.5', None, 1e20):
            self.assertEqual(to_float(bad, -1.0), -1.0, repr(bad))


class MathsTests(unittest.TestCase):
    def test_rate_never_divides_by_zero(self):
        self.assertEqual(rate(3, 4), 0.75)
        self.assertEqual(rate(5, 0), 0.0)

    def test_kda_counts_a_deathless_match_as_one_death(self):
        self.assertEqual(kda(10, 5, 5), 3.0)
        self.assertEqual(kda(4, 0, 2), 6.0)

    def test_wilson_matches_published_reference_values(self):
        low, high = wilson(3, 4)
        self.assertAlmostEqual(low, 0.3006, places=3)
        self.assertAlmostEqual(high, 0.9544, places=3)
        low, high = wilson(50, 100)
        self.assertAlmostEqual(low, 0.4038, places=3)
        self.assertAlmostEqual(high, 0.5962, places=3)

    def test_wilson_at_the_edges_stays_inside_zero_and_one(self):
        low, high = wilson(0, 10)
        self.assertEqual(low, 0.0)
        self.assertAlmostEqual(high, 0.2775, places=3)
        low, high = wilson(10, 10)
        self.assertAlmostEqual(low, 0.7225, places=3)
        self.assertEqual(high, 1.0)

    def test_wilson_with_no_matches_is_the_whole_range(self):
        self.assertEqual(wilson(0, 0), (0.0, 1.0))
        self.assertEqual(wilson(5, -3), (0.0, 1.0))

    def test_wilson_clamps_impossible_input(self):
        low, high = wilson(99, 10)
        self.assertTrue(0.0 <= low <= high <= 1.0)

    def test_more_matches_make_the_interval_narrower(self):
        small = wilson(6, 10)
        large = wilson(600, 1000)
        self.assertLess(large[1] - large[0], small[1] - small[0])

    def test_the_interval_contains_the_observed_rate(self):
        for wins, matches in ((0, 1), (1, 1), (7, 30), (300, 700)):
            low, high = wilson(wins, matches)
            self.assertLessEqual(low, wins / matches)
            self.assertGreaterEqual(high, wins / matches)
            self.assertTrue(math.isfinite(low) and math.isfinite(high))


class SteamIdTests(unittest.TestCase):
    NUMBER = 123456789

    def test_every_spelling_gives_the_same_number(self):
        spellings = ['123456789', ' 123456789 ', str(STEAM64_BASE + 123456789), '[U:1:123456789]',
                     'https://steamcommunity.com/profiles/%d' % (STEAM64_BASE + 123456789),
                     'steamcommunity.com/profiles/%d/' % (STEAM64_BASE + 123456789),
                     'https://www.steamcommunity.com/profiles/%d?l=english' % (STEAM64_BASE + 123456789),
                     'http://steamcommunity.com/profiles/123456789']
        for text in spellings:
            self.assertEqual(account_id(text), self.NUMBER, text)

    def test_integers_are_accepted_too(self):
        self.assertEqual(account_id(self.NUMBER), self.NUMBER)

    def test_a_vanity_address_is_refused_with_its_own_code(self):
        for text in ('https://steamcommunity.com/id/gaben', 'steamcommunity.com/id/gaben/'):
            with self.assertRaises(SteamIdError) as caught:
                account_id(text)
            self.assertEqual(caught.exception.code, 'vanity')

    def test_empty_and_malformed_input(self):
        for text, code in (('', 'empty'), ('   ', 'empty'), (None, 'empty'), ('abc', 'format'), ('12 34', 'format'), ('-5', 'format'),
                           ('١٢٣', 'format'), ('1e5', 'format'), ('[U:1:abc]', 'format'), ('[U:2:123]', 'format'),
                           ('https://evil.example/profiles/76561198083722517', 'format'), ('https://steamcommunity.com.evil.example/profiles/1234', 'format'),
                           ('https://steamcommunity.com/groups/x', 'format'), ('ftp://steamcommunity.com/profiles/1234', 'format')):
            with self.assertRaises(SteamIdError, msg=repr(text)) as caught:
                account_id(text)
            self.assertEqual(caught.exception.code, code, repr(text))

    def test_out_of_range_numbers(self):
        for text in ('0', str(MAX_ACCOUNT + 1), '[U:1:0]', str(STEAM64_BASE), str(STEAM64_BASE + MAX_ACCOUNT + 1), '99999999999999999999'):
            with self.assertRaises(SteamIdError, msg=text) as caught:
                account_id(text)
            self.assertEqual(caught.exception.code, 'range', text)

    def test_the_largest_account_number_is_allowed(self):
        self.assertEqual(account_id(str(MAX_ACCOUNT)), MAX_ACCOUNT)
        self.assertEqual(account_id(str(STEAM64_BASE + MAX_ACCOUNT)), MAX_ACCOUNT)

    def test_account_from_a_steam_userdata_path(self):
        base = 'C:/Program Files (x86)/Steam/userdata/%d/1422450/local/cfg/video.txt'
        self.assertEqual(from_userdata_path(base % 123456789), 123456789)
        self.assertEqual(from_userdata_path((base % 42).replace('/', '\\')), 42)
        self.assertEqual(from_userdata_path('D:/Steam/UserData/77/x'), 77)

    def test_paths_without_an_account_give_none(self):
        for path in ('', None, 'C:/Steam/userdata', 'C:/Steam/userdata/', 'C:/Steam/userdata/abc/x', 'C:/Steam/userdata/0/x',
                     'C:/Steam/userdata/99999999999/x', 'C:/Steam/other/123/x'):
            self.assertIsNone(from_userdata_path(path), repr(path))


class ModelTests(unittest.TestCase):
    def test_hero_numbers(self):
        hero = HeroStat(1, 'Infernus', 200, 110, kills=700, deaths=300, assists=500, net_worth=6_000_000)
        self.assertEqual(hero.win_rate, 0.55)
        self.assertEqual(hero.kda, 4.0)
        self.assertEqual(hero.average_net_worth, 30000.0)
        low, high = hero.interval
        self.assertLess(low, 0.55)
        self.assertGreater(high, 0.55)

    def test_a_hero_with_no_matches_does_not_divide_by_zero(self):
        hero = HeroStat(1, 'X', 0, 0)
        self.assertEqual((hero.win_rate, hero.kda, hero.average_net_worth), (0.0, 0.0, 0.0))

    def test_pick_rate_is_the_share_of_matches_the_hero_was_in(self):
        heroes = (HeroStat(1, 'A', 600, 300), HeroStat(2, 'B', 300, 100), HeroStat(3, 'C', 100, 40))
        meta = Meta(14, 'ranked', 0, 1000, 2000.0, 0.05, heroes, 1)
        self.assertEqual([meta.pick_rate(h) for h in heroes], [0.6, 0.3, 0.1])
        self.assertEqual(Meta(14, '', 0, 0, 0.0, 0.0, (), 1).pick_rate(HeroStat(1, 'A', 5, 1)), 0.0)

    def test_average_win_rate(self):
        heroes = (HeroStat(1, 'A', 600, 300), HeroStat(2, 'B', 300, 100), HeroStat(3, 'C', 100, 40))
        self.assertAlmostEqual(Meta(14, '', 0, 1000, 0.0, 0.0, heroes, 1).average_win_rate, 0.44)
        self.assertEqual(Meta(14, '', 0, 0, 0.0, 0.0, (), 1).average_win_rate, 0.0)

    def test_distribution_totals(self):
        distribution = Distribution(14, '', (RankShare(1, 'Initiate', 10, 8), RankShare(2, 'Seeker', 5, 4)), 1)
        self.assertEqual(distribution.total_players, 12)

    def test_values_are_immutable(self):
        with self.assertRaises(Exception):
            HeroStat(1, 'A', 1, 1).wins = 5


if __name__ == '__main__':
    unittest.main()
