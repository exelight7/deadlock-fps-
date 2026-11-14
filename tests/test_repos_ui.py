"""Settings › Extra mod sources, driven the way a user drives it (offscreen, scripted transport, no network)."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QApplication, QLabel

from deadlock_fps.pages.source_list import SourceList, status_badge, trust_badge
from deadlock_fps.repos import RepositoryManager, RepositoryStore, TrustRegistry, RepoError
from deadlock_fps.shell.components import Badge
from repo_fixtures import FakeTransport, ok, index, mod, gh_repo, gh_asset, gh_release

IDX = 'https://mods.example.org/index.json'
GH = 'https://api.github.com/repos/mira/skins'


class Page(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.transport = FakeTransport({IDX: ok(index(mod('a-mod', name='Alpha Mod', categories=['skins']), mod('b-mod', name='Beta HUD', categories=['hud'])))})
        self.manager = RepositoryManager(RepositoryStore(Path(self.temp.name) / 'repositories'), self.transport, trust=TrustRegistry({}))
        self.page = SourceList(None, self.manager)
        self.addCleanup(self.page.deleteLater)

    def settle(self):
        QThreadPool.globalInstance().waitForDone(5000)
        for _ in range(3):
            self.app.processEvents()

    def add(self, url=IDX):
        self.page.address.setText(url)
        self.page.add_button.click()
        self.settle()

    def badges(self, row):
        return [b.text() for b in row.findChildren(Badge)]

    def notice(self):
        return ' '.join(l.text() for l in self.page.notice.findChildren(QLabel)) if self.page.notice else ''

    def test_starts_empty_and_says_so(self):
        self.assertEqual(len(self.page.list.rows), 0)
        self.assertFalse(self.page.empty.isHidden())
        self.assertTrue(self.page.list_card.isHidden())
        self.assertFalse(self.page.export_button.isEnabled())
        self.assertFalse(self.page.refresh_all_button.isEnabled())

    def test_adding_a_source_loads_and_lists_it_with_honest_badges(self):
        self.add()
        self.assertEqual(len(self.page.list.rows), 1)
        row = self.page.list.rows[0]
        self.assertIn('Example Mods', row.title.text().replace('‎', ''))
        self.assertIn(IDX, row.line.text().replace('​', ''))
        self.assertEqual(self.badges(row), ['Not reviewed', '2 mods'])
        self.assertEqual(self.page.address.text(), '')
        self.assertTrue(self.page.empty.isHidden())
        self.assertIn('Example Mods', self.notice())
        self.assertTrue(self.page.export_button.isEnabled())
        # The page shows what is saved: a second page over the same folder sees it without any network.
        self.transport.calls.clear()
        again = SourceList(None, RepositoryManager(RepositoryStore(Path(self.temp.name) / 'repositories'), self.transport, trust=TrustRegistry({})))
        self.assertEqual(len(again.list.rows), 1)
        self.assertEqual(self.transport.calls, [])

    def test_bad_and_duplicate_addresses_are_explained_on_the_field_and_not_stored(self):
        for bad in ('http://example.org/x', 'https://192.168.0.2/x', 'nonsense'):
            self.add(bad)
            self.assertEqual(len(self.page.list.rows), 0, bad)
        self.assertIn('public HTTPS', self.page.address_field.help.text())
        self.add()
        self.add()
        self.assertEqual(len(self.page.list.rows), 1)
        self.assertIn('already in your list', self.page.address_field.help.text())
        self.page.address.setText('')
        self.page.add_button.click()
        self.assertIn('Paste a source address', self.page.address_field.help.text())

    def test_an_unreachable_source_is_shown_as_such_and_recovers(self):
        self.transport.routes[IDX] = RepoError('network', 'cannot reach mods.example.org: timed out')
        self.add()
        row = self.page.list.rows[0]
        self.assertIn("Didn't answer", self.badges(row)[1])
        self.assertIn('timed out', row.line.text())
        self.transport.routes[IDX] = ok(index())
        self.page.refresh_one(row.source_id)
        self.settle()
        self.assertEqual(self.badges(self.page.list.rows[0])[1], '1 mod')
        self.assertNotIn('timed out', self.page.list.rows[0].line.text())

    def test_the_switch_turns_a_source_off_and_on(self):
        self.add()
        source_id = self.page.list.rows[0].source_id
        self.page.switches[source_id].setChecked(False)
        self.assertFalse(self.manager.get(source_id).source.enabled)
        self.assertEqual(self.badges(self.page.list.rows[0])[1], 'Off')
        self.page.switches[source_id].setChecked(True)
        self.assertTrue(self.manager.get(source_id).source.enabled)

    def test_removal_needs_confirmation(self):
        self.add()
        source_id = self.page.list.rows[0].source_id
        with patch('deadlock_fps.pages.source_list.confirm', return_value=False):
            self.page.remove(source_id)
        self.assertEqual(len(self.page.list.rows), 1)
        with patch('deadlock_fps.pages.source_list.confirm', return_value=True):
            self.page.remove(source_id)
        self.assertEqual((len(self.page.list.rows), self.manager.list()), (0, []))
        self.assertFalse(self.page.empty.isHidden())

    def test_a_translated_source_is_labelled_honestly(self):
        vpk = [gh_release('v1.0.0', [gh_asset('mira', 'skins', 'v1.0.0', 'red-v1.0.0.vpk')])]
        self.transport.routes.update({GH: ok(gh_repo()), GH + '/releases?per_page=30': ok(vpk)})
        self.add('https://github.com/mira/skins')
        view = self.manager.list()[0]
        self.assertEqual(trust_badge(view)[0], 'Not reviewed')
        self.assertEqual(status_badge(view)[0], '1 mod' if view.state.mod_count == 1 else '%d mods' % view.state.mod_count)

    def test_load_and_save_a_list(self):
        path = Path(self.temp.name) / 'mapping.json'
        path.write_text(json.dumps(index(name='Hand Mapped', ident='hand-mapped')), encoding='utf-8')
        with patch('deadlock_fps.pages.source_list.QFileDialog.getOpenFileName', return_value=(str(path), '')):
            self.page.import_button.click()
        self.assertIn('Hand Mapped', self.page.list.rows[0].title.text())
        with patch('deadlock_fps.pages.source_list.QFileDialog.getOpenFileName', return_value=(str(path), '')), \
                patch('deadlock_fps.pages.source_list.confirm', return_value=False):
            self.page.import_button.click()
        self.assertEqual(len(self.page.list.rows), 1)
        bad = Path(self.temp.name) / 'bad.json'
        bad.write_text('{"nope": true}')
        with patch('deadlock_fps.pages.source_list.QFileDialog.getOpenFileName', return_value=(str(bad), '')):
            self.page.import_button.click()
        self.assertIn('not a valid source index', self.notice())
        self.assertEqual(len(self.page.list.rows), 1)
        self.add()
        target = Path(self.temp.name) / 'export.json'
        with patch('deadlock_fps.pages.source_list.QFileDialog.getSaveFileName', return_value=(str(target), '')):
            self.page.export_button.click()
        exported = json.loads(target.read_text(encoding='utf-8'))
        self.assertEqual([r['url'] for r in exported['repositories']], [IDX])

    def test_controls_lock_while_work_is_running(self):
        self.add()
        self.page.jobs = 1
        self.page.sync_buttons()
        self.assertFalse(self.page.add_button.isEnabled())
        self.assertFalse(self.page.refresh_all_button.isEnabled())
        self.page.jobs = 0
        self.page.sync_buttons()
        self.assertTrue(self.page.refresh_all_button.isEnabled())

    def test_refresh_all_reports_failures(self):
        self.add()
        self.transport.routes[IDX] = RepoError('network', 'offline')
        self.page.refresh_all_button.click()
        self.settle()
        self.assertIn('1 could not be reached', self.notice())

    def test_text_from_a_source_is_plain_so_it_cannot_inject_markup(self):
        hostile = index(mod('x-mod', name='<b>Bold</b>', summary='<a href="https://evil.example">click</a>'), name='<h1>Big</h1>')
        self.transport.routes[IDX] = ok(hostile)
        self.add()
        title = self.page.list.rows[0].title
        self.assertEqual(title.textFormat().name, 'PlainText')
        self.assertIn('<h1>Big</h1>', title.text())

    def test_numbers_and_addresses_keep_their_reading_order_in_right_to_left(self):
        self.add()
        self.assertTrue(self.page.list.rows[0].title.text().startswith('‎'))


class InsideTheWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_the_sources_section_is_reachable_and_every_page_has_its_widget(self):
        from deadlock_fps.ui import Window
        window = Window()
        self.addCleanup(window.close)
        window.guard_timer.stop()
        window.detect_timer.stop()
        window.servers.activate = lambda: None
        self.assertIs(window.slots['store'], window.browse)
        self.assertIs(window.slots['stats'], window.stats.heroes_view)
        self.assertIs(window.settings_view.sections['sources'], window.repositories)
        window.nav['settings'].click()
        self.assertEqual(window.current_address, 'settings.general')
        window.navigate('settings.sources')
        self.assertEqual(window.current_address, 'settings.sources')
        self.assertIs(window.settings_view.stack.currentWidget(), window.repositories)
        self.assertTrue(window.nav['settings'].isChecked())
        self.assertEqual(window.page_title.text(), window.nav['settings'].text())
        self.assertEqual(set(window.slots), set(window.registry.slots()))
        for address in window.registry.addresses():
            window.navigate(address)
            self.assertIs(window.stack.currentWidget(), window.slots[window.current_slot])


if __name__ == '__main__':
    unittest.main()
