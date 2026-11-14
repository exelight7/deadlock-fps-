"""Project map: an interactive map of sources, mods and the project itself, drawn from real data (reached from Settings › Advanced).

The canvas is plain QPainter (no dependency). It supports panning, zooming, selection with relationship highlighting,
focus mode, expandable groups, search and filters. Everything also exists as text in the side panel (details and a
list of neighbours) so the graph is never the only way to read a relationship.
"""
import math
from pathlib import Path
from urllib.parse import quote

from PySide6.QtCore import Qt, QPointF, QRectF, QTimer, Signal, QUrl
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QPolygonF
from PySide6.QtWidgets import (QFrame, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QCheckBox, QListWidget, QListWidgetItem, QSplitter, QLabel, QSizePolicy, QGridLayout)
from PySide6.QtGui import QDesktopServices

from ..graph import build_graph, Layout, KINDS
from ..graph.build import default_collapsed
from ..graph.model import EDGE_KINDS
from ..i18n import tr
from ..installer import InstallError
from ..shell import theme
from ..shell.components import Banner, Button, Card, Chip, EmptyState, SearchField, Switch, mark, text_label


def text(value, component='CardText'):
    return text_label(value, component)


def C(token):
    """A colour from the current theme."""
    return QColor(theme.color(token))

ROOT = Path(__file__).resolve().parent.parent.parent
# source: accent, installed mod: success, author: warning, the rest muted or secondary (tokens, so both looks stay readable)
KIND_COLORS = {
    'repository': 'color.accent.text', 'mod': 'color.success.text', 'version': 'color.text.muted', 'author': 'color.warning.text', 'game': 'color.info.text',
    'feature': 'color.accent.fill', 'task': 'color.warning.text', 'decision': 'color.text.secondary', 'doc': 'color.info.text', 'module': 'color.text.secondary',
}


def kind_color(kind):
    return C(KIND_COLORS.get(kind, 'color.text.primary'))
KIND_NAMES = {
    'repository': lambda: tr('Source'), 'mod': lambda: tr('Mod'), 'version': lambda: tr('Version'), 'author': lambda: tr('Author'), 'game': lambda: tr('Game version'),
    'feature': lambda: tr('Feature'), 'task': lambda: tr('Task'), 'decision': lambda: tr('Decision'), 'doc': lambda: tr('Documentation'), 'module': lambda: tr('Module'),
}
BASE_RADIUS = {'repository': 12, 'mod': 8, 'version': 5, 'author': 6, 'game': 7, 'feature': 9, 'task': 6, 'decision': 8, 'doc': 7, 'module': 6}
DIRECTED = {'depends on', 'conflicts with', 'publishes', 'has version', 'implemented by', 'affects', 'describes'}
MAX_LABELS = 220
PAGE_SLOT_GRAPH = 'graph'


class GraphCanvas(QWidget):
    selected = Signal(str)
    activated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.graph = None
        self.view = None
        self.positions = {}
        self.layout = None
        self.zoom = 1.0
        self.pan = QPointF(0, 0)
        self.selected_id = None
        self.hover_id = None
        self.matches = set()
        self.related = set()
        self._descendants = {}
        self._drag = None
        self._moved = False
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._tick)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(360, 420)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAccessibleName(tr('Knowledge graph'))
        self.setAccessibleDescription(tr('Use the arrow keys to move, plus and minus to zoom, Tab to step through nodes, Enter to expand a group.'))

    # ---- data -------------------------------------------------------------------

    def set_view(self, graph, view, refit=False):
        self.graph, self.view = graph, view
        ids = [n.id for n in view.nodes]
        previous = {n: p for n, p in self.positions.items() if n in set(ids)}
        for node in view.nodes:                       # a node that just appeared (an expanded group) starts beside its parent
            if node.id not in previous:
                parent = next((a for a in graph.ancestors(node.id) if a in self.positions), None)
                if parent:
                    j = (hash(node.id) % 360) * math.pi / 180
                    previous[node.id] = (self.positions[parent][0] + math.cos(j) * 40, self.positions[parent][1] + math.sin(j) * 40)
        self.layout = Layout(ids, view.edges, previous=previous)
        if previous and len(previous) == len(ids):
            self.layout.temperature = 0                         # nothing appeared: keep every node where the user last saw it
        elif previous:
            self.layout.temperature = self.layout.k / 2          # an expanded group: settle gently around what is already placed
        self.positions = self.layout.positions
        kids = graph.children()
        self._descendants = {}
        for group in kids:
            stack, total = list(kids[group]), 0
            while stack:
                current = stack.pop()
                total += 1
                stack.extend(kids.get(current, ()))
            self._descendants[group] = total
        self._relate()
        if refit or not previous:
            self.fit()
        self.timer.start()
        self.update()

    def _tick(self):
        if self.layout is None or self.layout.cooled:
            self.timer.stop()
            return
        for _ in range(3):
            self.layout.step()
        self.positions = self.layout.positions
        self.update()

    def settle_now(self, iterations=300, seconds=3.0):
        """Run the layout to rest immediately (tests, and when the page first opens)."""
        if self.layout is not None:
            self.positions = self.layout.settle(iterations, seconds)
            self.fit()
            self.update()

    def _relate(self):
        self.related = set()
        if self.selected_id and self.view:
            for a, b, _, _ in self.view.edges:
                if a == self.selected_id:
                    self.related.add(b)
                elif b == self.selected_id:
                    self.related.add(a)

    # ---- geometry ------------------------------------------------------------------

    def to_screen(self, x, y):
        return QPointF(x * self.zoom + self.width() / 2 + self.pan.x(), y * self.zoom + self.height() / 2 + self.pan.y())

    def to_world(self, point):
        return ((point.x() - self.width() / 2 - self.pan.x()) / self.zoom, (point.y() - self.height() / 2 - self.pan.y()) / self.zoom)

    def fit(self):
        pts = list(self.positions.values())
        if not pts:
            self.zoom, self.pan = 1.0, QPointF(0, 0)
            return
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        w, h = max(1.0, max(xs) - min(xs)), max(1.0, max(ys) - min(ys))
        self.zoom = max(0.08, min(2.0, min((self.width() - 80) / w, (self.height() - 80) / h)))
        cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        self.pan = QPointF(-cx * self.zoom, -cy * self.zoom)

    def center_on(self, node_id):
        if node_id in self.positions:
            x, y = self.positions[node_id]
            self.pan = QPointF(-x * self.zoom, -y * self.zoom)
            self.update()

    def zoom_by(self, factor, anchor=None):
        anchor = anchor or QPointF(self.width() / 2, self.height() / 2)
        before = self.to_world(anchor)
        self.zoom = max(0.08, min(6.0, self.zoom * factor))
        after = self.to_screen(*before)
        self.pan += anchor - after
        self.update()

    def radius(self, node):
        bonus = min(7.0, math.sqrt(self._descendants.get(node.id, 0)) * 1.3)
        return (BASE_RADIUS.get(node.kind, 6) + bonus) * min(1.6, max(0.7, self.zoom ** 0.35))

    def node_at(self, point):
        best, best_d = None, 1e9
        for node in (self.view.nodes if self.view else []):
            p = self.positions.get(node.id)
            if p is None:
                continue
            s = self.to_screen(*p)
            d = math.hypot(s.x() - point.x(), s.y() - point.y())
            if d <= self.radius(node) + 5 and d < best_d:
                best, best_d = node.id, d
        return best

    # ---- painting ----------------------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), C('color.bg.sunken'))
        if not self.view or not self.view.nodes:
            painter.setPen(C('color.text.muted'))
            painter.drawText(self.rect(), Qt.AlignCenter, tr('Nothing to draw yet. Add a source, or check that the project notes are present.'))
            return
        focus = self.selected_id
        dim = focus is not None
        screen = {n.id: self.to_screen(*self.positions[n.id]) for n in self.view.nodes if n.id in self.positions}
        arrows = self.zoom > 0.5 and len(self.view.edges) < 2500
        for a, b, kind, count in self.view.edges:
            if a not in screen or b not in screen:
                continue
            hot = focus in (a, b)
            color = C('color.accent.text' if hot else 'color.border.control')
            color.setAlpha(230 if hot else (40 if dim else 120))
            pen = QPen(color, 1.8 if hot else 1.0)
            if kind == 'conflicts with':
                pen.setStyle(Qt.DashLine)
                color = C('color.danger.text')
                color.setAlpha(230 if hot else (60 if dim else 150))
                pen.setColor(color)
            painter.setPen(pen)
            p, q = screen[a], screen[b]
            painter.drawLine(p, q)
            if arrows and kind in DIRECTED:
                self._arrow(painter, p, q, color)
        labelled = 0
        order = sorted(self.view.nodes, key=lambda n: (n.id != focus, n.id not in self.related, n.id not in self.matches, -BASE_RADIUS.get(n.kind, 6)))
        for node in reversed(order):
            if node.id not in screen:
                continue
            p, r = screen[node.id], self.radius(node)
            related = node.id == focus or node.id in self.related
            faded = dim and not related
            base = kind_color(node.kind)
            base.setAlpha(70 if faded else 255)
            painter.setBrush(QBrush(base))
            ring = QPen(C('color.accent.text') if node.id == focus else C('color.bg.sunken'), 2.2 if node.id == focus else 1.0)
            if node.installed:
                ring = QPen(C('color.success.text'), 2.6)
            elif node.status == 'PROPOSED':
                ring = QPen(C('color.text.secondary'), 1.4, Qt.DashLine)
            elif node.status in ('IN PROGRESS', 'SOURCE GONE', 'NOT IN ANY CATALOGUE', 'WITHDRAWN'):
                ring = QPen(C('color.warning.text'), 2.0)
            painter.setPen(ring)
            painter.drawEllipse(p, r, r)
            if node.id in self.matches:
                halo = QPen(C('color.accent.text'), 1.6)
                painter.setPen(halo)
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(p, r + 5, r + 5)
            folded = self._descendants.get(node.id, 0) if node.id in self._collapsed_ids() else 0
            if folded:
                painter.setPen(C('color.text.on-accent'))
                painter.setFont(QFont(painter.font().family(), 7, QFont.Bold))
                painter.drawText(QRectF(p.x() - r, p.y() - r, 2 * r, 2 * r), Qt.AlignCenter, '+%d' % min(folded, 99))
            want = related or node.id in self.matches or node.id == self.hover_id or self.zoom >= 0.9 or node.kind == 'repository'
            if want and not faded and labelled < MAX_LABELS:
                labelled += 1
                font = QFont(painter.font().family(), 8)
                painter.setFont(font)
                painter.setPen(C('color.text.primary' if related or node.id in self.matches else 'color.text.secondary'))
                painter.drawText(QPointF(p.x() + r + 4, p.y() + 4), node.label[:34])

    def _collapsed_ids(self):
        return getattr(self, 'collapsed', set())

    @staticmethod
    def _arrow(painter, p, q, color):
        dx, dy = q.x() - p.x(), q.y() - p.y()
        d = math.hypot(dx, dy)
        if d < 24:
            return
        ux, uy = dx / d, dy / d
        tip = QPointF(q.x() - ux * 11, q.y() - uy * 11)
        left = QPointF(tip.x() - ux * 7 - uy * 3.5, tip.y() - uy * 7 + ux * 3.5)
        right = QPointF(tip.x() - ux * 7 + uy * 3.5, tip.y() - uy * 7 - ux * 3.5)
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(QPolygonF([tip, left, right]))

    # ---- interaction -------------------------------------------------------------------------

    def wheelEvent(self, event):
        self.zoom_by(1.15 if event.angleDelta().y() > 0 else 1 / 1.15, event.position())

    def mousePressEvent(self, event):
        self.setFocus()
        if event.button() == Qt.LeftButton:
            self._drag = event.position()
            self._moved = False

    def mouseMoveEvent(self, event):
        if self._drag is not None and event.buttons() & Qt.LeftButton:
            delta = event.position() - self._drag
            if delta.manhattanLength() > 3 or self._moved:
                self._moved = True
                self.pan += delta
                self._drag = event.position()
                self.update()
            return
        hover = self.node_at(event.position())
        if hover != self.hover_id:
            self.hover_id = hover
            node = self.graph.nodes[hover] if hover else None
            self.setToolTip('%s\n%s%s' % (node.label, KIND_NAMES[node.kind](), ('  ·  ' + node.status) if node.status else '') if node else '')
            self.setCursor(Qt.PointingHandCursor if hover else Qt.ArrowCursor)
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and not self._moved:
            self.select(self.node_at(event.position()))
        self._drag = None

    def mouseDoubleClickEvent(self, event):
        hit = self.node_at(event.position())
        if hit:
            self.select(hit)
            self.activated.emit(hit)

    def select(self, node_id):
        if node_id != self.selected_id:
            self.selected_id = node_id
            self._relate()
            self.selected.emit(node_id or '')
            self.update()

    def step_selection(self, delta):
        nodes = sorted(self.view.nodes if self.view else [], key=lambda n: (n.kind, n.label.lower()))
        if not nodes:
            return
        ids = [n.id for n in nodes]
        at = ids.index(self.selected_id) if self.selected_id in ids else -1
        self.select(ids[(at + delta) % len(ids)])
        self.center_on(self.selected_id)

    def keyPressEvent(self, event):
        key = event.key()
        step = 40
        if key in (Qt.Key_Plus, Qt.Key_Equal):
            self.zoom_by(1.2)
        elif key == Qt.Key_Minus:
            self.zoom_by(1 / 1.2)
        elif key == Qt.Key_Left:
            self.pan += QPointF(step, 0)
        elif key == Qt.Key_Right:
            self.pan -= QPointF(step, 0)
        elif key == Qt.Key_Up:
            self.pan += QPointF(0, step)
        elif key == Qt.Key_Down:
            self.pan -= QPointF(0, step)
        elif key == Qt.Key_F:
            self.fit()
        elif key == Qt.Key_Escape:
            self.select(None)
        elif key in (Qt.Key_Return, Qt.Key_Enter) and self.selected_id:
            self.activated.emit(self.selected_id)
        elif key == Qt.Key_Tab:
            self.step_selection(1)
        elif key == Qt.Key_Backtab:
            self.step_selection(-1)
        else:
            super().keyPressEvent(event)
            return
        self.update()

    def focusNextPrevChild(self, forward):
        if self.view and self.view.nodes:
            return False              # Tab steps through nodes while the canvas has focus; click elsewhere to leave
        return super().focusNextPrevChild(forward)


class GraphPage(QWidget):
    def __init__(self, window, service, vault_dir=None):
        super().__init__(window)
        mark(self, 'GraphPage')
        self.window = window
        self.service = service
        self.vault_dir = Path(vault_dir) if vault_dir else ROOT / 'vault'
        self.graph = None
        self.collapsed = set()
        self.hidden_kinds = set()
        self.focus_mode = False
        self.stale = True
        self._building = True
        t = theme.current()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(t.px('space.3'))
        outer.addWidget(self._toolbar())
        outer.addWidget(self._body(), 1)
        self.notes = text('', 'Muted')
        outer.addWidget(self.notes)
        service.changed.connect(self.mark_stale)
        self._building = False
        self._rebuild_pending = False

    def showEvent(self, event):
        super().showEvent(event)
        self._schedule_rebuild()

    def mark_stale(self, *_):
        self.stale = True
        self._schedule_rebuild()

    def _schedule_rebuild(self):
        # Several changes in a row (or a change while the page is being shown) cost one rebuild, not one each.
        if self.stale and self.isVisible() and not self._rebuild_pending:
            self._rebuild_pending = True
            QTimer.singleShot(0, self._rebuild_if_stale)

    def _rebuild_if_stale(self):
        self._rebuild_pending = False
        if self.stale and self.isVisible():
            self.rebuild()

    # ---- construction ---------------------------------------------------------------------

    def _toolbar(self):
        t = theme.current()
        widget = QWidget()
        c = QVBoxLayout(widget)
        c.setContentsMargins(0, 0, 0, 0)
        c.setSpacing(t.px('space.2'))
        row = QHBoxLayout()
        row.setSpacing(t.px('space.3'))
        self.query_field = SearchField(tr('Find a node by name or detail'))
        self.query = self.query_field.edit
        self.query.setAccessibleName(tr('Search the graph'))
        self.query.textChanged.connect(self.search)
        self.query.returnPressed.connect(self.next_match)
        row.addWidget(self.query_field, 1)
        self.fit_button = Button(tr('Fit'), 'secondary', icon='search')
        self.fit_button.clicked.connect(lambda: (self.canvas.fit(), self.canvas.update()))
        row.addWidget(self.fit_button)
        self.rebuild_button = Button(tr('Rebuild'), 'ghost', icon='refresh')
        self.rebuild_button.clicked.connect(self.rebuild)
        row.addWidget(self.rebuild_button)
        c.addLayout(row)
        row = QHBoxLayout()
        row.setSpacing(t.px('space.4'))
        self.focus_check = Switch(tr('Focus mode'))
        self.focus_check.setToolTip(tr('Show only the selected node and what it is directly connected to'))
        self.focus_check.toggled.connect(self.set_focus)
        self.links_check = Switch(tr('Show note links'))
        self.links_check.setToolTip(tr('Plain links between notes (dense). Typed relations are always shown.'))
        self.links_check.toggled.connect(self.refresh)
        self.expand_button = Button(tr('Expand all'), 'ghost', 'sm')
        self.expand_button.clicked.connect(self.expand_all)
        self.collapse_button = Button(tr('Collapse all'), 'ghost', 'sm')
        self.collapse_button.clicked.connect(self.collapse_all)
        for w in (self.focus_check, self.links_check, self.expand_button, self.collapse_button):
            row.addWidget(w)
        row.addStretch(1)
        c.addLayout(row)
        self.chips = QGridLayout()
        self.chips.setHorizontalSpacing(t.px('space.2'))
        self.chips.setVerticalSpacing(t.px('space.2'))
        self.kind_boxes = {}
        for position, kind in enumerate(KINDS):
            box = Chip(KIND_NAMES[kind]())
            box.setChecked(True)
            box.toggled.connect(lambda on, k=kind: self.toggle_kind(k, on))
            self.kind_boxes[kind] = box
            self.chips.addWidget(box, position // 5, position % 5)
        c.addLayout(self.chips)
        return widget

    def _body(self):
        t = theme.current()
        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)
        self.canvas = GraphCanvas()
        self.canvas.selected.connect(self.show_node)
        self.canvas.activated.connect(self.toggle_group)
        self.canvas.setMinimumHeight(320)
        split.addWidget(self.canvas)
        side = Card(tr('Details'))
        c = side.body
        self.d_title = text(tr('Select a node to see what it is and what it connects to.'), 'RowTitle')
        self.d_kind = text('', 'Muted')
        self.d_lines = text('')
        for w in (self.d_title, self.d_kind, self.d_lines):
            c.addWidget(w)
        c.addWidget(text(tr('Connections'), 'Muted'))
        self.neighbors = QListWidget()
        self.neighbors.setAccessibleName(tr('Connections of the selected node'))
        self.neighbors.itemActivated.connect(self.jump)
        self.neighbors.itemClicked.connect(self.jump)
        self.neighbors.setFrameShape(QFrame.NoFrame)
        c.addWidget(self.neighbors, 1)
        grid = QGridLayout()
        grid.setSpacing(t.px('space.2'))
        self.group_button = Button(tr('Expand'), 'secondary', 'sm')
        self.group_button.clicked.connect(self.toggle_selected_group)
        self.app_button = Button(tr('Open in app'), 'primary', 'sm')
        self.app_button.clicked.connect(self.open_in_app)
        self.note_button = Button(tr('Open note'), 'secondary', 'sm', icon='ext')
        self.note_button.clicked.connect(self.open_note)
        self.file_button = Button(tr('Open file'), 'secondary', 'sm', icon='folder')
        self.file_button.clicked.connect(self.open_file)
        for position, b in enumerate((self.app_button, self.group_button, self.note_button, self.file_button)):
            grid.addWidget(b, position // 2, position % 2)
        c.addLayout(grid)
        split.addWidget(side)
        side.setMinimumWidth(290)
        side.setMaximumWidth(380)
        split.setStretchFactor(0, 4)
        split.setStretchFactor(1, 1)
        return split

    # ---- data ------------------------------------------------------------------------------------

    def rebuild(self, *_):
        installed = []
        try:
            installed = self.service.installer().installed()
        except InstallError:
            pass
        self.graph = build_graph(self.vault_dir, ROOT, self.service.manager, installed)
        self.collapsed = default_collapsed(self.graph)
        self.canvas.collapsed = self.collapsed
        counts = self.graph.kind_counts()
        for kind, box in self.kind_boxes.items():
            box.setText('%s (%d)' % (KIND_NAMES[kind](), counts.get(kind, 0)))
            box.setEnabled(counts.get(kind, 0) > 0)
        self.notes.setText(' '.join(self.graph.notes))
        self.stale = False
        self.canvas.select(None)
        self.canvas.positions = {}
        self.refresh(refit=True)
        self.canvas.settle_now(250, 1.0)    # at most a second on the interface thread

    def refresh(self, *_, refit=False):
        if self.graph is None or self._building:
            return
        hidden_edges = set() if self.links_check.isChecked() else {'links to'}
        focus = self.canvas.selected_id if self.focus_mode else None
        view = self.graph.view(collapsed=self.collapsed, hidden_kinds=self.hidden_kinds, hidden_edges=hidden_edges, focus=focus)
        self.canvas.collapsed = self.collapsed
        self.canvas.set_view(self.graph, view, refit=refit)
        self.search()

    def toggle_kind(self, kind, on):
        (self.hidden_kinds.discard if on else self.hidden_kinds.add)(kind)
        self.refresh()

    def set_focus(self, on):
        self.focus_mode = on
        self.refresh(refit=True)

    def expand_all(self):
        self.collapsed.clear()
        self.refresh(refit=True)

    def collapse_all(self):
        self.collapsed.update(self.graph.groups() if self.graph else ())
        self.refresh(refit=True)

    def toggle_group(self, node_id):
        if self.graph and node_id in self.graph.groups():
            (self.collapsed.discard if node_id in self.collapsed else self.collapsed.add)(node_id)
            self.refresh()
            self.show_node(node_id)

    def toggle_selected_group(self):
        if self.canvas.selected_id:
            self.toggle_group(self.canvas.selected_id)

    # ---- search ---------------------------------------------------------------------------------------

    def search(self, *_):
        if self.graph is None:
            return
        hits = self.graph.search(self.query.text())
        shown = {n.id for n in self.canvas.view.nodes} if self.canvas.view else set()
        # A match inside a collapsed group is shown on the group that holds it, so the user can still find it.
        self.canvas.matches = {self.graph.representative(h, self.collapsed, self.hidden_kinds) or h for h in hits} & shown
        self._match_order = [m for m in dict.fromkeys(self.graph.representative(h, self.collapsed, self.hidden_kinds) or h for h in hits) if m in shown]
        self._match_at = -1
        if self.query.text().strip():
            self.notes.setText(tr('{0} matches').format(len(self._match_order)) + ((' · ' + ' '.join(self.graph.notes)) if self.graph.notes else ''))
        else:
            self.notes.setText(' '.join(self.graph.notes))
        self.canvas.update()

    def next_match(self):
        if getattr(self, '_match_order', None):
            self._match_at = (self._match_at + 1) % len(self._match_order)
            target = self._match_order[self._match_at]
            self.canvas.select(target)
            self.canvas.center_on(target)

    # ---- details ---------------------------------------------------------------------------------------

    def show_node(self, node_id):
        node = self.graph.nodes.get(node_id) if (self.graph and node_id) else None
        self.neighbors.clear()
        if node is None:
            self.d_title.setText(tr('Select a node to see what it is and what it connects to.'))
            self.d_kind.setText('')
            self.d_lines.setText('')
            for b in (self.group_button, self.app_button, self.note_button, self.file_button):
                b.setEnabled(False)
            if self.focus_mode:
                self.refresh()
            return
        self.d_title.setText(node.label)
        self.d_kind.setText(KIND_NAMES[node.kind]() + (' · ' + node.status if node.status else '') + (' · ' + tr('installed') if node.installed else ''))
        self.d_lines.setText('\n'.join(node.lines))
        for other, kind, direction in self.graph.neighbors(node.id)[:200]:
            target = self.graph.nodes[other]
            arrow = '→' if direction == 'out' else '←'
            item = QListWidgetItem('%s %s  %s' % (arrow, kind, target.label))
            item.setData(Qt.UserRole, other)
            item.setForeground(kind_color(target.kind))
            self.neighbors.addItem(item)
        is_group = node.id in self.graph.groups()
        self.group_button.setEnabled(is_group)
        self.group_button.setText(tr('Expand') if node.id in self.collapsed else tr('Collapse'))
        kind = node.nav[0] if node.nav else ''
        self.app_button.setEnabled(kind in ('page', 'mod'))
        self.note_button.setEnabled(kind == 'note')
        self.file_button.setEnabled(kind == 'file')
        if self.focus_mode:
            self.refresh()

    def jump(self, item):
        target = item.data(Qt.UserRole)
        shown = {n.id for n in self.canvas.view.nodes}
        rep = self.graph.representative(target, self.collapsed, self.hidden_kinds) or target
        if rep not in shown:
            return
        self.canvas.select(rep)
        self.canvas.center_on(rep)

    # ---- navigation ---------------------------------------------------------------------------------------

    def current_node(self):
        return self.graph.nodes.get(self.canvas.selected_id) if (self.graph and self.canvas.selected_id) else None

    def open_in_app(self):
        node = self.current_node()
        if node is None or not node.nav or self.window is None:
            return
        if node.nav[0] == 'page':
            self.window.navigate(node.nav[1])
        elif node.nav[0] == 'mod':
            if hasattr(self.window, 'search_sources'):
                self.window.search_sources(node.label)
            else:
                self.window.navigate('mods.browse')

    def note_path(self, title):
        return next((p for p in self.vault_dir.rglob(title + '.md')), None)

    def open_note(self):
        node = self.current_node()
        if node is None or not node.nav or node.nav[0] != 'note':
            return
        path = self.note_path(node.nav[1])
        if path is None:
            return
        # Obsidian's own URL scheme first; any Markdown editor (via the file) if Obsidian is not installed or the vault is not registered.
        if not QDesktopServices.openUrl(QUrl('obsidian://open?path=' + quote(str(path.resolve()), safe=''))):
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def open_file(self):
        node = self.current_node()
        if node is not None and node.nav and node.nav[0] == 'file':
            QDesktopServices.openUrl(QUrl.fromLocalFile(str((ROOT / node.nav[1]).resolve())))
