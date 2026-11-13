"""Render every screen of the app to PNG without touching a real game, real settings or the network.

    python scripts/make_screenshots.py [output folder] [--size 1200x820] [--only 0,4] [--dialogs] [--lang en|ar] [--docs]

The window runs against a throw-away Deadlock folder and a temporary data
folder, ping results are sample values, and nothing is applied. `--docs`
writes the README images into docs/.
"""
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# The native platform gives real font fallback; the window is never mapped to the screen (WA_DontShowOnScreen).
if '--offscreen' in sys.argv or (sys.platform != 'win32' and not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY')):
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_ENABLE_HIGHDPI_SCALING', '0')

from PySide6.QtCore import Qt, QThreadPool  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

SHOWN_PATH = r'C:\Program Files (x86)\Steam\steamapps\common\Deadlock'
NAMES = ['overview', 'graphics', 'mods', 'backups', 'servers', 'crosshair', 'update-center', 'mod-inspector', 'settings']
DOCS = {'overview': 'screenshot.png', 'graphics': 'graphics.png', 'mods': 'mods.png', 'backups': 'backups.png', 'servers': 'servers.png',
        'crosshair': 'crosshair.png', 'update-center': 'update-center.png', 'mod-inspector': 'mod-inspector.png', 'settings': 'settings.png'}


def option(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def settle(app, rounds=6):
    for _ in range(rounds):
        QThreadPool.globalInstance().waitForDone(1500)
        app.processEvents()


def main():
    from deadlock_fps import i18n
    i18n.activate(option('--lang', 'en'))            # before the interface modules are imported
    from deadlock_fps.core import ASSETS
    from deadlock_fps.design import STYLE, dark_palette, load_fonts
    from deadlock_fps.servers import PingResult
    docs = '--docs' in sys.argv
    positional = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith('--') and sys.argv[i - 1] not in ('--size', '--only', '--lang')]
    target = ROOT / 'docs' if docs else Path(positional[0] if positional else ROOT / 'build/screenshots')
    width, height = (int(v) for v in option('--size', '1200x820').split('x'))
    only = [int(v) for v in option('--only', ','.join(map(str, range(9)))).split(',')]
    target.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    app.setLayoutDirection(Qt.RightToLeft if i18n.LANGUAGE == 'ar' and '--ltr' not in sys.argv else Qt.LeftToRight)
    app.setStyle('Fusion')
    load_fonts()
    app.setPalette(dark_palette())
    app.setStyleSheet(STYLE)
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        game = root / 'steamapps/common/Deadlock'
        gameinfo = game / 'game/citadel/gameinfo.gi'
        gameinfo.parent.mkdir(parents=True)
        gameinfo.write_bytes((ASSETS / 'reference/gameinfo.gi').read_bytes())
        video = root / 'userdata/100200300/1422450/local/cfg/video.txt'
        video.parent.mkdir(parents=True)
        video.write_bytes((ASSETS / 'reference/video.txt').read_bytes())
        with patch('deadlock_fps.ui.QStandardPaths.writableLocation', return_value=str(root / 'data')), \
                patch('deadlock_fps.ui.detect_games', return_value=[game]), patch('deadlock_fps.ui.video_files', return_value=[video]), \
                patch('deadlock_fps.core.video_files', return_value=[video]), patch('deadlock_fps.mods.ModLibrary.discover', return_value=[]):
            from deadlock_fps.ui import Window
            window = Window()
            window.guard_timer.stop()
            window.servers.activate = lambda: None
            window.intro_played = True
            window.setAttribute(Qt.WA_DontShowOnScreen)
            window.resize(width, height)
            window.show()
            settle(app)
            samples = [18.4, 31.0, 44.6, 58.2, 73.9, 96.5, 121.3, 148.0, 187.4]
            for row in range(min(window.servers.table.rowCount(), 14)):
                code = window.servers.table.item(row, 0).data(Qt.UserRole)
                result = PingResult(samples[row], 0, 'ok', 'sample', '0.0.0.0') if row < len(samples) else PingResult(None, 100, 'no_reply', 'sample')
                window.servers.ping_progress((code, result))
            for row in (0, 2):
                window.servers.table.item(row, 0).setCheckState(Qt.Checked)
            for index in only:
                window.navigate(index)
                settle(app)
                window.transition.finish()
                deadline = time.monotonic() + .6
                while time.monotonic() < deadline:
                    app.processEvents()
                    time.sleep(.01)
                if docs and i18n.LANGUAGE == 'ar':
                    if index:
                        continue
                    DOCS['overview'] = 'screenshot-ar.png'
                name = DOCS[NAMES[index]] if docs else '%d-%s-%dx%d.png' % (index, NAMES[index], width, height)
                real = window.path.text()
                window.path.setText(SHOWN_PATH)      # never publish the temporary folder (it contains the user name)
                app.processEvents()
                window.grab().save(str(target / name))
                window.path.setText(real)
                print(target / name)
            if '--dialogs' in sys.argv or docs:
                from types import SimpleNamespace
                from deadlock_fps.crosshair_ui import CrosshairGallery
                from deadlock_fps.mod_ui import ModReview
                gallery = CrosshairGallery(window.crosshair.profiles, window.crosshair)
                plan = {game / 'game/citadel/fps_studio/pak01_dir.vpk': b'0' * 48213, game / 'game/citadel/gameinfo.gi': b'0' * 9120}
                finding = SimpleNamespace(severity='warning', title='Daylock', detail='جرّب الوضوح داخل التدريب بعد التركيب.')
                review = ModReview(SimpleNamespace(plan=plan, settings=SimpleNamespace(mods=('daylock',)), report=SimpleNamespace(findings=[finding])), window.mods_page)
                for name, dialog in (('crosshair-gallery', gallery), ('mod-review', review)):
                    dialog.setAttribute(Qt.WA_DontShowOnScreen)
                    dialog.show()
                    settle(app, 2)
                    if not (docs and name == 'mod-review'):
                        path = target / (name + '.png' if docs else 'dialog-%s.png' % name)
                        dialog.grab().save(str(path))
                        print(path)
                    dialog.close()
            window.close()
            settle(app, 2)


if __name__ == '__main__':
    main()
