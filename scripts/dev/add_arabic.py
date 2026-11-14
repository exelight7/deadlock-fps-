"""Add Arabic for new English source strings: python scripts/dev/add_arabic.py FILE.py

FILE.py defines `NEW = {'English source string': 'Arabic'}` (into lang_ar.py) and/or `NEW_EN = {'Arabic source string': 'English'}` (into
lang_en.py). Entries are merged sorted; existing entries are kept unless the file sets REPLACE = True. Run `scripts/i18n_tool.py check` afterwards.
"""
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def merge(target, new, replace):
    namespace = runpy.run_path(str(target))
    text = dict(namespace['TEXT'])
    added = 0
    for key, value in new.items():
        if key not in text or replace:
            text[key] = value
            added += 1
    doc = namespace.get('__doc__') or ''
    lines = ['"""%s"""' % doc, '', 'TEXT = {']
    for key in sorted(text):
        lines.append('    %r: %r,' % (key, text[key]))
    lines.append('}')
    target.write_bytes(('\n'.join(lines) + '\n').encode('utf-8'))
    return added


def main(path):
    spec = runpy.run_path(path)
    replace = spec.get('REPLACE', False)
    for name, new in (('lang_ar.py', spec.get('NEW', {})), ('lang_en.py', spec.get('NEW_EN', {}))):
        if new:
            print(name, 'added', merge(ROOT / 'deadlock_fps' / name, new, replace), 'of', len(new))


if __name__ == '__main__':
    main(sys.argv[1])
