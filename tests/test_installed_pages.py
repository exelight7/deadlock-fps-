"""Mods > Installed, Check and Activity (the rebuilt pages), driven like a user against a throwaway game folder.

Mods are put into the game through the Mod Hub's page, as a user would, then the three pages are read and operated."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QApplication, QComboBox, QDialog, QLabel, QLineEdit, QScrollArea, QWidget

from deadlock_fps.installer import InstallError
from deadlock_fps.mod_service import ModService
from deadlock_fps.pages.activity import ActivityPage
from deadlock_fps.pages.browse import InstallReview
from deadlock_fps.mods import ModLibrary
from deadlock_fps.pages.check import CheckPage, fit_badge, made_for
from deadlock_fps.pages.classic import ClassicPack
from deadlock_fps.pages.sources import SourcesView
from deadlock_fps.pages.installed import BatchReview, FilesDialog, HistoryDialog, InstalledPage, status_badge
from deadlock_fps.repos import RepositoryManager, RepositoryStore, TrustRegistry
from installer_fixtures import GameCase, make_vpk, mod_document, HOST
from look_fixture import keep_look
from repo_fixtures import index, ok

IDX = 'https://mods.example.org/index.json'
SKIN, SKIN2, HUD = make_vpk(['materials/shared/skin.vmat'], b'v1'), make_vpk(['materials/shared/skin.vmat', 'materials/shared/extra.vmat'], b'v2'), make_vpk(['panorama/hud.css'], b'hud')


class StubClassic(QWidget):
    """Stands in for pages/classic.py's ClassicPack: the Installed page only asks it for a summary and shows it in the folded row."""

    def __init__(self, summary):
        super().__init__()
        self._summary = summary

    def summary(self):
        return self._summary()


class StubWindow(QWidget):
    """The few things ClassicPack asks of the main window, so the real widget can be built and measured on its own."""

    def __init__(self, library, game):
        super().__init__()
        self.library, self.path, self.accounts = library, QLineEdit(str(game)), QComboBox()

    def mod_selected(self, key, checked):
        pass

    def refresh_mod_library(self):
        pass

    def check_stale(self):
        pass


def plain(text):
    return text.replace('‎', '')


class PagesCase(GameCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        super().setUp()
        self.linked = str(self.root)
        self.classic = [('Daylock', True), ('Remove Name Tags', False), ('Old Healthbars', True), ('Sinner Fix', False)]
        self.publish([('crimson-skin', [{'version': '1.0.0', 'data': SKIN, 'changelog': 'First.'}, {'version': '2.0.0', 'data': SKIN2}], dict(categories=['skins'])),
                      ('clean-hud', [{'version': '1.0.0', 'data': HUD}], dict(categories=['hud'], name='Clean HUD'))])
        self.manager = RepositoryManager(RepositoryStore(Path(self.temp.name) / 'repos'), self.transport, trust=TrustRegistry({}))
        self.manager.refresh(self.manager.add(IDX).source.id)
        self.service = ModService(self.manager, lambda: self.linked, transport=self.transport)
        self.service.installer = self.fixture_installer
        self.hub = SourcesView(self.service)
        self.classic_widget = StubClassic(lambda: self.classic)
        self.installed = InstalledPage(self.service, self.classic_widget)
        self.check = CheckPage(self.service)
        self.activity = ActivityPage(self.service)
        for page in (self.hub, self.installed, self.check, self.activity):
            self.addCleanup(page.deleteLater)
        self.opened, self.required = [], []
        for page in (self.installed, self.check, self.activity):
            page.openRequested.connect(self.opened.append)
            page.gameRequired.connect(lambda: self.required.append(True))

    def fixture_installer(self):
        """The Installer built by the fixture's guard (a fake 'game is running' switch)."""
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

    def install(self, name, version=None):
        """Install a mod from "My sources", as a user would, then refresh the Installed page."""
        names = [card.name.text() for card in self.hub.card_order]
        self.hub.card_order[names.index(name)].clicked.emit()
        self.settle()
        if version:
            self.hub.version.setCurrentIndex(self.hub.version.findData(version))
        with self.accepting():
            self.hub.install_button.click()
            self.settle()
        self.installed.reload()

    def row(self, name=None):
        rows = list(self.installed.rows.values())
        return rows[0] if name is None else next(r for r in rows if r.title.text() == name)

    def act(self, row, words):
        """Choose an item of a row's "more" menu by the start of its text."""
        menu = self.installed.build_menu(row.key)
        action = next(a for a in menu.actions() if a.text().startswith(words))
        action.trigger()
        return action

    def accepting(self, acknowledge=True):
        def fake_exec(dialog):
            if acknowledge:
                dialog.ack.setChecked(True)
            return QDialog.Accepted
        return patch.object(InstallReview, 'exec', fake_exec)


class Installed(PagesCase):
    def test_a_row_shows_the_version_the_source_and_whether_there_is_an_update(self):
        self.install('Crimson-Skin', '1.0.0')
        p = self.installed
        self.assertEqual(len(p.rows), 1)
        row = self.row()
        self.assertEqual(row.title.text(), 'Crimson-Skin')
        self.assertIn('1.0.0 to 2.0.0', row.line.text())
        self.assertEqual((row.badge.text(), row.badge.property('variant')), ('Update', 'info'))
        self.assertIsNotNone(row.update_button)
        self.assertTrue(row.switch.isChecked())
        self.assertTrue(p.summary.text().startswith('1 mod · 1 update'), p.summary.text())
        self.assertEqual(p.all_button.text(), 'Update all (1)')
        self.assertTrue(p.empty.isHidden() and p.game_notice.isHidden() and not p.card.isHidden())

    def test_updating_restoring_and_the_old_copy_is_really_kept(self):
        self.install('Crimson-Skin', '1.0.0')
        p = self.installed
        with self.accepting():
            self.row().update_button.click()
            self.settle()
        self.assertEqual((self.addons / 'pak01_dir.vpk').read_bytes(), SKIN2)
        self.assertIn('Updated Crimson-Skin to 2.0.0', p.message)
        self.assertEqual(self.row().badge.text(), 'Up to date')
        self.assertIsNone(self.row().update_button)
        with patch.object(InstalledPage, 'ask', return_value=True) as asked:
            self.act(self.row(), 'Go back to 1.0.0')
            self.settle()
        self.assertIn('Crimson-Skin', asked.call_args[0][1])
        self.assertEqual((self.addons / 'pak01_dir.vpk').read_bytes(), SKIN)
        self.assertIn('back to version 1.0.0', p.message)

    def test_declining_the_review_changes_nothing(self):
        self.install('Crimson-Skin', '1.0.0')
        before = self.game_snapshot()
        with patch.object(InstallReview, 'exec', lambda dialog: QDialog.Rejected):
            self.row().update_button.click()
            self.settle()
        self.assertEqual(self.game_snapshot(), before)
        self.assertEqual(self.installed.message, 'Cancelled. Nothing was changed.')

    def test_the_switch_really_takes_the_file_out_of_the_addons_folder(self):
        self.install('Clean HUD')
        self.row().switch.setChecked(False)
        self.settle()
        self.assertEqual(self.addon_names(), [])
        self.assertEqual(self.row().badge.text(), 'Off')
        self.assertFalse(self.row().switch.isChecked())
        self.row().switch.setChecked(True)
        self.settle()
        self.assertEqual((self.addons / 'pak01_dir.vpk').read_bytes(), HUD)
        self.assertEqual(self.row().badge.text(), 'Up to date')

    def test_removal_needs_confirmation_and_keeps_the_files_recoverable(self):
        self.install('Clean HUD')
        p = self.installed
        with patch.object(InstalledPage, 'ask', return_value=False):
            self.act(self.row(), 'Remove')
            self.settle()
        self.assertEqual(len(self.installer.installed()), 1)
        with patch.object(InstalledPage, 'ask', return_value=True) as asked:
            self.act(self.row(), 'Remove')
            self.settle()
        self.assertTrue(asked.call_args[1].get('danger') or asked.call_args[0][-1] is True, 'removal is asked as a danger action')
        self.assertEqual(self.installer.installed(), [])
        self.assertEqual(self.addon_names(), [])
        self.assertTrue(any(q.name == 'pak01_dir.vpk' for q in (self.installer.store_dir / 'trash').rglob('*')))
        self.assertFalse(p.empty.isHidden())
        self.assertTrue(p.card.isHidden())

    def test_the_menu_lists_what_can_be_done_and_puts_remove_last(self):
        self.install('Crimson-Skin', '1.0.0')
        menu = self.installed.build_menu(self.row().key)
        names = [a.text() for a in menu.actions() if a.text()]
        self.assertEqual(names[0], 'Update to 2.0.0')
        self.assertEqual(names[-1], 'Remove')
        self.assertIn('Show files', names)
        self.assertIn('History', names)
        self.assertNotIn('Go back', ' '.join(names), 'no earlier version is kept yet')

    def test_update_all_prepares_everything_and_confirms_once(self):
        self.publish([('crimson-skin', [{'version': '1.0.0', 'data': SKIN}, {'version': '2.0.0', 'data': SKIN2}], dict(categories=['skins'])),
                      ('clean-hud', [{'version': '1.0.0', 'data': HUD}], dict(categories=['hud'], name='Clean HUD'))])
        self.manager.refresh(IDX.replace('https://', 'https:'))
        self.hub.reload()
        self.install('Crimson-Skin', '1.0.0')
        self.install('Clean HUD')
        self.publish([('crimson-skin', [{'version': '1.0.0', 'data': SKIN}, {'version': '2.0.0', 'data': SKIN2}], dict(categories=['skins'])),
                      ('clean-hud', [{'version': '1.0.0', 'data': HUD}, {'version': '1.1.0', 'data': make_vpk(['panorama/hud.css'], b'hud2')}], dict(categories=['hud'], name='Clean HUD'))])
        self.manager.refresh(IDX.replace('https://', 'https:'))
        self.installed.reload()
        self.assertTrue(self.installed.all_button.isEnabled())
        self.assertEqual(self.installed.all_button.text(), 'Update all (2)')
        shown = []

        def fake_exec(dialog):
            shown.append([plan.mod_name for plan in dialog.plans])
            dialog.ack.setChecked(True)
            return QDialog.Accepted
        with patch.object(BatchReview, 'exec', fake_exec):
            self.installed.all_button.click()
            self.settle()
        self.assertEqual(len(shown), 1)
        self.assertEqual(sorted(shown[0]), ['Clean HUD', 'Crimson-Skin'])
        self.assertEqual({m.name: m.version for m in self.installer.installed()}, {'Crimson-Skin': '2.0.0', 'Clean HUD': '1.1.0'})
        self.assertIn('Updated 2 mods', self.installed.message)

    def test_the_batch_review_waits_for_the_acknowledgement(self):
        self.install('Crimson-Skin', '1.0.0')
        self.publish([('crimson-skin', [{'version': '1.0.0', 'data': SKIN}, {'version': '2.0.0', 'data': SKIN2}], dict(categories=['skins']))])
        self.manager.refresh(IDX.replace('https://', 'https:'))
        self.installed.reload()
        plans = []

        def capture(dialog):
            plans.extend(dialog.plans)
            self.assertTrue(dialog.ack.isVisibleTo(dialog) or dialog.needs is False)
            self.assertEqual(dialog.go.isEnabled(), not dialog.needs)
            return QDialog.Rejected
        with patch.object(BatchReview, 'exec', capture):
            self.installed.all_button.click()
            self.settle()
        self.assertEqual(len(plans), 1)
        self.assertEqual(self.installed.message, 'Cancelled. Nothing was changed.')

    def test_files_and_history_dialogs_describe_the_installed_mod(self):
        self.install('Clean HUD')
        mod = self.installer.installed()[0]
        files = FilesDialog(mod, self.installer.addons, self.installer._disabled_dir(mod))
        self.addCleanup(files.deleteLater)
        self.assertEqual([files.table.item(0, c).text() for c in (0, 3)], ['pak01_dir.vpk', 'yes'])
        history = HistoryDialog(mod)
        self.addCleanup(history.deleteLater)
        self.assertEqual(history.table.item(0, 1).text(), 'Installed')

    def test_files_that_changed_are_reported_as_such(self):
        self.install('Clean HUD')
        (self.addons / 'pak01_dir.vpk').write_bytes(SKIN)
        mod = self.installer.installed()[0]
        files = FilesDialog(mod, self.installer.addons, self.installer._disabled_dir(mod))
        self.addCleanup(files.deleteLater)
        self.assertEqual(files.table.item(0, 3).text(), 'missing or changed')

    def test_checking_for_updates_refreshes_the_sources_and_says_so(self):
        self.install('Crimson-Skin', '1.0.0')
        p = self.installed
        p.check_updates()
        self.assertTrue(p.checking)
        self.assertFalse(p.check_button.isEnabled(), 'busy while the sources are asked')
        self.settle()
        self.assertFalse(p.checking)
        self.assertTrue(p.check_button.isEnabled())
        self.assertIn('Checked 1 sources', p.message)

    def test_a_failed_action_is_a_banner_that_says_nothing_was_changed(self):
        self.install('Clean HUD')
        self.running = True
        self.row().switch.setChecked(False)
        self.settle()
        p = self.installed
        self.assertEqual(p.banner.property('variant'), 'danger')
        self.assertIn('Close Deadlock first', p.notice_text())
        self.assertEqual(self.addon_names(), ['pak01_dir.vpk'])
        self.assertTrue(self.row().switch.isChecked(), 'the switch goes back to what is true')

    def test_the_unlinked_state_explains_itself_and_offers_the_link(self):
        self.linked = ''
        p = self.installed
        p.reload()
        self.assertFalse(p.game_notice.isHidden())
        self.assertEqual(len(p.rows), 0)
        self.assertFalse(p.check_button.isEnabled())
        self.assertTrue(p.empty.isHidden(), 'no "No mods yet" while the game is not linked')
        p.game_notice.findChildren(type(p.check_button))[-1].click()
        self.assertEqual(len(self.required), 1)

    def test_an_empty_list_offers_to_browse(self):
        p = self.installed
        self.assertFalse(p.empty.isHidden())
        self.assertTrue(p.card.isHidden())
        p.browse_button.click()
        self.assertEqual(self.opened, ['mods.browse'])

    def test_a_list_that_cannot_be_read_is_a_banner_and_the_page_survives(self):
        self.install('Clean HUD')
        p = self.installed
        with patch.object(type(self.installer), 'installed', side_effect=OSError('disk')):
            p.reload()
        self.assertEqual(p.banner.property('variant'), 'danger')
        self.assertIn("couldn't be read", p.notice_text())
        self.assertIn('game files were not touched', p.notice_text())
        self.assertEqual(len(p.rows), 0)
        self.assertTrue(p.empty.isHidden())
        p.reload()
        self.assertEqual(len(p.rows), 1)
        self.assertIsNone(p.banner, 'the banner goes when the list can be read again')

    def test_the_folded_rows_show_the_classic_pack_and_files_toolbox_did_not_install(self):
        p = self.installed
        p.reload()
        self.assertEqual(p.classic_fold.title.text(), 'Classic pack (4)')
        self.assertEqual((p.classic_fold.badge.text(), p.classic_fold.badge.isHidden()), ('2 on', False))
        self.assertTrue(p.other_fold.isHidden())
        self.assertFalse(p.classic_fold.expanded)
        p.classic_fold.toggle()
        self.assertTrue(p.classic_fold.expanded and not p.classic_fold.body.isHidden())
        self.assertIs(p.classic_fold.inner.itemAt(0).widget(), self.classic_widget, 'the classic pack itself sits inside the folded row')
        p.classic_fold.toggle()
        p.show_classic()
        self.assertTrue(p.classic_fold.expanded, 'show_classic opens the row')
        p.show_classic()
        self.assertTrue(p.classic_fold.expanded, 'and keeps it open')
        self.addons.mkdir(parents=True, exist_ok=True)
        (self.addons / 'pak05_dir.vpk').write_bytes(HUD)
        p.reload()
        self.assertFalse(p.other_fold.isHidden())
        self.assertEqual(p.other_fold.title.text(), 'Not installed by Toolbox (1)')
        self.assertIn('pak05_dir.vpk', p.other_names.text())
        self.classic = []
        p.reload()
        self.assertTrue(p.classic_fold.isHidden())

    def test_status_words(self):
        mod = type('M', (), {'enabled': True, 'repository_id': 'github:a/b'})()
        self.assertEqual(status_badge(mod, None), ('Installed', 'success'))
        self.assertEqual(status_badge(type('M', (), {'enabled': False, 'repository_id': 'github:a/b'})(), None), ('Off', 'neutral'))
        unreachable = type('S', (), {'state': 'unavailable', 'fit': None})()
        self.assertEqual(status_badge(mod, unreachable), ('Source unreachable', 'warning'))
        store_mod = type('M', (), {'enabled': True, 'repository_id': 'store:gamebanana'})()
        self.assertEqual(status_badge(store_mod, unreachable), ('Installed', 'success'), 'a store mod has no source to be unreachable')


class Check(PagesCase):
    def test_an_all_clear_says_so(self):
        self.install('Clean HUD')
        p = self.check
        p.reload()
        self.assertFalse(p.clear.isHidden())
        self.assertTrue(p.findings.isHidden())
        self.assertTrue(p.summary.text().startswith('Checked just now'), p.summary.text())
        self.assertFalse(p.check_button.isHidden() or not p.check_button.isEnabled())

    def test_real_problems_come_first_with_plain_titles_and_the_repair_works(self):
        self.install('Clean HUD')
        (self.addons / 'pak01_dir.vpk').write_bytes(SKIN)                 # changed behind Toolbox's back
        self.gi.write_bytes(self.original_gi)                             # and Steam restored gameinfo.gi
        p = self.check
        p.reload()
        titles = [row.title.text() for row in p.list.rows]
        self.assertIn('Your mods are switched off in the game', titles)
        self.assertIn('Clean HUD was changed after it was installed', titles)
        self.assertFalse(p.findings.isHidden())
        self.assertTrue(p.clear.isHidden())
        repair = next(row.control for row in p.list.rows if row.control is not None)
        self.assertEqual(repair.text(), 'Repair')
        repair.click()
        self.settle()
        titles = [row.title.text() for row in p.list.rows]
        self.assertNotIn('Your mods are switched off in the game', titles)
        self.assertIn('Clean HUD was changed after it was installed', titles)

    def test_two_mods_that_change_the_same_files_are_a_warning(self):
        self.install('Clean HUD')
        self.addons.mkdir(parents=True, exist_ok=True)
        (self.addons / 'pak05_dir.vpk').write_bytes(make_vpk(['panorama/hud.css'], b'other'))
        p = self.check
        p.reload()
        row = next(r for r in p.list.rows if r.title.text() == 'Two mods change the same files')
        self.assertIn('wins over', row.line.text())

    def test_the_fit_table_lists_every_mod_with_a_badge(self):
        self.install('Clean HUD')
        self.install('Crimson-Skin', '1.0.0')
        p = self.check
        p.reload()
        self.assertEqual(p.fits.rowCount(), 2)
        self.assertEqual({p.fits.item(r, 0).text() for r in range(2)}, {'Clean HUD', 'Crimson-Skin'})
        badge = p.fits.cellWidget(0, 2).findChildren(QLabel)[0]
        self.assertEqual(badge.property('component'), 'Badge')
        self.assertIn(badge.text(), ('Fits', 'Not tested on this version', 'Other game version', 'Unknown'))

    def test_fit_words(self):
        self.assertEqual(fit_badge(None, 6857), ('Unknown', 'neutral'))
        game = type('G', (), {'min_build': 6700, 'max_build': 6800, 'tested_build': None})()
        version = type('V', (), {'game': game})()
        self.assertEqual(fit_badge(version, 6857), ('Other game version', 'danger'))
        self.assertEqual(fit_badge(version, 6750), ('Fits', 'success'))
        self.assertEqual(plain(made_for(version)), '6700 to 6800')
        self.assertEqual(made_for(None), 'not stated')

    def test_a_check_that_cannot_finish_is_a_clear_message_and_nothing_else_breaks(self):
        self.install('Clean HUD')
        p = self.check
        with patch.object(type(self.installer), 'analyze', side_effect=OSError('disk')):
            p.reload()
        self.assertFalse(p.broken.isHidden())
        self.assertTrue(p.findings.isHidden() and p.fits_card.isHidden())
        self.assertEqual(p.summary.text(), 'The check could not finish.')
        p.try_button.click()
        self.assertTrue(p.broken.isHidden())
        self.assertFalse(p.clear.isHidden())

    def test_the_unlinked_state_explains_itself(self):
        self.linked = ''
        p = self.check
        p.reload()
        self.assertFalse(p.game_notice.isHidden())
        self.assertTrue(p.findings.isHidden() and p.clear.isHidden() and p.fits_card.isHidden())
        self.assertFalse(p.check_button.isEnabled())
        p.game_notice.findChildren(type(p.check_button))[-1].click()
        self.assertEqual(len(self.required), 1)


class Activity(PagesCase):
    def test_the_history_is_newest_first_and_says_what_happened(self):
        self.install('Clean HUD')
        self.install('Crimson-Skin', '1.0.0')
        p = self.activity
        p.reload()
        self.assertEqual([r.title.text() for r in p.list.rows], ['Installed Crimson-Skin 1.0.0', 'Installed Clean HUD 1.0.0'])
        self.assertRegex(plain(p.list.rows[0].line.text()), r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}')
        self.assertTrue(p.empty.isHidden())
        self.assertFalse(p.now.isHidden())

    def test_nothing_yet_is_an_empty_state(self):
        p = self.activity
        p.reload()
        self.assertFalse(p.empty.isHidden())
        self.assertTrue(p.history.isHidden())

    def test_a_download_that_is_running_shows_how_far_it_is_and_can_be_cancelled(self):
        p = self.activity
        p.busy(True)
        self.assertFalse(p.running.isHidden())
        self.assertTrue(p.now.isHidden())
        p.show_progress(11_200_000, 24_800_000)
        self.assertIn('Downloading', p.running_text.text())
        self.assertIn('MB', p.running_text.text())
        self.assertEqual((p.bar.minimum(), p.bar.maximum()), (0, 1000))
        self.assertGreater(p.bar.value(), 400)
        p.busy(False)
        self.assertTrue(p.running.isHidden())
        self.assertFalse(p.now.isHidden())
        self.service.cancel_event = None
        p.cancel_button.click()                      # no operation is running: cancelling is harmless

    def test_a_failed_item_is_in_the_danger_look_with_the_reason(self):
        self.install('Clean HUD')
        entry = {'at': '2026-11-14T10:00:00+0000', 'action': 'install', 'name': 'Night Skyline', 'version': '2.0.1', 'result': 'verify failed', 'note': 'put back as it was'}
        with patch.object(type(self.installer), 'history', return_value=[entry]):
            self.activity.reload()
        row = self.activity.list.rows[0]
        self.assertEqual(row.title.text(), 'Installed Night Skyline 2.0.1')
        self.assertIn('verify failed', row.line.text())
        self.assertIn('put back as it was', row.line.text())
        glyph = next(w for w in row.findChildren(QLabel) if w.property('tone'))
        self.assertEqual(glyph.property('tone'), 'danger')

    def test_the_unlinked_state_explains_itself(self):
        self.linked = ''
        p = self.activity
        p.reload()
        self.assertFalse(p.game_notice.isHidden())
        self.assertTrue(p.history.isHidden() and p.empty.isHidden())


class Layout(PagesCase):
    def test_no_sideways_scrolling_at_the_minimum_window_and_130_percent_text(self):
        from deadlock_fps.shell.base import load_fonts
        from deadlock_fps.ui import start_look
        keep_look(self, self.app)
        self.app.setStyle('Fusion')                       # the style the application starts with; the platform's own style measures differently
        load_fonts()
        start_look(self.app, {'mode': 'dark', 'accent': 'blue', 'scale': 130})
        self.install('Crimson-Skin', '1.0.0')
        self.install('Clean HUD')
        self.addons.mkdir(parents=True, exist_ok=True)
        (self.addons / 'pak05_dir.vpk').write_bytes(make_vpk(['panorama/hud.css'], b'other'))
        window = StubWindow(ModLibrary(Path(self.temp.name) / 'library'), Path(self.temp.name) / 'no-game')      # no game linked: the "Link the game" button shows too
        self.addCleanup(window.deleteLater)
        pack = ClassicPack(window)
        pack.refresh()
        pages = []
        for make in (lambda: InstalledPage(self.service, pack), lambda: CheckPage(self.service), lambda: ActivityPage(self.service),
                     lambda: SourcesView(self.service)):
            page = make()
            self.addCleanup(page.deleteLater)
            page.resize(668, 560)                               # the page area of the 940 px window
            page.show()
            pages.append(page)
        pages[0].show_classic()                                 # the classic pack open inside Installed: the widest thing on any of these pages
        self.app.processEvents()
        for page in pages:
            page.reload()
            self.app.processEvents()
            self.assertLessEqual(page.scroll.widget().minimumSizeHint().width(), page.scroll.viewport().width(), type(page).__name__)
            self.assertFalse(page.scroll.horizontalScrollBar().isVisible(), type(page).__name__)
            page.hide()


if __name__ == '__main__':
    unittest.main()
