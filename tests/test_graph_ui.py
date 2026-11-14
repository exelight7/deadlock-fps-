"""The Knowledge Graph page, driven with real mouse, wheel and keyboard events."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import Qt, QPoint, QPointF, QEvent
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

from deadlock_fps.graph import Graph, Node
from deadlock_fps.pages.map import GraphPage, GraphCanvas, ROOT
from deadlock_fps.mod_service import ModService
from deadlock_fps.repos import RepositoryManager, RepositoryStore, TrustRegistry
from repo_fixtures import FakeTransport, ok, index, mod as mod_doc, version as version_doc
import tempfile


class FakeWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.visited = []

        self.searched = ''

    def navigate(self, page):
        self.visited.append(page)

    def search_sources(self, text):
        self.navigate('mods.browse')
        self.searched = text


class Interact(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        transport = FakeTransport({'https://one.example.org/i.json': ok(index(
            mod_doc('crimson-skin', name='Crimson', author='Mira', versions=[version_doc('1.0.0', game={'tested_build': 150}), version_doc('1.1.0', game={'tested_build': 160}, dependencies=[{'id': 'base-lib', 'range': '*'}])]),
            mod_doc('base-lib', name='Base Lib', author='Mira', versions=[version_doc('2.0.0')]), name='One'))})
        self.manager = RepositoryManager(RepositoryStore(Path(self.temp.name)), transport, trust=TrustRegistry({}))
        self.manager.refresh(self.manager.add('https://one.example.org/i.json').source.id)
        self.service = ModService(self.manager, lambda: '')
        self.window = FakeWindow()
        self.page = GraphPage(self.window, self.service)
        self.addCleanup(self.page.deleteLater)
        self.window.resize(1300, 900)
        self.window.show()
        self.page.resize(1200, 800)
        self.page.show()
        self.page.rebuild()
        self.canvas = self.page.canvas
        self.app.processEvents()

    def node(self, label, kind=None):
        return next(n for n in self.page.graph.nodes.values() if n.label == label and (kind is None or n.kind == kind))

    def at(self, node_id):
        return self.canvas.to_screen(*self.canvas.positions[node_id]).toPoint()

    def click(self, node_id):
        QTest.mouseClick(self.canvas, Qt.LeftButton, Qt.NoModifier, self.at(node_id))

    def drag(self, start, end):
        press = QMouseEvent(QEvent.MouseButtonPress, QPointF(start), QPointF(start), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        move = QMouseEvent(QEvent.MouseMove, QPointF(end), QPointF(end), Qt.NoButton, Qt.LeftButton, Qt.NoModifier)
        release = QMouseEvent(QEvent.MouseButtonRelease, QPointF(end), QPointF(end), Qt.LeftButton, Qt.NoButton, Qt.NoModifier)
        for event in (press, move, release):
            self.app.sendEvent(self.canvas, event)

    def wheel(self, point, delta):
        event = QWheelEvent(QPointF(point), QPointF(point), QPoint(0, 0), QPoint(0, delta), Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
        self.app.sendEvent(self.canvas, event)

    # ---- content -------------------------------------------------------------------------

    def test_the_graph_holds_real_vault_and_catalogue_data_with_honest_filters(self):
        counts = self.page.graph.kind_counts()
        for kind in ('feature', 'decision', 'doc', 'module', 'repository', 'mod', 'author', 'game', 'version'):
            self.assertGreater(counts.get(kind, 0), 0, kind)
        self.assertEqual(self.page.kind_boxes['mod'].text(), 'Mod (2)')
        self.assertEqual(self.page.kind_boxes['repository'].text(), 'Source (1)')
        self.assertTrue(all(self.page.kind_boxes[k].isEnabled() == (counts.get(k, 0) > 0) for k in self.page.kind_boxes))

    def test_versions_and_code_modules_start_folded_and_expand_on_double_click(self):
        kinds = {n.kind for n in self.canvas.view.nodes}
        self.assertNotIn('version', kinds)
        crimson = self.node('Crimson', 'mod')
        before = {n.id: self.canvas.positions[n.id] for n in self.canvas.view.nodes}
        QTest.mouseDClick(self.canvas, Qt.LeftButton, Qt.NoModifier, self.at(crimson.id))
        self.app.processEvents()
        self.assertIn('version', {n.kind for n in self.canvas.view.nodes})
        self.assertNotIn(crimson.id, self.page.collapsed)
        moved = [n for n, p in before.items() if n in self.canvas.positions and self.canvas.positions[n] != p]
        self.assertLess(len(moved), len(before) / 2 + 3)                      # expanding eases things apart, it does not scramble the view
        QTest.mouseDClick(self.canvas, Qt.LeftButton, Qt.NoModifier, self.at(crimson.id))
        self.assertNotIn('version', {n.kind for n in self.canvas.view.nodes})

    def test_expand_all_and_collapse_all(self):
        self.page.expand_all()
        full = len(self.canvas.view.nodes)
        self.assertEqual(full, len(self.page.graph.nodes))
        self.page.collapse_all()
        self.assertLess(len(self.canvas.view.nodes), full)

    # ---- selection ------------------------------------------------------------------------

    def test_clicking_selects_highlights_relations_and_fills_the_details(self):
        picked = []
        self.canvas.selected.connect(picked.append)
        feature = self.node('Repository Manager', 'feature')
        self.click(feature.id)
        self.assertEqual((self.canvas.selected_id, picked), (feature.id, [feature.id]))
        self.assertEqual(self.page.d_title.text(), 'Repository Manager')
        self.assertIn('Feature · IMPLEMENTED', self.page.d_kind.text())
        self.assertIn('Status: IMPLEMENTED', self.page.d_lines.text())
        listed = [self.page.neighbors.item(i).text() for i in range(self.page.neighbors.count())]
        self.assertTrue(any('affects' in t and 'ADR-003' in t for t in listed))
        self.assertTrue(any('contains' in t and 'manager.py' in t for t in listed))
        self.assertEqual(self.canvas.related, {b for a, b, _, _ in self.canvas.view.edges if a == feature.id} | {a for a, b, _, _ in self.canvas.view.edges if b == feature.id})
        self.click_empty()
        self.assertIsNone(self.canvas.selected_id)
        self.assertEqual(self.canvas.related, set())

    def click_empty(self):
        for x in range(10, self.canvas.width() - 10, 25):
            for y in range(10, self.canvas.height() - 10, 25):
                if self.canvas.node_at(QPointF(x, y)) is None:
                    QTest.mouseClick(self.canvas, Qt.LeftButton, Qt.NoModifier, QPoint(x, y))
                    return
        self.fail('no empty spot')

    def test_clicking_a_neighbour_in_the_list_jumps_to_it(self):
        feature = self.node('Repository Manager', 'feature')
        self.click(feature.id)
        row = next(i for i in range(self.page.neighbors.count()) if 'ADR-003' in self.page.neighbors.item(i).text())
        self.page.jump(self.page.neighbors.item(row))
        self.assertTrue(self.canvas.selected_id.startswith('note:ADR-003'))
        self.assertEqual(self.page.d_kind.text().split(' · ')[0], 'Decision')

    # ---- pan and zoom ---------------------------------------------------------------------------

    def test_dragging_pans_without_selecting_and_the_wheel_zooms_around_the_cursor(self):
        pan = QPointF(self.canvas.pan)
        self.drag(QPoint(200, 200), QPoint(260, 230))
        self.assertEqual((self.canvas.pan - pan).toPoint(), QPoint(60, 30))
        self.assertIsNone(self.canvas.selected_id)
        cursor = QPoint(500, 400)
        before = self.canvas.to_world(QPointF(cursor))
        zoom = self.canvas.zoom
        self.wheel(cursor, 120)
        self.assertGreater(self.canvas.zoom, zoom)
        after = self.canvas.to_world(QPointF(cursor))
        self.assertAlmostEqual(before[0], after[0], places=3)
        self.assertAlmostEqual(before[1], after[1], places=3)
        for _ in range(60):
            self.wheel(cursor, -120)
        self.assertGreaterEqual(self.canvas.zoom, 0.08)
        for _ in range(80):
            self.wheel(cursor, 120)
        self.assertLessEqual(self.canvas.zoom, 6.0)

    def test_keyboard_navigation(self):
        self.canvas.setFocus()
        zoom = self.canvas.zoom
        QTest.keyClick(self.canvas, Qt.Key_Plus)
        self.assertGreater(self.canvas.zoom, zoom)
        QTest.keyClick(self.canvas, Qt.Key_Minus)
        self.assertAlmostEqual(self.canvas.zoom, zoom, places=6)
        pan = QPointF(self.canvas.pan)
        QTest.keyClick(self.canvas, Qt.Key_Left)
        self.assertEqual((self.canvas.pan - pan).toPoint(), QPoint(40, 0))
        QTest.keyClick(self.canvas, Qt.Key_Tab)
        first = self.canvas.selected_id
        self.assertIsNotNone(first)
        QTest.keyClick(self.canvas, Qt.Key_Tab)
        self.assertNotEqual(self.canvas.selected_id, first)
        QTest.keyClick(self.canvas, Qt.Key_Backtab)
        self.assertEqual(self.canvas.selected_id, first)
        QTest.keyClick(self.canvas, Qt.Key_Escape)
        self.assertIsNone(self.canvas.selected_id)
        QTest.keyClick(self.canvas, Qt.Key_F)
        self.assertTrue(0.08 <= self.canvas.zoom <= 2.0)

    def test_enter_expands_the_selected_group(self):
        crimson = self.node('Crimson', 'mod')
        self.canvas.select(crimson.id)
        QTest.keyClick(self.canvas, Qt.Key_Return)
        self.assertIn('version', {n.kind for n in self.canvas.view.nodes})

    # ---- search, filters, focus ----------------------------------------------------------------------

    def test_search_marks_matches_cycles_with_enter_and_finds_hidden_nodes_through_their_group(self):
        self.page.query.setText('repository manager')
        feature = self.node('Repository Manager', 'feature')
        self.assertIn(feature.id, self.canvas.matches)
        self.assertIn('matches', self.page.notes.text())
        QTest.keyClick(self.page.query, Qt.Key_Return)
        self.assertEqual(self.canvas.selected_id, self.page._match_order[0])
        self.page.query.setText('1.1.0')                                         # a version, folded into its mod
        self.assertEqual(self.canvas.matches, {self.node('Crimson', 'mod').id})
        self.page.query.setText('zzzzzz')
        self.assertEqual(self.canvas.matches, set())
        self.assertIn('0 matches', self.page.notes.text())

    def test_kind_filters_hide_and_show_nodes_and_their_edges(self):
        self.page.kind_boxes['doc'].setChecked(False)
        self.assertNotIn('doc', {n.kind for n in self.canvas.view.nodes})
        self.assertTrue(all(a in {n.id for n in self.canvas.view.nodes} and b in {n.id for n in self.canvas.view.nodes} for a, b, _, _ in self.canvas.view.edges))
        self.page.kind_boxes['doc'].setChecked(True)
        self.assertIn('doc', {n.kind for n in self.canvas.view.nodes})

    def test_plain_note_links_are_off_until_asked_for(self):
        self.assertNotIn('links to', {k for _, _, k, _ in self.canvas.view.edges})
        self.page.links_check.setChecked(True)
        self.assertIn('links to', {k for _, _, k, _ in self.canvas.view.edges})

    def test_focus_mode_shows_only_the_selection_and_its_neighbours(self):
        feature = self.node('Repository Manager', 'feature')
        self.canvas.select(feature.id)
        everything = len(self.canvas.view.nodes)
        self.page.focus_check.setChecked(True)
        shown = {n.id for n in self.canvas.view.nodes}
        graph, collapsed = self.page.graph, self.page.collapsed
        neighbours = {graph.representative(other, collapsed) for other, kind, _d in graph.neighbors(feature.id) if kind != 'links to'}      # plain note links are filtered out by default
        expected = {feature.id} | {n for n in neighbours if n}                      # hidden module files stand in as their package
        self.assertEqual(shown, expected)
        self.assertLess(len(shown), everything)
        self.page.focus_check.setChecked(False)
        self.assertEqual(len(self.canvas.view.nodes), everything)

    # ---- navigation ------------------------------------------------------------------------------------------

    def test_nodes_lead_to_app_pages_notes_and_files(self):
        self.canvas.select(self.node('One', 'repository').id)
        self.assertTrue(self.page.app_button.isEnabled())
        self.page.app_button.click()
        self.assertEqual(self.window.visited, ['settings.sources'])
        self.canvas.select(self.node('Crimson', 'mod').id)
        self.page.app_button.click()
        self.assertEqual((self.window.visited[-1], self.window.searched), ('mods.browse', 'Crimson'))
        feature = self.node('Repository Manager', 'feature')
        self.canvas.select(feature.id)
        self.assertTrue(self.page.note_button.isEnabled())
        self.assertFalse(self.page.file_button.isEnabled())
        opened = []
        with patch('deadlock_fps.pages.map.QDesktopServices.openUrl', side_effect=lambda url: (opened.append(bytes(url.toEncoded()).decode()), False)[1]):
            self.page.note_button.click()
        self.assertTrue(opened[0].startswith('obsidian://open?path='))
        self.assertIn('Repository%20Manager.md', opened[0])                           # the path travels percent-encoded
        self.assertTrue(opened[1].startswith('file:///'))                                # not registered: falls back to the file
        self.canvas.select(self.node('manager.py', 'module').id)
        self.assertTrue(self.page.file_button.isEnabled())
        with patch('deadlock_fps.pages.map.QDesktopServices.openUrl', side_effect=lambda url: opened.append(bytes(url.toEncoded()).decode()) or True):
            self.page.file_button.click()
        self.assertTrue(opened[-1].endswith('deadlock_fps/repos/manager.py'))
        self.assertTrue((ROOT / 'deadlock_fps/repos/manager.py').is_file())

    def test_the_graph_follows_the_catalogue_but_only_rebuilds_while_visible(self):
        self.assertEqual(self.page.kind_boxes['mod'].text(), 'Mod (2)')
        self.page.hide()
        self.manager.set_enabled(self.manager.list()[0].source.id, False)
        self.service.changed.emit()
        self.assertTrue(self.page.stale)                                           # hidden: nothing is recomputed behind the user's back
        self.assertEqual(self.page.kind_boxes['mod'].text(), 'Mod (2)')
        self.page.show()
        QApplication.processEvents()                                               # the rebuild runs on the next turn of the event loop
        self.assertFalse(self.page.stale)
        self.assertEqual(self.page.graph.kind_counts().get('mod', 0), 0)
        self.assertEqual(self.page.kind_boxes['mod'].text(), 'Mod (0)')
        self.manager.set_enabled(self.manager.list()[0].source.id, True)
        self.service.changed.emit()                                                # visible: follows at once
        self.service.changed.emit()                                                # a burst of changes costs one rebuild
        with patch.object(self.page, 'rebuild', wraps=self.page.rebuild) as rebuild:
            QApplication.processEvents()
        self.assertEqual(rebuild.call_count, 1)
        self.assertEqual(self.page.kind_boxes['mod'].text(), 'Mod (2)')

    # ---- drawing ----------------------------------------------------------------------------------------------------

    def test_the_canvas_actually_draws_and_survives_extremes(self):
        image = self.canvas.grab().toImage()
        colours = {image.pixel(x, y) for x in range(0, image.width(), 9) for y in range(0, image.height(), 9)}
        self.assertGreater(len(colours), 6)                                              # background plus coloured nodes, edges and labels
        for size in ((200, 200), (2000, 1400), (50, 50)):
            self.canvas.resize(*size)
            self.canvas.fit()
            self.assertFalse(self.canvas.grab().isNull())
        empty = GraphCanvas()
        empty.resize(300, 300)
        self.assertFalse(empty.grab().isNull())                                          # nothing to draw: a message, not a crash

    def test_a_large_graph_still_paints_quickly(self):
        g = Graph()
        for i in range(2000):
            g.add_node(Node('n%d' % i, ('mod', 'doc', 'module', 'feature')[i % 4], 'Node %d' % i))
        for i in range(2000):
            g.add_edge('n%d' % i, 'n%d' % ((i * 7 + 3) % 2000), 'links to')
        canvas = GraphCanvas()
        canvas.resize(1000, 700)
        canvas.set_view(g, g.view())
        canvas.settle_now(40, 2.0)
        started = time.monotonic()
        canvas.grab()
        self.assertLess(time.monotonic() - started, 2.5)


if __name__ == '__main__':
    unittest.main()
