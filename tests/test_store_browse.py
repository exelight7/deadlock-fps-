"""Mods > Browse (the rebuilt Mod Store page), driven offscreen against a fake GameBanana and, for installs, the real engine on a throwaway game folder."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QScrollArea

from deadlock_fps.shell.base import load_fonts
from deadlock_fps.pages.installed import InstalledPage
from deadlock_fps.installer import InstallError
from deadlock_fps.mod_service import ModService
from deadlock_fps.pages.browse import BrowsePage, InstallReview, CARD_MIN, ROW_LIMIT, PAGE_SIZE, ago_text, day_text, failure_text
from deadlock_fps.repos import RepositoryManager, RepositoryStore, TrustRegistry
from deadlock_fps.ui import start_look
from deadlock_fps.store.install import STORE_ID
from deadlock_fps.shell.components import Button
from deadlock_fps.store_service import StoreService
from installer_fixtures import GameCase, make_vpk, make_zip
from look_fixture import keep_look
from store_fixtures import PagedGameBanana, record, profile_document, file_entry, status


def plain(text):
    """Without the invisible marks that keep numbers in reading order."""
    return text.replace('‎', '')


def settle(app):
    for _ in range(4):
        QThreadPool.globalInstance().waitForDone(5000)
        app.processEvents()


class StoreCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.server = PagedGameBanana([
            record(1, 'Pink Doorman', category='Skins', sub='Doorman', author='Mira'),
            record(2, 'Crimson Wraith', category='Skins', sub='Wraith', author='Zed'),
            record(3, 'Clean HUD', category='HUD', sub='', author='Mira'),
            record(4, 'Adult Skin', category='Skins', sub='Doorman', visibility='hide'),
            record(5, 'Old Map', category='Maps', sub='', obsolete=True),
        ])
        self.server.profiles[1] = profile_document(1, 'Pink Doorman')
        self.service = StoreService(self.folder / 'store', transport=self.server, pause=0)
        self.page = BrowsePage(self.service)
        self.addCleanup(self.page.deleteLater)

    def settle(self):
        settle(self.app)

    def download(self):
        self.page.start_sync()
        self.settle()

    def names(self):
        return [card.name.text() for card in self.page.card_order]

    def card(self, name):
        return self.page.card_order[self.names().index(name)]

    def open(self, name):
        self.card(name).clicked.emit()
        self.settle()


class FirstRun(StoreCase):
    def test_an_empty_catalogue_explains_itself_and_offers_the_download(self):
        p = self.page
        self.assertEqual(p.card_order, [])
        self.assertFalse(p.first_run.isHidden())
        self.assertTrue(p.filters.isHidden() and p.grid_host.isHidden())
        self.assertEqual(p.first_button.text(), 'Get the mod list')
        self.assertTrue(p.first_button.isEnabled())
        self.assertIn('2 minutes and 26 MB', p.first_run.text.text(), 'the cost is stated before anything is fetched')
        self.assertEqual(self.server.calls, [], 'opening the page fetches nothing')

    def test_downloading_fills_the_grid_and_changes_the_button(self):
        self.download()
        p = self.page
        self.assertEqual(self.names(), ['Clean HUD', 'Crimson Wraith', 'Pink Doorman'], 'adult and outdated are left out, newest first')
        self.assertIn('Catalogue downloaded: 5 listings.', p.message)
        self.assertTrue(p.first_run.isHidden())
        self.assertFalse(p.filters.isHidden())
        self.assertFalse(p.check_button.isHidden())
        self.assertIn('3 mods', plain(p.count_label.text()))
        self.assertIn('list checked just now', plain(p.count_label.text()))
        self.assertFalse(self.service.busy)

    def test_a_second_check_only_refreshes(self):
        self.download()
        self.server.calls.clear()
        self.download()
        self.assertEqual({sort for sort, _ in self.server.index_requests()}, {'Generic_LatestModified'})
        self.assertIn('Checked', self.page.message)

    def test_progress_and_placeholders_show_while_the_list_is_fetched(self):
        p = self.page
        p.start_sync()
        self.assertTrue(self.service.busy)
        self.assertFalse(p.progress_card.isHidden())
        self.assertFalse(p.skeletons.isHidden())
        self.assertTrue(p.first_run.isHidden())
        self.settle()
        self.assertTrue(p.progress_card.isHidden() and p.skeletons.isHidden())

    def test_a_rate_limit_keeps_the_progress_and_offers_to_continue(self):
        self.server.records = [record(i) for i in range(1, 121)]
        self.server.hook = lambda url, query: status(429) if query.get('_nPage') == '2' else None
        self.download()
        p = self.page
        self.assertIn('slow down', p.notice_text())
        self.assertEqual(p.banner.property('variant'), 'warning')
        self.assertFalse(p.partial.isHidden())
        self.assertIn('50 mods are saved', plain(p.partial.title.text()))
        self.assertEqual((p.total, len(p.card_order)), (50, PAGE_SIZE))
        self.server.hook = None
        self.download()
        self.assertTrue(p.partial.isHidden())
        self.assertFalse(p.check_button.isHidden())

    def test_a_network_failure_is_reported_with_a_way_to_try_again(self):
        self.server.hook = lambda url, query: status(503)
        self.download()
        p = self.page
        self.assertIn('Could not reach GameBanana.', p.notice_text())
        self.assertEqual(p.banner.property('variant'), 'danger')
        self.assertFalse(self.service.busy)
        self.assertTrue(p.first_button.isEnabled() and not p.first_run.isHidden())
        self.server.hook = None
        p.banner.findChildren(Button)[-1].click()          # "Try again"
        self.settle()
        self.assertEqual(p.notice_text(), '', 'the banner goes when the next try starts')
        self.assertEqual(len(p.card_order), 3)

    def test_only_one_sync_runs_at_a_time(self):
        self.assertTrue(self.service.start_sync(lambda r: None, lambda m, c: None))
        self.assertFalse(self.service.start_sync(lambda r: None, lambda m, c: None))
        self.settle()
        self.assertTrue(self.service.start_sync(lambda r: None, lambda m, c: None))
        self.settle()


class Browsing(StoreCase):
    def setUp(self):
        super().setUp()
        self.download()

    def test_search_filters_the_grid_and_an_empty_result_offers_to_clear_the_filter(self):
        p = self.page
        p.query.setText('wraith')
        self.assertEqual(self.names(), ['Crimson Wraith'])
        p.query.setText('zzz')
        self.assertEqual(p.card_order, [])
        self.assertFalse(p.empty_filter.isHidden())
        self.assertTrue(p.grid_host.isHidden())
        p.empty_filter.button.click()
        self.assertEqual(p.query.text(), '')
        self.assertEqual(len(p.card_order), 3)
        self.assertTrue(p.empty_filter.isHidden())

    def test_adult_and_outdated_listings_are_opt_in(self):
        p = self.page
        self.assertNotIn('Adult Skin (18+)', self.names())
        p.adult.setChecked(True)
        self.assertIn('Adult Skin (18+)', self.names())
        self.assertNotIn('Old Map', self.names())
        p.hide_outdated.setChecked(False)
        self.assertIn('Old Map', self.names())

    def test_type_and_hero_choices(self):
        p = self.page
        self.assertEqual(p.category.itemText(0), 'All types')
        self.assertFalse(p.subcategory.isEnabled())
        p.category.setCurrentIndex(p.category.findData('Skins'))
        self.assertTrue(p.subcategory.isEnabled())
        self.assertEqual(self.names(), ['Crimson Wraith', 'Pink Doorman'])
        p.subcategory.setCurrentIndex(p.subcategory.findData('Wraith'))
        self.assertEqual(self.names(), ['Crimson Wraith'])
        p.category.setCurrentIndex(p.category.findData('HUD'))
        self.assertFalse(p.subcategory.isEnabled(), 'a type with no heroes leaves the hero list off')
        p.category.setCurrentIndex(0)
        self.assertFalse(p.subcategory.isEnabled(), 'the hero list follows the type')

    def test_sorting(self):
        self.page.sort.setCurrentIndex(self.page.sort.findData('name'))
        self.assertEqual(self.names(), ['Clean HUD', 'Crimson Wraith', 'Pink Doorman'])

    def test_a_card_says_the_hero_for_a_skin_and_the_type_for_the_rest(self):
        self.assertEqual(self.card('Pink Doorman').line.text(), 'Doorman · Mira')
        self.assertEqual(self.card('Clean HUD').line.text(), 'HUD · Mira')

    def test_pressing_a_card_opens_the_sheet_and_loads_the_mod_page(self):
        p = self.page
        self.assertTrue(p.sheet.isHidden())
        self.card('Pink Doorman').clicked.emit()
        self.assertFalse(p.sheet.isHidden())
        self.assertEqual((p.sheet.title.text(), p.current), ('Pink Doorman', 1))
        self.assertEqual(self.card('Pink Doorman').property('state'), 'selected')
        self.settle()
        self.assertEqual(p.d_description.text(), 'Gives a pink retexture')
        self.assertEqual(p.file_pick.count(), 1)
        self.assertIn('pak52_dir_ab12.zip', p.file_pick.itemText(0))
        shown = ' | '.join(label.text() for label in p.facts.findChildren(QLabel))
        for expected in ('03f6e9f9e25675d14521c84e010a33c2', 'Clean, says GameBanana', 'Checksum published', 'CC BY-NC-ND 4.0'):
            self.assertIn(expected, shown)
        self.assertEqual(self.service.catalog.get(1).views, 988, 'the counts are kept in the catalogue')

    def test_the_mod_page_is_fetched_only_when_a_card_is_pressed(self):
        self.assertFalse([u for u in self.server.calls if u.endswith('/ProfilePage')])
        self.open('Pink Doorman')
        self.assertEqual(len([u for u in self.server.calls if u.endswith('/ProfilePage')]), 1)

    def test_a_visited_mod_is_not_fetched_twice(self):
        p = self.page
        self.open('Pink Doorman')
        requests = lambda: [u for u in self.server.calls if u.endswith('/ProfilePage')]
        self.assertEqual(len(requests()), 1)
        p.close_sheet()
        self.assertIsNone(p.current)
        self.assertEqual(self.card('Pink Doorman').property('state'), None, 'closing the sheet clears the selection')
        self.open('Clean HUD')
        self.open('Pink Doorman')
        self.assertEqual(len(requests()), 2, 'Pink Doorman came from the session cache; only Clean HUD was fetched')
        self.assertEqual(p.d_description.text(), 'Gives a pink retexture')

    def test_a_missing_page_is_explained(self):
        self.open('Clean HUD')                          # no profile registered for it: the server answers 404
        self.assertEqual(self.page.d_description.text(), 'The mod page could not be loaded.')
        self.assertIn('no such page', self.page.result_text())
        self.assertEqual(self.page.result.property('variant'), 'danger')

    def test_trust_is_stated_and_a_page_without_an_installer_only_browses(self):
        p = self.page
        self.open('Pink Doorman')
        self.assertIn('has not reviewed it', p.trust_notice.text.text())
        self.assertEqual(p.trust_notice.property('variant'), 'warning')
        self.assertIn('private folder', p.d_note.text())
        self.assertTrue(p.install_block.isHidden(), 'no installer was given: nothing to click')

    def test_pictures_are_not_requested_until_asked(self):
        p = self.page
        self.open('Pink Doorman')
        self.assertTrue(p.pictures_box.count() == 0)
        self.assertEqual(p.pictures_button.text(), 'Show pictures')

    def test_open_uses_an_address_built_from_the_id(self):
        self.open('Pink Doorman')
        with patch('deadlock_fps.pages.browse.QDesktopServices.openUrl') as opened:
            self.page.open_button.click()
        self.assertEqual(opened.call_args[0][0].toString(), 'https://gamebanana.com/mods/1')

    def test_text_from_gamebanana_is_never_interpreted_as_markup(self):
        name = '<b>Bold</b><img src=x onerror=1>'
        self.server.records.append(record(9, name, author='<i>Eve</i>'))
        self.download()
        self.assertIn(name, self.names())
        card = self.card(name)
        self.open(name)
        for label in (card.name, card.line, self.page.sheet.title, self.page.d_by, self.page.d_description):
            self.assertEqual(label.textFormat(), Qt.PlainText)
        self.assertEqual(self.page.sheet.title.text(), name)
        self.assertIn('<i>Eve</i>', self.page.d_by.text())

    def test_the_grid_is_built_a_page_at_a_time_and_capped(self):
        self.server.records = [record(i, 'Mod %03d' % i) for i in range(1, 361)]
        self.service.catalog.clear()
        self.download()
        p = self.page
        self.assertEqual((len(p.card_order), p.total, len(p.rows)), (PAGE_SIZE, 360, ROW_LIMIT))
        self.assertFalse(p.more.isHidden())
        while not p.more.isHidden():
            p.more.click()
        self.assertEqual(len(p.card_order), ROW_LIMIT)
        self.assertIn('Showing the first 300 of 360', plain(p.note.text()))

    def test_the_selection_survives_a_reload(self):
        self.open('Clean HUD')
        self.page.reload()
        self.assertEqual(self.page.current, 3)
        self.assertEqual(self.card('Clean HUD').property('state'), 'selected')

    def test_the_grid_has_as_many_columns_as_fit(self):
        p = self.page
        p.resize(668, 600)                              # the page area of the 940 px window
        p.show()
        self.app.processEvents()
        p.arrange()
        self.assertEqual(p.columns, 3, 'three columns at the smallest window')
        p.resize(1000, 600)
        self.app.processEvents()
        p.arrange()
        self.assertEqual(p.columns, 5)
        self.assertEqual([p.grid.itemAtPosition(0, c).widget() for c in range(3)], p.card_order, 'cards keep their order')
        p.hide()

    def test_nothing_scrolls_sideways_at_the_minimum_window_and_130_percent_text(self):
        load_fonts()                                    # the faces the app ships; the fallback face is wider
        keep_look(self, self.app)
        start_look(self.app, {'mode': 'dark', 'accent': 'blue', 'scale': 130})      # the real start-up look, old base style included
        page = BrowsePage(self.service)
        self.addCleanup(page.deleteLater)
        page.resize(668, 560)                           # the page area of the 940 px window
        page.show()
        self.app.processEvents()
        self.assertFalse(page.scroll.horizontalScrollBar().isVisible())
        self.assertEqual(page.columns, 3)
        page.card_order[0].clicked.emit()
        self.settle()
        self.assertLessEqual(page.sheet.scroll.widget().minimumSizeHint().width(), page.sheet.scroll.viewport().width(), 'the sheet grows with the text size, so its rows fit')
        page.hide()

    def test_long_names_are_cut_not_widened(self):
        self.server.records.append(record(8, 'A very long mod name ' * 6))
        self.download()
        card = self.card(('A very long mod name ' * 6).strip())
        card.resize(190, 200)
        card.show()
        self.app.processEvents()
        self.assertLessEqual(card.minimumSizeHint().width(), CARD_MIN, 'a long name never forces the card wider')
        self.assertTrue(card.name.toolTip().startswith('A very long'))
        card.hide()


class Installing(GameCase):
    """The whole path a user takes: pick a file, download and inspect it, read the review, confirm, and see it installed."""

    URL = 'https://gamebanana.com/dl/%d'

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        super().setUp()
        self.linked = str(self.root)
        self.data = make_zip({'readme.txt': b'hi', 'pak52_dir.vpk': make_vpk(['materials/a.vmat'])})
        self.transport.files[self.URL % 1801337] = self.data
        self.server = PagedGameBanana([record(711387, 'Pink Drifter', category='Skins', sub='Drifter')])
        self.profile_files([file_entry(ident=1801337, name='pak52_dir.zip', size=len(self.data), md5=hashlib.md5(self.data).hexdigest())])
        self.store = StoreService(Path(self.temp.name) / 'store', transport=self.server, pause=0)
        manager = RepositoryManager(RepositoryStore(Path(self.temp.name) / 'repos'), self.transport, trust=TrustRegistry({}))
        self.mods = ModService(manager, lambda: self.linked, transport=self.transport)

        def installer():                               # the Installer built by the fixture, with its fake "game is running" guard
            if not (self.mods.game_path() or '').strip():
                raise InstallError('no-game', 'Link your Deadlock folder on the Home page first.')
            return self.installer
        self.mods.installer = installer
        self.page = BrowsePage(self.store, self.mods)
        self.addCleanup(self.page.deleteLater)
        self.opened, self.required = [], []
        self.page.openRequested.connect(self.opened.append)
        self.page.gameRequired.connect(lambda: self.required.append(True))
        self.page.start_sync()
        self.settle()

    def profile_files(self, files):
        self.server.profiles[711387] = profile_document(711387, 'Pink Drifter', files=files)

    def settle(self):
        settle(self.app)

    def open_mod(self):
        self.page.card_order[0].clicked.emit()
        self.settle()

    def accepting(self, acknowledge=True):
        def fake_exec(dialog):
            if acknowledge:
                dialog.ack.setChecked(True)
            return QDialog.Accepted
        return patch.object(InstallReview, 'exec', fake_exec)

    def test_the_install_controls_follow_the_mod_page(self):
        self.page.card_order[0].clicked.emit()
        self.assertFalse(self.page.install_button.isEnabled(), 'nothing to install until the mod page has arrived')
        self.settle()
        self.assertEqual((self.page.install_button.text(), self.page.install_button.isEnabled(), self.page.file_pick.count()), ('Install', True, 1))
        self.assertIn('pak52_dir.zip', self.page.file_pick.itemText(0))
        self.assertIn('private folder', self.page.d_note.text())
        self.assertTrue(self.page.game_notice.isHidden())

    def test_installing_end_to_end(self):
        self.open_mod()
        with self.accepting():
            self.page.install_button.click()
            self.settle()
        self.assertEqual(self.addon_names(), ['pak01_dir.vpk'])
        (mod,) = self.installer.installed()
        self.assertEqual((mod.repository_id, mod.mod_id, mod.name, mod.trust, mod.repository_name), (STORE_ID, 'gb-711387', 'Pink Drifter', 'UNVERIFIED', 'GameBanana'))
        self.assertIn('Installed Pink Drifter', self.page.result_text())
        self.assertIn('Every file was re-checked', self.page.result_text())
        self.assertEqual(self.page.result.property('variant'), 'success')
        self.assertEqual(self.page.install_button.text(), 'Reinstall')
        self.assertIn('Installed:', self.page.d_status.text())
        self.assertTrue(self.page.activity.isHidden())
        self.assertIsNotNone(self.page.card_order[0].installed, 'the card carries the Installed badge')

    def test_the_review_shows_where_the_file_comes_from_and_asks_for_acknowledgement(self):
        self.open_mod()
        seen = []

        def fake_exec(dialog):
            seen.append((dialog.plan.requires_ack, dialog.plan.md5_verified, dialog.install_button.isEnabled(), dialog.trust.text(), dialog.check.property('variant'),
                         dialog.ack.isHidden()))
            return QDialog.Rejected
        with patch.object(InstallReview, 'exec', fake_exec):
            self.page.install_button.click()
            self.settle()
        self.assertEqual(seen, [(True, True, False, 'Not reviewed', 'warning', False)], 'the Install button stays off until the warnings are acknowledged')

    def test_declining_the_review_changes_nothing_and_cleans_up(self):
        self.open_mod()
        before = self.game_snapshot()
        with patch.object(InstallReview, 'exec', lambda dialog: QDialog.Rejected):
            self.page.install_button.click()
            self.settle()
        self.assertEqual((self.game_snapshot(), self.installer.installed()), (before, []))
        self.assertEqual(self.page.result_text(), 'Cancelled. Nothing was changed.')
        staging = self.installer.store_dir / 'staging'
        self.assertTrue(not staging.exists() or not any(staging.iterdir()))

    def test_without_a_linked_game_the_button_is_off_and_the_banner_offers_the_link(self):
        self.linked = ''
        self.open_mod()
        self.assertFalse(self.page.install_button.isEnabled())
        self.assertFalse(self.page.game_notice.isHidden())
        self.page.game_notice.findChildren(Button)[-1].click()
        self.assertEqual(len(self.required), 1)
        self.assertEqual(self.transport.downloads, [])

    def test_a_game_unlinked_after_the_sheet_opened_still_downloads_nothing(self):
        self.open_mod()
        self.linked = ''
        self.page.install_button.click()
        self.settle()
        self.assertIn('Link your Deadlock folder', self.page.result_text())
        self.assertEqual(self.transport.downloads, [])

    def test_a_wrong_checksum_is_reported_and_nothing_is_installed(self):
        self.profile_files([file_entry(ident=1801337, name='pak52_dir.zip', size=len(self.data), md5='a' * 32)])
        self.open_mod()
        with self.accepting():
            self.page.install_button.click()
            self.settle()
        self.assertIn('did not match the checksum', self.page.result_text())
        self.assertEqual(self.page.result.property('variant'), 'danger')
        self.assertEqual((self.addon_names(), self.installer.installed()), ([], []))
        self.assertTrue(self.page.activity.isHidden() and self.page.install_button.isEnabled())

    def test_unsupported_files_are_listed_but_cannot_be_installed(self):
        rar = file_entry(ident=1801400, name='alt_skin.rar', size=10)
        self.profile_files([rar, file_entry(ident=1801337, name='pak52_dir.zip', size=len(self.data), md5=hashlib.md5(self.data).hexdigest())])
        self.open_mod()
        self.assertIn('.zip', self.page.file_pick.currentText(), 'the first file that can be installed is chosen')
        self.assertIn('not supported', self.page.file_pick.itemText(0))
        self.page.file_pick.setCurrentIndex(0)
        self.assertFalse(self.page.install_button.isEnabled())
        self.assertIn('.rar archive', self.page.d_status.text())
        self.page.install_button.click()
        self.settle()
        self.assertEqual(self.transport.downloads, [])

    def test_the_button_is_off_while_another_operation_runs(self):
        self.open_mod()
        self.mods.busy = True
        self.page.sync_install()
        self.assertFalse(self.page.install_button.isEnabled())
        self.mods.busy = False
        self.page.sync_install()
        self.assertTrue(self.page.install_button.isEnabled())

    def test_the_file_facts_follow_the_chosen_file(self):
        self.profile_files([file_entry(ident=1801337, name='a.zip', size=len(self.data), md5='b' * 32), file_entry(ident=1801338, name='b.zip', size=len(self.data), md5='c' * 32)])
        self.open_mod()
        shown = lambda: ' | '.join(label.text() for label in self.page.facts.findChildren(QLabel))
        self.assertIn('b' * 32, shown())
        self.page.file_pick.setCurrentIndex(1)
        self.assertIn('c' * 32, shown())
        self.assertNotIn('b' * 32, shown())

    def test_the_file_choice_survives_a_reload(self):
        self.profile_files([file_entry(ident=1801337, name='a.zip', size=len(self.data)), file_entry(ident=1801338, name='b.zip', size=len(self.data))])
        self.open_mod()
        self.page.file_pick.setCurrentIndex(1)
        self.page.reload()
        self.assertEqual(self.page.file_pick.currentData(), 1801338)

    def test_the_installed_page_lists_the_store_mod_without_pretending_it_has_a_repository(self):
        self.open_mod()
        with self.accepting():
            self.page.install_button.click()
            self.settle()
        installed = InstalledPage(self.mods)
        self.addCleanup(installed.deleteLater)
        installed.reload()
        self.assertEqual(len(installed.rows), 1)
        (row,) = installed.rows.values()
        self.assertEqual(row.title.text(), 'Pink Drifter')
        self.assertIn('GameBanana', row.line.text())
        self.assertEqual(row.badge.text(), 'Installed', 'a store mod is not called "source unreachable"')
        self.assertIn('Mod Store', row.badge.toolTip())
        (status,) = self.mods.statuses()
        self.assertEqual(status.state, 'unavailable')
        self.assertIn('Mod Store', status.note)

    def test_an_installed_mod_is_marked_on_its_card_and_the_mark_goes_when_it_is_removed(self):
        self.assertIsNone(self.page.card_order[0].installed)
        self.open_mod()
        with self.accepting():
            self.page.install_button.click()
            self.settle()
        self.assertIsNotNone(self.page.card_order[0].installed)
        self.installer.uninstall(STORE_ID, 'gb-711387')
        self.mods.changed.emit()
        self.settle()
        self.assertIsNone(self.page.card_order[0].installed)

    def test_the_installed_button_leads_to_the_installed_tab(self):
        self.open_mod()
        self.assertTrue(self.page.installed_button.isHidden())
        with self.accepting():
            self.page.install_button.click()
            self.settle()
        self.assertFalse(self.page.installed_button.isHidden())
        self.page.installed_button.click()
        self.assertEqual(self.opened, ['mods.installed'])

    def test_without_a_linked_game_nothing_is_marked_and_nothing_breaks(self):
        self.linked = ''
        self.page.reload()
        self.assertIsNone(self.page.card_order[0].installed)

    def test_install_is_above_the_facts_and_the_description_so_it_is_seen_first(self):
        body = self.page.sheet.body
        self.assertLess(body.indexOf(self.page.install_block), body.indexOf(self.page.facts))
        self.assertLess(body.indexOf(self.page.install_block), body.indexOf(self.page.d_description))
        self.assertLess(body.indexOf(self.page.d_by), body.indexOf(self.page.install_block))

    def test_uninstalling_a_store_mod_updates_the_page(self):
        self.open_mod()
        with self.accepting():
            self.page.install_button.click()
            self.settle()
        self.installer.uninstall(STORE_ID, 'gb-711387')
        self.mods.changed.emit()
        self.settle()
        self.assertEqual(self.page.install_button.text(), 'Install')
        self.assertEqual(self.addon_names(), [])


class Review(unittest.TestCase):
    """The review dialog on its own, from a plan made by hand."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def plan(self, **changes):
        fields = dict(action='install', mod_name='Clean HUD', version='1.2', replaces='', trust='UNVERIFIED', repository_name='GameBanana', verified=False, md5_verified=True,
                      actual_sha256='ab' * 32, files=(SimpleNamespace(name='pak07_dir.vpk', source='clean.vpk', size=25_000_000, entries=3),), removed=(), warnings=(), blockers=(),
                      requires_ack=True, can_install=True)
        fields.update(changes)
        return SimpleNamespace(**fields)

    def test_the_button_waits_for_the_acknowledgement(self):
        dialog = InstallReview(self.plan(warnings=('It changes the same files as Night Skyline.',)))
        self.addCleanup(dialog.deleteLater)
        self.assertEqual(dialog.windowTitle(), 'Review before installing')
        self.assertFalse(dialog.install_button.isEnabled())
        self.assertFalse(dialog.ack.isHidden())
        dialog.ack.setChecked(True)
        self.assertTrue(dialog.install_button.isEnabled() and dialog.acknowledged)

    def test_the_exact_path_is_shown_and_a_blocker_cannot_be_acknowledged(self):
        dialog = InstallReview(self.plan(blockers=('Deadlock is running.',), can_install=False))
        self.addCleanup(dialog.deleteLater)
        self.assertIn('game/citadel/addons/pak07_dir.vpk', [label.text() for label in dialog.findChildren(QLabel)])
        self.assertIn('Deadlock is running.', [label.text() for label in dialog.findChildren(QLabel)])
        self.assertTrue(dialog.ack.isHidden())
        self.assertFalse(dialog.install_button.isEnabled())

    def test_an_update_says_so_and_a_verified_hash_is_not_a_warning(self):
        dialog = InstallReview(self.plan(action='update', replaces='1.0', verified=True, md5_verified=False, requires_ack=False))
        self.addCleanup(dialog.deleteLater)
        self.assertEqual(dialog.windowTitle(), 'Review before updating')
        self.assertEqual(dialog.install_button.text(), 'Update')
        self.assertEqual(dialog.check.property('variant'), 'success')
        self.assertTrue(dialog.install_button.isEnabled() and dialog.acknowledged)

    def test_the_dialog_is_tall_enough_for_wrapped_text(self):
        dialog = InstallReview(self.plan(warnings=('It changes the same files as Clean HUD. Clean HUD keeps winning because it has the lower number.',)))
        self.addCleanup(dialog.deleteLater)
        dialog.show()
        self.app.processEvents()
        self.assertGreaterEqual(dialog.height(), dialog.layout().totalHeightForWidth(dialog.width()))
        dialog.hide()

    def test_many_files_scroll_instead_of_growing_the_dialog(self):
        files = tuple(SimpleNamespace(name='pak%02d_dir.vpk' % n, source='', size=1000, entries=1) for n in range(9))
        dialog = InstallReview(self.plan(files=files))
        self.addCleanup(dialog.deleteLater)
        self.assertTrue(dialog.findChildren(QScrollArea))


class Unavailable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_an_unusable_location_disables_the_page_instead_of_crashing(self):
        with tempfile.TemporaryDirectory() as folder:
            blocker = Path(folder) / 'file'
            blocker.write_bytes(b'x')
            service = StoreService(blocker / 'inside', transport=PagedGameBanana(), pause=0)
            page = BrowsePage(service)
            self.assertFalse(service.ready)
            self.assertFalse(service.start_sync(lambda r: None, lambda m, c: None))
            self.assertFalse(page.unavailable.isHidden())
            self.assertIn('unavailable', page.unavailable.title.text())
            self.assertTrue(page.first_run.isHidden() and page.filters.isHidden())
            service.fetch_profile(1, lambda p: None, lambda m, c: None)       # a no-op, not an error
            page.deleteLater()


class Helpers(unittest.TestCase):
    def test_failure_text(self):
        self.assertNotIn('\n', failure_text('rate-limited', 'retry after 60'))
        self.assertTrue(failure_text('network', 'boom').endswith('\nboom'))
        self.assertTrue(failure_text('something-new', 'x').startswith('Something went wrong.'))

    def test_day_text(self):
        self.assertEqual((day_text(0), day_text(-10 ** 18)), ('—', '—'))
        self.assertRegex(day_text(1_700_000_000), r'^\d{4}-\d{2}-\d{2}$')

    def test_ago_text(self):
        now = 1_700_000_000
        self.assertEqual([plain(ago_text(now - s, now)) for s in (5, 600, 7200, 3 * 86400)], ['just now', '10 minutes ago', '2 hours ago', '3 days ago'])
        self.assertEqual(ago_text(0), 'never')
        self.assertEqual(ago_text(now + 500, now), 'just now', 'a clock that runs fast never shows a negative age')


if __name__ == '__main__':
    unittest.main()
