"""Photograph Mods > Browse in the real window offscreen, with sample data and no network (for the Phase 3 checks: look at the picture).

    .venv/Scripts/python.exe scripts/dev/shot_browse.py OUT.png [--state first|filled|sheet|review|loading|error|partial|nogame]
        [--lang en|ar] [--look dark|light] [--size 1200x820] [--scale 100]

The catalogue is filled from the fake GameBanana of the tests; nothing outside a temporary folder is read or written.
"""
import argparse
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from unittest.mock import patch   # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument('out')
parser.add_argument('--state', default='filled')
parser.add_argument('--lang', default='en')
parser.add_argument('--look', default='dark')
parser.add_argument('--size', default='1200x820')
parser.add_argument('--scale', type=int, default=100)
args = parser.parse_args()

from deadlock_fps import i18n   # noqa: E402
i18n.activate(args.lang)
from PySide6.QtCore import Qt, QThreadPool   # noqa: E402
from PySide6.QtWidgets import QApplication   # noqa: E402
app = QApplication([])
app.setLayoutDirection(Qt.RightToLeft if i18n.rtl() else Qt.LeftToRight)
from deadlock_fps import ui   # noqa: E402
from deadlock_fps.shell.base import dark_palette, load_fonts   # noqa: E402
from deadlock_fps.detection import GameStatus   # noqa: E402
from deadlock_fps.pages.browse import InstallReview   # noqa: E402
from deadlock_fps.shell import theme   # noqa: E402
from store_fixtures import PagedGameBanana, file_entry, profile_document, record   # noqa: E402
app.setStyle('Fusion')
load_fonts()
app.setPalette(dark_palette())
theme.apply_direction(app, i18n.rtl())
ui.start_look(app, {'mode': args.look, 'accent': 'blue', 'scale': args.scale})

NAMES = (('Clean HUD', 'HUD', '', 'mira'), ('Night Skyline', 'Maps', '', 'oskar'), ('Abrams Steel', 'Skins', 'Abrams', 'vento'), ('Soft Hit Sounds', 'Sounds', '', 'noor'),
         ('Haze Ember', 'Skins', 'Haze', 'kael'), ('Minimal Map', 'Maps', '', 'mira'), ('Lash Arctic', 'Skins', 'Lash', 'juno'), ('Clear Skies', 'Maps', '', 'oskar'),
         ('A mod with a very long name that cannot possibly fit on one line of a card', 'Skins', 'Wraith', 'a-very-long-author-name'),
         ('Pink Doorman', 'Skins', 'Doorman', 'mira'), ('Crimson Wraith', 'Skins', 'Wraith', 'zed'), ('Quiet Menu', 'HUD', '', 'noor'))


def settle():
    for _ in range(4):
        QThreadPool.globalInstance().waitForDone(5000)
        app.processEvents()


with tempfile.TemporaryDirectory() as folder:
    root = Path(folder)
    game = root / 'Deadlock'
    (game / 'game/citadel').mkdir(parents=True)
    (game / 'game/citadel/gameinfo.gi').write_text('test')
    video = root / 'Steam/userdata/111/1422450/local/cfg/video.txt'
    video.parent.mkdir(parents=True)
    video.write_text('test')
    linked = args.state != 'nogame'
    found = [game] if linked else []
    status = GameStatus('installed', game, '6857', 33_000_000_000, False, 2) if linked else GameStatus('missing', None, '', 0, False, 2)
    with patch('PySide6.QtCore.QStandardPaths.writableLocation', return_value=str(root / 'data')), \
            patch('deadlock_fps.game_link.detect_games', return_value=found), patch('deadlock_fps.game_link.scan', return_value=status), \
            patch('deadlock_fps.game_link.video_files', return_value=[video]), patch('deadlock_fps.core.video_files', return_value=[video]), \
            patch('deadlock_fps.mods.ModLibrary.discover', return_value=[]):
        window = ui.Window()
        window.guard_timer.stop()
        window.detect_timer.stop()
        window.servers.activate = lambda: None
        window.intro_played = True
        width, height = (int(n) for n in args.size.split('x'))
        window.resize(width, height)
        page, service = window.store, window.store_service
        records = [record(100 + n, name, category=category, sub=sub, author=author, images=3) for n, (name, category, sub, author) in enumerate(NAMES)]
        records += [record(200 + n, 'Sample mod %02d' % n, category='Skins', sub='Haze') for n in range(30)]
        server = PagedGameBanana(records)
        server.profiles[102] = profile_document(102, 'Abrams Steel', text='A brushed-steel look for Abrams with matching ability effects. Sample text standing in for the description from the mod page.',
                                                files=[file_entry(1, 'abrams_steel_v3.zip', 26_000_000, '03f6e9f9e25675d14521c84e010a33c2'), file_entry(2, 'abrams_steel_lite.zip', 9_000_000, 'ab' * 16)])
        service.transport = server
        service.client.transport = server
        if args.state != 'first':
            now = 1_700_000_000
            service.client.transport = server
            result = service.client.index_page(1, newest=True)
            service.catalog.save_page(result.submissions, 1)
            result = service.client.index_page(2, newest=True)
            service.catalog.save_page(result.submissions, 1)
            import time
            service.catalog.set_meta(crawl_done=int(time.time()) - 7200)
            page.reload()
        window.navigate('mods.browse')
        window.show()
        app.processEvents()
        if args.state in ('sheet', 'review', 'nogame'):
            card = next(c for c in page.card_order if c.name.text() == 'Abrams Steel')
            card.clicked.emit()
            settle()
        if args.state == 'loading':
            service.busy = True
            page.progress_bar.set_known(41, 123)
            page.progress_text.setText('Page 41 of about 123.')
            page.show_state()
            if not page.card_order:
                pass
        if args.state == 'error':
            page.sync_failed('HTTP 503', 'network')
        if args.state == 'partial':
            service.catalog.set_meta(crawl_next=3, crawl_done=0)
            page.reload()
        settle()
        app.processEvents()
        if args.state == 'review':
            plan = SimpleNamespace(action='install', mod_name='Abrams Steel', version='3.0', replaces='', trust='UNVERIFIED', repository_name='GameBanana', verified=False,
                                   md5_verified=True, actual_sha256='ab' * 32, files=(SimpleNamespace(name='pak07_dir.vpk', source='abrams_steel_v3.zip', size=24_100_000, entries=1),),
                                   removed=(), warnings=('It changes the same files as Clean HUD. Clean HUD keeps winning because it has the lower number.',), blockers=(),
                                   requires_ack=True, can_install=True)
            dialog = InstallReview(plan, window)
            dialog.show()
            app.processEvents()
            dialog.grab().save(args.out)
            print('saved', args.out, '(dialog)')
            dialog.close()
        else:
            window.grab().save(args.out)
            print('saved', args.out, window.current_address, '| cards:', len(page.card_order), '| columns:', page.columns)
        window.close()
