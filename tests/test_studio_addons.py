"""Studio manages the citadel/addons search path without disturbing graphics or the four reference mods."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from deadlock_fps import kv
from deadlock_fps.core import Studio, ASSETS
from deadlock_fps.settings import Settings


def vanilla():
    """A gameinfo.gi as Valve ships it: no addons path."""
    text = (ASSETS / 'reference/gameinfo.gi').read_text(encoding='utf-8')
    return text.replace('            Game          "citadel/addons"\n', '')


class AddonsPath(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve() / 'Deadlock'
        self.gi = self.root / 'game/citadel/gameinfo.gi'
        self.gi.parent.mkdir(parents=True)
        self.gi.write_text(vanilla(), encoding='utf-8')
        self.original = self.gi.read_bytes()
        self.video = self.root / 'game/citadel/cfg/video.txt'
        self.video.parent.mkdir()
        self.video.write_bytes((ASSETS / 'reference/video.txt').read_bytes())
        self.patch = patch('deadlock_fps.core.ensure_closed')
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.addCleanup(self.temp.cleanup)
        self.studio = Studio(self.root, self.video)

    def paths(self):
        node = kv.section(self.gi.read_text(encoding='utf-8'), ['GameInfo', 'FileSystem', 'SearchPaths'])
        return [(c.key, c.value) for c in node.children]

    def test_the_path_is_added_above_the_first_citadel_entry_and_nothing_else_moves(self):
        self.assertFalse(self.studio.addons_enabled())
        self.studio.enable_addons()
        self.assertTrue(self.studio.addons_enabled())
        names = [v for _, v in self.paths()]
        self.assertLess(names.index('citadel/addons'), names.index('citadel'))
        before = [kv_pair for kv_pair in kv.section(self.original.decode(), ['GameInfo', 'FileSystem', 'SearchPaths']).children]
        self.assertEqual([(c.key, c.value) for c in before], [p for p in self.paths() if p[1] != 'citadel/addons'])

    def test_enabling_twice_changes_nothing_and_restore_returns_the_exact_original(self):
        self.studio.enable_addons()
        once = self.gi.read_bytes()
        self.studio.enable_addons()
        self.assertEqual(self.gi.read_bytes(), once)
        self.assertEqual(once.decode().count('citadel/addons'), 1)
        self.studio.restore()
        self.assertEqual(self.gi.read_bytes(), self.original)

    def test_graphics_changes_keep_the_addons_path(self):
        self.studio.enable_addons()
        settings = Settings()
        self.studio.apply(self.studio.plan(settings), settings)
        self.assertTrue(self.studio.addons_enabled())
        self.assertIn('r_shadows', self.gi.read_text(encoding='utf-8'))
        engine_off = Settings(engine=False)
        self.studio.apply(self.studio.plan(engine_off), engine_off)
        self.assertTrue(self.studio.addons_enabled())

    def test_reference_mod_selection_and_removal_keep_the_addons_path(self):
        self.studio.enable_addons()
        settings = Settings(mods=())
        self.studio.apply(self.studio.plan_mods((), self.temp.name), settings, mod_only=True)
        self.assertTrue(self.studio.addons_enabled())
        self.assertNotIn('fps_studio', self.gi.read_text(encoding='utf-8'))

    def test_enabling_after_graphics_keeps_the_graphics(self):
        settings = Settings()
        self.studio.apply(self.studio.plan(settings), settings)
        self.studio.enable_addons()
        text = self.gi.read_text(encoding='utf-8')
        self.assertIn('r_shadows', text)
        self.assertIn('citadel/addons', text)
        self.studio.restore()
        self.assertEqual(self.gi.read_bytes(), self.original)

    def test_a_steam_update_that_restores_gameinfo_is_repaired_for_a_mods_only_state(self):
        self.studio.enable_addons()
        self.gi.write_bytes(self.original)                       # Steam 'verify integrity'
        self.assertFalse(self.studio.addons_enabled())
        self.studio.enable_addons()
        self.assertTrue(self.studio.addons_enabled())
        self.assertEqual(self.gi.read_text(encoding='utf-8').count('citadel/addons'), 1)

    def test_a_foreign_edit_with_graphics_managed_asks_for_the_repair_button(self):
        settings = Settings()
        self.studio.apply(self.studio.plan(settings), settings)
        self.gi.write_bytes(b'// patched\n' + self.gi.read_bytes())
        with self.assertRaises(ValueError):
            self.studio.enable_addons()

    def test_malformed_files_are_refused_not_corrupted(self):
        self.gi.write_text('"GameInfo" { broken', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.studio.enable_addons()
        self.assertEqual(self.gi.read_text(encoding='utf-8'), '"GameInfo" { broken')

    def test_existing_path_from_another_manager_is_recognised_and_left_alone(self):
        self.gi.write_bytes((ASSETS / 'reference/gameinfo.gi').read_bytes())
        before = self.gi.read_bytes()
        self.assertTrue(self.studio.addons_enabled())
        self.studio.enable_addons()
        self.assertEqual(self.gi.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
