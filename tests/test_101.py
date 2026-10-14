import copy, hashlib, struct, tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
from deadlock_fps import kv
from deadlock_fps.core import Studio,ASSETS,RESOLUTION_KEYS
from deadlock_fps.settings import PRESETS,Settings,values,MODS
from deadlock_fps.mods import ModLibrary

class Resolution(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve()/'Deadlock'
        self.gi=self.root/'game/citadel/gameinfo.gi';self.gi.parent.mkdir(parents=True);self.gi.write_bytes((ASSETS/'reference/gameinfo.gi').read_bytes())
        self.video=self.root/'game/citadel/cfg/video.txt';self.video.parent.mkdir()
        text=kv.update((ASSETS/'reference/video.txt').read_text(),['video.cfg'],{'setting.defaultres':'2560','setting.defaultresheight':'1440','setting.mat_viewportscale':'0.77','setting.r_citadel_upscaling':'3'})
        self.video.write_text(text);self.studio=Studio(self.root,self.video)
    def tearDown(self):self.temp.cleanup()
    def protected(self):return [(n.key,n.value) for n in kv.section(self.video.read_text(),['video.cfg']).children if n.key in RESOLUTION_KEYS]
    def test_every_preset_preserves_resolution_and_upscaler(self):
        protected=self.protected()
        for preset in PRESETS.values():
            s=copy.deepcopy(preset);self.studio.apply(self.studio.plan(s),s);self.assertEqual(protected,self.protected())
            self.assertFalse(set(values(s)[0])&RESOLUTION_KEYS)
        self.studio.restore();self.assertEqual(protected,self.protected())
    def test_legacy_profile_ignores_resolution(self):
        s=Settings.from_dict({'scale':25,'width':640,'height':480,'textures':4})
        self.assertNotIn('scale',s.to_dict());self.assertEqual(s.textures,4)
    def test_upgrade_and_restore_do_not_restore_old_resolution(self):
        old=self.video.read_bytes();s=Settings();self.studio.apply(self.studio.plan(s),s)
        # Simulate a 1.0.0 managed file whose resolution differs from its original backup.
        text=kv.update(self.video.read_text(),['video.cfg'],{'setting.defaultres':'1920','setting.mat_viewportscale':'0.5'})
        self.video.write_text(text)
        state=self.studio.state();state['files'][str(self.video)]['applied']=hashlib.sha256(self.video.read_bytes()).hexdigest()
        import json
        self.studio.manifest.write_text(json.dumps(state));protected=self.protected()
        self.studio.apply(self.studio.plan(s),s);self.assertEqual(protected,self.protected())
        self.studio.restore();self.assertEqual(protected,self.protected())
    def test_mod_only_does_not_touch_video_or_engine_graphics(self):
        before_video=self.video.read_bytes();before_gi=self.gi.read_text()
        folder=Path(self.temp.name)/'mods';folder.mkdir();data=mod_data();(folder/MODS['daylock'][0]).write_bytes(data)
        plan=self.studio.plan_mods(('daylock',),folder);self.assertNotIn(self.video,plan)
        self.studio.apply(plan,Settings(mods=('daylock',)))
        self.assertEqual(self.video.read_bytes(),before_video)
        self.assertEqual([(n.key,n.value) for n in kv.section(self.gi.read_text(),['GameInfo','ConVars']).children],[(n.key,n.value) for n in kv.section(before_gi,['GameInfo','ConVars']).children])
        plan=self.studio.plan_mods((),folder);self.studio.apply(plan,Settings())
        self.assertNotIn('citadel/fps_studio',self.gi.read_text());self.assertEqual(self.video.read_bytes(),before_video)

def mod_data():
    tree=b'txt\0test\0asset\0'+struct.pack('<IHHIIH',0,0,0x7fff,0,4,0xffff)+b'\0\0\0'
    return struct.pack('<III',0x55aa1234,1,len(tree))+tree+b'test'

class Imports(unittest.TestCase):
    def test_zip_and_renamed_file_identified_by_content(self):
        data=mod_data()
        with tempfile.TemporaryDirectory() as d,patch.dict('deadlock_fps.mods.HASHES',{'daylock':hashlib.sha256(data).hexdigest()}):
            root=Path(d);library=ModLibrary(root/'cache');z=root/'mods.zip'
            with zipfile.ZipFile(z,'w') as archive:archive.writestr('../../renamed.vpk',data)
            self.assertEqual(library.import_sources([z]),{'daylock'});self.assertEqual(library.available(),{'daylock'})
            self.assertFalse((root.parent/'renamed.vpk').exists())
            renamed=root/'anything.vpk';renamed.write_bytes(data);self.assertEqual(library.import_sources([renamed]),{'daylock'})
    def test_unknown_mod_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'unknown.vpk';p.write_bytes(b'bad')
            with self.assertRaises(ValueError):ModLibrary(root/'cache').import_sources([p])
