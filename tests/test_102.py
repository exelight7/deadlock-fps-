import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from deadlock_fps import kv
from deadlock_fps.core import Studio,ASSETS,flat
from deadlock_fps.settings import Settings,values,PRESETS

class Repair(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve()/'Deadlock'
        self.gi=self.root/'game/citadel/gameinfo.gi';self.gi.parent.mkdir(parents=True);self.gi.write_bytes((ASSETS/'reference/gameinfo.gi').read_bytes())
        self.video=self.root/'game/citadel/cfg/video.txt';self.video.parent.mkdir();self.video.write_bytes((ASSETS/'reference/video.txt').read_bytes())
        self.studio=Studio(self.root,self.video);self.settings=Settings.at_level(80)
        self.studio.apply(self.studio.plan(self.settings),self.settings)
    def tearDown(self):self.temp.cleanup()
    def test_numeric_reformat_and_screen_changes_are_not_reset(self):
        text=kv.update(self.video.read_text(),['video.cfg'],{'setting.r_effects_bloom':'0','setting.r_texture_stream_mip_bias':'4.000000','setting.defaultres':'2560','setting.mat_viewportscale':'0.91'})
        self.video.write_text(text);self.assertEqual(self.studio.drift(),[])
        self.studio.plan(self.settings)
    def test_actual_reset_repaired_preserves_resolution_and_new_fields(self):
        text=kv.update(self.video.read_text(),['video.cfg'],{'setting.r_texture_stream_mip_bias':'0','setting.defaultres':'2560','setting.mat_viewportscale':'0.91','new_driver_setting':'keep'})
        self.video.write_text(text);self.assertIn('video.txt',self.studio.drift())
        self.studio.repair(self.temp.name)
        result=flat(self.video.read_text(),['video.cfg']);self.assertEqual(result['setting.r_texture_stream_mip_bias'],'4');self.assertEqual(result['setting.defaultres'],'2560');self.assertEqual(result['setting.mat_viewportscale'],'0.91');self.assertEqual(result['new_driver_setting'],'keep')
        self.assertEqual(self.studio.drift(),[])
        self.studio.restore();self.assertEqual(flat(self.video.read_text(),['video.cfg'])['new_driver_setting'],'keep')
    def test_game_patch_keeps_unrelated_schema_and_restores_managed_values(self):
        text=self.gi.read_text().replace('GameInfo','GameInfo // new patch',1)
        text=kv.update(text,['GameInfo','ConVars'],{'r_grass_quality':'2','new_valve_convar':'keep'})
        self.gi.write_text(text);self.studio.repair(self.temp.name)
        result=self.gi.read_text();self.assertIn('// new patch',result);self.assertEqual(flat(result,['GameInfo','ConVars'])['new_valve_convar'],'keep');self.assertEqual(flat(result,['GameInfo','ConVars'])['r_grass_quality'],'0')
        self.studio.restore();self.assertIn('new_valve_convar',self.gi.read_text())
    def test_repair_stops_while_game_running(self):
        before=self.video.read_bytes();fake=type('Process',(),{'info':{'name':'deadlock.exe'}})()
        with patch('deadlock_fps.core.psutil.process_iter',return_value=[fake]):
            with self.assertRaises(ValueError):self.studio.repair(self.temp.name)
        self.assertEqual(self.video.read_bytes(),before)
    def test_malformed_patch_not_overwritten(self):
        self.gi.write_text('GameInfo { broken');before=self.gi.read_bytes();state=self.studio.manifest.read_bytes()
        with self.assertRaises(ValueError):self.studio.repair(self.temp.name)
        self.assertEqual(self.gi.read_bytes(),before);self.assertEqual(self.studio.manifest.read_bytes(),state)
    def test_dial_can_lower_strength_and_remove_aggressive_keys(self):
        high=self.studio.plan(Settings.at_level(100));self.studio.apply(high,Settings.at_level(100))
        self.studio.apply(self.studio.plan(Settings.at_level(0)),Settings.at_level(0))
        result=flat(self.gi.read_text(),['GameInfo','ConVars'])
        # Original source has these keys too; it must restore original, not retain the highest override.
        self.assertEqual(result['r_texture_stream_mip_bias'],'0');self.assertEqual(result['r_shadows'],'1')
    def test_original_files_unchanged_by_failed_repair(self):
        self.video.write_text(kv.update(self.video.read_text(),['video.cfg'],{'setting.r_texture_stream_mip_bias':'0'}))
        before=self.video.read_bytes();manifest=self.studio.manifest.read_bytes()
        with patch.object(self.studio,'apply',side_effect=OSError('disk error')):
            with self.assertRaises(OSError):self.studio.repair(self.temp.name)
        self.assertEqual(self.video.read_bytes(),before);self.assertEqual(self.studio.manifest.read_bytes(),manifest)

class Levels(unittest.TestCase):
    def test_monotonic_control(self):
        previous=Settings.at_level(0)
        for level in range(1,101):
            current=Settings.at_level(level);self.assertGreaterEqual(current.textures,previous.textures);self.assertLessEqual(current.particles,previous.particles)
            for name in ['shadows','fog','bloom','ao']:self.assertLessEqual(getattr(current,name),getattr(previous,name))
            previous=current
        self.assertEqual(PRESETS['performance'].level,80)
        self.assertNotIn('r_aspectratio',values(previous)[1])
