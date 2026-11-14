"""Render the Mod Store page offscreen. Usage: shot_store.py <repo root> <out.png> en|ar [empty|live]

`empty` shows the first-run state. `live` reads two real pages from GameBanana (read-only, nothing is installed),
opens the first mod's sheet and waits for its page and screenshots, so the picture shows realistic data.
"""
import os
import sys
import tempfile
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
root, out, lang = sys.argv[1], sys.argv[2], sys.argv[3]
mode = sys.argv[4] if len(sys.argv) > 4 else 'empty'
sys.path.insert(0, root)
from unittest.mock import patch
from deadlock_fps import i18n
i18n.activate(lang)
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
app = QApplication([])
app.setLayoutDirection(Qt.RightToLeft if i18n.rtl() else Qt.LeftToRight)
from deadlock_fps import ui
from deadlock_fps.shell.base import dark_palette, load_fonts
from deadlock_fps.shell import theme
app.setStyle('Fusion'); load_fonts(); app.setPalette(dark_palette()); theme.apply_direction(app, i18n.rtl()); ui.start_look(app, {'mode': 'dark', 'accent': 'blue', 'scale': 100})

with tempfile.TemporaryDirectory() as folder, patch('deadlock_fps.ui.QStandardPaths.writableLocation', return_value=folder), \
        patch('PySide6.QtCore.QStandardPaths.writableLocation', return_value=folder), \
        patch('deadlock_fps.game_link.detect_games', return_value=[]), patch('deadlock_fps.mods.ModLibrary.discover', return_value=[]):
    from deadlock_fps.ui import Window
    w = Window(); w.guard_timer.stop(); w.detect_timer.stop(); w.servers.activate = lambda: None
    w.intro_played = True
    w.resize(1200, 820)
    page, service = w.store, w.store_service
    if mode == 'live':
        import time
        for number in (1, 2):
            result = service.client.index_page(number, newest=True)
            service.catalog.save_page(result.submissions, 1)
            time.sleep(1)
        service.catalog.set_meta(crawl_done=int(time.time()))
        page.reload()
        page.open_mod(page.rows[0].id)
    w.navigate('mods.browse')
    w.show()
    for _ in range(40):                 # transitions, the profile request and the screenshots
        QTest.qWait(200)
    w.grab().save(out)
    print('saved', out, '| title:', w.page_title.text(), '| cards:', len(page.card_order), '| first-run shown:', not page.first_run.isHidden())
    w.close()
