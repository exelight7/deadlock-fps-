"""The rebuilt Home page: the page on its own (drawn from what it is given), then inside the real window with a throwaway game folder."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from deadlock_fps.detection import GameStatus
from deadlock_fps.pages.home import HomePage


def installed_status(running=False, build='6857'):
    return GameStatus('installed', Path('/game'), build, 33 * 1024 ** 3, running, 2)


class PageOnItsOwn(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.page = HomePage()
        self.opened, self.required = [], []
        self.page.openRequested.connect(self.opened.append)
        self.page.gameRequired.connect(lambda: self.required.append(True))

    def test_first_run_shows_the_link_card_and_asks_for_the_game(self):
        p = self.page
        p.show()
        self.assertTrue(p.link_card.isVisible())
        self.assertTrue(p.hint.isVisible())
        p.open_door('mods', 'mods.browse')
        p.open_door('performance', 'performance')
        self.assertEqual((self.opened, len(self.required)), ([], 2))
        p.open_door('stats', 'stats')                       # Stats works without the game
        self.assertEqual(self.opened, ['stats'])

    def test_linked_hides_the_card_and_opens_every_door(self):
        p = self.page
        p.show()
        p.set_linked(True)
        self.assertFalse(p.link_card.isVisible())
        self.assertFalse(p.hint.isVisible())
        p.open_door('mods', 'mods.browse')
        self.assertEqual((self.opened, self.required), (['mods.browse'], []))
        p.show_link_card(True)                              # the game pill brings it back, to change the folder
        self.assertTrue(p.link_card.isVisible())
        p.show_link_card(False)
        self.assertFalse(p.link_card.isVisible())

    def test_a_door_card_press_goes_through_the_same_check(self):
        self.page.doors['mods'].clicked.emit()
        self.assertEqual(len(self.required), 1)
        self.page.set_linked(True)
        self.page.doors['mods'].clicked.emit()
        self.assertEqual(self.opened, ['mods.browse'])

    def test_every_game_state_has_one_plain_message(self):
        p = self.page
        cases = [(GameStatus('missing', None, '', 0, False, 3), False, 'danger', 'not found'),
                 (GameStatus('updating', None, '', 0, False, 1), False, 'info', 'still downloading'),
                 (GameStatus('no_steam', None, '', 0, False, 0), False, 'warning', 'Steam was not found'),
                 (installed_status(), False, 'info', 'was found'),
                 (installed_status(running=True), True, 'warning', 'is running')]
        for status, linked, variant, words in cases:
            p.show_status(status, linked)
            self.assertEqual(p.banner.property('variant'), variant, status)
            self.assertIn(words, p.banner.title.text())
        p.show_status(installed_status(), True)             # linked and quiet: no banner at all
        self.assertIsNone(p.banner)

    def test_install_button_only_when_the_game_is_missing_or_downloading(self):
        p = self.page
        p.show_status(GameStatus('missing', None, '', 0, False, 2), False)
        self.assertFalse(p.install_button.isHidden())
        p.show_status(GameStatus('no_steam', None, '', 0, False, 0), False)
        self.assertTrue(p.install_button.isHidden())
        p.show_status(GameStatus('missing', None, '', 0, False, 2), True)
        self.assertTrue(p.install_button.isHidden())

    def test_searching_is_visible_and_busy(self):
        p = self.page
        p.show()
        p.set_searching(True)
        self.assertTrue(p.search.isVisible() and p.find_button.busy)
        p.set_searching(False)
        self.assertFalse(p.search.isVisible() or p.find_button.busy)

    def test_door_and_card_texts(self):
        p = self.page
        p.set_mods(0, 0)
        self.assertEqual(p.doors['mods'].status.text(), p.mods_text)
        p.set_mods(12, 2)
        self.assertEqual(p.doors['mods'].status.text(), '12 installed · 2 updates')
        p.set_mods(3, 0)
        self.assertEqual(p.doors['mods'].status.text(), '3 installed')
        p.set_performance(80, 'Balanced')
        self.assertEqual(p.doors['performance'].status.text(), 'Level 80 · Balanced')
        p.set_small('servers', '2 regions blocked')
        self.assertEqual(p.small['servers'].status.text(), '2 regions blocked')
        p.small['backups'].clicked.emit()
        self.assertEqual(self.opened, ['backups'])

    def test_attention_list_counts_and_hides_when_empty(self):
        p = self.page
        pressed = []
        p.show()
        p.set_attention([{'tone': 'danger', 'icon': 'warn', 'title': 'A', 'line': 'a', 'action': 'Fix', 'callback': lambda: pressed.append('A')},
                         {'tone': 'info', 'icon': 'info', 'title': 'B', 'action': 'Look', 'callback': lambda: pressed.append('B')}])
        self.assertTrue(p.attention.isVisible())
        self.assertEqual((p.count.text(), len(p.rows)), ('2', 2))
        p.rows[1].control.click()
        self.assertEqual(pressed, ['B'])
        p.set_attention([])
        self.assertEqual(len(p.rows), 0)
        self.assertFalse(p.attention.isVisible())


class InTheWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.game = self.root / 'Deadlock'
        info = self.game / 'game/citadel/gameinfo.gi'
        info.parent.mkdir(parents=True)
        info.write_text('test')
        self.video = self.root / 'Steam/userdata/111/1422450/local/cfg/video.txt'
        self.video.parent.mkdir(parents=True)
        self.video.write_text('test')
        self.status = installed_status()
        for context in (patch('deadlock_fps.ui.QStandardPaths.writableLocation', return_value=str(self.root / 'data')),
                        patch('deadlock_fps.game_link.detect_games', return_value=[]), patch('deadlock_fps.game_link.scan', side_effect=lambda games: self.status),
                        patch('deadlock_fps.game_link.video_files', return_value=[self.video]), patch('deadlock_fps.core.video_files', return_value=[self.video]),
                        patch('deadlock_fps.mods.ModLibrary.discover', return_value=[])):
            context.start()
            self.addCleanup(context.stop)
        from deadlock_fps.ui import Window
        self.w = Window()
        self.w.guard_timer.stop()
        self.w.detect_timer.stop()
        self.addCleanup(self.w.close)

    def link(self):
        self.w.path.setText(str(self.game))
        self.w.refresh_accounts()

    def test_starts_unlinked_with_the_pill_and_card(self):
        w = self.w
        w.show()
        self.assertEqual((w.game_linked, w.game_pill.property('state')), (False, 'none'))
        self.assertTrue(w.home.link_card.isVisible())
        self.assertIs(w.stack.currentWidget(), w.slots['home'])

    def test_linking_follows_through_everywhere(self):
        w = self.w
        w.show()
        self.link()
        self.assertTrue(w.game_linked)
        self.assertEqual(w.game_pill.property('state'), 'linked')
        self.assertFalse(w.home.link_card.isVisible())
        self.assertIn('Linked', w.connection_note.text())
        self.assertEqual(w.steam_account(), 111)

    def test_running_game_turns_the_pill_blue_and_warns(self):
        w = self.w
        self.link()
        self.status = installed_status(running=True)
        w.update_game_status()
        self.assertEqual(w.game_pill.property('state'), 'running')
        self.assertEqual(w.home.banner.property('variant'), 'warning')

    def test_game_pill_opens_the_card_on_home(self):
        w = self.w
        w.show()
        self.link()
        w.navigate('crosshair')
        w.game_pill.click()
        self.assertEqual(w.current_address, 'home')
        self.assertTrue(w.home.link_card.isVisible())

    def test_a_door_that_needs_the_game_sends_you_to_the_card(self):
        w = self.w
        w.show()
        w.navigate('stats')
        w.home.doors['mods'].clicked.emit()
        self.assertEqual(w.current_address, 'home')
        self.assertTrue(w.home.link_card.isVisible())

    def test_attention_list_is_built_from_the_installer(self):
        w = self.w
        self.link()
        mod = SimpleNamespace(name='Clean HUD')
        w.mod_service.installer = lambda: SimpleNamespace(installed=lambda: [mod, SimpleNamespace(name='Night Skyline')])
        w.mod_service.statuses = lambda: [SimpleNamespace(updatable=True, mod=mod), SimpleNamespace(updatable=False, mod=mod)]
        w.studio = lambda: SimpleNamespace(addons_enabled=lambda: False)
        w.refresh_home()
        self.assertEqual([r.title.text() for r in w.home.rows], ['Your mods are switched off in the game', '1 mods have updates'])
        self.assertEqual(w.home.doors['mods'].status.text(), '2 installed · 1 updates')
        w.home.rows[1].control.click()
        self.assertEqual(w.current_address, 'mods.installed')

    def test_repair_runs_the_installer_repair_and_says_so(self):
        w = self.w
        calls = []
        w.mod_service.operate = lambda name, args, done, failed: (calls.append(name), done(None))
        w.repair_mods()
        self.assertEqual(calls, ['repair'])

    def test_no_sideways_scrolling_at_the_minimum_window_and_130_percent_text(self):
        from deadlock_fps.shell import theme
        theme.apply(self.app, 'dark', 'blue', 130)
        self.addCleanup(theme.apply, self.app, 'dark', 'blue', 100)
        w = self.w
        w.resize(940, 680)
        w.show()
        w.home.show_status(GameStatus('missing', None, '', 0, False, 2), False)
        self.app.processEvents()
        self.assertTrue(w.home.install_button.isVisible())
        self.assertFalse(w.slots['home'].horizontalScrollBar().isVisible())

    def test_nothing_to_flag_without_a_game(self):
        w = self.w
        w.refresh_home()
        self.assertEqual(len(w.home.rows), 0)
        self.assertFalse(w.home.attention.isVisible())


if __name__ == '__main__':
    unittest.main()
