"""Phase 2 of the redesign: page registry, tokens, theme, base components, the shell window."""
import ast
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from deadlock_fps.shell import components as C
from deadlock_fps.shell import theme
from deadlock_fps.shell.registry import FLAGS, LEGACY_SLOTS, Page, Registry, Tab, default_registry
from deadlock_fps.shell.tokens import Theme, argb, load, qss_color, rgba, scales


class FakeApp:
    """Stands in for QApplication when a test switches the theme: restyling every widget left open by
    earlier tests in the whole suite takes minutes; the real app has one window."""
    def __init__(self):
        self.style = ''

    def setStyleSheet(self, text):
        self.style = text

    def styleSheet(self):
        return self.style

    def topLevelWidgets(self):
        return []


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.r = default_registry()

    def test_ids_groups_and_tabs_follow_the_design(self):
        self.assertEqual([p.id for p in self.r.group('main')], ['home', 'mods', 'performance', 'stats', 'crosshair', 'servers'])
        self.assertEqual([p.id for p in self.r.group('bottom')], ['backups', 'settings'])
        self.assertEqual([p.id for p in self.r.group('hidden')], ['map'])
        self.assertEqual([t.id for t in self.r.get('mods').tabs][:5], ['browse', 'installed', 'health', 'activity'])
        self.assertEqual([t.id for t in self.r.get('settings').tabs], ['general', 'game', 'protection', 'update', 'sources', 'advanced', 'about'])

    def test_every_old_page_has_exactly_one_home(self):
        self.assertEqual(sorted(self.r.slots()), sorted(LEGACY_SLOTS))
        self.assertEqual(len(self.r.slots()), len(set(self.r.slots())))

    def test_resolve(self):
        page, tab, slot = self.r.resolve('mods.health')
        self.assertEqual((page.id, tab.id, slot), ('mods', 'health', 'compatibility'))
        self.assertEqual(self.r.resolve('mods')[2], 'store')               # the first tab
        self.assertEqual(self.r.resolve('home'), (self.r.get('home'), None, 'home'))
        for bad in ('nope', 'mods.nope', 'home.tab'):
            self.assertRaises(KeyError, self.r.resolve, bad)
        self.assertRaises(TypeError, self.r.resolve, 3)
        for address in self.r.addresses():
            self.r.resolve(address)
        self.assertEqual(self.r.address_of('compatibility'), 'mods.health')
        self.assertEqual(self.r.address_of('graph'), 'map')
        self.assertEqual(self.r.resolve('map')[2], 'graph')

    def test_flags_point_at_real_addresses(self):
        for address in FLAGS.values():
            self.r.resolve(address)

    def test_bad_registrations_are_refused(self):
        r = Registry()
        r.register(Page('a', 'A', 'main', 'home', slot='a'))
        self.assertRaises(ValueError, r.register, Page('a', 'A', 'main', 'home', slot='b'))
        self.assertRaises(ValueError, Page, 'b', 'B', 'top', 'home', slot='b')
        self.assertRaises(ValueError, Page, 'b', 'B', 'main', 'home')
        self.assertRaises(ValueError, r.register, Page('c', 'C', 'main', 'home', tabs=(Tab('x', 'X', 's'), Tab('x', 'X', 't'))))
        self.assertRaises(ValueError, r.register, Page('d.e', 'D', 'main', 'home', slot='d'))

    def test_icons_exist(self):
        names = set(theme.icon_names())
        for page in self.r.pages:
            self.assertIn(page.icon, names)


class TokenTests(unittest.TestCase):
    def test_package_copy_matches_the_design_file(self):
        self.assertEqual((ROOT / 'deadlock_fps/shell/tokens.json').read_bytes(), (ROOT / 'docs/design-prototype/tokens.json').read_bytes())

    def test_every_combination_resolves_every_token(self):
        data = load()
        names = set(data['themes']['dark'])
        self.assertEqual(names, set(data['themes']['light']))
        self.assertEqual(len(names), 39)
        for mode in ('dark', 'light'):
            for accent in data['accents']:
                for scale in scales():
                    t = Theme(mode, accent, scale)
                    for name in t.names():
                        t.qss(name)

    def test_colour_conversion(self):
        self.assertEqual(rgba('#000000A6'), (0, 0, 0, 166))
        self.assertEqual(qss_color('#000000A6'), 'rgba(0, 0, 0, 166)')
        self.assertEqual(qss_color('#171a20'), '#171A20')
        self.assertEqual(argb('#11223344'), '#44112233')
        self.assertRaises(ValueError, rgba, 'blue')

    def test_scale_multiplies_only_the_scaled_families(self):
        big = Theme('dark', 'blue', 130)
        self.assertEqual(big.px('space.4'), 21)
        self.assertEqual(big.px('font.size.body'), 18)
        self.assertEqual(big.px('radius.md'), 10)
        self.assertEqual(big.px('size.sidebar'), 216)
        self.assertRaises(ValueError, Theme, 'dim')
        self.assertRaises(ValueError, Theme, 'dark', 'pink')
        self.assertRaises(ValueError, Theme, 'dark', 'blue', 125)

    def test_accent_overrides(self):
        self.assertNotEqual(Theme('dark', 'violet')['color.accent.fill'], Theme('dark', 'blue')['color.accent.fill'])
        self.assertEqual(Theme('light', 'orange')['color.bg.app'], Theme('light', 'blue')['color.bg.app'])

    def test_render_and_the_stylesheet_template(self):
        t = Theme('light')
        self.assertEqual(t.render('a { color: {color.text.primary}; }'), 'a { color: %s; }' % qss_color(t['color.text.primary']))
        self.assertRaises(KeyError, t.render, '{color.nope}')
        for mode in ('dark', 'light'):
            text = theme.stylesheet(Theme(mode))
            self.assertNotIn('{color.', text)
            self.assertNotIn('{space.', text)
            self.assertEqual(text.count('{'), text.count('}'))


class IconExport(unittest.TestCase):
    def test_icons_match_the_mock_up(self):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/dev/export_icons.py'), '--check'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class Widgets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        theme.apply(FakeApp(), 'dark', 'blue', 100)

    def test_every_component_named_in_the_design_exists(self):
        spec = (ROOT / 'vault/Design/New Design/06 Handoff to Build.md').read_text(encoding='utf-8')
        line = next(l for l in spec.splitlines() if l.startswith('`Button`'))
        named = [part.split('`')[1] for part in line.split('·')]
        self.assertEqual(tuple(named), C.COMPONENTS)
        for name in named:
            self.assertTrue(callable(getattr(C, name)), name)

    def test_components_build_and_carry_their_properties(self):
        host = C.Card('Title', 'One sentence.')
        built = [C.Button('Go', 'primary', 'lg', icon='download'), C.IconButton('more', 'More'), C.LinkButton('See'), C.Menu(),
                 C.TextField('Label', 'Help'), C.SearchField('Find'), C.PathField(), C.Select(), C.Checkbox('I understand'),
                 C.Switch('On'), C.SegmentedControl([('a', 'A'), ('b', 'B')]), C.Slider(0, 10, 3), C.Chip('Hide'),
                 host, C.DoorCard('home', 'Home', 'Ready', 'Open'), C.ModCard('Mod', 'Skin · someone', True), C.StatTile('51.2 %', 'Win rate'),
                 C.Tabs(), C.Sidebar(), C.NavItem('home', 'Home', 'home'), C.TopBar(), C.GamePill('Connect game'), C.ActionBar(),
                 C.Sheet(host, 'Details'), C.Dialog('Sure?', 'Text', 'confirm', 'Do it'), C.DataTable(['Hero', 'Win'], numeric=(1,)),
                 C.List(), C.ListRow('Row', 'line', 'info'), C.KeyValue([('Size', '4 MB')]), C.Badge('3', 'count'), C.Bar(.4),
                 C.ConfidenceBar(.52, .58), C.Banner('Heads up', 'More', 'warning'), C.ProgressBar(), C.Spinner(), C.Skeleton(80),
                 C.EmptyState('box', 'Nothing yet', 'Text', variant='danger')]
        for widget in built:
            self.assertIn(widget.property('component'), C.COMPONENTS)
            widget.grab()
        self.assertEqual(built[0].property('variant'), 'primary')
        self.assertRaises(ValueError, C.Button, 'x', 'loud')
        self.assertRaises(ValueError, C.Badge, 'x', 'gold')
        self.assertRaises(ValueError, C.IconButton, 'x', '')
        self.assertRaises(ValueError, C.SegmentedControl, [('a', 'A')])

    def test_states(self):
        field = C.TextField(help='Help')
        field.set_error('Wrong')
        self.assertEqual(field.edit.property('state'), 'error')
        self.assertEqual(field.help.text(), 'Wrong')
        field.set_error('')
        self.assertIsNone(field.edit.property('state'))
        self.assertEqual(field.help.text(), 'Help')
        b = C.Button('Install', 'primary')
        b.set_busy(True)
        self.assertFalse(b.isEnabled())
        b.set_busy(False)
        self.assertTrue(b.isEnabled())
        bar = C.ConfidenceBar()
        bar.set_range(.55, .6)
        self.assertEqual(bar.verdict(), 'success')
        bar.set_range(.3, .45)
        self.assertEqual(bar.verdict(), 'danger')
        bar.set_range(.45, .55)
        self.assertEqual(bar.verdict(), 'neutral')
        s = C.Slider(0, 100, 50)
        s.setValue(500)
        self.assertEqual(s.value(), 100)
        tabs = C.Tabs()
        seen = []
        tabs.changed.connect(seen.append)
        tabs.set_tabs([('a', 'A'), ('b', 'B')])
        tabs.set_current('a')
        tabs.step(1)
        self.assertEqual(seen, ['b'])

    def test_text_is_plain(self):
        label = C.text_label('<b>x</b>', 'CardText')
        self.assertEqual(label.textFormat(), Qt.PlainText)

    def test_theme_switch_reapplies_the_stylesheet_and_repaints(self):
        theme.set_base_style('')
        item = C.NavItem('home', 'Home', 'home')
        before = item.icon().cacheKey()
        fake = FakeApp()
        theme.apply(fake, 'light', 'violet', 115)
        self.assertEqual(theme.current().mode, 'light')
        self.assertIn(qss_color(Theme('light', 'violet', 115)['color.accent.fill']), fake.styleSheet())
        self.assertNotEqual(item.icon().cacheKey(), before)
        theme.apply(fake, 'system')
        self.assertIn(theme.current().mode, ('dark', 'light'))
        self.assertEqual(theme.choice()[0], 'system')
        self.assertEqual(theme.color('color.bg.scrim').alpha(), 166 if theme.current().mode == 'dark' else theme.color('color.bg.scrim').alpha())

    def test_mirrored_icons_flip_in_right_to_left(self):
        a = theme.icon('chev', rtl=False).pixmap(20, 20).toImage()
        b = theme.icon('chev', rtl=True).pixmap(20, 20).toImage()
        self.assertTrue(all(a.pixel(x, y) == b.pixel(a.width() - 1 - x, y) for x in range(a.width()) for y in range(a.height())))
        self.assertNotEqual(a, b)


class Window(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        for p in (patch('deadlock_fps.ui.QStandardPaths.writableLocation', return_value=self.folder.name),
                  patch('deadlock_fps.game_link.detect_games', return_value=[]),
                  patch('deadlock_fps.mods.ModLibrary.discover', return_value=[])):
            p.start()
            self.addCleanup(p.stop)
        from deadlock_fps.ui import Window as W
        self.w = W()
        self.w.guard_timer.stop()
        self.w.detect_timer.stop()
        self.w.servers.activate = lambda: None
        self.addCleanup(self.w.close)

    def test_navigation_by_name(self):
        w = self.w
        w.resize(940, 680)
        w.show()
        self.app.processEvents()
        self.assertEqual(list(w.nav), ['home', 'mods', 'performance', 'stats', 'crosshair', 'servers', 'backups', 'settings'])
        self.assertFalse(w.tabs.isVisible())
        w.navigate('mods.health')
        self.assertEqual((w.current_address, w.current_slot), ('mods.health', 'compatibility'))
        self.assertIs(w.stack.currentWidget(), w.compatibility)
        self.assertTrue(w.tabs.isVisible())
        self.assertEqual(w.tabs.current(), 'health')
        w.tabs.buttons['activity'].click()
        self.assertIs(w.stack.currentWidget(), w.downloads)
        self.assertTrue(w.nav['mods'].isChecked())
        w.nav['settings'].click()
        self.assertEqual(w.current_address, 'settings.general')
        w.navigate('map')
        self.assertIs(w.stack.currentWidget(), w.graph_page)
        self.assertFalse(any(b.isChecked() for b in w.nav.values()))
        w.navigate('settings.update')
        self.assertFalse(w.tabs.isVisible(), 'Settings shows its sections as a list, so there is no tab row')
        self.assertEqual(w.settings_view.current, 'update')

    def test_look_is_switched_and_remembered(self):
        theme.set_base_style('')
        with patch('deadlock_fps.ui.QApplication.instance', return_value=FakeApp()):
            self.w.set_look(mode='light', accent='orange', scale=90)
        saved = json.loads((Path(self.folder.name) / 'workspace.json').read_text(encoding='utf-8'))
        self.assertEqual(saved['look'], {'mode': 'light', 'accent': 'orange', 'scale': 90})
        theme.apply(FakeApp(), 'dark', 'blue', 100)

    def test_start_look_survives_bad_values(self):
        from deadlock_fps.ui import start_look
        fake = FakeApp()
        self.assertEqual(start_look(fake, {'mode': 'dark', 'scale': 'huge'}).mode, 'dark')
        self.assertEqual(start_look(fake, {'mode': 'nope'}).mode, 'dark')
        self.assertEqual(start_look(fake, None).scale, 100)
        self.assertIn('[component="Button"]', fake.styleSheet())
        theme.set_base_style('')


class NoPageNumbers(unittest.TestCase):
    def test_the_window_and_pages_never_navigate_by_number(self):
        for path in list((ROOT / 'deadlock_fps').glob('*.py')) + list((ROOT / 'deadlock_fps/legacy').glob('*.py')):
            tree = ast.parse(path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and getattr(node.func, 'attr', '') in ('navigate', 'setCurrentIndex') and node.args \
                        and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, int) and getattr(node.func.value, 'attr', getattr(node.func.value, 'id', '')) in ('window', 'self', 'stack'):
                    if node.func.attr == 'navigate' or getattr(node.func.value, 'attr', '') == 'stack':
                        self.fail('%s:%d navigates by number' % (path.name, node.lineno))


if __name__ == '__main__':
    unittest.main()
