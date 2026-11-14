"""Knowledge graph: model operations, builders from real sources, and layout."""
import itertools
import math
import tempfile
import time
import unittest
from pathlib import Path

from deadlock_fps.graph import Graph, Node, Layout, build_graph, build_vault, build_catalogue
from deadlock_fps.graph.build import default_collapsed
from deadlock_fps.installer.records import InstalledMod, InstalledFile
from deadlock_fps.repos import RepositoryManager, RepositoryStore, TrustRegistry
from deadlock_fps.vault import read_vault, frontmatter, links_in
from repo_fixtures import FakeTransport, ok, index, mod as mod_doc, version as version_doc

ROOT = Path(__file__).resolve().parents[1]


def tiny():
    g = Graph()
    for nid, kind, group in (('r', 'repository', ''), ('m1', 'mod', 'r'), ('m2', 'mod', 'r'), ('v1', 'version', 'm1'), ('v2', 'version', 'm1'), ('a', 'author', ''), ('g', 'game', '')):
        g.add_node(Node(nid, kind, nid.upper(), group=group))
    for a, b, k in (('r', 'm1', 'publishes'), ('r', 'm2', 'publishes'), ('m1', 'v1', 'has version'), ('m1', 'v2', 'has version'), ('m1', 'a', 'by'), ('m2', 'a', 'by'), ('v1', 'g', 'supports'), ('v2', 'g', 'supports'), ('m2', 'm1', 'depends on')):
        assert g.add_edge(a, b, k)
    return g


class Model(unittest.TestCase):
    def test_nodes_merge_and_bad_edges_are_refused(self):
        g = Graph()
        g.add_node(Node('x', 'mod', 'X'))
        merged = g.add_node(Node('x', 'mod', 'other', group='r', status='S', lines=('l',), installed=True))
        self.assertEqual((merged.label, merged.group, merged.status, merged.lines, merged.installed), ('X', 'r', 'S', ('l',), True))
        g.add_node(Node('y', 'mod', 'Y'))
        self.assertTrue(g.add_edge('x', 'y', 'depends on'))
        self.assertFalse(g.add_edge('x', 'y', 'depends on'))            # duplicate
        self.assertFalse(g.add_edge('x', 'x', 'depends on'))            # self
        self.assertFalse(g.add_edge('x', 'missing', 'depends on'))      # dangling
        self.assertEqual(len(g.edges), 1)

    def test_structure_queries(self):
        g = tiny()
        self.assertEqual(g.ancestors('v1'), ['m1', 'r'])
        self.assertEqual(g.descendant_count('r'), 4)
        self.assertEqual(g.kind_counts()['version'], 2)
        self.assertEqual([(o, k, d) for o, k, d in g.neighbors('m1')], [('a', 'by', 'out'), ('m2', 'depends on', 'in'), ('v1', 'has version', 'out'), ('v2', 'has version', 'out'), ('r', 'publishes', 'in')])      # sorted by relation, then name

    def test_a_cycle_in_groups_cannot_hang_the_graph(self):
        g = Graph()
        g.add_node(Node('a', 'mod', 'A', group='b'))
        g.add_node(Node('b', 'mod', 'B', group='a'))
        self.assertEqual(len(g.ancestors('a')), 1)
        self.assertEqual(len(g.view(collapsed={'a', 'b'}).nodes) <= 2, True)

    def test_collapsing_folds_nodes_and_reroutes_or_drops_edges(self):
        g = tiny()
        full = g.view()
        self.assertEqual((len(full.nodes), full.hidden), (7, 0))
        view = g.view(collapsed={'m1'})
        ids = {n.id for n in view.nodes}
        self.assertEqual(ids, {'r', 'm1', 'm2', 'a', 'g'})
        self.assertEqual(view.hidden, 2)
        edges = {(a, b, k): c for a, b, k, c in view.edges}
        self.assertEqual(edges[('m1', 'g', 'supports')], 2)              # two versions' edges merge, with a count
        self.assertNotIn(('m1', 'v1', 'has version'), edges)             # internal edge vanishes
        nested = g.view(collapsed={'r', 'm1'})
        self.assertEqual({n.id for n in nested.nodes}, {'r', 'a', 'g'})
        self.assertEqual({(a, b, k) for a, b, k, _ in nested.edges}, {('r', 'a', 'by'), ('r', 'g', 'supports')})

    def test_filters_and_focus(self):
        g = tiny()
        self.assertNotIn('a', {n.id for n in g.view(hidden_kinds={'author'}).nodes})
        self.assertFalse(any(k == 'by' for _, _, k, _ in g.view(hidden_kinds={'author'}).edges))
        self.assertFalse(any(k == 'depends on' for _, _, k, _ in g.view(hidden_edges={'depends on'}).edges))
        focused = g.view(focus='m1')
        self.assertEqual({n.id for n in focused.nodes}, {'m1', 'r', 'a', 'v1', 'v2', 'm2'})
        self.assertEqual({n.id for n in g.view(collapsed={'m1'}, focus='v1').nodes}, {'r', 'a', 'g', 'm1', 'm2'})      # a hidden node focuses its group

    def test_search_ranks_exact_then_prefix_then_contains_and_requires_every_word(self):
        g = Graph()
        for nid, label, lines in (('1', 'Crimson Skin', ()), ('2', 'Crimson', ()), ('3', 'The crimson one', ()), ('4', 'Unrelated', ('mentions crimson in detail',))):
            g.add_node(Node(nid, 'mod', label, lines=lines))
        self.assertEqual(g.search('crimson'), ['2', '1', '3', '4'])
        self.assertEqual(g.search('crimson skin'), ['1'])
        self.assertEqual(g.search('  '), [])
        self.assertEqual(g.search('nothing'), [])


class Vaults(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        (self.dir / 'src/pkg').mkdir(parents=True)
        (self.dir / 'src/pkg/real.py').write_text('x = 1')
        (self.dir / 'vault').mkdir()

    def note(self, title, front, body=''):
        (self.dir / 'vault' / (title + '.md')).write_text('---\n' + front + '\n---\n' + body, encoding='utf-8')

    def test_frontmatter_and_links_ignore_code_spans(self):
        meta, body = frontmatter('---\ntitle: T\ncode: [a.py, b.py]\n---\nSee [[Real]] and `[[Example]]` and [[Other#Head|alias]].')
        self.assertEqual(meta['code'], ['a.py', 'b.py'])
        self.assertEqual(links_in(body), (('Real', ''), ('Other', 'Head')))

    def test_notes_become_typed_nodes_and_relations_come_from_what_they_say(self):
        self.note('Feat', 'title: F\ntype: feature\nstatus: IMPLEMENTED\ncode: [src/pkg/real.py, src/pkg/planned.py, notes.txt]', 'Uses [[Other Feat]].')
        self.note('Other Feat', 'title: O\ntype: feature\nstatus: PROPOSED')
        self.note('Overview', 'title: D\ntype: architecture', 'Explains [[Feat]] and mentions [[Overview]] and [[Missing]].')
        self.note('ADR', 'title: A\ntype: decision\naffects: [Feat, Nowhere]', 'Also links [[Feat]].')
        self.note('Do it', 'title: T\ntype: task\nstatus: IMPLEMENTED\nimplements: [Feat]')
        g = build_vault(Graph(), self.dir / 'vault', self.dir)
        kinds = {n.label: n.kind for n in g.nodes.values()}
        self.assertEqual({k: v for k, v in kinds.items() if v != 'module'}, {'Feat': 'feature', 'Other Feat': 'feature', 'Overview': 'doc', 'ADR': 'decision', 'Do it': 'task'})
        self.assertEqual(sorted((n.label for n in g.nodes.values() if n.kind == 'module')), ['real.py', 'src/pkg/'])        # planned.py / notes.txt are not modules
        edges = {(g.nodes[e.source].label, g.nodes[e.target].label, e.kind) for e in g.edges}
        self.assertEqual(edges, {('src/pkg/', 'real.py', 'contains'), ('real.py', 'Feat', 'contains'), ('Feat', 'Other Feat', 'links to'), ('Overview', 'Feat', 'describes'),
                                 ('ADR', 'Feat', 'affects'), ('Feat', 'Do it', 'implemented by')})                       # no duplicate for ADR's own link, none to missing notes
        self.assertEqual(g.nodes['note:Feat'].status, 'IMPLEMENTED')
        self.assertEqual(g.nodes['code:src/pkg/real.py'].group, 'code:src/pkg/')
        self.assertEqual(default_collapsed(g), {'code:src/pkg/'})

    def test_raw_source_notes_are_not_drawn_and_do_not_link_anything(self):
        self.note('Real', 'title: R\ntype: feature\nstatus: PROPOSED')
        self.note('Transcript', 'title: T\ntype: raw', 'Mentions [[Real]] and quotes the whole conversation.')
        g = build_vault(Graph(), self.dir / 'vault', self.dir)
        self.assertEqual([n.label for n in g.nodes.values()], ['Real'])
        self.assertEqual(g.edges, [])

    def test_without_a_vault_the_user_is_told(self):
        g = build_graph(vault_dir=self.dir / 'absent', root=self.dir)
        self.assertEqual((len(g.nodes), len(g.notes)), (0, 1))

    def test_the_projects_own_vault_builds_a_complete_consistent_graph(self):
        notes = {t: n for t, n in read_vault(ROOT / 'vault').items() if n.type != 'raw'}          # raw transcripts are not knowledge
        g = build_vault(Graph(), ROOT / 'vault', ROOT)
        self.assertEqual({n.label for n in g.nodes.values() if n.id.startswith('note:')}, set(notes))
        self.assertTrue(all(e.source in g.nodes and e.target in g.nodes for e in g.edges))
        counts = g.kind_counts()
        for kind in ('feature', 'decision', 'doc', 'module'):
            self.assertGreater(counts.get(kind, 0), 0, kind)
        by_label = {n.label: n for n in g.nodes.values()}
        self.assertEqual(by_label['Repository Manager'].kind, 'feature')
        self.assertTrue(any(e.kind == 'contains' and g.nodes[e.target].label == 'Repository Manager' and g.nodes[e.source].label == 'manager.py' for e in g.edges))
        self.assertTrue(any(e.kind == 'affects' and g.nodes[e.source].label.startswith('ADR-003') for e in g.edges))
        for node in g.nodes.values():
            if node.kind == 'module' and node.nav[0] == 'file':
                self.assertTrue((ROOT / node.nav[1]).exists(), node.nav)


class Catalogue(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.transport = FakeTransport()
        self.manager = RepositoryManager(RepositoryStore(Path(self.temp.name)), self.transport, trust=TrustRegistry({}))

    def add(self, url, *mods, name='Repo'):
        self.transport.routes[url] = ok(index(*mods, name=name, ident=name.lower().replace(' ', '-')))
        self.manager.refresh(self.manager.add(url).source.id)

    def test_repositories_mods_versions_authors_builds_and_relations(self):
        crimson = mod_doc('crimson-skin', name='Crimson', author='Mira', versions=[version_doc('1.0.0', game={'min_build': 100, 'tested_build': 150}), version_doc('1.1.0', game={'tested_build': 150, 'max_build': 160},
                                                                                                                                       dependencies=[{'id': 'base-lib', 'range': '*'}, {'id': 'ghost', 'range': '*'}], conflicts=[{'id': 'azure-skin', 'range': '*'}])])
        base = mod_doc('base-lib', name='Base Lib', author='Mira', versions=[version_doc('2.0.0')])
        azure = mod_doc('azure-skin', name='Azure', author='Zed', versions=[version_doc('1.0.0')])
        self.add('https://one.example.org/i.json', crimson, base, name='One')
        self.add('https://two.example.org/i.json', azure, name='Two')
        g = build_catalogue(Graph(), self.manager)
        kinds = g.kind_counts()
        self.assertEqual((kinds['repository'], kinds['mod'] - 1, kinds['author'], kinds['version']), (2, 3, 2, 4))      # one placeholder mod: ghost
        edges = {(g.nodes[e.source].label, g.nodes[e.target].label, e.kind) for e in g.edges}
        for expected in (('One', 'Crimson', 'publishes'), ('Crimson', 'Mira', 'by'), ('Crimson', '1.1.0', 'has version'), ('Crimson', 'Base Lib', 'depends on'),
                         ('Crimson', 'Azure', 'conflicts with'), ('1.1.0', 'Build 160', 'supports'), ('1.0.0', 'Build 100', 'supports'), ('Crimson', 'ghost', 'depends on')):
            self.assertIn(expected, edges)
        self.assertEqual(sum(1 for n in g.nodes.values() if n.kind == 'game'), 3)                 # builds 100, 150, 160, shared by the two versions of crimson
        self.assertEqual(g.nodes['mod:?|ghost'].status, 'NOT IN ANY CATALOGUE')
        self.assertIn('Mira', {n.label for n in g.nodes.values() if n.kind == 'author'})
        self.assertEqual(len([n for n in g.nodes.values() if n.kind == 'author']), 2)             # Mira is one node for both repositories' mods

    def test_installed_mods_are_marked_and_survive_their_repository(self):
        self.add('https://one.example.org/i.json', mod_doc('crimson-skin', versions=[version_doc('1.0.0')]), name='One')
        rid = self.manager.list()[0].source.id
        have = InstalledMod(rid, 'crimson-skin', 'Crimson-Skin', '1.0.0', (InstalledFile('pak01_dir.vpk', 'a' * 64, 1),))
        gone = InstalledMod('https:vanished.example.org/x', 'old-mod', 'Old Mod', '0.5.0', ())
        g = build_catalogue(Graph(), self.manager, [have, gone])
        self.assertTrue(g.nodes['mod:%s|crimson-skin' % rid].installed)
        self.assertTrue(g.nodes['ver:%s|crimson-skin|1.0.0' % rid].installed)
        self.assertEqual(g.nodes['mod:https:vanished.example.org/x|old-mod'].status, 'SOURCE GONE')

    def test_disabled_repositories_are_left_out_and_large_catalogues_are_truncated_honestly(self):
        many = [mod_doc('mod-%03d' % i, versions=[version_doc('1.0.0')]) for i in range(30)]
        self.add('https://big.example.org/i.json', *many, name='Big')
        rid = self.manager.list()[0].source.id
        have = InstalledMod(rid, 'mod-029', 'Mod-029', '1.0.0', ())
        g = build_catalogue(Graph(), self.manager, [have], limit=5)
        mods = [n for n in g.nodes.values() if n.kind == 'mod']
        self.assertEqual(len(mods), 5)
        self.assertIn('mod:%s|mod-029' % rid, g.nodes)                                            # installed mods are always kept
        self.assertTrue(any('Showing 5 of 30 mods' in n for n in g.notes))
        self.manager.set_enabled(rid, False)
        self.assertEqual(len(build_catalogue(Graph(), self.manager).nodes), 0)

    def test_default_collapse_hides_versions_and_modules_but_not_repositories(self):
        self.add('https://one.example.org/i.json', mod_doc('crimson-skin', versions=[version_doc('1.0.0')]), name='One')
        g = build_catalogue(Graph(), self.manager)
        collapsed = default_collapsed(g)
        self.assertEqual({g.nodes[c].kind for c in collapsed}, {'mod'})
        view = g.view(collapsed=collapsed)
        self.assertEqual(sorted(n.kind for n in view.nodes), ['author', 'game', 'game', 'mod', 'repository'])     # shared game builds stay; versions fold into their mod
        self.assertIn('supports', {k for _, _, k, _ in view.edges})                                          # and the mod now carries its versions' 'supports' edges


class Layouts(unittest.TestCase):
    def ring(self, n):
        ids = ['n%d' % i for i in range(n)]
        return ids, [(ids[i], ids[(i + 1) % n], 'x') for i in range(n)]

    def test_small_cases_do_not_crash(self):
        for ids, edges in (([], []), (['a'], []), (['a', 'b'], [('a', 'b', 'x')]), (['a', 'b'], [])):
            positions = Layout(ids, edges).settle()
            self.assertEqual(set(positions), set(ids))
            self.assertTrue(all(math.isfinite(x) and math.isfinite(y) for x, y in positions.values()))

    def test_it_is_deterministic_and_cools_down(self):
        ids, edges = self.ring(30)
        a, b = Layout(ids, edges, seed=3), Layout(ids, edges, seed=3)
        self.assertEqual(a.settle(iterations=400, seconds=30), b.settle(iterations=400, seconds=30))
        self.assertTrue(a.cooled)
        self.assertNotEqual(Layout(ids, edges, seed=4).settle(), a.positions)

    def test_connected_nodes_end_up_closer_than_unconnected_ones_and_nothing_overlaps(self):
        ids, edges = self.ring(40)
        pos = Layout(ids, edges).settle(iterations=500, seconds=30)
        dist = lambda a, b: math.dist(pos[a], pos[b])
        linked = [dist(a, b) for a, b, _ in edges]
        others = [dist(a, b) for a, b in itertools.combinations(ids, 2) if (a, b, 'x') not in edges and (b, a, 'x') not in edges]
        self.assertLess(sum(linked) / len(linked), sum(others) / len(others) / 2)
        self.assertGreater(min(dist(a, b) for a, b in itertools.combinations(ids, 2)), 1.0)

    def test_identical_start_positions_are_separated(self):
        layout = Layout(['a', 'b', 'c'], [], seed=1)
        layout.x, layout.y = [5.0] * 3, [5.0] * 3
        pos = layout.settle(iterations=100, seconds=5)
        self.assertGreater(min(math.dist(pos[a], pos[b]) for a, b in itertools.combinations('abc', 2)), 1.0)

    def test_previous_positions_are_kept_so_expanding_a_group_does_not_scramble_the_view(self):
        ids, edges = self.ring(10)
        first = Layout(ids, edges).settle()
        again = Layout(ids + ['extra'], edges, previous=first)
        self.assertTrue(all(again.positions[n] == first[n] for n in ids))

    def test_a_large_graph_settles_within_its_time_budget(self):
        ids, edges = self.ring(1500)
        started = time.monotonic()
        positions = Layout(ids, edges).settle(iterations=60, seconds=3.0)
        self.assertLess(time.monotonic() - started, 6.0)
        self.assertEqual(len(positions), 1500)


if __name__ == '__main__':
    unittest.main()
