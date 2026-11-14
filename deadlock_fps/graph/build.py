"""Derive the knowledge graph from real sources only.

* The repository catalogues and the installed-mod records give Repositories, Mods, Versions, Authors, Game versions,
  and the depends-on / conflicts-with relations the publishers declared.
* The project vault gives Features, Decisions, Tasks and Documentation, joined by the links and frontmatter the notes
  really contain, and Modules: the source files those notes name, but only when the file exists.

A relation whose other end is unknown becomes a visibly marked placeholder (never a silent drop, never an invention).
"""
import posixpath
from pathlib import Path

from ..installer.updates import STORE_PREFIX
from ..vault import read_vault
from .model import Graph, Node

# Window addresses (shell/registry.py) a node opens.
PAGE_REPOSITORIES, PAGE_HUB, PAGE_INSTALLED = 'settings.sources', 'mods.browse', 'mods.installed'
NOTE_KINDS = {'feature': 'feature', 'decision': 'decision', 'task': 'task'}


def build_vault(graph, vault_dir, root=None):
    notes = {t: n for t, n in read_vault(vault_dir).items() if n.type != 'raw'}        # raw transcripts are source material, not knowledge
    root = Path(root) if root else None
    for note in notes.values():
        kind = NOTE_KINDS.get(note.type, 'doc')
        lines = tuple(x for x in ('Type: %s' % note.type if note.type else '', 'Status: %s' % note.status if note.status else '', 'Updated: %s' % note.meta.get('updated', '') if note.meta.get('updated') else '') if x)
        graph.add_node(Node('note:' + note.title, kind, note.title, status=note.status, lines=lines, nav=('note', note.title)))
    linked = set()

    def link(a, b, kind):
        if graph.add_edge(a, b, kind):
            linked.add(frozenset((a, b)))
    for note in notes.values():
        me = 'note:' + note.title
        if note.type == 'feature' and root is not None:
            for path in note.listed('code'):
                if not path.endswith('.py') or not (root / path).is_file():
                    continue                                     # planned or moved files are not modules (yet)
                package = posixpath.dirname(path)
                pkg_id = 'code:' + package + '/'
                graph.add_node(Node(pkg_id, 'module', package + '/', lines=('Package', package), nav=('file', package)))
                mod_id = 'code:' + path
                graph.add_node(Node(mod_id, 'module', posixpath.basename(path), group=pkg_id, lines=('Source file', path), nav=('file', path)))
                graph.add_edge(pkg_id, mod_id, 'contains')
                graph.add_edge(mod_id, me, 'contains')
        for target in note.listed('affects'):
            if target in notes:
                link(me, 'note:' + target, 'affects')
        for target in note.listed('implements'):
            if target in notes:
                link('note:' + target, me, 'implemented by')
    for note in notes.values():
        me = 'note:' + note.title
        for target, _anchor in note.links:
            if target not in notes or target == note.title:
                continue
            other = 'note:' + target
            if frozenset((me, other)) in linked:
                continue
            if graph.nodes[me].kind == 'doc' and graph.nodes[other].kind == 'feature':
                link(me, other, 'describes')
            else:
                link(me, other, 'links to')
    return graph


def build_catalogue(graph, manager, installed=(), limit=400):
    installed = {m.key: m for m in installed}
    views = [v for v in manager.list() if v.source.enabled and v.state.status in ('ok', 'error')]
    entries = []
    for view in views:
        index = manager.index(view.source.id)
        if index is None:
            continue
        graph.add_node(Node('repo:' + view.source.id, 'repository', view.name, nav=('page', PAGE_REPOSITORIES), lines=(
            'Trust: %s' % view.trust.value, 'Compatibility: %s' % view.compat.value, view.source.url or 'Imported from a file', '%d mods' % len(index.mods))))
        for mod in index.mods:
            entries.append((view, mod))
    entries.sort(key=lambda e: ((e[0].source.id, e[1].id) not in installed, e[0].name.lower(), e[1].name.lower()))
    shown = entries[:limit]
    if len(entries) > limit:
        graph.notes.append('Showing %d of %d mods (installed mods first). Use the Mod Hub to browse the rest.' % (limit, len(entries)))
    by_id = {}
    for view, mod in shown:
        repo = 'repo:' + view.source.id
        mid = 'mod:%s|%s' % (view.source.id, mod.id)
        have = installed.get((view.source.id, mod.id))
        latest = mod.latest() or (mod.versions[0] if mod.versions else None)
        lines = ['Repository: ' + view.name, 'Author: ' + (mod.author or 'unknown'), 'Latest: ' + (latest.version.text if latest else '—')]
        if have:
            lines.append('Installed: %s%s' % (have.version, '' if have.enabled else ' (disabled)'))
        if mod.categories:
            lines.append('Categories: ' + ', '.join(mod.categories))
        graph.add_node(Node(mid, 'mod', mod.name, group=repo, lines=tuple(lines), nav=('mod', view.source.id, mod.id), installed=bool(have)))
        graph.add_edge(repo, mid, 'publishes')
        by_id.setdefault(mod.id, []).append((view.source.id, mid))
        if mod.author:
            author = 'author:' + mod.author.lower()
            graph.add_node(Node(author, 'author', mod.author, lines=('Author',)))
            graph.add_edge(mid, author, 'by')
        for v in mod.versions:
            vid = 'ver:%s|%s|%s' % (view.source.id, mod.id, v.version.text)
            flag = ' (installed)' if have and have.version == v.version.text else ''
            graph.add_node(Node(vid, 'version', v.version.text, group=mid, status='' if not v.yanked else 'WITHDRAWN', installed=bool(flag),
                                lines=('%s %s%s' % (mod.name, v.version.text, flag), 'Published: ' + (v.published[:10] or '—'), 'Download: %s' % (('%d bytes' % v.package.size) if v.package and v.package.size else 'unknown size')),
                                nav=('mod', view.source.id, mod.id)))
            graph.add_edge(mid, vid, 'has version')
            for build in sorted({b for b in (v.game.tested_build, v.game.max_build, v.game.min_build) if b is not None}):
                gid = 'game:%d' % build
                graph.add_node(Node(gid, 'game', 'Build %d' % build, lines=('Deadlock Steam build %d' % build,)))
                graph.add_edge(vid, gid, 'supports')
    for key, have in installed.items():                              # installed, but no longer in any enabled catalogue
        mid = 'mod:%s|%s' % key
        if mid not in graph.nodes and key[0].startswith(STORE_PREFIX):     # from the Mod Store: it never had a repository catalogue
            graph.add_node(Node(mid, 'mod', have.name, installed=True, status='MOD STORE', nav=('page', PAGE_INSTALLED),
                                lines=('Installed: ' + have.version, 'Installed from the Mod Store (GameBanana).')))
            by_id.setdefault(key[1], []).append((key[0], mid))
        elif mid not in graph.nodes:
            graph.add_node(Node(mid, 'mod', have.name, installed=True, status='SOURCE GONE', nav=('page', PAGE_INSTALLED),
                                lines=('Installed: ' + have.version, 'Its repository is disabled, removed or no longer lists this mod.')))
            by_id.setdefault(key[1], []).append((key[0], mid))
    for view, mod in shown:
        latest = mod.latest() or (mod.versions[0] if mod.versions else None)
        if latest is None:
            continue
        me = 'mod:%s|%s' % (view.source.id, mod.id)
        for relation, kind in [(r, 'depends on') for r in latest.dependencies] + [(r, 'conflicts with') for r in latest.conflicts]:
            candidates = by_id.get(relation.id, [])
            target = next((m for repo, m in candidates if repo == view.source.id), None) or (candidates[0][1] if candidates else None)
            if target is None:
                target = 'mod:?|' + relation.id
                graph.add_node(Node(target, 'mod', relation.id, status='NOT IN ANY CATALOGUE', lines=('Referenced by %s but not listed by any enabled repository.' % mod.name,)))
            graph.add_edge(me, target, kind)
    return graph


def default_collapsed(graph):
    """Mods hide their versions and code packages hide their files until the user expands them."""
    kids = graph.children()
    return {g for g in kids if graph.nodes[g].kind == 'module' or (graph.nodes[g].kind == 'mod' and any(graph.nodes[c].kind == 'version' for c in kids[g]))}


def build_graph(vault_dir=None, root=None, manager=None, installed=(), limit=400):
    graph = Graph()
    if vault_dir and Path(vault_dir).is_dir():
        build_vault(graph, vault_dir, root)
    else:
        graph.notes.append('The project notes were not found, so only repositories and mods are shown.')
    if manager is not None:
        build_catalogue(graph, manager, installed, limit)
    return graph
