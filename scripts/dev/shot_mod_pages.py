import os, sys, tempfile
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('root')
parser.add_argument('outdir')
parser.add_argument('lang', nargs='?', default='en')
parser.add_argument('--look', default='dark')
parser.add_argument('--size', default='1200x820')
parser.add_argument('--scale', type=int, default=100)
parser.add_argument('--pages', default='installed,check,activity', help='comma list of: hub, installed, check, activity')
args = parser.parse_args()
root, outdir, lang = args.root, args.outdir, args.lang
sys.path.insert(0, root)
sys.path.insert(0, os.path.join(root, 'tests'))
from pathlib import Path
from unittest.mock import patch
from deadlock_fps import i18n
i18n.activate(lang)
from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import QApplication
app = QApplication([])
app.setLayoutDirection(Qt.RightToLeft if i18n.rtl() else Qt.LeftToRight)
from deadlock_fps import ui
from deadlock_fps.shell.base import dark_palette, load_fonts
from deadlock_fps.shell import theme
app.setStyle('Fusion'); load_fonts(); app.setPalette(dark_palette()); theme.apply_direction(app, i18n.rtl())
ui.start_look(app, {'mode': args.look, 'accent': 'blue', 'scale': args.scale})
from deadlock_fps.core import ASSETS
from installer_fixtures import ServingTransport, make_vpk, mod_document, HOST
from repo_fixtures import ok, index

with tempfile.TemporaryDirectory() as folder, patch('PySide6.QtCore.QStandardPaths.writableLocation', return_value=folder), \
        patch('deadlock_fps.game_link.detect_games', return_value=[]), patch('deadlock_fps.mods.ModLibrary.discover', return_value=[]), patch('deadlock_fps.core.ensure_closed'):
    game = Path(folder) / 'Deadlock'
    gi = game / 'game/citadel/gameinfo.gi'
    gi.parent.mkdir(parents=True)
    gi.write_text((ASSETS / 'reference/gameinfo.gi').read_text(encoding='utf-8').replace('            Game          "citadel/addons"\n', ''), encoding='utf-8')
    transport = ServingTransport()
    catalogue = [
        ('crimson-skin', [{'version': '1.0.0', 'data': make_vpk(['materials/shared/skin.vmat'], b'1')}, {'version': '1.2.0', 'data': make_vpk(['materials/shared/skin.vmat', 'materials/x.vmat'], b'2'), 'game': {'min_build': 100, 'tested_build': 160}, 'changelog': 'Brighter second material.\nFixes a seam on the shoulder.'}],
         dict(name='Crimson Skin', categories=['skins'], summary='A deep red recolour.', description='Replaces the default texture with a crimson palette. Works with every hero that uses the shared material.', license='CC-BY-4.0')),
        ('clean-hud', [{'version': '0.9.0', 'data': make_vpk(['panorama/hud.css'], b'h')}], dict(name='Clean HUD', categories=['hud'], summary='Removes clutter from the interface.')),
        ('night-map', [{'version': '2.1.0', 'data': make_vpk(['maps/night.vmap'], b'n'), 'game': {'min_build': 100, 'max_build': 120}}], dict(name='Night Map', categories=['maps'], summary='A darker version of the lane map.')),
    ]
    docs = []
    for ident, versions, extra in catalogue:
        for v in versions:
            transport.files[HOST + '%s-%s.vpk' % (ident, v['version'])] = v['data']
        docs.append(mod_document(ident, versions, **extra))
    transport.routes['https://mods.example.org/index.json'] = ok(index(*docs, name='Community Mods'))

    from deadlock_fps.ui import Window
    w = Window(); w.guard_timer.stop(); w.detect_timer.stop(); w.servers.activate = lambda: None
    w.intro_played = True
    w.resize(*(int(n) for n in args.size.split('x')))
    manager = w.repositories.manager
    manager.transport = transport
    w.mod_service.transport = transport
    manager.refresh(manager.add('https://mods.example.org/index.json').source.id)
    w.path.setText(str(game))
    w.show(); app.processEvents()
    installer = w.mod_service.installer()
    from installed_fixture import install_all
    install_all(installer, manager)
    w.mod_service.changed.emit()
    for name, index_ in (('hub', 'mods.browse'), ('installed', 'mods.installed'), ('check', 'mods.health'), ('activity', 'mods.activity')):
        if name not in args.pages.split(','):
            continue
        w.navigate(index_)
        import time
        for _ in range(3):
            QThreadPool.globalInstance().waitForDone(2000); app.processEvents()
        end = time.monotonic() + 1.2
        while time.monotonic() < end:
            app.processEvents(); time.sleep(0.02)
        if name == 'hub':
            w.browse.show_view('sources')
            app.processEvents()
            w.sources_view.card_order[0].clicked.emit()
            app.processEvents()
        if name == 'installed':
            w.installed.other_fold.toggle()
            w.installed.show_classic()
            app.processEvents()
        if name == 'installed' and os.environ.get('DEBUG_LAYOUT'):
            from PySide6.QtWidgets import QWidget as _W
            ins = w.installed
            print('MEASURE installed', ins.scroll.widget().minimumSizeHint().width(), ins.scroll.viewport().width(), ins.width())
            for c in ins.scroll.widget().findChildren(_W):
                if c.isVisibleTo(ins) and c.minimumSizeHint().width() > 560: print('  wide', type(c).__name__, c.property('component'), c.minimumSizeHint().width())
        if name == 'check':
            (installer.addons / 'pak03_dir.vpk').write_bytes(make_vpk(['materials/shared/skin.vmat'], b'foreign'))
            w.compatibility.reload()
            app.processEvents()
            if os.environ.get('DEBUG_LAYOUT'):
                for i in range(w.compatibility.column.count()):
                    it = w.compatibility.column.itemAt(i)
                    wd = it.widget()
                    print(i, type(wd).__name__ if wd else type(it).__name__, wd.geometry() if wd else '', wd.isVisible() if wd else '')
        w.grab().save(os.path.join(outdir, '%s_%s.png' % (name, lang)))
        print('saved', name)
    w.close()
