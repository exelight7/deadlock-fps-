import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from PySide6.QtWidgets import QApplication
from deadlock_fps.ui import Window
from deadlock_fps.settings import PRESETS
class Interface(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_presets_roundtrip_and_navigation(self):
        w=Window()
        for key,expected in PRESETS.items():
            w.load_preset(key);s=w.settings()
            for field in ['textures','shadows','fog','ao','particles','fps','cpu','engine']:
                self.assertEqual(getattr(s,field),getattr(expected,field))
        for i in range(4):w.navigate(i);self.assertEqual(w.stack.currentIndex(),i)
        self.assertFalse(hasattr(w,'resolution'));self.assertNotIn('scale',w.controls)
        w.mod_checks['names'].setChecked(True);w.mod_checks['health'].setChecked(True)
        self.assertFalse(w.mod_checks['names'].isChecked());self.assertTrue(w.mod_checks['health'].isChecked())
        w.close()

    def test_guard_waits_for_stability_and_limits_repeated_resets(self):
        from unittest.mock import MagicMock,patch
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'video.txt';p.write_text('same rejected values')
            w=Window();w.guard_timer.stop();w.path.setText(d)
            studio=MagicMock();studio.drift.return_value=['video.txt'];studio.state.return_value={'files':{str(p):{}}};studio.repair.return_value='repaired'
            with patch.object(w,'studio',return_value=studio),patch('deadlock_fps.core.ensure_closed'):
                w.guard_tick();studio.repair.assert_not_called()
                for _ in range(6):w.guard_tick()
                self.assertEqual(studio.repair.call_count,2)
                w.guard.setChecked(False);w.guard_tick();self.assertEqual(studio.repair.call_count,2)
            w.close()
