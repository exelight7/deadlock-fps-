import os,tempfile,unittest,json
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QMessageBox
from deadlock_fps.servers import ServerStore,parse_catalog
from deadlock_fps.server_ui import ServerPage
from deadlock_fps.region_info import region_info,flag_icon
from deadlock_fps.core import ASSETS

DATA={'pops':{
 'dxb':{'desc':'Dubai (United Arab Emirates)','relays':[{'ipv4':'185.25.183.163','port_range':[27015,27060]}]},
 'fra':{'desc':'Frankfurt (Germany)','relays':[{'ipv4':'155.133.226.68','port_range':[27015,27060]}]},
 'atl':{'desc':'Atlanta (Georgia)','relays':[{'ipv4':'162.254.199.170','port_range':[27015,27060]}]},
}}

class Selection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtGui import QFontDatabase
        cls.app=QApplication.instance() or QApplication([]);cls.app.setStyle('Fusion')
        QFontDatabase.addApplicationFont(str(ASSETS/'fonts/NotoSansArabic.ttf'))
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=ServerStore(self.temp.name)
        self.store.cache.write_text(json.dumps(DATA))
        self.page=ServerPage(store=self.store);self.page.activate=lambda:None
        self.page.resize(1180,850);self.page.show();self.app.processEvents()
    def tearDown(self):self.page.close();self.temp.cleanup()
    def row(self,code):
        return next(r for r in range(self.page.table.rowCount()) if self.page.table.item(r,0).data(Qt.UserRole)==code)
    def click(self,code,col=1):
        p=self.page;index=p.table.model().index(self.row(code),col)
        QTest.mouseClick(p.table.viewport(),Qt.LeftButton,pos=p.table.visualRect(index).center())
    def test_click_any_column_space_and_checkbox_toggle_once(self):
        p=self.page;self.click('dxb');self.assertEqual(p.selected_codes(),{'dxb'})
        self.click('dxb',3);self.assertEqual(p.selected_codes(),set())
        self.click('dxb',0);self.assertEqual(p.selected_codes(),{'dxb'})
        p.table.setCurrentCell(self.row('dxb'),1);QTest.keyClick(p.table,Qt.Key_Space)
        self.assertEqual(p.selected_codes(),set())
    def test_hidden_selection_survives_search_refresh_and_bulk_select(self):
        p=self.page;self.click('fra');p.search.setText('الإمارات');p.select_visible()
        self.assertEqual(p.selected_codes(),{'dxb','fra'});self.assertIn('خارج البحث',p.selection_note.text())
        p.render(p.selected_codes());self.assertEqual(p.selected_codes(),{'dxb','fra'})
        p.clear_selection();self.assertEqual(p.selected_codes(),set());self.assertFalse(p.unblock_button.isEnabled());self.assertTrue(p.clear_block_button.isEnabled())
    def test_manual_dubai_selection_keeps_list_visible_and_search_is_explicit(self):
        p=self.page;self.click('fra');self.click('dxb');self.assertEqual(p.selected_codes(),{'dxb','fra'})
        self.assertEqual(p.search.text(),'');self.assertEqual(p.view_filter.currentIndex(),0)
        self.assertFalse(any(p.table.isRowHidden(row) for row in range(p.table.rowCount())))
        self.assertFalse(hasattr(p,'dubai_button'));self.assertFalse(hasattr(p,'select_dubai'))
        self.assertEqual(p.table.item(0,0).data(Qt.UserRole),'dxb')
        for term in ['دبي','الإمارات','Dubai','dxb','ae']:
            p.search.setText(term);self.assertFalse(p.table.isRowHidden(self.row('dxb')))
        p.search.clear();self.assertEqual(p.selected_codes(),{'dxb','fra'})
        self.assertFalse(any(p.table.isRowHidden(row) for row in range(p.table.rowCount())))
        self.assertFalse(self.store.state_path.exists())
    def test_blocked_and_selected_filters_are_independent_of_checks(self):
        p=self.page;self.store.record(['fra'],[]);p.render()
        p.view_filter.setCurrentIndex(1)
        self.assertTrue(p.table.isRowHidden(self.row('dxb')));self.assertFalse(p.table.isRowHidden(self.row('fra')))
        p.select_visible();p.view_filter.setCurrentIndex(2);self.assertEqual(p.selected_codes(),{'fra'})
        p.clear_selection();self.assertTrue(all(p.table.isRowHidden(r) for r in range(p.table.rowCount())))
    def test_all_snapshot_regions_have_renderable_country_flags(self):
        regions=parse_catalog(json.loads((ASSETS/'servers/deadlock-sdr.json').read_text()))
        for region in regions:
            info=region_info(region);self.assertTrue(info.country,region.code)
            self.assertFalse(flag_icon(info.country).pixmap(32,24).isNull(),region.code)
        atl=next(r for r in self.page.regions if r.code=='atl');self.assertEqual(region_info(atl).country,'us')
    def run_apply(self,action):
        p=self.page
        def start(fn,success,*args,**kwargs):success(fn())
        with patch('deadlock_fps.server_ui.ensure_closed'),patch('deadlock_fps.server_ui.QMessageBox.question',return_value=QMessageBox.Yes) as question,patch('deadlock_fps.server_ui.apply_elevated') as elevate,patch.object(p,'start',side_effect=start):
            p.apply_action(action);return question.call_args.args[2],elevate.call_args.args[0]
    def test_unblock_hidden_selected_and_clear_without_selection(self):
        p=self.page;regions=p.regions
        plan,blocked=self.store.plan(regions,{'dxb','fra'},'block');self.store.record(blocked,plan['new']);p.render()
        self.click('dxb');p.search.setText('Frankfurt')
        message,plan=self.run_apply('unblock');self.assertIn('فك الحظر',message)
        self.assertEqual(self.store.state()['blocked'],['fra']);self.assertTrue(all(r['ip']!='185.25.183.163' for r in plan['new']))
        p.clear_selection();message,plan=self.run_apply('clear')
        self.assertTrue(plan['reset']);self.assertEqual(plan['new'],[]);self.assertEqual(self.store.state()['blocked'],[])
        self.assertIn('تم فك كل حظر',p.status.text())
    def test_cancel_does_not_change_firewall_or_saved_state(self):
        self.click('dxb')
        with patch('deadlock_fps.server_ui.ensure_closed'),patch('deadlock_fps.server_ui.QMessageBox.question',return_value=QMessageBox.No),patch('deadlock_fps.server_ui.apply_elevated') as elevate:
            self.page.apply_action('only');elevate.assert_not_called()
        self.assertFalse(self.store.state_path.exists())
    def test_measurement_allows_selection_but_prevents_parallel_firewall_action(self):
        p=self.page
        with patch('deadlock_fps.server_ui.QThreadPool.globalInstance') as pool:
            p.start(lambda emit:None,lambda result:None,'قياس',progress=True)
            pool.return_value.start.assert_called_once()
            self.assertTrue(p.table.isEnabled());self.assertTrue(p.search.isEnabled());self.assertTrue(p.select_visible_button.isEnabled())
            self.click('dxb');self.assertEqual(p.selected_codes(),{'dxb'});self.assertFalse(p.unblock_button.isEnabled())
            p.finished();self.assertTrue(p.unblock_button.isEnabled())
    def assert_selected_paint(self,code,checked):
        from deadlock_fps.server_delegate import SELECTED_BACKGROUND
        self.app.processEvents();image=self.page.table.viewport().grab().toImage();row=self.row(code)
        for col in range(self.page.table.columnCount()):
            if self.page.table.isColumnHidden(col):continue
            rect=self.page.table.visualRect(self.page.table.model().index(row,col))
            color=image.pixelColor(rect.left()+5,rect.top()+8).name()
            self.assertEqual(color==SELECTED_BACKGROUND,checked,f'column {col}: {color}')
        rect=self.page.table.visualRect(self.page.table.model().index(row,0))
        color=image.pixelColor(rect.center().x()-6,rect.center().y()-8).name()
        self.assertEqual(color=='#e7c08a',checked,'checkbox paint must agree with model state')
    def test_checked_paint_banner_and_clear_follow_clicks_and_live_results(self):
        from deadlock_fps.ui import STYLE
        from deadlock_fps.servers import PingResult
        old=self.app.styleSheet();self.app.setStyleSheet(STYLE)
        try:
            p=self.page;self.assert_selected_paint('dxb',False)
            self.click('dxb',0)
            value=p.table.model().index(self.row('dxb'),0).data(Qt.CheckStateRole)
            self.assertIs(type(value),int);self.assertEqual(value,Qt.Checked.value)
            self.assertTrue(p.selection_note.property('hasSelection'));self.assertIn('تم تحديد 1',p.selection_note.text())
            self.assert_selected_paint('dxb',True)
            p.ping_progress(('dxb',PingResult(44.4,0,'ok','test')));self.assert_selected_paint('dxb',True)
            p.render(p.selected_codes());self.assert_selected_paint('dxb',True)
            p.sort_ping();self.assert_selected_paint('dxb',True)
            p.clear_selection();self.assert_selected_paint('dxb',False);self.assertFalse(p.selection_note.property('hasSelection'))
            self.click('dxb',1);self.assert_selected_paint('dxb',True)
            self.click('dxb',0);self.assert_selected_paint('dxb',False)
        finally:self.app.setStyleSheet(old)
    def test_legacy_enum_model_state_is_still_painted_checked_and_can_be_cleared(self):
        from deadlock_fps.ui import STYLE
        old=self.app.styleSheet();self.app.setStyleSheet(STYLE)
        try:
            index=self.page.table.model().index(self.row('dxb'),0)
            index.model().setData(index,Qt.Checked,Qt.CheckStateRole)
            self.assertEqual(self.page.selected_codes(),{'dxb'});self.assert_selected_paint('dxb',True)
            self.click('dxb',0);self.assertEqual(self.page.selected_codes(),set());self.assert_selected_paint('dxb',False)
        finally:self.app.setStyleSheet(old)
    def test_actions_stay_visible_in_main_window_and_measurement_keeps_selection_usable(self):
        from deadlock_fps.ui import Window
        w=Window();w.guard_timer.stop();w.servers.activate=lambda:None;w.resize(940,680);w.show();w.navigate(4);self.app.processEvents()
        for b in [w.servers.unblock_button,w.servers.clear_block_button]:
            self.assertTrue(b.isVisible());self.assertTrue(w.rect().contains(b.mapTo(w,b.rect().center())))
        self.assertTrue(w.servers.table.isColumnHidden(2));self.assertGreater(w.servers.table.columnWidth(1),200)
        w.resize(1280,900);self.app.processEvents();self.assertFalse(w.servers.table.isColumnHidden(2))
        self.assertFalse(w.actionbar.isVisible());w.navigate(0);self.assertTrue(w.actionbar.isVisible());self.assertFalse(w.servers.actions_panel.isVisible());w.close()
