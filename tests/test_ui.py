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
            for field in ['scale','width','height','textures','shadows','fog','ao','particles','fps','cpu','engine']:
                self.assertEqual(getattr(s,field),getattr(expected,field))
        for i in range(4):w.navigate(i);self.assertEqual(w.stack.currentIndex(),i)
        w.close()
