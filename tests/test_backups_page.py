"""Backups: the page's buttons, the saved copies, and what the window does when each one is pressed."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication, QLabel

from deadlock_fps.pages.backups import BackupsPage, history_rows
from deadlock_fps.settings import Settings


class ThePage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_the_buttons_say_what_was_asked(self):
        page = BackupsPage()
        self.addCleanup(page.deleteLater)
        got = []
        page.restoreRequested.connect(lambda keep: got.append(('restore', keep)))
        page.folderRequested.connect(lambda: got.append('folder'))
        page.undoRequested.connect(lambda key: got.append(('undo', key)))
        page.exportRequested.connect(lambda: got.append('export'))
        page.importRequested.connect(lambda: got.append('import'))
        page.restore_button.click()
        page.keep.setChecked(True)
        page.restore_button.click()
        page.folder_button.click()
        for key, button in page.undo_buttons.items():
            button.click()
        page.export_button.click()
        page.import_button.click()
        self.assertEqual(got, [('restore', False), ('restore', True), 'folder', ('undo', 'crosshair'), ('undo', 'mods'), ('undo', 'servers'), 'export', 'import'])

    def test_saved_copies_show_a_list_or_an_empty_state(self):
        page = BackupsPage()
        self.addCleanup(page.deleteLater)
        self.assertFalse(page.copies_empty.isHidden())
        self.assertTrue(page.copy_list.isHidden())
        page.set_copies([('2026-11-14 10:00', 3), ('2026-11-13 09:30', 1)])
        self.assertTrue(page.copies_empty.isHidden())
        self.assertEqual(len(page.copy_list.rows), 2)
        self.assertEqual(page.copy_list.rows[0].title.text(), '2026-11-14 10:00')
        self.assertEqual(page.copy_list.rows[1].line.text(), '1 file')

    def test_the_busy_state_locks_the_buttons_that_write(self):
        page = BackupsPage()
        self.addCleanup(page.deleteLater)
        page.set_busy(True)
        self.assertFalse(page.restore_button.isEnabled())
        self.assertFalse(page.undo_buttons['mods'].isEnabled())
        page.set_busy(False)
        self.assertTrue(page.restore_button.isEnabled())

    def test_a_notice_replaces_the_one_before_it(self):
        page = BackupsPage()
        self.addCleanup(page.deleteLater)
        page.say('First', 'a', 'danger')
        page.say('Second', 'b', 'warning')
        titles = [l.text() for l in page.findChildren(QLabel) if l.text() in ('First', 'Second')]
        self.assertEqual(titles, ['Second'])
        page.say('')
        self.assertEqual(page.notice_box.count(), 0)

    def test_history_rows_read_the_restore_points_newest_first(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Path(folder)
            for name, files in (('20261112T080000000000', 1), ('20261114T100000123456', 3)):
                entry = store / 'history' / name
                entry.mkdir(parents=True)
                for n in range(files):
                    (entry / ('%d.bin' % n)).write_bytes(b'x')
                (entry / 'state.json').write_bytes(b'{}')
            studio = MagicMock(store=store)
            self.assertEqual(history_rows(studio), [('2026-11-14 10:00', 3), ('2026-11-12 08:00', 1)])
            self.assertEqual(history_rows(MagicMock(store=store / 'nothing')), [])


class InTheWindow(unittest.TestCase):
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
        for target, value in (('deadlock_fps.game_link.detect_games', []), ('deadlock_fps.mods.ModLibrary.discover', [])):
            patcher = patch(target, return_value=value)
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

    def notice_titles(self, w):
        return [l.text() for l in w.backups_page.findChildren(QLabel)]

    def test_restore_without_a_game_brings_up_the_link_card_and_changes_nothing(self):
        w = self.window()
        w.navigate('backups')
        with patch.object(type(w), 'studio') as studio:
            w.restore(False)
        studio.assert_not_called()
        self.assertEqual(w.current_slot, 'home')

    def test_restore_asks_first_and_nothing_happens_on_cancel(self):
        w = self.window()
        w.path.setText('C:/Games/Deadlock')
        with patch.object(type(w), 'studio') as studio, patch('deadlock_fps.pages.backups.confirm', return_value=False):
            w.restore(False)
        studio.return_value.restore.assert_not_called()

    def test_restore_passes_the_keep_choice_switches_the_guard_off_and_reports(self):
        w = self.window()
        w.path.setText('C:/Games/Deadlock')
        self.assertTrue(w.guard.isChecked())
        with patch.object(type(w), 'studio') as studio, patch('deadlock_fps.pages.backups.confirm', return_value=True):
            studio.return_value.restore.return_value = 'Restored.'
            studio.return_value.store = self.folder / 'store'
            w.backups_page.keep.setChecked(True)
            w.backups_page.restore_button.click()
        studio.return_value.restore.assert_called_once_with(True)
        self.assertFalse(w.guard.isChecked(), 'the guard must not put the settings back right after a restore')

    def test_a_change_made_outside_toolbox_points_at_the_checkbox(self):
        w = self.window()
        w.path.setText('C:/Games/Deadlock')
        with patch.object(type(w), 'studio') as studio, patch('deadlock_fps.pages.backups.confirm', return_value=True):
            studio.return_value.restore.side_effect = ValueError('توجد تغييرات فعلية خارج البرنامج.')
            w.restore(False)
        self.assertIn('The game files changed outside Toolbox', self.notice_titles(w))

    def test_another_error_is_shown_as_nothing_was_changed(self):
        w = self.window()
        w.path.setText('C:/Games/Deadlock')
        with patch.object(type(w), 'studio') as studio, patch('deadlock_fps.pages.backups.confirm', return_value=True):
            studio.return_value.restore.side_effect = ValueError('Close Deadlock first.')
            w.restore(False)
        texts = self.notice_titles(w)
        self.assertIn('Nothing was changed', texts)
        self.assertIn('Close Deadlock first.', texts)

    def test_export_and_import_round_trip_the_graphics_choices(self):
        w = self.window()
        w.load_settings(Settings.at_level(120, aspect_ratio=2.0, fps=144))
        target = self.folder / 'profile.json'
        with patch('deadlock_fps.pages.backups.QFileDialog.getSaveFileName', return_value=(str(target), '')):
            w.backups_page.export_button.click()
        saved = json.loads(target.read_text())
        self.assertEqual((saved['level'], saved['fps'], saved['aspect_ratio']), (120, 144, 2.0))
        w.load_preset('balanced')
        with patch('deadlock_fps.pages.backups.QFileDialog.getOpenFileName', return_value=(str(target), '')):
            w.backups_page.import_button.click()
        self.assertEqual((w.level.value(), w.level_page.fps.value()), (120, 144))
        self.assertEqual(w.current_address, 'performance.level', 'after loading a file the user is taken to the page that shows it')

    def test_a_bad_file_is_refused_with_a_message_and_changes_nothing(self):
        w = self.window()
        w.load_preset('balanced')
        bad = self.folder / 'bad.json'
        bad.write_text('{"level": 9999}')
        with patch('deadlock_fps.pages.backups.QFileDialog.getOpenFileName', return_value=(str(bad), '')):
            w.backups_page.import_button.click()
        self.assertIn('That file could not be used', self.notice_titles(w))
        self.assertEqual(w.level.value(), 25)

    def test_the_shortcuts_reach_the_other_tools(self):
        w = self.window()
        w.crosshair.review = MagicMock()
        w.servers.apply_action = MagicMock()
        w.install_mods = MagicMock()
        w.backups_page.undo_buttons['crosshair'].click()
        w.crosshair.review.assert_called_once_with(True)
        w.backups_page.undo_buttons['servers'].click()
        w.servers.apply_action.assert_called_once_with('clear')
        w.backups_page.undo_buttons['mods'].click()
        w.install_mods.assert_called_once()
        self.assertEqual(w.current_address, 'mods.installed')


if __name__ == '__main__':
    unittest.main()
