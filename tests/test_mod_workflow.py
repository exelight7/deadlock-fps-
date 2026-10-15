"""Regression coverage for imports, isolated mod installs and desktop controls."""
import hashlib,threading,time,zipfile
from unittest.mock import patch
from PySide6.QtCore import QMimeData,QUrl,QThreadPool
from deadlock_fps.core import Studio,atomic
from deadlock_fps.settings import MODS
from deadlock_fps.mods import ModLibrary,HASHES,ImportCancelled,ImportReport
from deadlock_fps.mod_install import prepare_mods,commit_mods
from deadlock_fps.mod_ui import DropArea
import test_mod_inspector as fixtures
vpk=fixtures.vpk

class Imports(fixtures.GameFixture):
    def bundle(self):
        a,b=vpk(b'A'),vpk(b'B');path=self.folder/'bundle.zip'
        with zipfile.ZipFile(path,'w') as archive:
            archive.writestr('../../escape.vpk',a);archive.writestr('MODS/renamed.vpk',b);archive.writestr('ignored.vpk',b'unknown')
        return path,a,b
    def test_nested_zip_content_recognition_does_not_extract_paths(self):
        path,a,b=self.bundle()
        with patch.dict(HASHES,daylock=hashlib.sha256(a).hexdigest(),sinner=hashlib.sha256(b).hexdigest()):
            report=self.library.import_report([self.folder]);self.assertEqual(report.matched,{'daylock','sinner'});self.assertEqual(report.ignored,['ignored.vpk'])
            self.assertEqual(self.library.available(),report.matched)
        self.assertFalse((self.folder.parent/'escape.vpk').exists())
    def test_cancel_before_commit_preserves_library(self):
        path,a,b=self.bundle();event=threading.Event()
        with patch.dict(HASHES,daylock=hashlib.sha256(a).hexdigest(),sinner=hashlib.sha256(b).hexdigest()):
            with self.assertRaises(ImportCancelled):self.library.import_report([path],event,lambda _:event.set())
        self.assertFalse(self.library.cache.exists())
    def test_invalid_recognized_vpk_prevents_all_library_writes(self):
        good,bad=vpk(),b'bad-vpk-data';a=self.folder/'a.vpk';b=self.folder/'b.vpk';a.write_bytes(good);b.write_bytes(bad)
        with patch.dict(HASHES,daylock=hashlib.sha256(good).hexdigest(),sinner=hashlib.sha256(bad).hexdigest()):
            with self.assertRaises(ValueError):self.library.import_report([a,b])
        self.assertFalse(self.library.cache.exists())
    def test_failed_second_write_rolls_back_import(self):
        path,a,b=self.bundle();calls=[]
        def failing(target,data):
            calls.append(target)
            if len(calls)==2:raise OSError('disk full')
            atomic(target,data)
        with patch.dict(HASHES,daylock=hashlib.sha256(a).hexdigest(),sinner=hashlib.sha256(b).hexdigest()),patch('deadlock_fps.mods.atomic',side_effect=failing):
            with self.assertRaises(OSError):self.library.import_report([path])
        self.assertEqual(list(self.library.cache.glob('*')),[])
    def test_verification_cache_detects_replaced_file(self):
        data=vpk();path=self.library.cache/MODS['daylock'][0];path.parent.mkdir();path.write_bytes(data)
        with patch.dict(HASHES,daylock=hashlib.sha256(data).hexdigest()):
            self.assertIn('daylock',self.library.available());path.write_bytes(vpk(b'B'));self.assertNotIn('daylock',self.library.available())

class Installation(fixtures.GameFixture):
    def setUp(self):
        super().setUp();self.closed=patch('deadlock_fps.mod_install.ensure_closed');self.closed.start();self.data=vpk();self.hash=patch.dict(HASHES,daylock=hashlib.sha256(self.data).hexdigest());self.hash.start();self.library.cache.mkdir();(self.library.cache/MODS['daylock'][0]).write_bytes(self.data)
    def tearDown(self):self.hash.stop();self.closed.stop();super().tearDown()
    def test_install_remove_without_video_account_preserves_graphics(self):
        gi=self.gi.read_bytes();video=self.video.read_bytes();prepared=prepare_mods(self.root,self.library,('daylock',));self.assertEqual(self.gi.read_bytes(),gi)
        commit_mods(prepared,self.library);self.assertFalse(Studio(self.root).graphics_managed(Studio(self.root).state()));self.assertEqual(self.video.read_bytes(),video)
        from deadlock_fps.core import flat
        self.assertEqual(flat(gi.decode('utf-8-sig'),['GameInfo','ConVars']),flat(self.gi.read_text(encoding='utf-8-sig'),['GameInfo','ConVars']))
        commit_mods(prepare_mods(self.root,self.library,()),self.library);self.assertEqual(self.video.read_bytes(),video)
        self.assertNotIn('citadel/fps_studio',self.gi.read_text(encoding='utf-8-sig'));self.assertFalse((self.root/'game/citadel/fps_studio'/MODS['daylock'][0].split(' - ')[0]).exists())
    def test_stale_review_rejects_changed_manifest_before_writes(self):
        prepared=prepare_mods(self.root,self.library,('daylock',));studio=Studio(self.root);atomic(studio.manifest,b'{"files":{},"other":"changed"}');before=self.gi.read_bytes()
        with self.assertRaisesRegex(ValueError,'تغيّرت'):commit_mods(prepared,self.library)
        self.assertEqual(self.gi.read_bytes(),before)
    def test_changed_source_after_review_blocks_install(self):
        prepared=prepare_mods(self.root,self.library,('daylock',));(self.library.cache/MODS['daylock'][0]).write_bytes(vpk(b'changed'));before=self.gi.read_bytes()
        with self.assertRaises(ValueError):commit_mods(prepared,self.library)
        self.assertEqual(self.gi.read_bytes(),before)
    def test_repair_mod_only_state_never_applies_graphics_defaults(self):
        original=self.gi.read_bytes();video=self.video.read_bytes();commit_mods(prepare_mods(self.root,self.library,('daylock',)),self.library)
        # Simulate Steam rewriting gameinfo immediately after installation.
        self.gi.write_bytes(original);studio=Studio(self.root);studio.repair(self.library.cache)
        self.assertEqual(self.video.read_bytes(),video);self.assertIn('citadel/fps_studio',self.gi.read_text(encoding='utf-8-sig'))
        self.assertFalse(studio.graphics_managed(studio.state()))
        before=original.decode('utf-8-sig');after=self.gi.read_text(encoding='utf-8-sig')
        from deadlock_fps.core import flat
        for scope in (['GameInfo','ConVars'],['GameInfo','SceneSystem']):self.assertEqual(flat(before,scope),flat(after,scope))
        state=studio.state();state.pop('graphics_managed');self.assertFalse(studio.graphics_managed(state))

class DesktopControls(fixtures.GameFixture):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        super().setUp();from deadlock_fps.ui import Window
        with patch('deadlock_fps.ui.detect_games',return_value=[]),patch('deadlock_fps.mods.ModLibrary.discover',return_value=[]),patch('deadlock_fps.server_ui.ServerStore',return_value=fixtures.ServerStore(self.folder/'servers')):self.window=Window()
        self.window.guard_timer.stop();self.window.servers.activate=lambda:None;self.window.path.setText(str(self.root));self.window.library=self.library
    def tearDown(self):
        self.window.close();QThreadPool.globalInstance().waitForDone(3000);self.app.processEvents();super().tearDown()
    def settle(self):
        deadline=time.monotonic()+5
        while self.window.mods_page.busy and time.monotonic()<deadline:
            QThreadPool.globalInstance().waitForDone(30);self.app.processEvents()
        self.assertFalse(self.window.mods_page.busy)

    def test_drag_accepts_local_files_only(self):
        mime=QMimeData();mime.setUrls([QUrl.fromLocalFile(str(self.folder/'mods.zip'))]);self.assertEqual(DropArea.paths(mime),[self.folder/'mods.zip'])
        mime.setUrls([QUrl('https://example.com/mods.zip')]);self.assertEqual(DropArea.paths(mime),[])
    def test_conflicting_import_requires_choice_and_card_highlights(self):
        page=self.window.mods_page;page.imported(ImportReport({'names','health','daylock'},[]));self.assertTrue(page.checks['daylock'].isChecked());self.assertFalse(page.checks['names'].isChecked());self.assertFalse(page.checks['health'].isChecked())
        page.checks['names'].setChecked(True);page.checks['health'].setChecked(True);self.assertFalse(page.checks['names'].isChecked());self.assertTrue(page.cards['health'].property('selected'))
    def test_graphics_slider_is_direct_and_synced(self):
        self.window.graphics_level.setValue(165);self.assertEqual(self.window.level.value(),165);self.window.level.setValue(75);self.assertEqual(self.window.graphics_level.value(),75)
    def test_stale_worker_cannot_clear_active_install(self):
        page=self.window.mods_page;page.sequence=2;page.stage='apply';page.finished(1);self.assertTrue(page.applying);page.finished(2);self.assertFalse(page.busy)
    def test_cancel_review_leaves_game_and_manifest_unchanged(self):
        data=vpk();self.library.cache.mkdir();(self.library.cache/MODS['daylock'][0]).write_bytes(data);self.window.mod_checks['daylock'].setChecked(True)
        with patch.dict(HASHES,daylock=hashlib.sha256(data).hexdigest()),patch('deadlock_fps.mod_install.ensure_closed'):
            prepared=prepare_mods(self.root,self.library,('daylock',));before=self.gi.read_bytes()
            with patch('deadlock_fps.mod_ui.ModReview.exec',return_value=0):self.window.mods_page.prepared(prepared)
        self.assertEqual(self.gi.read_bytes(),before);self.assertFalse(Studio(self.root).manifest.exists());self.assertFalse(self.window.mods_page.busy)

    def test_cancel_queued_preparation_never_opens_review(self):
        from unittest.mock import Mock
        page=self.window.mods_page;page.stage='prepare';page.cancel_event=threading.Event();page.cancel_event.set()
        with patch('deadlock_fps.mod_ui.ModReview') as review:page.prepared(Mock());review.assert_not_called()
        self.assertFalse(page.busy);self.assertFalse(Studio(self.root).manifest.exists())
    def test_compact_mod_workspace_keeps_cards_and_actions_visible(self):
        self.window.resize(940,680);self.window.navigate(2);self.window.show();self.app.processEvents()
        page=self.window.mods_page;self.assertFalse(self.window.hero.isVisible());self.assertTrue(page.actions_panel.isVisible())
        viewport=page.drop.parentWidget().parentWidget()
        card=page.cards['daylock'];self.assertTrue(viewport.rect().intersects(card.geometry()));self.assertGreaterEqual(viewport.height(),card.geometry().bottom())

    def test_background_import_and_single_confirm_install_end_to_end(self):
        data=vpk();source=self.folder/'renamed.vpk';source.write_bytes(data);before=self.video.read_bytes();page=self.window.mods_page
        from PySide6.QtWidgets import QDialog
        with patch.dict(HASHES,daylock=hashlib.sha256(data).hexdigest()),patch('deadlock_fps.mod_install.ensure_closed'),patch('deadlock_fps.mod_ui.ModReview.exec',return_value=QDialog.Accepted) as review:
            page.import_paths([source]);self.settle();self.assertTrue(page.checks['daylock'].isChecked());self.assertFalse(Studio(self.root).manifest.exists())
            page.install();self.settle();self.assertEqual(review.call_count,1)
        self.assertEqual(self.video.read_bytes(),before);self.assertEqual(Studio(self.root).state()['settings']['mods'],['daylock']);self.assertTrue(self.window.path.isEnabled());self.assertIn('تم',page.status.text())
