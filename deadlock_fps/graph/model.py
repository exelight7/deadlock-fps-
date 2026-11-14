"""The knowledge graph as data: nodes, typed edges, groups that collapse, filters, focus and search. Qt-free.

The graph is only ever *derived* from real sources (the repository catalogues, the installed-mod records, the project
vault and the code paths it names); nothing is invented to fill space.
"""
from dataclasses import dataclass, field

# kind -> (readable name, colour token from theme.py used by the canvas)
KINDS = {
    'module': 'Module', 'feature': 'Feature', 'task': 'Task', 'decision': 'Decision', 'doc': 'Documentation',
    'repository': 'Repository', 'mod': 'Mod', 'version': 'Version', 'author': 'Author', 'game': 'Game version',
}
EDGE_KINDS = ('publishes', 'has version', 'depends on', 'conflicts with', 'supports', 'by', 'contains', 'implemented by', 'describes', 'affects', 'links to')
STATUSES = ('PROPOSED', 'IN PROGRESS', 'IMPLEMENTED', 'VERIFIED')


@dataclass
class Node:
    id: str
    kind: str
    label: str
    group: str = ''                 # id of the node this one collapses into
    status: str = ''
    lines: tuple = ()               # detail lines for the side panel
    nav: tuple = ()                 # ('page', address) | ('note', title) | ('file', relative path)
    installed: bool = False


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    kind: str


@dataclass
class View:
    nodes: list
    edges: list                     # (source, target, kind, count) between visible nodes
    hidden: int                     # nodes folded into collapsed groups or filtered out


class Graph:
    def __init__(self):
        self.nodes = {}
        self.edges = []
        self._seen = set()
        self.notes = []             # things the user should know, e.g. "showing 400 of 1200 mods"

    # ---- building ---------------------------------------------------------------

    def add_node(self, node):
        known = self.nodes.get(node.id)
        if known is None:
            self.nodes[node.id] = node
            return node
        for name in ('group', 'status', 'nav'):                        # a later source may fill what an earlier one lacked
            if not getattr(known, name) and getattr(node, name):
                setattr(known, name, getattr(node, name))
        known.lines = known.lines or node.lines
        known.installed = known.installed or node.installed
        return known

    def add_edge(self, source, target, kind):
        if source == target or source not in self.nodes or target not in self.nodes:
            return False
        key = (source, target, kind)
        if key in self._seen:
            return False
        self._seen.add(key)
        self.edges.append(Edge(source, target, kind))
        return True

    # ---- structure ----------------------------------------------------------------

    def children(self):
        result = {}
        for node in self.nodes.values():
            if node.group:
                result.setdefault(node.group, []).append(node.id)
        return result

    def groups(self):
        return set(self.children())

    def ancestors(self, node_id):
        chain, seen = [], {node_id}
        group = self.nodes[node_id].group
        while group and group in self.nodes and group not in seen:
            chain.append(group)
            seen.add(group)
            group = self.nodes[group].group
        return chain

    def descendant_count(self, group_id):
        kids = self.children()
        stack, total = list(kids.get(group_id, [])), 0
        while stack:
            current = stack.pop()
            total += 1
            stack.extend(kids.get(current, []))
        return total

    def kind_counts(self):
        counts = {}
        for node in self.nodes.values():
            counts[node.kind] = counts.get(node.kind, 0) + 1
        return counts

    def neighbors(self, node_id):
        """[(other id, edge kind, 'out' | 'in')] over the full graph, sorted for stable display."""
        found = []
        for edge in self.edges:
            if edge.source == node_id:
                found.append((edge.target, edge.kind, 'out'))
            elif edge.target == node_id:
                found.append((edge.source, edge.kind, 'in'))
        return sorted(found, key=lambda n: (n[1], self.nodes[n[0]].label.lower()))

    # ---- views ------------------------------------------------------------------------

    def representative(self, node_id, collapsed, hidden_kinds=frozenset()):
        """The visible node that stands for `node_id`: itself, or the outermost collapsed group above it. None when filtered out."""
        node = self.nodes[node_id]
        if node.kind in hidden_kinds:
            return None
        rep = node_id
        for ancestor in self.ancestors(node_id):
            if ancestor in collapsed:
                rep = ancestor
        if rep != node_id and self.nodes[rep].kind in hidden_kinds:
            return None
        return rep

    def view(self, collapsed=frozenset(), hidden_kinds=frozenset(), hidden_edges=frozenset(), focus=None):
        """What to draw. Edges whose ends fall into the same collapsed group vanish; parallel edges merge with a count."""
        reps = {nid: self.representative(nid, collapsed, hidden_kinds) for nid in self.nodes}
        merged = {}
        for edge in self.edges:
            if edge.kind in hidden_edges:
                continue
            a, b = reps[edge.source], reps[edge.target]
            if a is None or b is None or a == b:
                continue
            merged[(a, b, edge.kind)] = merged.get((a, b, edge.kind), 0) + 1
        visible = {r for r in reps.values() if r is not None}
        if focus is not None:
            center = reps.get(focus) or focus
            near = {center} | {b for (a, b, _), _c in merged.items() if a == center} | {a for (a, b, _), _c in merged.items() if b == center}
            visible &= near
            merged = {k: c for k, c in merged.items() if k[0] in visible and k[1] in visible}
        nodes = [self.nodes[n] for n in sorted(visible, key=lambda n: (self.nodes[n].kind, self.nodes[n].label.lower()))]
        edges = [(a, b, kind, count) for (a, b, kind), count in sorted(merged.items())]
        return View(nodes, edges, len(self.nodes) - len(nodes))

    def search(self, query, limit=50):
        """Node ids whose label or detail lines contain every word of `query`, best matches first."""
        words = [w for w in (query or '').lower().split() if w]
        if not words:
            return []
        scored = []
        for node in self.nodes.values():
            label = node.label.lower()
            hay = label + ' ' + ' '.join(node.lines).lower() + ' ' + node.kind
            if all(w in hay for w in words):
                rank = 0 if label == ' '.join(words) else (1 if label.startswith(words[0]) else (2 if all(w in label for w in words) else 3))
                scored.append((rank, label, node.id))
        return [nid for _, _, nid in sorted(scored)[:limit]]
