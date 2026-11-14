"""The Obsidian vault must agree with the repository (scripts/check_vault.py)."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import check_vault  # noqa: E402


def note(folder, name, front, body='text'):
    path = Path(folder) / (name + '.md')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('---\n' + front + '\n---\n' + body + '\n', encoding='utf-8')


class Vault(unittest.TestCase):
    def test_the_real_vault_is_consistent(self):
        self.assertEqual(check_vault.check(), [])

    def test_the_real_vault_has_the_notes_the_brief_asks_for(self):
        names = {p.stem for p in (ROOT / 'vault').rglob('*.md')}
        for required in ('Architecture Overview', 'Codebase Structure', 'Repository Specification', 'Mod Lifecycle', 'Security Model', 'Design System',
                         'Dependencies', 'Known Issues', 'Testing', 'Roadmap', 'Implementation Log', 'Technical Debt'):
            self.assertIn(required, names)

    def test_it_catches_overclaiming_and_broken_links(self):
        with tempfile.TemporaryDirectory() as folder:
            base = 'title: T\ntype: feature\nupdated: 2026-11-14\n'
            note(folder, 'A', base + 'status: IMPLEMENTED\ncode: [does/not/exist.py]', 'See [[Missing Note]] and [[B#No Such Heading]] and [[B#Real]] and `[[in code]]`.')
            note(folder, 'B', base + 'status: DONE', '# Real')
            note(folder, 'C', 'title: T\ntype: spec\nupdated: 2026-11-14', 'no status')
            note(folder, 'D', 'title: T\ntype: guide', 'no date')
            problems = '\n'.join(check_vault.check(folder, ROOT))
        for expected in ('does/not/exist.py', 'missing note [[Missing Note]]', '[[B#No Such Heading]] heading not found', "unknown status 'DONE'",
                         'a spec note needs a status', "missing frontmatter field 'updated'"):
            self.assertIn(expected, problems)
        self.assertNotIn('in code', problems)
        self.assertNotIn('[[B#Real]]', problems)

    def test_a_proposed_note_may_list_paths_that_do_not_exist_yet(self):
        with tempfile.TemporaryDirectory() as folder:
            note(folder, 'P', 'title: T\ntype: feature\nupdated: 2026-11-14\nstatus: PROPOSED\ncode: [future/module.py]')
            self.assertEqual(check_vault.check(folder, ROOT), [])


if __name__ == '__main__':
    unittest.main()
