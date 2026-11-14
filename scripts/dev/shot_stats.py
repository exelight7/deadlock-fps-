"""Render the Stats page offscreen. Usage: shot_stats.py <repo root> <out.png> en|ar empty|heroes|ranks|me|failed

Runs the whole window against a scripted fake of api.deadlock-api.com (no network): `heroes` and `ranks` press "Load
statistics" first, `me` also looks an account up, `failed` shows the page after a server error. Then look at the PNG.
"""
import os
import random
import sys
import tempfile
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
root, out, lang, what = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
sys.path.insert(0, root)
sys.path.insert(0, os.path.join(root, 'tests'))
from unittest.mock import patch
from deadlock_fps import i18n
i18n.activate(lang)
from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
app = QApplication([])
app.setLayoutDirection(Qt.RightToLeft if i18n.rtl() else Qt.LeftToRight)
from deadlock_fps import ui
from deadlock_fps.shell.base import dark_palette, load_fonts
from deadlock_fps.shell import theme
app.setStyle('Fusion'); load_fonts(); app.setPalette(dark_palette()); theme.apply_direction(app, i18n.rtl())
ui.start_look(app, {'mode': os.environ.get('LOOK', 'dark'), 'accent': 'blue', 'scale': 100})
from stats_fixtures import FakeServer, badge_row, hero_row, player_row, status

NAMES = ['Abrams', 'Bebop', 'Dynamo', 'Grey Talon', 'Haze', 'Infernus', 'Ivy', 'Kelvin', 'Lady Geist', 'Lash', 'McGinnis', 'Mo & Krill', 'Paradox',
         'Pocket', 'Seven', 'Shiv', 'Sinclair', 'Viscous', 'Vindicta', 'Vyper', 'Warden', 'Wraith', 'Yamato']
ACCOUNT = 123456789
random.seed(7)
server = FakeServer()
server.heroes = [{'id': i + 1, 'name': name} for i, name in enumerate(NAMES)]
server.hero_rows = []
for i in range(len(NAMES)):
    matches = random.randint(900, 24000)
    wins = int(matches * random.uniform(0.44, 0.57))
    server.hero_rows.append(hero_row(i + 1, matches, wins, kills=matches * random.randint(5, 9), deaths=matches * random.randint(4, 7),
                                     assists=matches * random.randint(7, 12), net_worth=matches * random.randint(32000, 52000)))
server.hero_rows.append(hero_row(24, 12, 9, kills=60, deaths=20, assists=80, net_worth=500000))
server.heroes.append({'id': 24, 'name': 'Rarely Played'})
server.game = [{'total_matches': 41234, 'avg_duration_s': 2183.2, 'abandon_rate': 0.063}]
server.badges = [badge_row(tier * 10 + sub, random.randint(800, 4000) * (6 - abs(tier - 5)), random.randint(300, 2000) * (6 - abs(tier - 5))) for tier in range(1, 12) for sub in range(1, 7)]
server.ranked[ACCOUNT] = {'badge': 63, 'rank': 6, 'subrank': 3, 'last_match': None}
server.players[ACCOUNT] = [player_row(ACCOUNT, 6, 64, 38, kills=520, deaths=340, assists=610), player_row(ACCOUNT, 5, 31, 14, kills=240, deaths=210, assists=300),
                           player_row(ACCOUNT, 15, 12, 5, kills=90, deaths=80, assists=110), player_row(ACCOUNT, 19, 3, 3, kills=30, deaths=9, assists=22)]


def settle():
    for _ in range(4):
        QThreadPool.globalInstance().waitForDone()
        app.processEvents()


with tempfile.TemporaryDirectory() as folder, patch('deadlock_fps.ui.QStandardPaths.writableLocation', return_value=folder), \
        patch('PySide6.QtCore.QStandardPaths.writableLocation', return_value=folder), \
        patch('deadlock_fps.game_link.detect_games', return_value=[]), patch('deadlock_fps.mods.ModLibrary.discover', return_value=[]):
    from deadlock_fps.ui import Window
    w = Window(); w.guard_timer.stop(); w.detect_timer.stop(); w.servers.activate = lambda: None
    w.intro_played = True
    w.resize(1200, 820)
    w.stats_service.source.api.transport = server
    w.navigate('stats')
    w.show()
    page = w.stats
    if what == 'failed':
        server.hook = lambda url, query: status(503)
    if what != 'empty':
        page.load()
        settle()
    if what == 'ranks':
        w.navigate('stats.ranks')
    if what == 'me':
        w.navigate('stats.me')
        page.account_field.setText(str(ACCOUNT))
        page.look_up()
        settle()
    for _ in range(6):
        QTest.qWait(200)
    w.grab().save(out)
    print('saved', out, '| status:', page.status.text()[:100].replace('\n', ' / '))
    w.close()
