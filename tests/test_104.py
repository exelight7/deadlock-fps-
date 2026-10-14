import tempfile,unittest
from pathlib import Path
from deadlock_fps.settings import Settings,MAX_LEVEL,values
from deadlock_fps.core import Studio,ASSETS,flat,remove_keys
from PySide6.QtWidgets import QApplication
from deadlock_fps.ui import Window

class ExtendedLevels(unittest.TestCase):
    def test_expanded_range_and_distinct_groups(self):
        self.assertEqual(MAX_LEVEL,200)
        for level in [100,150,151,175,200]:Settings(level=level).validate()
        with self.assertRaises(ValueError):Settings(level=201).validate()
        self.assertEqual(Settings.at_level(999).level,200)
        for low,high in [(100,110),(110,125),(125,150),(150,175),(175,200)]:
            self.assertNotEqual(values(Settings.at_level(low)),values(Settings.at_level(high)))
        profile=Settings.at_level(200,aspect_ratio=3.5)
        self.assertEqual(Settings.from_dict(profile.to_dict()),profile)
        for level in range(101,201):
            s=Settings.at_level(level);self.assertEqual(s.textures,4);self.assertFalse(s.shadows);self.assertEqual(s.particles,0)
    def test_extended_keys_apply_and_undo_without_changing_resolution(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();gi=root/'game/citadel/gameinfo.gi';gi.parent.mkdir(parents=True)
            text=(ASSETS/'reference/gameinfo.gi').read_text()
            extra=['r_physics_particle_op_spawn_scale','snd_occlusion_bounces','snd_occlusion_rays','snd_steamaudio_max_occlusion_samples','snd_steamaudio_num_diffuse_samples']
            gi.write_text(remove_keys(text,['GameInfo','ConVars'],extra));original=gi.read_bytes()
            video=root/'game/citadel/cfg/video.txt';video.parent.mkdir();video.write_bytes((ASSETS/'reference/video.txt').read_bytes());original_video=video.read_bytes()
            studio=Studio(root,video);s=Settings.at_level(200,aspect_ratio=3.5);studio.apply(studio.plan(s),s)
            self.assertEqual(flat(gi.read_text(),['GameInfo','ConVars'])['r_physics_particle_op_spawn_scale'],'0')
            low=Settings.at_level(100,aspect_ratio=3.5);studio.apply(studio.plan(low),low)
            result=flat(gi.read_text(),['GameInfo','ConVars'])
            self.assertTrue(all(key not in result for key in extra));self.assertEqual(result['r_aspectratio'],'3.50')
            studio.restore();self.assertEqual(gi.read_bytes(),original);self.assertEqual(video.read_bytes(),original_video)
    def test_interface_above_150_keeps_aspect_independent(self):
        app=QApplication.instance() or QApplication([]);w=Window();w.guard_timer.stop();w.aspect.setValue(250)
        self.assertEqual(w.level.maximum(),200)
        w.level.setValue(175);self.assertEqual(w.settings().level,175);self.assertIn('175/200',w.level_title.text())
        w.level.setValue(200);self.assertEqual(w.settings().aspect_ratio,2.5);self.assertIn('200/200',w.level_title.text());w.close()
