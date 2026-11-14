"""Mods > Browse > My sources (the old Mod Hub, rebuilt) and the host that holds it beside GameBanana, driven like a user against a throwaway game folder."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QApplication, QDialog, QLabel

from deadlock_fps.installer import InstallError
from deadlock_fps.mod_service import ModService
from deadlock_fps.pages.browse import BrowsePage, InstallReview
from deadlock_fps.pages.browse_host import BrowseHost
from deadlock_fps.pages.sources import SourcesView
from deadlock_fps.repos import RepositoryManager, RepositoryStore, TrustRegistry
from deadlock_fps.repos.model import RepositoryView
from deadlock_fps.shell.components import Button
from deadlock_fps.store_service import StoreService
from installer_fixtures import GameCase, make_vpk, mod_document, HOST
from repo_fixtures import index, ok
from store_fixtures import PagedGameBanana

IDX = 'https://mods.example.org/index.json'
SKIN, SKIN2, HUD = make_vpk(['materials/shared/skin.vmat'], b'v1'), make_vpk(['materials/shared/skin.vmat', 'materials/shared/extra.vmat'], b'v2'), make_vpk(['panorama/hud.css'], b'hud')


def plain(text):
    return text.replace('‎', '')


class SourcesCase(GameCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        super().setUp()
        self.linked = str(self.root)
        self.publish([('crimson-skin', [{'version': '1.0.0', 'data': SKIN, 'changelog': 'First.'}, {'version': '2.0.0', 'data': SKIN2}], dict(categories=['skins'])),
                      ('clean-hud', [{'version': '1.0.0', 'data': HUD}], dict(categories=['hud'], name='Clean HUD'))])
        self.manager = RepositoryManager(RepositoryStore(Path(self.temp.name) / 'repos'), self.transport, trust=TrustRegistry({}))
        self.manager.refresh(self.manager.add(IDX).source.id)
        self.service = ModService(self.manager, lambda: self.linked, transport=self.transport)
        self.service.installer = self.fixture_installer
        self.view = SourcesView(self.service)
        self.addCleanup(self.view.deleteLater)
        self.opened, self.required = [], []
        self.view.openRequested.connect(self.opened.append)
        self.view.gameRequired.connect(lambda: self.required.append(True))

    def fixture_installer(self):
        if not (self.service.game_path() or '').strip():
            raise InstallError('no-game', 'Link your Deadlock folder on the Home page first.')
        return self.installer

    def publish(self, mods):
        documents = []
        for ident, versions, extra in mods:
            for v in versions:
                self.transport.files[HOST + '%s-%s.vpk' % (ident, v['version'])] = v['data']
            documents.append(mod_document(ident, versions, **extra))
        self.transport.routes[IDX] = ok(index(*documents))

    def settle(self):
        for _ in range(4):
            QThreadPool.globalInstance().waitForDone(5000)
            self.app.processEvents()

    def names(self):
        return [card.name.text() for card in self.view.card_order]

    def open(self, name, version=None):
        card = self.view.card_order[self.names().index(name)]
        card.clicked.emit()
        self.settle()
        if version:
            self.view.version.setCurrentIndex(self.view.version.findData(version))

    def accepting(self, acknowledge=True):
        def fake_exec(dialog):
            if acknowledge:
                dialog.ack.setChecked(True)
            return QDialog.Accepted
        return patch.object(InstallReview, 'exec', fake_exec)

    def install(self, name, version=None):
        self.open(name, version)
        with self.accepting():
            self.view.install_button.click()
            self.settle()


class Sources(SourcesCase):
    def test_every_enabled_source_is_listed_and_a_card_opens_the_details(self):
        v = self.view
        self.assertEqual(sorted(self.names()), ['Clean HUD', 'Crimson-Skin'])
        self.assertIn('2 mods from 1 source', plain(v.count_label.text()))
        self.assertTrue(v.sheet.isHidden())
        self.open('Crimson-Skin')
        self.assertFalse(v.sheet.isHidden())
        self.assertEqual(v.sheet.title.text(), 'Crimson-Skin')
        self.assertEqual([v.version.itemData(i) for i in range(v.version.count())], ['2.0.0', '1.0.0'])
        v.version.setCurrentIndex(v.version.findData('1.0.0'))
        self.assertEqual(v.d_changelog.text(), 'First.')
        self.assertEqual(v.install_button.text(), 'Install 1.0.0')
        shown = ' | '.join(label.text() for label in v.facts.findChildren(QLabel))
        self.assertIn('SHA-256 published', shown)
        self.assertEqual(v.trust_notice.title.text(), 'Not reviewed')
        self.assertFalse(v.trust_notice.isHidden(), 'a source nobody reviewed says so in the sheet')
        self.assertEqual(self.view.cards[(self.manager.list()[0].source.id, 'crimson-skin')].property('state'), 'selected')

    def test_search_type_and_empty_results(self):
        v = self.view
        v.query.setText('hud')
        self.assertEqual(self.names(), ['Clean HUD'])
        v.query.setText('')
        v.category.setCurrentIndex(v.category.findData('hud'))
        self.assertEqual(self.names(), ['Clean HUD'])
        v.category.setCurrentIndex(0)
        v.query.setText('zzzz')
        self.assertEqual(self.names(), [])
        self.assertFalse(v.empty_filter.isHidden())
        self.assertTrue(v.grid_host.isHidden())

    def test_installing_goes_through_a_review_and_only_then_changes_the_game(self):
        v = self.view
        self.open('Clean HUD')
        before = self.game_snapshot()
        seen = []

        def fake_exec(dialog):
            seen.append((dialog.plan.mod_id, dialog.plan.requires_ack, dialog.install_button.isEnabled()))
            dialog.ack.setChecked(True)
            return QDialog.Accepted
        with patch.object(InstallReview, 'exec', fake_exec):
            v.install_button.click()
            self.settle()
        self.assertEqual(seen, [('clean-hud', True, False)], 'the button is off until the warnings are acknowledged')
        self.assertEqual((self.addons / 'pak01_dir.vpk').read_bytes(), HUD)
        self.assertNotEqual(self.game_snapshot(), before)
        self.assertIn('Installed Clean HUD 1.0.0', v.result_text())
        self.assertIn('re-checked', v.result_text())
        self.assertEqual(v.result.property('variant'), 'success')
        self.assertTrue(v.remove_button.isEnabled() and not v.remove_button.isHidden())
        self.assertEqual(v.install_button.text(), 'Reinstall 1.0.0')
        self.assertIsNotNone(v.cards[(self.manager.list()[0].source.id, 'clean-hud')].installed, 'the card carries the Installed badge')

    def test_cancelling_the_review_changes_nothing_and_cleans_up(self):
        self.open('Clean HUD')
        before = self.game_snapshot()
        with patch.object(InstallReview, 'exec', lambda dialog: QDialog.Rejected):
            self.view.install_button.click()
            self.settle()
        self.assertEqual(self.game_snapshot(), before)
        self.assertEqual(self.installer.installed(), [])
        self.assertEqual(self.view.result_text(), 'Cancelled. Nothing was changed.')
        staging = self.installer.store_dir / 'staging'
        self.assertFalse(staging.exists() and any(staging.iterdir()))

    def test_an_unacknowledged_unverified_install_is_refused_by_the_engine_not_just_the_dialog(self):
        self.open('Clean HUD')
        with self.accepting(acknowledge=False):
            self.view.install_button.click()
            self.settle()
        self.assertFalse(self.addons.exists())
        self.assertIn('acknowledge', self.view.result_text())

    def test_the_game_must_be_closed_and_must_be_linked(self):
        v = self.view
        self.open('Clean HUD')
        self.running = True
        with self.accepting():
            v.install_button.click()
            self.settle()
        self.assertIn('Close Deadlock first', v.result_text())
        self.assertFalse(self.addons.exists())
        self.running = False
        self.linked = ''
        v.sync_install()
        self.assertFalse(v.install_button.isEnabled(), 'no game linked: nothing to click')
        self.assertFalse(v.game_notice.isHidden())
        v.game_notice.findChildren(Button)[-1].click()
        self.assertEqual(len(self.required), 1)
        v.install()
        self.assertIn('Link your Deadlock folder', v.result_text())
        self.assertEqual(self.transport.downloads, [HOST + 'clean-hud-1.0.0.vpk'], 'the unlinked attempt downloaded nothing')

    def test_a_bad_download_is_reported_and_leaves_nothing(self):
        self.transport.files[HOST + 'clean-hud-1.0.0.vpk'] = HUD[:-1] + b'X'
        self.open('Clean HUD')
        seen = []
        with patch.object(InstallReview, 'exec', lambda dialog: seen.append(dialog) or QDialog.Accepted):
            self.view.install_button.click()
            self.settle()
        self.assertEqual(seen, [])
        self.assertIn('thrown away', self.view.result_text())
        self.assertEqual(self.view.result.property('variant'), 'danger')
        self.assertFalse(self.addons.exists())

    def test_an_installed_mod_can_be_removed_after_asking_and_is_recoverable(self):
        v = self.view
        self.install('Clean HUD')
        with patch.object(SourcesView, 'ask', return_value=False):
            v.remove_button.click()
            self.settle()
        self.assertEqual(len(self.installer.installed()), 1)
        with patch.object(SourcesView, 'ask', return_value=True):
            v.remove_button.click()
            self.settle()
        self.assertEqual(self.installer.installed(), [])
        self.assertEqual(self.addon_names(), [])
        self.assertTrue(any(p.name == 'pak01_dir.vpk' for p in (self.installer.store_dir / 'trash').rglob('*')))
        self.assertIn('Removed Clean HUD', v.result_text())

    def test_an_update_is_offered_as_such(self):
        self.install('Crimson-Skin', '1.0.0')
        self.open('Crimson-Skin')
        self.assertEqual(self.view.install_button.text(), 'Update to 2.0.0')
        self.assertIn('Installed: 1.0.0', self.view.d_status.text())

    def test_text_from_a_source_is_never_interpreted_as_markup(self):
        self.publish([('evil', [{'version': '1.0.0', 'data': HUD}], dict(name='<b>Bold</b>', categories=['hud'], summary='<img src=x onerror=1>'))])
        self.manager.refresh(self.manager.list()[0].source.id)
        self.view.reload()
        self.assertIn('<b>Bold</b>', self.names())
        self.open('<b>Bold</b>')
        from PySide6.QtCore import Qt
        for label in (self.view.sheet.title, self.view.d_summary, self.view.d_by, self.view.d_description):
            self.assertEqual(label.textFormat(), Qt.PlainText)

    def test_the_review_gates_the_install_button(self):
        self.open('Clean HUD')
        repository = self.manager.list()[0]
        found = self.manager.find_mod(repository.source.id, 'clean-hud')
        plan = self.installer.prepare(RepositoryView(repository.source, repository.state, repository.trust), found[1], found[1].latest())
        dialog = InstallReview(plan)
        self.addCleanup(dialog.deleteLater)
        self.assertFalse(dialog.install_button.isEnabled())
        dialog.ack.setChecked(True)
        self.assertTrue(dialog.install_button.isEnabled())
        blocked = InstallReview(plan)
        self.addCleanup(blocked.deleteLater)
        plan.blockers = ('Requires something',)
        blocked.refresh()
        blocked.ack.setChecked(True)
        self.assertFalse(blocked.install_button.isEnabled())
        self.installer.discard(plan)

    def test_no_sources_is_an_empty_state_with_the_way_to_add_one(self):
        folder = Path(self.temp.name) / 'empty-repos'
        service = ModService(RepositoryManager(RepositoryStore(folder), self.transport, trust=TrustRegistry({})), lambda: self.linked, transport=self.transport)
        view = SourcesView(service)
        self.addCleanup(view.deleteLater)
        self.assertFalse(view.empty.isHidden())
        self.assertTrue(view.filters.isHidden() and view.grid_host.isHidden())
        got = []
        view.openRequested.connect(got.append)
        view.add_button.click()
        self.assertEqual(got, ['settings.sources'])


class Host(SourcesCase):
    def make(self, with_sources=True):
        self.store_folder = Path(self.temp.name) / 'store'
        store = StoreService(self.store_folder, transport=PagedGameBanana(), pause=0)
        browse = BrowsePage(store, self.service)
        self.addCleanup(browse.deleteLater)
        host = BrowseHost(browse, self.view, self.service)
        self.addCleanup(host.deleteLater)
        return host, browse

    def test_the_switch_shows_only_when_there_is_a_source_of_your_own(self):
        host, browse = self.make()
        self.assertFalse(host.switch_row.isHidden())
        self.assertEqual(host.current(), 'gamebanana')
        host.show_view('sources')
        self.assertEqual((host.current(), host.switch.value()), ('sources', 'sources'))
        host.switch.set_value('gamebanana')
        host.show_view('gamebanana')
        self.assertEqual(host.current(), 'gamebanana')
        service = ModService(RepositoryManager(RepositoryStore(Path(self.temp.name) / 'none'), self.transport, trust=TrustRegistry({})), lambda: self.linked, transport=self.transport)
        view = SourcesView(service)
        self.addCleanup(view.deleteLater)
        store = StoreService(Path(self.temp.name) / 'store2', transport=PagedGameBanana(), pause=0)
        page = BrowsePage(store, service)
        self.addCleanup(page.deleteLater)
        lone = BrowseHost(page, view, service)
        self.addCleanup(lone.deleteLater)
        self.assertTrue(lone.switch_row.isHidden(), 'no sources: nothing to switch to')
        lone.show_view('sources')
        self.assertEqual(lone.current(), 'gamebanana')

    def test_switching_closes_an_open_sheet_and_the_signals_pass_through(self):
        host, browse = self.make()
        got, need = [], []
        host.openRequested.connect(got.append)
        host.gameRequired.connect(lambda: need.append(True))
        host.show_view('sources')
        self.open('Clean HUD')
        self.assertFalse(self.view.sheet.isHidden())
        host.show_view('gamebanana')
        self.assertTrue(self.view.sheet.isHidden())
        self.assertIsNone(self.view.current)
        self.view.openRequested.emit('settings.sources')
        browse.gameRequired.emit()
        self.assertEqual((got, len(need)), (['settings.sources'], 1))

    def test_removing_the_last_source_sends_you_back_to_gamebanana(self):
        host, browse = self.make()
        host.show_view('sources')
        self.manager.remove(self.manager.list()[0].source.id)
        self.service.changed.emit()
        self.assertEqual(host.current(), 'gamebanana')
        self.assertTrue(host.switch_row.isHidden())


if __name__ == '__main__':
    unittest.main()
