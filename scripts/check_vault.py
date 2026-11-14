"""Check the Obsidian vault against the repository: python scripts/check_vault.py

Fails (exit 1) when
  * a [[wikilink]] points at a note or heading that does not exist,
  * an `affects` or `implements` entry names a note that does not exist,
  * a note's `status` is not one of PROPOSED / IN PROGRESS / IMPLEMENTED / VERIFIED,
  * a note claiming IMPLEMENTED or VERIFIED lists a `code:` or `tests:` path that does not exist,
  * a feature, spec or task note has no status, or a note has no `title`/`type`/`updated`.
The vault is documentation, so the codebase wins: fix the note, not the check.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deadlock_fps.vault import read_vault, headings  # noqa: E402

VAULT = ROOT / 'vault'
STATUSES = {'PROPOSED', 'IN PROGRESS', 'IMPLEMENTED', 'VERIFIED'}
NEEDS_STATUS = {'feature', 'spec', 'task'}
RELATIONS = ('affects', 'implements')


def check(vault=VAULT, root=ROOT):
    problems = []
    notes = read_vault(vault)
    if not notes:
        return ['no notes found in %s' % vault]
    for name, note in notes.items():
        where = note.path.relative_to(vault).as_posix()
        for field in ('title', 'type', 'updated'):
            if not note.meta.get(field):
                problems.append('%s: missing frontmatter field %r' % (where, field))
        if note.type in NEEDS_STATUS and not note.status:
            problems.append('%s: a %s note needs a status' % (where, note.type))
        if note.status and note.status not in STATUSES:
            problems.append('%s: unknown status %r' % (where, note.status))
        if note.status in ('IMPLEMENTED', 'VERIFIED'):
            for field in ('code', 'tests'):
                for item in note.listed(field):
                    if not (Path(root) / item).exists():
                        problems.append('%s: %s path does not exist: %s' % (where, field, item))
        for relation in RELATIONS:
            for target in note.listed(relation):
                if target not in notes:
                    problems.append('%s: %s names a missing note %r' % (where, relation, target))
        for target, anchor in note.links:
            if target not in notes:
                problems.append('%s: link to missing note [[%s]]' % (where, target))
            elif anchor and ' '.join(anchor.split()) not in headings(notes[target].body):
                problems.append('%s: [[%s#%s]] heading not found' % (where, target, anchor))
    return problems


if __name__ == '__main__':
    found = check()
    sys.stdout.reconfigure(encoding='utf-8')
    print('\n'.join(found) if found else 'vault consistent')
    sys.exit(1 if found else 0)
