"""Settings: the section list, the look, the language, the protection switch, the game facts and the two small choices that are remembered."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from deadlock_fps.pages.settings import SECTIONS, TEXT_SIZES, SettingsPage
from test_shell import FakeApp


class Case(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def window(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        for target in ('deadlock_fps.ui.QStandardPaths.writableLocation', 'PySide6.QtCore.QStandardPaths.writableLocation'):
            patcher = patch(target, return_value=folder.name)
            patcher.start()
            self.addCleanup(patcher.stop)
        for target in ('deadlock_fps.game_link.detect_games',):
            patcher = patch(target, return_value=[])
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch('deadlock_fps.mods.ModLibrary.discover', return_value=[])
        patcher.start()
        self.addCleanup(patcher.stop)
        from deadlock_fps.ui import Window
        w = Window()
        self.addCleanup(self.discard, w)
        w.guard_timer.stop()
        w.detect_timer.stop()
        w.servers.activate = lambda: None
        return w

    def discard(self, w):
        w.close()
        w.deleteLater()

    def saved(self):
        return json.loads((self.folder / 'workspace.json').read_text(encoding='utf-8'))


class Sections(Case):
    def test_there_are_seven_sections_and_each_address_shows_its_own(self):
        w = self.window()
        self.assertEqual(len(SECTIONS), 7)
        for key in SECTIONS:
            w.navigate('settings.' + key)
            self.assertEqual(w.settings_view.current, key)
            self.assertIs(w.settings_view.stack.currentWidget(), w.settings_view.sections[key])
            self.assertTrue(w.settings_view.nav[key].isChecked())
            self.assertEqual(sum(b.isChecked() for b in w.settings_view.nav.values()), 1)
        with self.assertRaises(KeyError):
            w.settings_view.show_section('nope')

    def test_clicking_a_section_shows_it(self):
        w = self.window()
        w.navigate('settings')
        w.settings_view.nav['about'].click()
        self.assertEqual(w.settings_view.current, 'about')

    def test_the_update_and_sources_sections_are_the_real_pages(self):
        w = self.window()
        self.assertIs(w.settings_view.sections['update'], w.updates)
        self.assertIs(w.settings_view.sections['sources'], w.repositories)

    def test_the_update_news_puts_a_dot_on_the_section_and_on_settings(self):
        w = self.window()
        w.show_update_dot(True)
        self.assertTrue(w.settings_view.nav['update'].badged)
        self.assertTrue(w.nav['settings'].badged)
        w.show_update_dot(False)
        self.assertFalse(w.settings_view.nav['update'].badged)


class General(Case):
    def test_the_look_and_text_size_switch_at_once_and_are_remembered(self):
        from deadlock_fps.shell import theme
        w = self.window()
        w.navigate('settings.general')
        theme.set_base_style('')
        self.addCleanup(theme.apply, FakeApp(), 'dark', 'blue', 100)           # put the theme state back; never restyle the real widgets left open by earlier tests
        with patch('deadlock_fps.ui.QApplication.instance', return_value=FakeApp()):
            w.settings_view.look.buttons['light'].click()
            self.assertEqual(theme.current().mode, 'light')
            w.settings_view.size.buttons['115'].click()
            self.assertEqual(theme.current().scale, 115)
            self.assertEqual(theme.current().mode, 'light', 'changing the text size keeps the look')
        look = self.saved()['look']
        self.assertEqual((look['mode'], look['scale']), ('light', 115))
        self.assertEqual(TEXT_SIZES, (90, 100, 115, 130))

    def test_a_saved_look_is_shown_selected_when_the_window_opens(self):
        w = self.window()
        w.settings_view.set_look_choice('light', 130)
        self.assertEqual((w.settings_view.look.value(), w.settings_view.size.value()), ('light', '130'))

    def test_choosing_another_language_saves_it_and_offers_a_restart(self):
        w = self.window()
        self.assertTrue(w.settings_view.restart_banner.isHidden())
        other = 'ar' if w.language.currentData() == 'en' else 'en'
        w.language.setCurrentIndex(w.language.findData(other))
        self.assertEqual(self.saved()['language'], other)
        self.assertFalse(w.settings_view.restart_banner.isHidden())
        with patch('deadlock_fps.pages.settings.QProcess.startDetached', return_value=(False, 0)) as start:
            w.settings_view.restart_button.click()
        start.assert_called_once()

    def test_less_motion_is_remembered_and_stops_the_page_slide(self):
        w = self.window()
        w.settings_view.less_motion.setChecked(True)
        self.assertTrue(self.saved()['look']['less_motion'])
        captured = []
        w.transition.capture = lambda direction=1: captured.append(direction)
        w.navigate('performance')
        w.navigate('stats')
        self.assertEqual(captured, [])
        w.settings_view.less_motion.setChecked(False)
        w.navigate('performance')
        self.assertEqual(len(captured), 1)


class GameAndProtection(Case):
    def test_without_a_game_the_section_says_so_and_with_one_it_lists_the_facts(self):
        w = self.window()
        view = w.settings_view
        self.assertFalse(view.game_banner.isHidden())
        view.set_game(True, 'C:/Games/Deadlock', '6857', 'Installed', 'Steam 111')
        self.assertTrue(view.game_banner.isHidden())
        self.assertEqual((view.game_path.text(), view.game_version.text(), view.game_state.text(), view.game_account.text()), ('C:/Games/Deadlock', '6857', 'Installed', 'Steam 111'))
        view.set_game(False)
        self.assertEqual(view.game_path.text(), '—')

    def test_the_buttons_ask_the_window_to_choose_or_find_the_game(self):
        w = self.window()
        asked = []
        w.settings_view.chooseGame.connect(lambda: asked.append('choose'))
        w.settings_view.findGame.connect(lambda: asked.append('find'))
        with patch('deadlock_fps.game_link.QFileDialog.getExistingDirectory', return_value=''):        # the real window would open a folder picker
            w.settings_view.choose_button.click()
        w.settings_view.find_button.click()
        self.assertEqual(asked, ['choose', 'find'])

    def test_the_protection_switch_is_what_the_guard_reads(self):
        w = self.window()
        self.assertIs(w.guard, w.settings_view.guard)
        self.assertTrue(w.guard.isChecked())
        w.guard.setChecked(False)
        w.path.setText('C:/nowhere')
        with patch('deadlock_fps.core.ensure_closed') as closed:
            w.guard_tick()
        closed.assert_not_called()

    def test_check_and_repair_reports_in_the_status_line(self):
        w = self.window()
        with patch.object(type(w), 'studio') as studio:
            studio.return_value.repair.return_value = 'Nothing to repair.'
            w.settings_view.repair_button.click()
        self.assertEqual(w.guard_status.text(), 'Nothing to repair.')


class Advanced(Case):
    def test_mod_pictures_are_off_by_default_and_remembered_when_turned_on(self):
        w = self.window()
        self.assertFalse(w.settings_view.pictures.isChecked())
        w.settings_view.pictures.setChecked(True)
        self.assertTrue(self.saved()['look']['pictures'])
        self.assertTrue(w.saved_look['pictures'])
        self.assertTrue(w.store.auto_pictures, 'the Browse page follows the setting')
        w.settings_view.pictures.setChecked(False)
        self.assertFalse(w.store.auto_pictures)

    def test_the_map_and_the_data_folder_buttons_do_something(self):
        w = self.window()
        w.settings_view.map_button.click()
        self.assertEqual(w.current_address, 'map')
        with patch('deadlock_fps.pages.settings.QDesktopServices.openUrl') as opened:
            w.settings_view.data_button.click()
        opened.assert_called_once()

    def test_about_names_the_version_and_links_out(self):
        from deadlock_fps import __version__
        w = self.window()
        texts = ' '.join(label.text() for label in w.settings_view.sections['about'].findChildren(type(w.page_title)))
        self.assertIn(__version__, texts)
        with patch('deadlock_fps.pages.settings.QDesktopServices.openUrl') as opened:
            w.settings_view.github_button.click()
        self.assertIn('github.com', opened.call_args[0][0].toString())


if __name__ == '__main__':
    unittest.main()
