"""Language system, game detection states and the regrouped navigation."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

# Runs in a fresh interpreter because the language must be chosen before the interface is imported.
PROBE = r'''
import os, re, sys, tempfile
from pathlib import Path
from unittest.mock import patch
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, sys.argv[1])
from deadlock_fps import i18n
i18n.activate(sys.argv[2])
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QCheckBox
app = QApplication([])
app.setLayoutDirection(Qt.RightToLeft if i18n.rtl() else Qt.LeftToRight)
with tempfile.TemporaryDirectory() as folder, patch('deadlock_fps.ui.QStandardPaths.writableLocation', return_value=folder), \
        patch('deadlock_fps.ui.detect_games', return_value=[]), patch('deadlock_fps.mods.ModLibrary.discover', return_value=[]):
    from deadlock_fps.ui import Window
    w = Window(); w.guard_timer.stop(); w.detect_timer.stop(); w.servers.activate = lambda: None
    arabic = re.compile('[ء-ي]{2,}')
    leaks = set()
    for page in range(9):
        w.navigate(page)
        assert w.stack.currentIndex() == page
    for widget in w.findChildren(QLabel) + w.findChildren(QPushButton) + w.findChildren(QCheckBox):
        if arabic.search(widget.text()):
            leaks.add(widget.text())
    print('LANG', i18n.LANGUAGE, 'RTL', w.layoutDirection() == Qt.RightToLeft, 'CROSSHAIR_RTL', w.crosshair.layoutDirection() == Qt.RightToLeft)
    print('NAV', w.nav[0].text(), '|', w.nav[8].text())
    print('LEAKS', len(leaks), sorted(leaks)[:5])
    w.close()
'''


class Catalogues(unittest.TestCase):
    def test_every_source_string_is_translated_with_matching_placeholders(self):
        import i18n_tool
        self.assertTrue(i18n_tool.check())

    def test_source_mode_is_the_default_and_leaves_text_alone(self):
        from deadlock_fps import i18n
        self.assertEqual(i18n.LANGUAGE, 'source')
        self.assertEqual(i18n.tr('المودات'), 'المودات')
        self.assertEqual(list(i18n.LANGUAGES), ['en', 'ar'])

    def test_saved_language_wins_and_bad_files_fall_back(self):
        from deadlock_fps import i18n
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / 'workspace.json'
            file.write_text(json.dumps({'language': 'ar'}), encoding='utf-8')
            self.assertEqual(i18n.preferred(file), 'ar')
            file.write_text(json.dumps({'language': 'xx'}), encoding='utf-8')
            self.assertIn(i18n.preferred(file), ('en', 'ar'))
            file.write_text('not json', encoding='utf-8')
            self.assertIn(i18n.preferred(file), ('en', 'ar'))


class Interface(unittest.TestCase):
    def probe(self, language):
        result = subprocess.run([sys.executable, '-c', PROBE, str(ROOT), language], capture_output=True, text=True, encoding='utf-8',
                                env=dict(os.environ, PYTHONIOENCODING='utf-8'), timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
        return result.stdout

    def test_english_interface_has_no_arabic_left_and_reads_left_to_right(self):
        output = self.probe('en')
        self.assertIn('LANG en RTL False CROSSHAIR_RTL False', output)
        self.assertIn('NAV Home | Settings', output)
        self.assertIn('LEAKS 0', output, output)

    def test_arabic_interface_is_right_to_left_including_the_crosshair_workspace(self):
        output = self.probe('ar')
        self.assertIn('LANG ar RTL True CROSSHAIR_RTL True', output)
        self.assertIn('NAV الرئيسية | الإعدادات', output)


class Detection(unittest.TestCase):
    def test_states_cover_installed_updating_and_absent(self):
        from deadlock_fps.detection import scan, GameStatus
        with tempfile.TemporaryDirectory() as folder:
            library = Path(folder) / 'steamapps'
            game = library / 'common/Deadlock'
            (game / 'game/citadel').mkdir(parents=True)
            (game / 'game/citadel/gameinfo.gi').write_text('x')
            manifest = library / 'appmanifest_1422450.acf'
            manifest.write_text('"AppState"\n{\n\t"appid"\t\t"1422450"\n\t"StateFlags"\t\t"4"\n\t"buildid"\t\t"123456"\n\t"SizeOnDisk"\t\t"2147483648"\n}\n')
            status = scan([game])
            self.assertEqual((status.state, status.build, status.size, status.found), ('installed', '123456', 2147483648, True))
            manifest.write_text(manifest.read_text().replace('"4"', '"1026"'))
            self.assertEqual(scan([game]).state, 'updating')
            manifest.unlink()
            self.assertEqual(scan([game]).state, 'installed', 'a folder picked by hand has no Steam manifest')
        absent = scan([])
        self.assertIsInstance(absent, GameStatus)
        self.assertIn(absent.state, ('missing', 'updating', 'no_steam'))
        self.assertFalse(absent.found)


if __name__ == '__main__':
    unittest.main()
