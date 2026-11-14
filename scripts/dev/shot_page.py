"""Photograph one page of the real window offscreen, for the Phase 3 checks (look at the picture; do not trust the code).

    .venv/Scripts/python.exe scripts/dev/shot_page.py OUT.png ADDRESS [--lang en|ar] [--look dark|light] [--size 1200x820]
        [--state linked|unlinked|missing|running] [--scale 100]

`linked` builds a throwaway game folder; nothing outside the temporary folder is touched or read.
"""
import argparse
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from unittest.mock import patch   # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument('out')
parser.add_argument('address')
parser.add_argument('--lang', default='en')
parser.add_argument('--look', default='dark')
parser.add_argument('--size', default='1200x820')
parser.add_argument('--state', default='unlinked')
parser.add_argument('--scale', type=int, default=100)
parser.add_argument('--sample', action='store_true', help='fill the Home attention list with sample rows')
args = parser.parse_args()

from deadlock_fps import i18n   # noqa: E402
i18n.activate(args.lang)
from PySide6.QtCore import Qt   # noqa: E402
from PySide6.QtWidgets import QApplication   # noqa: E402
app = QApplication([])
app.setLayoutDirection(Qt.RightToLeft if i18n.rtl() else Qt.LeftToRight)
from deadlock_fps import ui   # noqa: E402
from deadlock_fps.shell.base import dark_palette, load_fonts   # noqa: E402
from deadlock_fps.detection import GameStatus   # noqa: E402
from deadlock_fps.shell import theme   # noqa: E402
app.setStyle('Fusion')
load_fonts()
app.setPalette(dark_palette())
theme.apply_direction(app, i18n.rtl())
ui.start_look(app, {'mode': args.look, 'accent': 'blue', 'scale': args.scale})

with tempfile.TemporaryDirectory() as folder:
    root = Path(folder)
    game = root / 'Deadlock'
    (game / 'game/citadel').mkdir(parents=True)
    (game / 'game/citadel/gameinfo.gi').write_text('test')
    video = root / 'Steam/userdata/111/1422450/local/cfg/video.txt'
    video.parent.mkdir(parents=True)
    video.write_text('test')
    found = [game] if args.state in ('linked', 'running') else []
    status = GameStatus('installed', game, '6857', 33_000_000_000, args.state == 'running', 2) if found else GameStatus('missing', None, '', 0, False, 2)
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
        window.navigate(args.address)
        window.show()
        app.processEvents()
        window.refresh_home()
        if args.sample and window.current_slot == 'home':
            noop = lambda: None
            window.home.set_mods(12, 2)
            window.home.set_attention([
                {'tone': 'danger', 'icon': 'warn', 'title': 'Your mods are switched off in the game', 'line': 'Steam restored a game file. One press puts it back.', 'action': 'Repair', 'callback': noop},
                {'tone': 'info', 'icon': 'info', 'title': '2 mods have updates', 'line': 'Clean HUD · Night Skyline', 'action': 'See updates', 'callback': noop},
                {'tone': 'info', 'icon': 'download', 'title': 'Toolbox 4.1 is ready', 'line': 'You have 4.0.0.', 'action': 'Update', 'callback': noop}])
        app.processEvents()
        window.grab().save(args.out)
        print('saved', args.out, window.current_address)
        window.close()
