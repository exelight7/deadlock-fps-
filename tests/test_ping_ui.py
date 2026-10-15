import tempfile,unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch
from deadlock_fps.servers import PingResult,Region,Relay,probe_region,probe_address,ping_regions,ServerStore

class Probes(unittest.TestCase):
    def test_first_relay_no_reply_uses_alternative(self):
        region=Region('test','Test',(Relay('8.8.8.8',1,2),Relay('1.1.1.1',1,2)))
        replies=[PingResult(None,100,'no_reply','no reply'),PingResult(32.5,0,'ok','response','1.1.1.1')]
        with patch('deadlock_fps.servers.probe_address',side_effect=replies) as probe:
            result=probe_region(region);self.assertEqual(result.latency,32.5);self.assertEqual(probe.call_count,2)
    def test_missing_tool_is_error_not_100_percent_loss(self):
        region=Region('test','Test',(Relay('8.8.8.8',1,2),))
        with patch('deadlock_fps.servers.probe_address',side_effect=FileNotFoundError()):
            result=probe_region(region);self.assertEqual(result.status,'error');self.assertIsNone(result.loss)
    def test_permission_failure_not_reported_as_dead_server(self):
        with patch('deadlock_fps.servers.os.name','posix'),patch('subprocess.run',return_value=CompletedProcess([],2,'','Operation not permitted')):
            result=probe_address('8.8.8.8');self.assertEqual(result.status,'error');self.assertIsNone(result.loss)
    def test_whitespace_and_decimal_ping_output(self):
        output='time = 20 ms\ntime= 21,5 ms\ntime< 1 ms'
        with patch('deadlock_fps.servers.os.name','posix'),patch('subprocess.run',return_value=CompletedProcess([],0,output,'')):
            result=probe_address('8.8.8.8');self.assertEqual(result.status,'ok');self.assertEqual(result.latency,14.2);self.assertEqual(result.loss,0)
    def test_progress_reported_per_region(self):
        regions=[Region('a','A',(Relay('8.8.8.8',1,2),)),Region('b','B',(Relay('1.1.1.1',1,2),))];progress=[]
        with patch('deadlock_fps.servers.probe_region',return_value=PingResult(20,0,'ok','test')):
            results=ping_regions(regions,lambda code,result:progress.append(code))
        self.assertEqual(set(progress),{'a','b'});self.assertEqual(set(results),{'a','b'})

class Interface(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])
    def test_clear_states_numeric_sort_and_selection(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from deadlock_fps.server_ui import ServerPage
        with tempfile.TemporaryDirectory() as d:
            page=ServerPage(store=ServerStore(d));page.resize(1150,900);page.show();self.app.processEvents()
            self.assertEqual(page.table.item(0,3).text(),'لم يُقَس')
            index=page.table.model().index(0,0);rect=page.table.visualRect(index)
            QTest.mouseClick(page.table.viewport(),Qt.LeftButton,pos=rect.center());self.assertEqual(page.table.item(0,0).checkState(),Qt.Checked);self.assertIn('1',page.selection_note.text())
            a=page.table.item(0,0).data(Qt.UserRole);b=page.table.item(1,0).data(Qt.UserRole)
            page.ping_progress((a,PingResult(120.0,0,'ok','actual A')));page.ping_progress((b,PingResult(30.0,0,'ok','actual B')))
            self.assertEqual(page.table.item(0,3).text(),'120.0');page.sort_ping();self.assertEqual(page.table.item(0,3).text(),'30.0')
            page.ping_progress((b,PingResult(None,None,'error','tool not installed')))
            error_row=next(row for row in range(page.table.rowCount()) if page.table.item(row,0).data(Qt.UserRole)==b)
            self.assertEqual(page.table.item(error_row,3).text(),'تعذر القياس');self.assertNotEqual(page.table.item(error_row,4).text(),'100%')
            self.assertEqual(page.table.item(0,3).text(),'120.0')
            page.clear_selection();self.assertFalse(page.selected_codes());page.close()
