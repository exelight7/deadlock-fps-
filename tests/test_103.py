import tempfile,unittest
from pathlib import Path
from deadlock_fps.core import Studio,ASSETS,flat
from deadlock_fps.settings import Settings,values
from PySide6.QtWidgets import QApplication
from deadlock_fps.ui import Window

class Aspect(unittest.TestCase):
    def test_range_and_legacy_profiles(self):
        for bad in [1.77,3.51,float('nan'),float('inf'),'3.50',True]:
            with self.assertRaises(ValueError):Settings(aspect_ratio=bad).validate()
        for value in [1.78,2.30,3.50]:
            s=Settings(aspect_ratio=value);s.validate();self.assertEqual(values(s)[1]['r_aspectratio'],f'{value:.2f}')
        self.assertIsNone(Settings.from_dict({'level':80}).aspect_ratio)
        self.assertEqual(Settings.from_dict(Settings(aspect_ratio=3.5).to_dict()).aspect_ratio,3.5)
    def test_apply_repair_and_restore_keep_screen_dimensions(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();gi=root/'game/citadel/gameinfo.gi';gi.parent.mkdir(parents=True);gi.write_bytes((ASSETS/'reference/gameinfo.gi').read_bytes())
            video=root/'game/citadel/cfg/video.txt';video.parent.mkdir();video.write_bytes((ASSETS/'reference/video.txt').read_bytes());before=flat(video.read_text(),['video.cfg']);original=gi.read_bytes()
            studio=Studio(root,video);s=Settings(aspect_ratio=3.5)
            studio.apply(studio.plan(s),s);self.assertEqual(flat(gi.read_text(),['GameInfo','ConVars'])['r_aspectratio'],'3.50')
            from deadlock_fps import kv
            gi.write_text(kv.update(gi.read_text(),['GameInfo','ConVars'],{'r_aspectratio':'1.78'}));studio.repair(d)
            self.assertEqual(flat(gi.read_text(),['GameInfo','ConVars'])['r_aspectratio'],'3.50')
            after=flat(video.read_text(),['video.cfg'])
            for key in ['setting.defaultres','setting.defaultresheight','setting.mat_viewportscale','setting.r_citadel_upscaling']:self.assertEqual(before[key],after[key])
            studio.restore();self.assertEqual(flat(gi.read_text(),['GameInfo','ConVars']),flat(original.decode(),['GameInfo','ConVars']))
            s=Settings(engine=False,aspect_ratio=3.5);studio.apply(studio.plan(s),s)
            self.assertEqual(flat(gi.read_text(),['GameInfo','ConVars'])['r_aspectratio'],'3.50')
    def test_slider_and_master_level_are_independent(self):
        app=QApplication.instance() or QApplication([]);w=Window();w.guard_timer.stop()
        self.assertEqual((w.aspect.minimum(),w.aspect.maximum()),(178,350));w.aspect.setValue(350)
        self.assertEqual(w.aspect_value.text(),'3.50');self.assertEqual(w.settings().aspect_ratio,3.5)
        w.level.setValue(25);self.assertEqual(w.settings().aspect_ratio,3.5)
        w.load_preset('ultra');self.assertEqual(w.settings().aspect_ratio,3.5)
        w.aspect.setValue(178);self.assertEqual(w.aspect_value.text(),'1.78');w.close()
