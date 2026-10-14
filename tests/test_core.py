import copy, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from deadlock_fps import kv
from deadlock_fps.core import Studio, ASSETS, vpk_entries
from deadlock_fps.settings import Settings, PRESETS

class Operations(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve()/'Deadlock'
        self.gi=self.root/'game/citadel/gameinfo.gi';self.gi.parent.mkdir(parents=True)
        self.gi.write_bytes((ASSETS/'reference/gameinfo.gi').read_bytes())
        self.video=self.root/'game/citadel/cfg/video.txt';self.video.parent.mkdir()
        self.video.write_bytes((ASSETS/'reference/video.txt').read_bytes())
        self.original_gi=self.gi.read_bytes();self.original_video=self.video.read_bytes()
        self.studio=Studio(self.root,self.video)
    def tearDown(self):self.temp.cleanup()
    def apply(self,s):self.studio.apply(self.studio.plan(s),s)
    def test_preview_has_no_side_effects(self):
        self.studio.plan(Settings());self.assertEqual(self.gi.read_bytes(),self.original_gi)
        self.assertFalse(self.studio.store.exists())
    def test_preserves_gpu_and_unknown_fields(self):
        text=self.video.read_text().replace('"Version"','"custom_key" "keep"\n"Version"')
        self.video.write_text(text);self.apply(Settings())
        result=self.video.read_text();self.assertIn('"VendorID"\t\t"4318"',result);self.assertIn('"custom_key" "keep"',result)
    def test_repeat_and_restore_exact_bytes(self):
        self.apply(Settings());self.apply(copy.deepcopy(PRESETS['ultra']))
        self.assertFalse(self.studio.plan(copy.deepcopy(PRESETS['ultra'])))
        self.studio.restore();self.assertEqual(self.gi.read_bytes(),self.original_gi);self.assertEqual(self.video.read_bytes(),self.original_video)
    def test_turn_engine_off_restores_baseline(self):
        self.apply(Settings());s=Settings(engine=False);self.apply(s)
        self.assertEqual(self.gi.read_bytes(),self.original_gi)
    def test_external_patch_blocks_overwrite_and_restore(self):
        self.apply(Settings());self.gi.write_bytes(b'// patched\n'+self.gi.read_bytes())
        with self.assertRaises(ValueError):self.studio.plan(Settings())
        with self.assertRaises(ValueError):self.studio.restore()
        self.studio.restore(True);self.assertEqual(self.gi.read_bytes(),self.original_gi)
        self.assertTrue(list((self.studio.store/'history').rglob('state.json')))
    def test_rollback_on_failed_second_write(self):
        import deadlock_fps.core as core
        original=core.atomic;calls=0
        def fail_once(p,b):
            nonlocal calls
            if p in (self.gi,self.video):
                calls+=1
                if calls==2:raise OSError('simulated disk error')
            return original(p,b)
        with patch.object(core,'atomic',side_effect=fail_once):
            with self.assertRaises(OSError):self.apply(Settings())
        self.assertEqual(self.gi.read_bytes(),self.original_gi);self.assertEqual(self.video.read_bytes(),self.original_video)
        self.assertFalse(self.studio.manifest.exists())
    def test_running_game_blocks_apply(self):
        fake=type('Process',(),{'info':{'name':'deadlock.exe'}})()
        with patch('deadlock_fps.core.psutil.process_iter',return_value=[fake]):
            with self.assertRaises(ValueError):self.studio.plan(Settings())
    def test_symlink_outside_game_rejected(self):
        target=Path(self.temp.name)/'outside';target.mkdir()
        (self.root/'game/citadel/fps_studio').symlink_to(target,target_is_directory=True)
        with self.assertRaises(ValueError):self.studio.plan(Settings())
    def test_mods_conflict_rejected(self):
        with self.assertRaises(ValueError):Settings(mods=('names','health')).validate()
    def test_mod_install_deselect_and_restore(self):
        import struct
        from deadlock_fps.settings import MODS
        folder=Path(self.temp.name)/'mods';folder.mkdir()
        entry=struct.pack('<IHHIIH',0,0,0x7fff,0,4,0xffff)
        tree=b'txt\0test\0asset\0'+entry+b'\0\0\0'
        data=struct.pack('<III',0x55aa1234,1,len(tree))+tree+b'test'
        source=folder/MODS['daylock'][0];source.write_bytes(data)
        settings=Settings(mods=('daylock',))
        plan=self.studio.plan(settings,folder);self.studio.apply(plan,settings)
        target=self.root/'game/citadel/fps_studio/pak01_dir.vpk'
        self.assertEqual(target.read_bytes(),data)
        self.assertIn('citadel/fps_studio',self.gi.read_text())
        self.apply(Settings());self.assertFalse(target.exists())
        self.assertNotIn('citadel/fps_studio',self.gi.read_text())
        self.studio.restore();self.assertEqual(self.gi.read_bytes(),self.original_gi)
    def test_wrong_video_rejected(self):
        with self.assertRaises(ValueError):Studio(self.root,Path(self.temp.name)/'arbitrary.txt')

class KeyValues(unittest.TestCase):
    def test_lossless_scoped_edit(self):
        text='GameInfo { // hello\n A { x "1" x "2" } B { x "3" } }'
        out=kv.update(text,['GameInfo','A'],{'x':'4','y':'5'})
        self.assertIn('B { x "3" }',out);self.assertIn('// hello',out)
        a=kv.section(out,['GameInfo','A']);self.assertEqual([n.value for n in a.children if n.key=='x'],['4','4'])
    def test_search_path_idempotent(self):
        text=(ASSETS/'reference/gameinfo.gi').read_text();new=kv.add_search_path(text)
        self.assertEqual(new,kv.add_search_path(new))
    def test_malformed_is_rejected(self):
        for text in ['A { b "1"','A }','}']:
            with self.assertRaises(ValueError):kv.parse(text)
    def test_invalid_vpk(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.vpk';p.write_bytes(b'not a mod')
            with self.assertRaises(ValueError):vpk_entries(p)
if __name__=='__main__':unittest.main()
