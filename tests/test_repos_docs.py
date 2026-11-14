"""The published specification and its examples must stay true to the code."""
import json
import unittest
from pathlib import Path

from deadlock_fps.repos import spec, parse_index
from deadlock_fps.repos.model import GameFit
from deadlock_fps.repos.compat import fit

DOCS = Path(__file__).resolve().parents[1] / 'docs'


class SpecificationExamples(unittest.TestCase):
    def test_the_example_index_is_valid_and_exercises_the_features_it_claims(self):
        result = parse_index((DOCS / 'repository-example' / 'deadlock-repo.json').read_bytes())
        self.assertEqual(result.warnings, ())
        self.assertEqual([m.id for m in result.mods], ['crimson-skin', 'clean-hud'])
        crimson = result.get('crimson-skin')
        self.assertEqual([str(v.version) for v in crimson.versions], ['1.1.0', '1.0.0'])
        self.assertEqual(crimson.versions[1].package.mirrors, ('https://mirror.example.net/crimson-skin-1.0.0.zip',))
        self.assertEqual(crimson.versions[0].conflicts[0].id, 'azure-skin')
        self.assertEqual(fit(crimson.versions[0].game, 120), GameFit.COMPATIBLE)
        self.assertEqual(fit(crimson.versions[1].game, 200), GameFit.INCOMPATIBLE)
        hud = result.get('clean-hud')
        self.assertTrue(hud.versions[0].prerelease)
        self.assertIsNone(hud.latest())                            # only a beta exists, so nothing stable to offer
        self.assertEqual(hud.versions[0].dependencies[0].range, '>=1.0 <2')
        self.assertTrue(all(v.installable for m in result.mods for v in m.versions))

    def test_the_example_repository_list_is_valid(self):
        entries = spec.parse_repository_list((DOCS / 'repository-example' / 'repository-list.json').read_bytes())
        self.assertEqual([e['url'] for e in entries], ['https://github.com/owner/repository', 'https://mods.example.org/'])
        self.assertEqual(entries[1]['provider'], 'https')

    def test_every_json_block_in_the_spec_that_claims_a_schema_parses(self):
        text = (DOCS / 'REPOSITORY_SPEC.md').read_text(encoding='utf-8')
        blocks = [b.split('```', 1)[0] for b in text.split('```json\n')[1:]]
        self.assertGreaterEqual(len(blocks), 3)
        checked = 0
        for block in blocks:
            if '"schema"' in block and '…' not in block:
                document = json.loads(block)
                if document['schema'] == spec.LIST_SCHEMA:
                    spec.parse_repository_list(document)
                    checked += 1
        self.assertEqual(checked, 1)

    def test_numbers_quoted_in_the_spec_match_the_code(self):
        text = (DOCS / 'REPOSITORY_SPEC.md').read_text(encoding='utf-8')
        self.assertIn('**8 MiB** and **5000 mods**; a mod to **200 versions**', text)
        self.assertEqual((spec.MAX_INDEX_BYTES, spec.MAX_MODS, spec.MAX_VERSIONS), (8 * 1024 ** 2, 5000, 200))
        self.assertIn('up to 12 https URLs', text)
        self.assertEqual(spec.MAX_SCREENSHOTS, 12)
        self.assertIn('bytes, 1 – 2 GiB', text)
        self.assertEqual(spec.MAX_PACKAGE_BYTES, 2 * 1024 ** 3)
        self.assertIn('up to 8 alternate', text)
        self.assertIn('exactly `deadlock-mod-repository`', text)
        self.assertEqual(spec.SCHEMA, 'deadlock-mod-repository')
        self.assertEqual(spec.SUPPORTED_MAJOR, 1)


if __name__ == '__main__':
    unittest.main()
