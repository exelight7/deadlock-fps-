import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from deadlock_fps.core import game_root
from deadlock_fps.ui import Window


class Workspace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.game=self.root/'Deadlock';gi=self.game/'game/citadel/gameinfo.gi';gi.parent.mkdir(parents=True);gi.write_text('test')
        self.files=[self.root/f'Steam/userdata/{account}/1422450/local/cfg/video.txt' for account in ('111','222')]
        for file in self.files:file.parent.mkdir(parents=True);file.write_text('test')
        self.patches=[patch('deadlock_fps.ui.QStandardPaths.writableLocation',return_value=str(self.root/'data')),
                      patch('deadlock_fps.ui.detect_games',return_value=[]),patch('deadlock_fps.ui.video_files',return_value=self.files),
                      patch('deadlock_fps.core.video_files',return_value=self.files)]
        for context in self.patches:context.start()
        self.windows=[]
    def tearDown(self):
        for window in self.windows:window.close()
        for context in reversed(self.patches):context.stop()
        self.temp.cleanup()
    def window(self):
        window=Window();window.guard_timer.stop();self.windows.append(window);return window
    def test_folder_and_account_survive_reopen_with_readable_labels(self):
        first=self.window();first.path.setText(str(self.game/'game/citadel'));first.refresh_accounts()
        first.accounts.setCurrentIndex(1)
        self.assertEqual(first.accounts.currentText(),'Steam 222')
        self.assertEqual(first.path.text(),str(self.game))
        second=self.window()
        self.assertEqual(second.path.text(),str(self.game));self.assertEqual(second.accounts.currentData(),str(self.files[1]))
        self.assertEqual(second.studio().video,self.files[1])
    def test_empty_apply_guides_user_without_error_dialog_or_writes(self):
        window=self.window();window.navigate(1)
        with patch('deadlock_fps.ui.QMessageBox.warning') as warning:window.preview()
        self.assertEqual(window.stack.currentIndex(),0);self.assertIn('أولًا',window.connection_note.text());warning.assert_not_called()
        self.assertFalse((self.game/'.deadlock-fps-studio').exists())
    def test_missing_saved_game_keeps_app_usable(self):
        data=self.root/'data';data.mkdir();(data/'workspace.json').write_text(json.dumps({'game':str(self.root/'missing'),'account':'missing'}))
        window=self.window();self.assertFalse(window.path.text());window.navigate(6)
        self.assertEqual(window.stack.currentIndex(),6)
    def test_picker_accepts_game_or_citadel_subfolder(self):
        for path in [self.game,self.game/'game',self.game/'game/citadel']:self.assertEqual(game_root(path),self.game)
        with self.assertRaises(ValueError):game_root('')
