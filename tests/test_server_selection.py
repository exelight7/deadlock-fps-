"""The Servers page: choosing regions, filtering, measuring, sorting, and the reviewed firewall actions."""
import json
import os
import tempfile
import unittest
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from unittest.mock import patch

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel

from deadlock_fps.core import ASSETS
from deadlock_fps.pages.servers import PingCell, ServerPage, ping_tone
from deadlock_fps.region_info import flag_icon, region_info
from deadlock_fps.servers import PingResult, ServerStore, parse_catalog

DATA = {'pops': {
    'dxb': {'desc': 'Dubai (United Arab Emirates)', 'relays': [{'ipv4': '185.25.183.163', 'port_range': [27015, 27060]}]},
    'fra': {'desc': 'Frankfurt (Germany)', 'relays': [{'ipv4': '155.133.226.68', 'port_range': [27015, 27060]}]},
    'atl': {'desc': 'Atlanta (Georgia)', 'relays': [{'ipv4': '162.254.199.170', 'port_range': [27015, 27060]}]},
}}


class Selection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtGui import QFontDatabase
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle('Fusion')
        QFontDatabase.addApplicationFont(str(ASSETS / 'fonts/NotoSansArabic.ttf'))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = ServerStore(self.temp.name)
        self.store.cache.write_text(json.dumps(DATA))
        self.page = ServerPage(store=self.store)
        self.page.activate = lambda: None
        self.page.resize(1180, 850)
        self.page.show()
        self.app.processEvents()

    def tearDown(self):
        self.page.close()
        self.temp.cleanup()

    def row(self, code):
        return self.page.find_row(code)

    def click(self, code, col=1):
        p = self.page
        index = p.table.model().index(self.row(code), col)
        QTest.mouseClick(p.table.viewport(), Qt.LeftButton, pos=p.table.visualRect(index).center())

    def check(self, code):
        """Press the checkbox itself, as a finger would."""
        box = self.page.boxes[code]
        QTest.mouseClick(box, Qt.LeftButton, pos=QPoint(8, box.height() // 2))          # the indicator is at the leading edge of the widget

    def test_a_click_on_any_column_the_checkbox_and_space_each_toggle_once(self):
        p = self.page
        self.click('dxb')
        self.assertEqual(p.selected_codes(), {'dxb'})
        self.click('dxb', 3)
        self.assertEqual(p.selected_codes(), set())
        self.check('dxb')
        self.assertEqual(p.selected_codes(), {'dxb'})
        p.table.setCurrentCell(self.row('dxb'), 1)
        QTest.keyClick(p.table, Qt.Key_Space)
        self.assertEqual(p.selected_codes(), set())

    def test_a_selection_hidden_by_the_search_survives_refresh_and_bulk_select(self):
        p = self.page
        self.click('fra')
        p.search.setText('الإمارات')
        p.select_visible()
        self.assertEqual(p.selected_codes(), {'dxb', 'fra'})
        self.assertIn('خارج البحث', p.selection_note.text())
        p.render(p.selected_codes())
        self.assertEqual(p.selected_codes(), {'dxb', 'fra'})
        p.clear_selection()
        self.assertEqual(p.selected_codes(), set())
        self.assertFalse(p.unblock_button.isEnabled())
        self.assertTrue(p.clear_block_button.isEnabled(), 'unblocking everything needs no selection')

    def test_selecting_never_hides_the_list_and_search_finds_by_name_country_and_code(self):
        p = self.page
        self.click('fra')
        self.click('dxb')
        self.assertEqual(p.selected_codes(), {'dxb', 'fra'})
        self.assertEqual((p.search.text(), p.view_filter.currentIndex()), ('', 0))
        self.assertFalse(any(p.table.isRowHidden(r) for r in range(p.table.rowCount())))
        self.assertEqual(p.table.item(0, 1).data(Qt.UserRole), 'dxb', 'Dubai comes first')
        for term in ('دبي', 'الإمارات', 'Dubai', 'dxb', 'ae'):
            p.search.setText(term)
            self.assertFalse(p.table.isRowHidden(self.row('dxb')), term)
        p.search.clear()
        self.assertEqual(p.selected_codes(), {'dxb', 'fra'})
        self.assertFalse(self.store.state_path.exists(), 'choosing writes nothing')

    def test_the_blocked_and_selected_views_follow_the_saved_block_and_the_checks(self):
        p = self.page
        self.store.record(['fra'], [])
        p.render()
        p.view_filter.setCurrentIndex(1)
        self.assertTrue(p.table.isRowHidden(self.row('dxb')))
        self.assertFalse(p.table.isRowHidden(self.row('fra')))
        p.select_visible()
        p.view_filter.setCurrentIndex(2)
        self.assertEqual(p.selected_codes(), {'fra'})
        p.clear_selection()
        self.assertTrue(all(p.table.isRowHidden(r) for r in range(p.table.rowCount())))
        self.assertFalse(p.empty.isHidden(), 'nothing matches: the empty state says so')

    def test_every_region_in_the_snapshot_has_a_flag(self):
        regions = parse_catalog(json.loads((ASSETS / 'servers/deadlock-sdr.json').read_text()))
        for region in regions:
            info = region_info(region)
            self.assertTrue(info.country, region.code)
            self.assertFalse(flag_icon(info.country).pixmap(32, 24).isNull(), region.code)
        atl = next(r for r in self.page.regions if r.code == 'atl')
        self.assertEqual(region_info(atl).country, 'us')

    def test_ping_states_are_shown_in_words_and_the_error_is_not_a_full_loss(self):
        p = self.page
        row = self.row('dxb')
        self.assertEqual(p.table.item(row, 3).text(), 'لم يُقَس')
        p.ping_progress(('dxb', PingResult(120.0, 0, 'ok', 'actual')))
        self.assertEqual(p.table.item(self.row('dxb'), 3).text(), '120.0')
        p.ping_progress(('fra', PingResult(None, None, 'error', 'tool not installed')))
        self.assertEqual(p.table.item(self.row('fra'), 3).text(), 'تعذر القياس')
        self.assertNotIn('100%', p.table.item(self.row('fra'), 3).toolTip())
        p.ping_progress(('atl', PingResult(None, 100, 'no_reply', 'no reply')))
        self.assertEqual(p.table.item(self.row('atl'), 3).text(), 'لا رد')

    def test_the_colour_of_a_ping_follows_its_speed(self):
        self.assertEqual([ping_tone(v) for v in (20, 60, 90, 120, 200, None)],
                         ['color.success.text', 'color.success.text', 'color.warning.text', 'color.warning.text', 'color.danger.text', None])
        self.assertTrue(PingCell('30', 30.0) < PingCell('120', 120.0))
        self.assertTrue(PingCell('30', 30.0) < PingCell('—', None), 'unmeasured rows come last')

    def test_sorting_by_ping_keeps_each_checkbox_with_its_region(self):
        p = self.page
        self.check('dxb')
        p.ping_progress(('dxb', PingResult(120.0, 0, 'ok', 'A')))
        p.ping_progress(('fra', PingResult(30.0, 0, 'ok', 'B')))
        p.ping_progress(('atl', PingResult(70.0, 0, 'ok', 'C')))
        p.sort_ping()
        order = [p.table.item(r, 1).data(Qt.UserRole) for r in range(p.table.rowCount())]
        self.assertEqual(order, ['fra', 'atl', 'dxb'])
        self.assertEqual(p.selected_codes(), {'dxb'})
        self.assertTrue(p.boxes['dxb'].isChecked())
        p.ping_progress(('fra', PingResult(500.0, 0, 'ok', 'slow now')))
        order = [p.table.item(r, 1).data(Qt.UserRole) for r in range(p.table.rowCount())]
        self.assertEqual(order, ['atl', 'dxb', 'fra'], 'a new answer moves the row, the selection stays')
        self.assertEqual(p.selected_codes(), {'dxb'})

    def run_apply(self, action, answer=True):
        p = self.page

        def start(fn, success, *args, **kwargs):
            success(fn())
        with patch('deadlock_fps.pages.servers.ensure_closed'), patch('deadlock_fps.pages.servers.confirm', return_value=answer) as question, \
                patch('deadlock_fps.pages.servers.apply_elevated') as elevate, patch.object(p, 'start', side_effect=start):
            p.apply_action(action)
            return (question.call_args.args[2] if question.called else ''), (elevate.call_args.args[0] if elevate.called else None), elevate

    def test_unblock_a_hidden_selected_region_and_unblock_everything_without_a_selection(self):
        p = self.page
        plan, blocked = self.store.plan(p.regions, {'dxb', 'fra'}, 'block')
        self.store.record(blocked, plan['new'])
        p.render()
        self.click('dxb')
        p.search.setText('Frankfurt')
        message, plan, _ = self.run_apply('unblock')
        self.assertIn('فك الحظر', message)
        self.assertEqual(self.store.state()['blocked'], ['fra'])
        self.assertTrue(all(r['ip'] != '185.25.183.163' for r in plan['new']))
        p.clear_selection()
        message, plan, _ = self.run_apply('clear')
        self.assertTrue(plan['reset'])
        self.assertEqual(plan['new'], [])
        self.assertEqual(self.store.state()['blocked'], [])
        self.assertIn('تم فك كل حظر', p.status.text())

    def test_saying_no_in_the_review_changes_neither_the_firewall_nor_the_saved_state(self):
        self.click('dxb')
        _, _, elevate = self.run_apply('only', answer=False)
        elevate.assert_not_called()
        self.assertFalse(self.store.state_path.exists())

    def test_blocking_needs_a_selection_and_says_so_without_touching_anything(self):
        p = self.page
        _, _, elevate = self.run_apply('block')
        elevate.assert_not_called()
        self.assertTrue(any('حدد منطقة' in l.text() for l in p.findChildren(QLabel)))

    def test_a_refused_administrator_prompt_is_a_danger_notice_and_nothing_is_saved(self):
        p = self.page
        self.click('dxb')

        def start(fn, success, *args, **kwargs):
            try:
                success(fn())
            except Exception as error:
                p.failed(str(error))
        with patch('deadlock_fps.pages.servers.ensure_closed'), patch('deadlock_fps.pages.servers.confirm', return_value=True), \
                patch('deadlock_fps.pages.servers.apply_elevated', side_effect=PermissionError('refused')), patch.object(p, 'start', side_effect=start):
            p.apply_action('block')
        self.assertFalse(self.store.state_path.exists())
        self.assertTrue(any('refused' in l.text() for l in p.findChildren(QLabel)))

    def test_measuring_allows_choosing_but_never_a_parallel_firewall_action(self):
        p = self.page
        with patch('deadlock_fps.pages.servers.QThreadPool.globalInstance') as pool:
            p.start(lambda emit: None, lambda result: None, 'قياس', progress=True)
            pool.return_value.start.assert_called_once()
            self.assertTrue(p.table.isEnabled())
            self.assertTrue(p.search.isEnabled())
            self.assertTrue(p.select_visible_button.isEnabled())
            self.assertFalse(p.progress_row.isHidden())
            self.click('dxb')
            self.assertEqual(p.selected_codes(), {'dxb'})
            self.assertFalse(p.unblock_button.isEnabled())
            p.finished()
            self.assertTrue(p.unblock_button.isEnabled())
            self.assertTrue(p.progress_row.isHidden())

    def test_saved_choices_can_be_saved_loaded_and_deleted(self):
        p = self.page
        self.click('dxb')
        with patch('deadlock_fps.pages.servers.QInputDialog.getText', return_value=('Gulf', True)):
            p.save_preset()
        self.assertIn('Gulf', self.store.state()['presets'])
        p.clear_selection()
        p.load_preset('Gulf')
        self.assertEqual(p.selected_codes(), {'dxb'})
        with patch('deadlock_fps.pages.servers.QInputDialog.getItem', return_value=('Gulf', True)):
            p.choose_delete_preset()
        self.assertNotIn('Gulf', self.store.state().get('presets', {}))

    def test_the_actions_stay_visible_in_the_window_and_the_narrow_window_drops_a_column(self):
        from deadlock_fps.ui import Window
        w = Window()
        w.guard_timer.stop()
        w.detect_timer.stop()
        w.servers.activate = lambda: None
        w.resize(940, 680)
        w.show()
        w.navigate('servers')
        self.app.processEvents()
        for b in (w.servers.unblock_button, w.servers.clear_block_button):
            self.assertTrue(b.isVisible())
            self.assertTrue(w.rect().contains(b.mapTo(w, b.rect().center())))
        self.assertTrue(w.servers.table.isColumnHidden(2))
        self.assertGreater(w.servers.table.columnWidth(1), 150)
        w.resize(1280, 900)
        self.app.processEvents()
        self.assertFalse(w.servers.table.isColumnHidden(2))
        w.close()


if __name__ == '__main__':
    unittest.main()
