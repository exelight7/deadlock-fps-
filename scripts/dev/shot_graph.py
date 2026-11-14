import os, sys, tempfile
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
root, out, lang = sys.argv[1], sys.argv[2], sys.argv[3]
mode = sys.argv[4] if len(sys.argv) > 4 else 'default'
sys.path.insert(0, root)
sys.path.insert(0, os.path.join(root, 'tests'))
from unittest.mock import patch
from deadlock_fps import i18n
i18n.activate(lang)
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
app = QApplication([])
app.setLayoutDirection(Qt.RightToLeft if i18n.rtl() else Qt.LeftToRight)
from deadlock_fps.shell.base import dark_palette, load_fonts
from deadlock_fps import ui as _ui
app.setStyle('Fusion'); load_fonts(); app.setPalette(dark_palette()); _ui.start_look(app, {})
from repo_fixtures import FakeTransport, ok, index, mod, version

with tempfile.TemporaryDirectory() as folder, patch('PySide6.QtCore.QStandardPaths.writableLocation', return_value=folder), \
        patch('deadlock_fps.game_link.detect_games', return_value=[]), patch('deadlock_fps.mods.ModLibrary.discover', return_value=[]):
    from deadlock_fps.ui import Window
    w = Window(); w.guard_timer.stop(); w.detect_timer.stop(); w.servers.activate = lambda: None
    w.intro_played = True
    w.resize(1400, 1100)
    t = FakeTransport({
        'https://mods.example.org/index.json': ok(index(
            mod('crimson-skin', name='Crimson Skin', author='Mira', versions=[version('1.0.0', game={'tested_build': 150}), version('1.1.0', game={'tested_build': 160}, dependencies=[{'id': 'base-lib', 'range': '*'}], conflicts=[{'id': 'azure-skin', 'range': '*'}])]),
            mod('base-lib', name='Base Lib', author='Mira', versions=[version('2.0.0', game={'tested_build': 160})]),
            mod('azure-skin', name='Azure Skin', author='Zed', versions=[version('1.0.0', game={'tested_build': 150})]),
            mod('clean-hud', name='Clean HUD', author='Ian', versions=[version('0.9.0', game={'tested_build': 160})]), name='Community Mods')),
    })
    w.repositories.manager.transport = t
    w.repositories.manager.refresh(w.repositories.manager.add('https://mods.example.org/index.json').source.id)
    w.navigate('map')
    w.show()
    app.processEvents()
    page = w.graph_page
    page.rebuild()
    if mode == 'select':
        node = next(n for n in page.graph.nodes.values() if n.label == 'Repository Manager')
        page.canvas.select(node.id)
        page.canvas.center_on(node.id)
    if mode == 'expand':
        page.expand_all()
        page.canvas.settle_now(300, 4.0)
    app.processEvents()
    w.grab().save(out)
    print('saved', out, 'nodes', len(page.graph.nodes), 'edges', len(page.graph.edges), 'visible', len(page.canvas.view.nodes), '|', page.notes.text()[:80])
    w.close()
