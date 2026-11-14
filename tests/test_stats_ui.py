"""The Stats page and its service, driven offscreen against a fake Deadlock API."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import QApplication, QLabel, QWidget

from deadlock_fps.repos.errors import RepoError, NETWORK
from deadlock_fps.stats_service import StatsService
from deadlock_fps.shell.components import Bar
from deadlock_fps.pages.stats import StatsPage, NumberItem, failure_text, account_problem, percent, verdict_color
from stats_fixtures import FakeServer, hero_row, player_row, status

ACCOUNT = 123456789
STEAM64 = ACCOUNT + 76561197960265728


class StatsCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.server = FakeServer()
        self.own = None
        self.make()

    def make(self):
        self.service = StatsService(self.folder / 'stats', transport=self.server)
        self.page = StatsPage(QWidget(), self.service, lambda: self.own)
        self.addCleanup(self.page.deleteLater)

    def settle(self):
        for _ in range(4):
            QThreadPool.globalInstance().waitForDone()
            self.app.processEvents()

    def load(self):
        self.page.load()
        self.settle()

    def hero_names(self):
        return [self.page.hero_table.item(row, 0).text() for row in range(self.page.hero_table.rowCount())]

    def column(self, table, column):
        return [table.item(row, column).text().replace('‎', '') for row in range(table.rowCount())]

    def look_up(self, text=str(ACCOUNT)):
        self.page.account_field.setText(text)
        self.page.look_up()
        self.settle()


class OpeningTests(StatsCase):
    def test_opening_the_page_asks_the_server_for_nothing(self):
        self.assertEqual(self.server.calls, [])
        self.assertEqual(self.page.hero_table.rowCount(), 0)
        self.assertFalse(self.page.hero_empty.isHidden())
        self.assertEqual(self.page.load_button.text(), 'Load statistics')
        self.assertTrue(self.page.load_button.isEnabled())
        self.assertIn('Nothing is loaded', self.page.status.text())

    def test_the_default_choice_is_two_weeks_of_ranked_for_every_rank(self):
        self.assertEqual(self.page.choice(), (14, 'ranked', 0))

    def test_the_rank_filter_has_numbered_names_until_the_server_gives_real_ones(self):
        self.assertEqual([self.page.tier_box.itemText(i) for i in (0, 1, 11)], ['All ranks', 'Rank 1', 'Rank 11'])

    def test_the_page_says_what_is_sent(self):
        self.assertIn('nothing about you', self.page.note.text())
        self.assertIn('api.deadlock-api.com', self.page.note.text())


class LoadingTests(StatsCase):
    def test_loading_fills_the_hero_table_most_played_first(self):
        self.load()
        self.assertEqual(self.hero_names(), ['Infernus', 'Seven', 'Vindicta'])
        self.assertEqual(self.column(self.page.hero_table, 1), ['1,000', '600', '200'])
        self.assertTrue(self.page.hero_empty.isHidden())

    def test_the_numbers_in_a_row_are_the_right_ones(self):
        self.load()
        row = [self.page.hero_table.item(0, c).text().replace('‎', '') for c in range(7)]
        self.assertEqual(row[0], 'Infernus')
        self.assertEqual(row[2], '55.6 %')                       # 1000 of 1800 matches
        self.assertEqual(row[3], '52.0 %')
        self.assertRegex(row[4], r'^48\.\d – 55\.\d %$')          # the 95 % range around 52 %
        self.assertEqual(row[5], '3.20')                          # (7000 + 9000) / 5000
        self.assertEqual(row[6], '30,000')                        # 30 000 000 / 1000

    def test_the_status_line_says_what_was_loaded_and_when(self):
        self.load()
        text = self.page.status.text()
        for part in ('Last 14 days', 'Ranked', 'All ranks', '1,800', 'Updated'):
            self.assertIn(part, text)
        self.assertNotIn('saved copy', text)
        self.assertEqual(self.page.load_button.text(), 'Refresh')

    def test_the_summary_above_the_table(self):
        self.load()
        summary = self.page.summary.text().replace('‎', '')
        for part in ('1,800 matches', 'average length 35 min', 'abandon rate 7.0 %'):
            self.assertIn(part, summary)

    def test_the_server_receives_only_the_choice(self):
        self.load()
        text = ' '.join(self.server.calls)
        self.assertNotIn(str(ACCOUNT), text)
        self.assertNotIn('account', text)
        query = self.server.queries('/v1/analytics/hero-stats')[0]
        self.assertEqual(set(query), {'min_unix_timestamp', 'game_mode', 'match_mode'})

    def test_the_rank_filter_gets_the_real_names(self):
        self.load()
        self.assertEqual([self.page.tier_box.itemText(i) for i in (0, 1, 11)], ['All ranks', 'Initiate', 'Eternus'])

    def test_the_ranks_tab(self):
        self.load()
        table = self.page.rank_table
        self.assertEqual(self.column(table, 0), ['Initiate', 'Seeker', 'Eternus'])
        self.assertEqual(self.column(table, 1), ['120', '60', '4'])
        shown = [table.cellWidget(row, 2).findChild(QLabel).text().replace('‎', '') for row in range(3)]
        self.assertEqual(shown, ['65.2 %', '32.6 %', '2.2 %'])                                    # 120, 60 and 4 of 184 players
        bars = [table.cellWidget(row, 2).findChild(Bar).value for row in range(3)]
        self.assertEqual(bars[0], 1.0)                                                           # the widest bar is the biggest rank
        self.assertGreater(bars[0], bars[1])
        self.assertGreater(bars[1], bars[2])
        self.assertIn('184', self.page.rank_summary.text())
        self.assertTrue(self.page.rank_empty.isHidden())

    def test_a_failed_distribution_leaves_the_heroes_working(self):
        self.server.hook = lambda url, query: status(500) if url.startswith('https://api.deadlock-api.com/v1/analytics/badge') else None
        self.load()
        self.assertEqual(len(self.hero_names()), 3)
        self.assertEqual(self.page.rank_table.rowCount(), 0)
        self.assertFalse(self.page.rank_empty.isHidden())

    def test_hero_search_filters_and_keeps_the_data(self):
        self.load()
        self.page.search.setText('sev')
        self.assertEqual(self.hero_names(), ['Seven'])
        self.page.search.setText('nobody')
        self.assertEqual(self.hero_names(), [])
        self.assertFalse(self.page.hero_empty.isHidden())
        self.page.search.setText('')
        self.assertEqual(len(self.hero_names()), 3)

    def test_sorting_is_numeric_not_alphabetical(self):
        self.server.hero_rows = [hero_row(1, 9, 5), hero_row(2, 100, 50), hero_row(3, 1000, 500)]
        self.load()
        table = self.page.hero_table
        table.sortByColumn(1, Qt.AscendingOrder)
        self.assertEqual(self.column(table, 1), ['9', '100', '1,000'])
        table.sortByColumn(1, Qt.DescendingOrder)
        self.assertEqual(self.column(table, 1), ['1,000', '100', '9'])

    def test_sorting_by_the_range_puts_well_established_heroes_first(self):
        self.server.hero_rows = [hero_row(1, 4, 3), hero_row(2, 4000, 2400)]          # 75 % of 4 matches against 60 % of 4000
        self.load()
        self.page.hero_table.sortByColumn(4, Qt.DescendingOrder)
        self.assertEqual(self.hero_names(), ['Seven', 'Infernus'])

    def test_a_sort_survives_a_reload(self):
        self.load()
        self.page.hero_table.sortByColumn(3, Qt.AscendingOrder)
        order = self.hero_names()
        self.load()
        self.assertEqual(self.hero_names(), order)

    def test_clear_wins_are_green_clear_losses_red_and_close_ones_plain(self):
        self.assertIsNotNone(verdict_color(0.52, 0.58))
        self.assertIsNotNone(verdict_color(0.41, 0.48))
        self.assertNotEqual(verdict_color(0.52, 0.58).name(), verdict_color(0.41, 0.48).name())
        self.assertIsNone(verdict_color(0.47, 0.55))
        self.server.hero_rows = [hero_row(1, 8000, 5000), hero_row(2, 8000, 3000), hero_row(3, 20, 11)]
        self.load()
        colors = {self.page.hero_table.item(r, 0).text(): self.page.hero_table.item(r, 3).foreground().color().name() for r in range(3)}
        self.assertNotEqual(colors['Infernus'], colors['Seven'])
        self.assertEqual(colors['Vindicta'], self.page.hero_table.item(0, 1).foreground().color().name())       # default colour

    def test_names_from_the_server_are_shown_as_plain_text(self):
        self.server.heroes = [{'id': 1, 'name': '<b>Infernus</b>‮'}, {'id': 2, 'name': 'Seven'}, {'id': 3, 'name': 'Vindicta'}]
        self.load()
        shown = self.page.hero_table.item(0, 0).text()
        self.assertEqual(shown, '<b>Infernus</b>')
        self.assertNotIn('‮', shown)


class ChoiceTests(StatsCase):
    def test_a_loaded_choice_is_shown_again_without_a_request(self):
        self.load()
        calls = len(self.server.calls)
        self.page.mode_box.setCurrentIndex(self.page.mode_box.findData(''))
        self.assertEqual(self.hero_names(), [])
        self.assertIn('Nothing is loaded for this choice', self.page.status.text())
        self.assertEqual(self.page.load_button.text(), 'Load statistics')
        self.page.mode_box.setCurrentIndex(self.page.mode_box.findData('ranked'))
        self.assertEqual(len(self.hero_names()), 3)
        self.assertIn('saved copy', self.page.status.text())
        self.assertEqual(len(self.server.calls), calls)

    def test_changing_the_choice_never_starts_a_request(self):
        for index in range(self.page.window_box.count()):
            self.page.window_box.setCurrentIndex(index)
        for index in range(self.page.tier_box.count()):
            self.page.tier_box.setCurrentIndex(index)
        self.settle()
        self.assertEqual(self.server.calls, [])

    def test_the_rank_choice_is_sent_as_a_badge_range(self):
        self.load()
        self.page.tier_box.setCurrentIndex(self.page.tier_box.findData(5))
        self.load()
        query = self.server.queries('/v1/analytics/hero-stats')[-1]
        self.assertEqual((query['min_average_badge'], query['max_average_badge']), ('51', '56'))
        self.assertIn(self.page.tier_box.currentText(), self.page.status.text())

    def test_a_new_page_shows_what_an_earlier_one_saved(self):
        self.load()
        calls = len(self.server.calls)
        self.make()
        self.assertEqual(len(self.hero_names()), 3)
        self.assertIn('saved copy', self.page.status.text())
        self.assertEqual(self.page.load_button.text(), 'Refresh')
        self.assertEqual(len(self.server.calls), calls, 'opening the page again costs nothing')
        self.assertEqual(self.page.tier_box.itemText(1), 'Initiate', 'the saved rank names are used too')

    def test_an_answer_to_an_older_question_is_dropped(self):
        self.page.load()                                                 # asks for 14 days of ranked
        self.page.window_box.setCurrentIndex(self.page.window_box.findData(30))     # then the user changes their mind
        self.settle()
        self.assertEqual(self.hero_names(), [])
        self.assertIn('Nothing is loaded for this choice', self.page.status.text())
        self.assertEqual(self.page.load_button.text(), 'Load statistics')
        self.assertTrue(self.page.load_button.isEnabled())

    def test_refresh_asks_the_server_again(self):
        self.load()
        before = self.server.count('/v1/analytics/hero-stats')
        self.load()
        self.assertEqual(self.server.count('/v1/analytics/hero-stats'), before + 1)


class FailureTests(StatsCase):
    def test_the_server_down_is_explained_and_nothing_breaks(self):
        self.server.hook = lambda url, query: status(503)
        self.load()
        self.assertIn('Could not reach the statistics server.', self.page.status.text())
        self.assertEqual(self.hero_names(), [])
        self.assertFalse(self.service.busy)
        self.assertTrue(self.page.load_button.isEnabled())
        self.server.hook = None
        self.load()
        self.assertEqual(len(self.hero_names()), 3)

    def test_a_rate_limit_asks_for_patience(self):
        self.server.hook = lambda url, query: status(429, retry_after='60')
        self.load()
        self.assertIn('slow down', self.page.status.text())

    def test_refreshing_while_the_server_is_down_keeps_the_saved_numbers_and_says_so(self):
        self.load()
        self.server.hook = lambda url, query: RepoError(NETWORK, 'connection reset')
        self.load()
        self.assertEqual(len(self.hero_names()), 3)
        text = self.page.status.text()
        self.assertIn('saved earlier', text)
        self.assertIn('connection reset', text)

    def test_garbage_from_the_server_is_a_message_not_a_crash(self):
        self.server.hero_rows = 'surprise'
        self.load()
        self.assertIn('does not understand', self.page.status.text())
        self.assertFalse(self.service.busy)

    def test_failure_text_names_the_cause(self):
        for code, word in (('rate-limited', 'slow down'), ('network', 'Could not reach'), ('bad-response', 'does not understand'),
                           ('not-found', 'nothing for this request'), ('too-large', 'more data'), ('weird', 'Something went wrong')):
            self.assertIn(word, failure_text(code, 'detail'))
        self.assertIn('detail', failure_text('network', 'detail'))

    def test_only_one_load_runs_at_a_time(self):
        self.assertTrue(self.service.load_overview(14, 'ranked', 0, False, lambda o: None, lambda m, c: None))
        self.assertFalse(self.service.load_overview(14, 'ranked', 0, False, lambda o: None, lambda m, c: None))
        self.assertFalse(self.service.load_player(ACCOUNT, 14, 'ranked', lambda o: None, lambda m, c: None))
        self.settle()
        self.assertFalse(self.service.busy)
        self.assertTrue(self.service.load_overview(14, 'ranked', 0, False, lambda o: None, lambda m, c: None))
        self.settle()

    def test_buttons_are_disabled_while_a_load_runs(self):
        self.page.load()
        self.assertTrue(self.service.busy)
        self.assertFalse(self.page.load_button.isEnabled())
        self.assertFalse(self.page.look_button.isEnabled())
        self.settle()
        self.assertTrue(self.page.load_button.isEnabled())
        self.assertTrue(self.page.look_button.isEnabled())


class MyStatsTests(StatsCase):
    def setUp(self):
        super().setUp()
        self.server.ranked[ACCOUNT] = {'badge': 63, 'rank': 6, 'subrank': 3, 'last_match': None}
        self.server.players[ACCOUNT] = [player_row(ACCOUNT, 1, 40, 25, kills=300, deaths=150, assists=200), player_row(ACCOUNT, 2, 10, 3, kills=40, deaths=60, assists=50)]

    def test_nothing_is_sent_before_the_button(self):
        self.page.account_field.setText(str(ACCOUNT))
        self.settle()
        self.assertEqual(self.server.calls, [])
        self.assertFalse(self.page.me_empty.isHidden())

    def test_a_lookup_shows_rank_and_every_hero(self):
        self.look_up()
        self.assertEqual(self.column(self.page.me_table, 0), ['Infernus', 'Seven'])
        status_text = self.page.me_status.text().replace('‎', '')
        for part in ('Rank 6 3', '50 matches', '28 wins', '56.0 %', 'All time', 'All modes'):
            self.assertIn(part, status_text)

    def test_the_rank_name_is_used_when_known(self):
        self.load()
        self.look_up()
        self.assertIn('Emissary 3', self.page.me_status.text().replace('‎', ''))

    def test_each_hero_is_compared_with_everyone(self):
        self.look_up()
        row = [self.page.me_table.item(0, c).text().replace('‎', '') for c in range(7)]
        self.assertEqual(row[:4], ['Infernus', '40', '25', '62.5 %'])
        self.assertEqual(row[4], '52.0 %')
        self.assertEqual(row[5], '+10.5')
        self.assertEqual(row[6], '3.33')

    def test_without_the_everyone_numbers_the_comparison_is_blank(self):
        self.server.hook = lambda url, query: status(500) if url.startswith('https://api.deadlock-api.com/v1/analytics') else None
        self.look_up()
        self.assertEqual(self.page.me_table.item(0, 4).text(), '—')
        self.assertEqual(self.page.me_table.item(0, 5).text(), '—')
        self.assertEqual(self.page.me_table.rowCount(), 2)

    def test_every_spelling_of_the_account_reaches_the_server_as_the_same_number(self):
        for spelling in (str(ACCOUNT), str(STEAM64), '[U:1:%d]' % ACCOUNT, 'https://steamcommunity.com/profiles/%d' % STEAM64):
            self.server.calls.clear()
            self.look_up(spelling)
            self.assertEqual(self.server.queries('/v1/players/hero-stats')[0]['account_ids'], str(ACCOUNT), spelling)
            self.assertIn('/v1/players/%d/rank' % ACCOUNT, ' '.join(self.server.calls))

    def test_a_bad_account_is_explained_and_nothing_is_sent(self):
        for text, code in (('', 'empty'), ('gaben', 'format'), ('https://steamcommunity.com/id/gaben', 'vanity'), ('0', 'range')):
            self.page.account_field.setText(text)
            self.page.look_up()
            self.assertEqual(self.page.me_status.text(), account_problem(code), text)
        self.assertEqual(self.server.calls, [])

    def test_the_account_is_only_sent_to_player_addresses(self):
        self.look_up()
        self.load()
        for url in self.server.calls:
            if str(ACCOUNT) in url:
                self.assertTrue('/v1/players/' in url, url)

    def test_no_account_number_is_saved_on_disk(self):
        self.look_up()
        self.load()
        for path in (self.folder / 'stats').iterdir():
            self.assertNotIn(str(ACCOUNT).encode(), path.read_bytes(), path.name)
            self.assertNotIn(str(STEAM64).encode(), path.read_bytes(), path.name)

    def test_a_player_with_no_matches(self):
        self.server.players[ACCOUNT] = []
        self.server.ranked[ACCOUNT] = 404
        self.look_up()
        self.assertEqual(self.page.me_table.rowCount(), 0)
        self.assertFalse(self.page.me_empty.isHidden())
        self.assertIn('No rank on record', self.page.me_status.text())

    def test_a_player_service_failure_is_reported(self):
        self.server.hook = lambda url, query: status(503) if '/v1/players/' in url else None
        self.look_up()
        self.assertIn('Could not reach', self.page.me_status.text())
        self.assertTrue(self.page.look_button.isEnabled())

    def test_the_own_account_button(self):
        self.assertFalse(self.page.own_button.isEnabled())
        self.own = ACCOUNT
        self.page.refresh_buttons()
        self.assertTrue(self.page.own_button.isEnabled())
        self.page.use_own_account()
        self.assertEqual(self.page.account_field.text(), str(ACCOUNT))
        self.assertEqual(self.server.calls, [], 'reading the number from the Steam folder sends nothing')

    def test_the_table_sorts_numerically(self):
        self.server.players[ACCOUNT] = [player_row(ACCOUNT, 1, 9, 4), player_row(ACCOUNT, 2, 100, 50), player_row(ACCOUNT, 3, 1000, 500)]
        self.look_up()
        self.page.me_table.sortByColumn(1, Qt.AscendingOrder)
        self.assertEqual(self.column(self.page.me_table, 1), ['9', '100', '1,000'])

    def test_my_stats_has_its_own_period_and_mode_and_starts_with_everything(self):
        self.assertEqual((self.page.me_window.currentData(), self.page.me_mode.currentData()), (0, ''))
        self.look_up()
        self.assertEqual(set(self.server.queries('/v1/players/hero-stats')[0]), {'account_ids', 'game_mode'})      # no time limit, no mode
        self.page.window_box.setCurrentIndex(self.page.window_box.findData(7))                                      # the filters of the other tabs do not apply
        self.page.mode_box.setCurrentIndex(self.page.mode_box.findData('unranked'))
        self.server.calls.clear()
        self.look_up()
        self.assertEqual(set(self.server.queries('/v1/players/hero-stats')[0]), {'account_ids', 'game_mode'})

    def test_the_period_and_mode_chosen_here_are_sent(self):
        self.page.me_window.setCurrentIndex(self.page.me_window.findData(14))
        self.page.me_mode.setCurrentIndex(self.page.me_mode.findData('ranked'))
        self.look_up()
        query = self.server.queries('/v1/players/hero-stats')[0]
        self.assertEqual(query['match_mode'], 'ranked')
        self.assertIn('min_unix_timestamp', query)
        self.assertIn('Last 14 days · Ranked', self.page.me_status.text())

    def test_all_time_is_compared_with_the_last_thirty_days_and_a_window_with_itself(self):
        self.look_up()
        self.assertEqual(self.server.count('/v1/analytics/hero-stats'), 1)
        thirty = self.server.queries('/v1/analytics/hero-stats')[0]['min_unix_timestamp']
        self.assertIn('30 days', self.page.me_table.horizontalHeaderItem(4).toolTip())
        self.page.me_window.setCurrentIndex(self.page.me_window.findData(7))
        self.look_up()
        seven = self.server.queries('/v1/analytics/hero-stats')[-1]['min_unix_timestamp']
        self.assertGreater(int(seven), int(thirty))
        self.assertIn('7 days', self.page.me_table.horizontalHeaderItem(4).toolTip())

    def test_the_answer_says_what_period_it_covers_even_if_the_choice_changes_meanwhile(self):
        self.page.me_window.setCurrentIndex(self.page.me_window.findData(14))
        self.page.account_field.setText(str(ACCOUNT))
        self.page.look_up()
        self.page.me_window.setCurrentIndex(self.page.me_window.findData(30))
        self.settle()
        self.assertIn('Last 14 days', self.page.me_status.text())

    def test_a_player_with_no_matches_is_told_what_to_try(self):
        self.server.players[ACCOUNT] = []
        self.look_up()
        self.assertIn('All time', self.page.me_empty.text.text())


class WindowTests(unittest.TestCase):
    """The real main window, with the statistics transport and the AppData folder replaced: whatever the code does, nothing reaches the network or the user's folders."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.server = FakeServer()
        for target, replacement in (('deadlock_fps.stats_service.UrllibTransport', lambda user_agent=None: self.server),
                                    ('deadlock_fps.stats_service.QStandardPaths.writableLocation', lambda *_: folder.name),
                                    ('deadlock_fps.ui.QStandardPaths.writableLocation', lambda *_: folder.name)):
            patcher = patch(target, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)
        from deadlock_fps.ui import Window
        self.window = Window()
        self.addCleanup(self.window.close)
        self.window.guard_timer.stop()
        self.window.detect_timer.stop()

    def test_the_page_is_reachable_and_reads_the_steam_account_from_the_chosen_game_account(self):
        window = self.window
        self.assertIs(window.slots['stats'], window.stats.heroes_view)
        self.assertFalse(window.nav['stats'].isHidden())
        window.nav['stats'].click()
        self.assertEqual(window.current_slot,'stats')
        self.assertEqual(window.page_title.text(), window.nav['stats'].text())
        self.assertTrue(window.nav['stats'].isChecked())
        self.assertIsNone(window.steam_account())
        window.accounts.addItem('Steam 123456789', 'C:/Program Files (x86)/Steam/userdata/123456789/1422450/local/cfg/video.txt')
        window.accounts.setCurrentIndex(window.accounts.count() - 1)
        self.assertEqual(window.steam_account(), 123456789)
        window.stats.refresh_buttons()
        self.assertTrue(window.stats.own_button.isEnabled())
        window.stats.use_own_account()
        self.assertEqual(window.stats.account_field.text(), '123456789')

    def test_opening_the_window_and_the_page_makes_no_statistics_request(self):
        self.window.navigate('stats')
        QThreadPool.globalInstance().waitForDone()
        self.app.processEvents()
        self.assertEqual(self.server.calls, [])

    def test_a_load_from_the_window_reaches_the_service_and_saves_into_the_app_folder(self):
        self.window.navigate('stats')
        self.window.stats.load()
        for _ in range(4):
            QThreadPool.globalInstance().waitForDone()
            self.app.processEvents()
        self.assertEqual(self.window.stats.hero_table.rowCount(), 3)
        self.assertGreater(self.server.count('/v1/analytics/hero-stats'), 0)


class ArabicTests(unittest.TestCase):
    def test_summary_sentences_start_with_a_word_not_a_number(self):
        """A number wrapped for left-to-right at the start of an Arabic sentence flips the order of the whole sentence."""
        from deadlock_fps.lang_ar import TEXT as ARABIC
        for key in ('{0} matches · average length {1} min · abandon rate {2}', '{0} matches · {1} wins · {2} win rate', '{0} players · {1}', 'Rank: {0} {1}'):
            self.assertFalse(ARABIC[key].startswith('{'), key)


class SmallPartsTests(unittest.TestCase):
    def test_percent(self):
        self.assertEqual(percent(0.5), '50.0 %')
        self.assertEqual(percent(0.1234, 2), '12.34 %')

    def test_number_cells_sort_by_their_number_not_their_text(self):
        self.assertTrue(NumberItem('9', 9) < NumberItem('1,000', 1000))
        self.assertFalse(NumberItem('1,000', 1000) < NumberItem('9', 9))


if __name__ == '__main__':
    unittest.main()
