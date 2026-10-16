import hashlib,struct,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QApplication
from deadlock_fps.core import ASSETS
from deadlock_fps.settings import MODS
from deadlock_fps.mods import ModLibrary,HASHES
from deadlock_fps.mod_inspector import inspect_mods,require_mods
from deadlock_fps.servers import ServerStore

def vpk(payload=b'A'):
    tree=b'vmat\0materials\0shared\0'+struct.pack('<IHHIIH',0,0,0x7fff,0,len(payload),0xffff)+b'\0\0\0'
    return struct.pack('<III',0x55aa1234,1,len(tree))+tree+payload

class GameFixture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name).resolve();self.root=self.folder/'Deadlock';self.gi=self.root/'game/citadel/gameinfo.gi';self.gi.parent.mkdir(parents=True);self.gi.write_bytes((ASSETS/'reference/gameinfo.gi').read_bytes())
        self.video=self.root/'game/citadel/cfg/video.txt';self.video.parent.mkdir();self.video.write_bytes((ASSETS/'reference/video.txt').read_bytes());self.library=ModLibrary(self.folder/'mods')
        self.patches=[patch('deadlock_fps.core.ensure_closed')]
        for p in self.patches:p.start()
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()

class ModTests(GameFixture):
    def write_mod(self,key,payload=b'A',installed=False):
        data=vpk(payload);path=(self.root/'game/citadel/fps_studio'/MODS[key][0].split(' - ')[0]) if installed else self.library.cache/MODS[key][0];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);return path,hashlib.sha256(data).hexdigest()
    def test_missing_corrupted_and_valid_cache_are_distinguished_without_writes(self):
        self.assertTrue(inspect_mods(self.library,self.root,['daylock']).errors);path,sha=self.write_mod('daylock')
        with patch.dict(HASHES,daylock=sha):
            result=inspect_mods(self.library,self.root,['daylock']);self.assertFalse(result.errors);require_mods(self.library,self.root,['daylock']);self.assertEqual(path.read_bytes(),vpk())
            path.write_bytes(vpk(b'changed'));self.assertTrue(inspect_mods(self.library,self.root,['daylock']).errors)
            with self.assertRaises(ValueError):require_mods(self.library,self.root,['daylock'])
    def test_overlap_warning_known_conflict_and_installed_source_fallback(self):
        _,a=self.write_mod('daylock',b'A',True);_,b=self.write_mod('sinner',b'B')
        with patch.dict(HASHES,daylock=a,sinner=b):
            result=inspect_mods(self.library,self.root,['daylock','sinner']);self.assertFalse(result.errors);self.assertTrue(any('تداخل' in f.title for f in result.findings))
        self.assertTrue(any('تعارض' in f.title for f in inspect_mods(self.library,self.root,['names','health']).errors))
    def test_cancelled_scan_returns_no_partial_report(self):
        event=threading.Event();event.set();self.assertIsNone(inspect_mods(self.library,self.root,[],event))
    def test_installed_conflict_is_reported_even_when_no_mod_is_selected(self):
        _,a=self.write_mod('names',b'A',True);_,b=self.write_mod('health',b'B',True)
        with patch.dict(HASHES,names=a,health=b):self.assertTrue(any('تعارض' in f.title for f in inspect_mods(self.library,self.root).findings))

class Interface(GameFixture):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        super().setUp();from deadlock_fps.ui import Window
        with patch('deadlock_fps.ui.detect_games',return_value=[]),patch('deadlock_fps.mods.ModLibrary.discover',return_value=[]),patch('deadlock_fps.server_ui.ServerStore',return_value=ServerStore(self.folder/'servers')):self.window=Window()
        self.window.guard_timer.stop();self.window.servers.activate=lambda:None;self.window.path.setText(str(self.root));self.window.accounts.clear();self.window.accounts.addItem(str(self.video),str(self.video));self.window.library=self.library
    def tearDown(self):
        self.window.close();QThreadPool.globalInstance().waitForDone(3000);self.app.processEvents();super().tearDown()
    def test_only_inspector_is_added_and_removed_features_are_absent(self):
        from deadlock_fps.crosshair_ui import CrosshairGallery
        labels=[button.text() for button in self.window.nav]
        self.assertEqual(len(labels),8);self.assertEqual(labels[7],'فحص المودات')
        for name in ('Profiles Hub','Launch Center'):self.assertNotIn(name,labels)
        for name in ('profiles_page','launch_page','workspace'):self.assertFalse(hasattr(self.window,name))
        self.assertFalse(hasattr(self.window.crosshair,'favorite_button'))
        self.assertNotIn('المفضلة',[self.window.servers.view_filter.itemText(i) for i in range(self.window.servers.view_filter.count())])
        gallery=CrosshairGallery();self.assertNotIn('Favorites',[gallery.filter.itemText(i) for i in range(gallery.filter.count())]);gallery.close()
    def test_inspector_scans_at_minimum_size_without_writing_game_files(self):
        before={p:p.read_bytes() for p in (self.gi,self.video)}
        self.window.resize(940,680);self.window.show();self.window.navigate(7);self.app.processEvents();QThreadPool.globalInstance().waitForDone(3000);self.app.processEvents()
        page=self.window.inspector;self.assertFalse(page.busy);self.assertIsNotNone(page.result);self.assertEqual(page.table.rowCount(),4)
        self.assertFalse(self.window.hero.isVisible());self.assertFalse(self.window.actionbar.isVisible());self.assertTrue(page.scan_button.isVisible());self.assertEqual(before,{p:p.read_bytes() for p in before})
    def test_selection_change_invalidates_report_and_missing_selected_mod_blocks_apply(self):
        page=self.window.inspector;page.scan();QThreadPool.globalInstance().waitForDone(3000);self.app.processEvents();self.assertIsNotNone(page.result)
        self.window.mod_checks['daylock'].setChecked(True);self.assertIsNone(page.result)
        page.scan();QThreadPool.globalInstance().waitForDone(3000);self.app.processEvents();self.assertTrue(page.result.errors)
        before=self.gi.read_bytes()
        with patch('deadlock_fps.ui.QMessageBox.question') as confirm,patch('deadlock_fps.ui.QMessageBox.warning'):self.window.install_mods();confirm.assert_not_called()
        self.assertEqual(before,self.gi.read_bytes())

if __name__=='__main__':unittest.main()
