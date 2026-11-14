"""The game link of the main window: finding Deadlock, the Steam account, the workspace file, and what Home shows about it.

`Window` (deadlock_fps/ui.py) inherits this mixin. It owns the state (`path`, `accounts`, `game_linked`) and
feeds the Home page (deadlock_fps/pages/home.py), which only draws. Moved here from `legacy/home.py` in Phase 3.
"""
import json
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from . import i18n
from .core import Studio, atomic, detect_games, game_root, video_files
from .detection import INSTALL_URL, scan
from .i18n import tr
from .settings import Settings, level_info
from .shell.components import Toast
from .stats.steam import from_userdata_path


class GameLinkMixin:
    # --- linking -------------------------------------------------------------------------------------

    def link_saved_game(self):
        """At start-up: the folder saved last time if it still holds the game, otherwise the first game found."""
        games = detect_games()
        if self.saved_game and (Path(self.saved_game) / 'game/citadel/gameinfo.gi').is_file():
            self.path.setText(self.saved_game)
            self.refresh_accounts()
        elif games:
            self.path.setText(str(games[0]))
            self.refresh_accounts()

    def set_game_linked(self, linked):
        """The one place that says whether a game is linked: the pill in the top bar and the Home page follow it."""
        self.game_linked = bool(linked)
        self.home.set_linked(self.game_linked)
        if hasattr(self, 'level_page'):
            self.level_page.set_linked(self.game_linked)
        self.show_game_pill()

    def show_game_pill(self, running=False):
        if not self.game_linked:
            self.game_pill.set_state('none', tr('Game not linked'))
        elif running:
            self.game_pill.set_state('running', tr('Game is running'))
        else:
            self.game_pill.set_state('linked', tr('Game linked'))

    def update_game_status(self):
        """Say plainly whether the game is here: linked, downloading, missing, or no Steam at all."""
        if not hasattr(self, 'home'):
            return
        linked = self.game_linked
        try:
            status = scan([Path(self.path.text())] if linked else detect_games())
        except Exception:
            status = scan([])
        self.home.show_status(status, linked)
        if hasattr(self, 'settings_view'):
            states = {'installed': tr('Installed'), 'updating': tr('Steam is updating it'), 'missing': tr('Not found'), 'no_steam': tr('Steam is not installed')}
            account = self.accounts.currentText() if linked and self.accounts.count() else ''
            self.settings_view.set_game(linked, self.path.text() if linked else '', status.build, tr('Running') if status.running else states.get(status.state, ''), account)
        self.show_game_pill(status.running)
        details = [(tr('Game version {0}').format(status.build)) if status.build else '', '%.1f GB' % (status.size / 1073741824) if status.size else '']
        self.game_pill.setToolTip(' · '.join(part for part in details if part) or 'Deadlock')

    def auto_detect(self):
        """While nothing is linked, keep looking quietly and link the game the moment it appears."""
        if not self.isVisible() or self.mods_page.busy or QApplication.activeModalWidget() or self.game_linked or self.path.hasFocus():
            return
        games = detect_games()
        if games:
            self.path.setText(str(games[0]))
            self.refresh_accounts()
        elif self.current_slot == 'home':
            self.update_game_status()

    def browse_game(self):
        if self.mods_page.applying:
            return
        chosen = QFileDialog.getExistingDirectory(self, tr('اختر مجلد Deadlock'))
        if chosen:
            self.path.setText(chosen)
            self.refresh_accounts()

    def focus_game(self):
        """The game pill and the doors that need the game: Home, with the link card open and the folder field focused."""
        self.navigate('home')
        self.home.show_link_card(True)
        self.path.setFocus()
        QTimer.singleShot(0, lambda: self.slots['home'].ensureWidgetVisible(self.home.path_field))

    def detect_game(self):
        if self.mods_page.applying:
            return
        self.home.set_searching(True)
        QApplication.processEvents()
        try:
            games = detect_games()
        finally:
            self.home.set_searching(False)
        if games:
            self.path.setText(str(games[0]))
            self.refresh_accounts()
        else:
            self.connection_note.setText(tr('Not found automatically. In Steam: right-click Deadlock, Manage, Browse local files, then choose that folder here.'))
            self.update_game_status()

    def remember_account(self, *_):
        self.preferred_account = self.accounts.currentData()
        self.save_workspace()

    def save_workspace(self):
        language = self.language.currentData() if hasattr(self, 'language') else i18n.preferred(self.preferences_file)
        try:
            atomic(self.preferences_file, json.dumps({'game': self.path.text(), 'account': self.preferred_account, 'language': language,
                                                      'look': getattr(self, 'saved_look', {})}, ensure_ascii=False).encode('utf-8'))
        except OSError:
            self.notify(tr('اللعبة مرتبطة، لكن تعذر حفظ اختيار المجلد للجلسة القادمة.'))

    def refresh_accounts(self):
        self.accounts.blockSignals(True)
        self.accounts.clear()
        try:
            root = game_root(self.path.text())
            self.path.setText(str(root))
            for file in video_files(root):
                account = next((p.name for p in file.parents if p.parent.name == 'userdata'), None)
                self.accounts.addItem('Steam ' + account if account else tr('إعدادات محلية للعبة'), str(file))
                self.accounts.setItemData(self.accounts.count() - 1, str(file), Qt.ToolTipRole)
            index = self.accounts.findData(self.preferred_account)
            if index >= 0:
                self.accounts.setCurrentIndex(index)
            self.preferred_account = self.accounts.currentData()
            self.connection_note.setText(tr('Linked. Pick a tool on Home, or open one from the list.'))
            self.save_workspace()
            if not self.accounts.count():
                self.connection_note.setText(tr('Linked. Start the game once if you need the video settings and the crosshair.'))
            pass                        # the game pill already says it
            self.set_game_linked(True)
            self.home.show_link_card(False)
            saved = Studio(root, self.accounts.currentData()).state().get('settings')
            if saved:
                self.load_settings(Settings.from_dict(saved))
        except Exception as error:
            self.notify(str(error))
            self.connection_note.setText(tr('Choose the right Deadlock folder, or let Toolbox look for it.'))
            self.set_game_linked(False)
        finally:
            self.accounts.blockSignals(False)
            self.home.account_field.setVisible(self.accounts.count() > 1)
        self.refresh_mod_library()
        self.update_game_status()
        self.refresh_home()
        self.check_stale()

    # --- what Home shows -----------------------------------------------------------------------------

    def refresh_home(self):
        """Feed the Home page from the engines: counts for the doors, status lines, the attention list."""
        if not hasattr(self, 'home') or not hasattr(self, 'updates') or not hasattr(self, 'mod_service'):
            return
        home = self.home
        name, _ = level_info(self.level.value())
        home.set_performance(self.level.value(), name)
        home.set_small('crosshair', self.crosshair.design_name.text())
        try:
            blocked = len(self.servers.store.state().get('blocked', []))
        except Exception:
            blocked = 0
        home.set_small('servers', tr('{0} regions blocked').format(blocked) if blocked else tr('No regions blocked'))
        home.set_small('backups', tr('The originals are saved before the first change'))
        items = []
        mods, updatable, switched_off = [], [], False
        if self.game_linked:
            try:
                mods = self.mod_service.installer().installed()
                updatable = [s for s in self.mod_service.statuses() if s.updatable]
                switched_off = bool(mods) and not self.studio().addons_enabled()
            except Exception:
                mods, updatable, switched_off = [], [], False
        home.set_mods(len(mods), len(updatable))
        if switched_off:
            items.append({'tone': 'danger', 'icon': 'warn', 'title': tr('Your mods are switched off in the game'), 'line': tr('Steam restored a game file. One press puts it back.'),
                          'action': tr('Repair'), 'callback': self.repair_mods})
        if updatable:
            items.append({'tone': 'info', 'icon': 'info', 'title': tr('{0} mods have updates').format(len(updatable)),
                          'line': ' · '.join(s.mod.name for s in updatable[:3]), 'action': tr('See updates'), 'callback': lambda: self.navigate('mods.installed')})
        release = self.updates.release
        if self.update_available and release is not None:
            items.append({'tone': 'info', 'icon': 'download', 'title': tr('Toolbox {0} is ready').format(release.tag),
                          'line': tr('You have {0}.').format(str(self.updates.current)), 'action': tr('Update'), 'callback': lambda: self.navigate('settings.update')})
        home.set_attention(items)

    def repair_mods(self):
        """Put the mods folder back in gameinfo.gi (what Steam undoes after an update). The same repair as the Installed page."""
        def done(_):
            Toast(self.centralWidget(), tr('Your mods are switched back on.'))
            self.refresh_home()
        self.mod_service.operate('repair', (), done, lambda message, code: self.notify(message))

    def steam_account(self):
        """The Steam account number of the account chosen on the Home page (the folder name under Steam's userdata), or None."""
        return from_userdata_path(self.accounts.currentData())

    def studio(self):
        return Studio(self.path.text(), self.accounts.currentData())

    def error(self, error):
        QMessageBox.warning(self, tr('تعذر إكمال العملية'), str(error))
        self.notify(str(error))

    def mod_task_busy(self):
        if self.mods_page.busy:
            self.notify(tr('انتظر اكتمال عملية المودات الحالية، ثم أعد المحاولة.'))
            return True
        return False

    def open_install_page(self):
        QDesktopServices.openUrl(QUrl(INSTALL_URL))
