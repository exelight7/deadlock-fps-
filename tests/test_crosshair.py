import unittest,tempfile,json,zlib,base64,os
from pathlib import Path
from unittest.mock import patch
from dataclasses import replace,asdict
from deadlock_fps import kv3
from deadlock_fps.crosshair import Crosshair,CrosshairStore,PRESETS,export_design,import_design,share_code,read_code

HEADER='<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->'
def fixture():
    fields='\n'.join('        '+k+' = '+json.dumps(v) for k,v in Crosshair().native().items())
    return HEADER+'\n{\n base = {\n'+fields+'\n        mouse_sensitivity = "1.25" // KEEP ME\n        future = [ resource:"a/b", { enabled = true } ]\n }\n heroes = { hero_test = { crosshair_pip_width = "7" mouse_sensitivity = "2.5" } }\n}\n'

class KV3(unittest.TestCase):
    def test_roundtrip_edits_preserve_comments_headers_arrays_and_unrelated_values(self):
        text=fixture().replace('\n','\r\n')
        changed=kv3.update(text,['base'],{'crosshair_pip_width':'2','crosshair_color_g':'123'})
        self.assertIn('mouse_sensitivity = "1.25" // KEEP ME',changed)
        self.assertIn('future = [ resource:"a/b", { enabled = true } ]',changed)
        self.assertEqual(kv3.fields(changed,['heroes','hero_test'])['crosshair_pip_width'],'7')
        self.assertTrue(changed.startswith(HEADER+'\r\n'));self.assertNotIn('\n',changed.replace('\r\n',''))
        self.assertEqual(kv3.fields(changed,['base'])['crosshair_pip_width'],'2')
    def test_missing_duplicate_binary_malformed_and_deep_data_are_rejected(self):
        for text in ['binary',HEADER+'\n{base={ x = } }',HEADER+'\n{base={} base={}}',HEADER+'\n{base={a="unterminated}}']:
            with self.assertRaises(ValueError):kv3.section(text,['base'])
        with self.assertRaises(ValueError):kv3.fields(HEADER+'\n{base={x="1" x="2"}}',['base'])
        with self.assertRaises(ValueError):kv3.parse(HEADER+'\n'+(' { x = '*70)+'"a"'+(' } '*70))
    def test_insert_and_delete_only_target_key(self):
        text=HEADER+'\n{base={mouse_sensitivity="1"}heroes={}}'
        out=kv3.update(text,['base'],{'crosshair_pip_width':'2'})
        self.assertEqual(kv3.fields(out,['base'])['crosshair_pip_width'],'2')
        out=kv3.update(out,['base'],{'crosshair_pip_width':None})
        self.assertEqual(kv3.fields(out,['base']),{'mouse_sensitivity':'1'})

class Models(unittest.TestCase):
    def test_native_json_and_code_roundtrips_for_all_presets(self):
        for model in PRESETS.values():
            self.assertEqual(Crosshair.from_native(model.native()),model)
            self.assertEqual(import_design(export_design(model)),model)
            self.assertEqual(read_code(share_code(model)),model)
    def test_validation_rejects_injection_nonfinite_unknown_and_wrong_types(self):
        for data in [{'color':'#abc;cmd'}, {'width':float('nan')}, {'length':999}, {'static':'true'}, {'width':True}, {'commands':'exec exploit'}]:
            with self.assertRaises(ValueError):Crosshair.from_dict(data)
    def test_pixel_dimensions_match_native_integer_fields(self):
        model=replace(Crosshair(),width=3.6,length=9.4,dot=5.8,dot_border_gap=2.7,gap=-8.6,opacity=.78)
        native=model.native();self.assertEqual(native['crosshair_pip_width'],'4');self.assertEqual(native['crosshair_pip_height'],'9')
        self.assertEqual(native['crosshair_dot_size'],'6');self.assertEqual(native['crosshair_dot_outline_gap'],'3')
        self.assertEqual(native['crosshair_pip_gap'],'-8.6');self.assertEqual(native['crosshair_pip_opacity'],'0.78')
        with self.assertRaises(ValueError):import_design({'format':'deadlock-toolbox-crosshair','version':True,'design':{}})
    def test_share_codes_are_bounded_and_not_confused_with_native_dl_codes(self):
        for code in ['DL.wrong','DLTB1.'+'A'*5000,'DLTB1.!','DLTB1.AAAA']:
            with self.assertRaises(ValueError):read_code(code)
        bomb='DLTB1.'+base64.urlsafe_b64encode(zlib.compress(b'A'*100000)).decode().rstrip('=')
        with self.assertRaises(ValueError):read_code(bomb)

class Files(unittest.TestCase):
    def setUp(self):
        # Windows temporary folders can use 8.3 names (RUNNER~1). Match the
        # canonical paths returned by real video_files(), rather than mocking
        # it with aliases that the store correctly rejects after resolving.
        self.temp=tempfile.TemporaryDirectory();self.root=(Path(self.temp.name)/'Deadlock').resolve();(self.root/'game/citadel/cfg').mkdir(parents=True)
        (self.root/'game/citadel/gameinfo.gi').write_text('GameInfo {}')
        self.video=(Path(self.temp.name)/'Steam/userdata/1/1422450/local/cfg/video.txt').resolve();self.video.parent.mkdir(parents=True);self.video.write_text('video.cfg {}')
        self.remote=self.video.parent.parent.parent/'remote/cfg/citadel_hero_settings.lst';self.remote.parent.mkdir(parents=True)
        self.local=self.root/'game/citadel/cfg/citadel_hero_settings.lst'
        for p in (self.local,self.remote):p.write_bytes(fixture().encode())
        self.patch=patch('deadlock_fps.crosshair.video_files',return_value=[self.video]);self.patch.start()
        self.closed=patch('deadlock_fps.crosshair.ensure_closed');self.closed.start()
        self.store=CrosshairStore(self.root,self.video)
    def tearDown(self):self.patch.stop();self.closed.stop();self.temp.cleanup()
    def test_reads_native_and_plans_both_files_without_writes(self):
        before={p:p.read_bytes() for p in (self.local,self.remote)}
        model,paths=self.store.current();self.assertEqual(model,Crosshair());self.assertEqual(len(paths),2)
        plan=self.store.plan(PRESETS['نقطة خضراء']);self.assertEqual(len(plan.changes),2)
        self.assertEqual(before,{p:p.read_bytes() for p in before});self.assertFalse(self.store.folder.exists())
    def test_apply_only_crosshair_preserves_hero_sensitivity_and_creates_restorable_backup(self):
        original={p:p.read_bytes() for p in (self.local,self.remote)};self.store.apply(self.store.plan(PRESETS['صليب صغير']))
        for p in original:
            text=p.read_text();self.assertEqual(kv3.fields(text,['base'])['mouse_sensitivity'],'1.25')
            self.assertEqual(kv3.fields(text,['heroes','hero_test'])['crosshair_pip_width'],'7')
        self.assertTrue(self.store.can_restore());self.store.apply(self.store.restore_plan())
        self.assertEqual(original,{p:p.read_bytes() for p in original});self.assertFalse(self.store.can_restore())
    def test_opt_in_all_heroes_changes_only_reticle_and_restore_preserves_later_unrelated_changes(self):
        self.store.apply(self.store.plan(PRESETS['صليب صغير'],True))
        for p in (self.local,self.remote):
            text=p.read_text();self.assertEqual(kv3.fields(text,['heroes','hero_test'])['crosshair_pip_width'],'2')
            p.write_text(kv3.update(text,['heroes','hero_test'],{'mouse_sensitivity':'3.75'}))
        self.store.apply(self.store.restore_plan())
        for p in (self.local,self.remote):
            fields=kv3.fields(p.read_text(),['heroes','hero_test']);self.assertEqual(fields['mouse_sensitivity'],'3.75');self.assertEqual(fields['crosshair_pip_width'],'7')
    def test_stale_preview_running_game_invalid_second_file_and_foreign_account_are_rejected(self):
        plan=self.store.plan(PRESETS['دائرة']);self.local.write_text(fixture()+'\n// external change')
        with self.assertRaises(ValueError):self.store.apply(plan)
        with patch('deadlock_fps.crosshair.ensure_closed',side_effect=ValueError('running')):
            with self.assertRaises(ValueError):self.store.apply(self.store.plan(PRESETS['دائرة']))
        self.remote.write_text('invalid')
        with self.assertRaises(ValueError):self.store.plan(PRESETS['دائرة'])
        self.assertFalse(self.store.latest.exists())
        with self.assertRaises(ValueError):CrosshairStore(self.root,self.video.parent/'other.txt')
    def test_failed_second_write_rolls_back_first_file(self):
        from deadlock_fps.core import atomic
        before={p:p.read_bytes() for p in (self.local,self.remote)};plan=self.store.plan(PRESETS['دائرة'])
        def fail(path,data):
            if path==self.remote and data!=before[self.remote]:raise OSError('disk error')
            atomic(path,data)
        with patch('deadlock_fps.crosshair.atomic',side_effect=fail):
            with self.assertRaises(OSError):self.store.apply(plan)
        self.assertEqual(before,{p:p.read_bytes() for p in before});self.assertFalse(self.store.latest.exists())
    def test_corrupt_backup_is_rejected_without_touching_current_files(self):
        self.store.apply(self.store.plan(PRESETS['دائرة']));before={p:p.read_bytes() for p in (self.local,self.remote)}
        snapshot=json.loads(self.store.latest.read_text())['snapshot'];(self.store.folder/snapshot/'0.before').write_bytes(b'corrupt')
        with self.assertRaises(ValueError):self.store.restore_plan()
        self.assertEqual(before,{p:p.read_bytes() for p in before})
    def test_gui_cancel_save_apply_and_restore_use_scoped_backend(self):
        from PySide6.QtWidgets import QApplication,QDialog
        from deadlock_fps.crosshair_ui import CrosshairPage
        type(self).app=QApplication.instance() or QApplication([])
        p=CrosshairPage(lambda:(str(self.root),str(self.video)),library=Path(self.temp.name)/'profiles.json');p.resize(900,650);p.show();self.app.processEvents()
        before={q:q.read_bytes() for q in (self.local,self.remote)};p.set_model(PRESETS['نقطة خضراء'],True)
        with patch('deadlock_fps.crosshair_ui.ensure_closed'),patch('deadlock_fps.crosshair_ui.QDialog.exec',return_value=QDialog.Rejected):p.review()
        self.assertEqual(before,{q:q.read_bytes() for q in before});self.assertFalse(self.store.folder.exists())
        with patch('deadlock_fps.crosshair_ui.QInputDialog.getText',return_value=('تجربة',True)):p.save_profile()
        self.assertEqual(import_design(json.loads(p.library.read_text())['تجربة']),PRESETS['نقطة خضراء'])
        with patch('deadlock_fps.crosshair_ui.ensure_closed'),patch('deadlock_fps.crosshair_ui.QDialog.exec',return_value=QDialog.Accepted):p.review()
        self.assertEqual(self.store.current()[0],PRESETS['نقطة خضراء']);self.assertTrue(p.restore_button.isEnabled())
        with patch('deadlock_fps.crosshair_ui.ensure_closed'),patch('deadlock_fps.crosshair_ui.QDialog.exec',return_value=QDialog.Accepted):p.review(True)
        self.assertEqual(before,{q:q.read_bytes() for q in before});self.assertFalse(p.restore_button.isEnabled());p.close()
    def test_same_design_does_not_write_and_unsupported_files_are_not_created(self):
        self.assertFalse(self.store.plan(Crosshair()).changes)
        for p in (self.local,self.remote):p.unlink()
        with self.assertRaises(ValueError):self.store.current()
        self.assertFalse(self.store.folder.exists())

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
class Interface(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([]);cls.app.setStyle('Fusion')
    def test_preview_is_idle_event_driven_and_reuses_background(self):
        from PySide6.QtCore import QTimer
        from deadlock_fps.crosshair_ui import CrosshairPreview
        preview=CrosshairPreview();preview.resize(340,280);preview.show();self.app.processEvents()
        key=preview.background.cacheKey();count=preview.paint_count
        for _ in range(5):self.app.processEvents()
        self.assertEqual(preview.paint_count,count);self.assertFalse(preview.findChildren(QTimer))
        for i in range(100):preview.set_design(replace(PRESETS['صليب صغير'],gap=i/10))
        self.app.processEvents();self.assertLessEqual(preview.paint_count-count,3);self.assertEqual(preview.background.cacheKey(),key);preview.close()
    def test_editor_controls_presets_sharing_and_compact_layout_without_game_writes(self):
        from PySide6.QtWidgets import QMessageBox
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt
        from deadlock_fps.ui import Window
        w=Window();w.guard_timer.stop();w.servers.activate=lambda:None;w.show();w.navigate(5);self.app.processEvents();p=w.crosshair
        self.assertEqual(w.stack.currentIndex(),5);self.assertTrue(p.actions_panel.isVisible());self.assertFalse(w.actionbar.isVisible())
        p.presets.setCurrentIndex(0);self.assertEqual(p.model,PRESETS['صليب صغير'])
        p.controls['gap'][1].setValue(9.5);self.assertEqual(p.model.gap,9.5);self.assertEqual(p.preview.design,p.model)
        p.copy_code();self.assertEqual(read_code(self.app.clipboard().text()),p.model)
        w.resize(940,680);self.app.processEvents();self.assertEqual(w.size().toTuple(),(940,680));self.assertFalse(w.hero.isVisible())
        for b in [p.reload_button,p.apply_button,p.restore_button]:self.assertTrue(w.rect().contains(b.mapTo(w,b.rect().center())))
        w.navigate(0);self.assertTrue(w.hero.isVisible());self.assertFalse(p.actions_panel.isVisible());w.close()
    def test_native_base_gap_spread_and_static_reference_geometry(self):
        from deadlock_fps.crosshair_ui import CrosshairPreview
        p=CrosshairPreview();reference=replace(Crosshair(),gap=-8.6,dot=5.8,color='#aa0000',opacity=.78)
        p.set_design(reference)
        self.assertAlmostEqual(p.inner_gap,7.4)
        top=p.shapes[0][1].boundingRect();self.assertAlmostEqual(top.bottom(),-7.4);self.assertAlmostEqual(top.height(),16)
        p.set_design(replace(reference,static=True,gap=0,length=6));self.assertEqual(p.inner_gap,8)
        p.set_spread(25);self.assertEqual(p.inner_gap,8)
        p.set_design(replace(reference,static=False));self.assertAlmostEqual(p.inner_gap,24.4)
        self.assertEqual(p.design,reference);p.set_resolution_height(1440);self.assertEqual(p.design,reference)
    def test_gallery_catalog_search_selection_sources_and_no_idle_loop(self):
        from PySide6.QtCore import QTimer
        from deadlock_fps.crosshair_ui import CrosshairGallery
        from deadlock_fps.crosshair_catalog import PLAYERS,entries,shape
        g=CrosshairGallery({'تجربة':PRESETS['دائرة']});g.show();self.app.processEvents()
        self.assertEqual(g.tiles.count(),51);self.assertEqual(g.chosen.name,'Hydration')
        self.assertTrue(all(e.source.startswith('https://deadlocklabs.gg/crosshairs/pro/') for e in PLAYERS));self.assertEqual(len({e.key for e in PLAYERS}),9)
        for e in PLAYERS:e.design.validate()
        self.assertIn('Only',next(e.detail for e in PLAYERS if e.key=='dew'));self.assertIn('defaults',next(e.detail for e in PLAYERS if e.key=='crayon'))
        designs=entries();self.assertEqual(len(designs),50);self.assertEqual(len({e.key for e in designs}),50)
        self.assertEqual(len({json.dumps(e.design.native(),sort_keys=True) for e in designs}),50)
        for entry in designs:self.assertEqual(read_code(share_code(entry.design)),entry.design)
        g.filter.setCurrentIndex(2);g.shape_filter.setCurrentText('Ring');self.assertGreater(g.tiles.count(),5)
        for row in range(g.tiles.count()):
            key=g.tiles.item(row).data(256);self.assertEqual(shape(next(e.design for e in designs if e.key==key)),'Ring')
        g.shape_filter.setCurrentIndex(0);g.filter.setCurrentIndex(0)
        g.search.setText('mikael');self.app.processEvents();self.assertEqual(g.tiles.count(),1);self.assertEqual(g.chosen.name,'MikaelS');self.assertIn('2025-03',g.source.text())
        icon_key=g.icons['mikaels'].cacheKey();g.search.clear();g.search.setText('mikael');self.assertEqual(g.icons['mikaels'].cacheKey(),icon_key)
        g.search.setText('missing');self.assertIsNone(g.chosen);self.assertFalse(g.apply_button.isEnabled());self.assertFalse(g.edit_button.isEnabled())
        g.search.clear();g.filter.setCurrentIndex(3);self.assertEqual(g.tiles.count(),1);self.assertEqual(g.chosen.name,'تجربة')
        count=g.preview.paint_count;self.app.processEvents();count=g.preview.paint_count
        for _ in range(5):self.app.processEvents()
        self.assertEqual(g.preview.paint_count,count);self.assertFalse(g.findChildren(QTimer));g.finish(False);self.assertFalse(g.apply_requested);g.close()
    def test_gallery_choice_loads_editor_only_and_direct_apply_calls_review(self):
        from PySide6.QtWidgets import QDialog
        from deadlock_fps.crosshair_ui import CrosshairPage
        from deadlock_fps.crosshair_catalog import PLAYERS
        with tempfile.TemporaryDirectory() as folder:
            p=CrosshairPage(lambda:('',''),library=Path(folder)/'profiles.json');before=p.model
            with patch('deadlock_fps.crosshair_ui.CrosshairGallery') as make:
                gallery=make.return_value;gallery.exec.return_value=QDialog.Rejected;gallery.chosen=PLAYERS[1];gallery.apply_requested=True
                with patch.object(p,'review') as review:
                    p.open_gallery();self.assertEqual(p.model,before);review.assert_not_called()
                    gallery.exec.return_value=QDialog.Accepted;gallery.apply_requested=False;p.open_gallery();self.assertEqual(p.model,PLAYERS[1].design);review.assert_not_called()
                    gallery.apply_requested=True;p.open_gallery();review.assert_called_once_with()
            p.set_model(replace(Crosshair(),gap=-8.6,themed=True,collapse=True));p.make_static();self.assertTrue(p.model.static);self.assertFalse(p.model.themed);self.assertFalse(p.model.collapse);self.assertEqual(p.model.gap,-8.6)
            self.assertFalse(p.library.exists());p.close()
    def test_tabs_preview_settings_and_palette_preserve_design_and_stay_english(self):
        from PySide6.QtWidgets import QDialog,QLabel,QPushButton
        from PySide6.QtCore import Qt
        from deadlock_fps.crosshair_ui import CrosshairPage
        import re
        with tempfile.TemporaryDirectory() as folder:
            p=CrosshairPage(lambda:('',''),library=Path(folder)/'profiles.json');p.resize(760,540);p.show();self.app.processEvents()
            p.set_model(PRESETS['صليب صغير'],True);before=p.model
            for tab in range(p.tabs.count()):p.tabs.setCurrentIndex(tab);self.app.processEvents();self.assertEqual(p.model,before)
            p.pick_palette('#73e8ff');self.assertEqual(p.model.color,'#73e8ff');self.assertEqual(p.preview.design,p.model)
            p.controls['border'][1].setValue(3);self.assertEqual(p.model.border,3)
            before=p.model
            with patch('deadlock_fps.crosshair_ui.QDialog.exec',return_value=QDialog.Accepted):p.toggle_calibration()
            self.assertEqual(p.model,before);self.assertEqual(p.calibration.parent(),p);self.assertFalse(p.calibration.isVisible())
            p.reload_current();self.assertFalse(re.search('[\u0600-\u06ff]',p.status.text()))
            texts=[w.text() for w in p.findChildren((QLabel))]+[w.text() for w in p.findChildren(QPushButton)]
            self.assertFalse(any(re.search('[\u0600-\u06ff]',text) for text in texts));self.assertEqual(p.layoutDirection(),Qt.LeftToRight);p.close()
