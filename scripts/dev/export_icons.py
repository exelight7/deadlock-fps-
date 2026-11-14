"""Write the redesign's line icons (the ICONS table of docs/design-prototype/app.js) to assets/icons2/*.svg.

The paths are original to this project (Phase 1). The SVGs use `currentColor`; deadlock_fps/shell/icons.py
replaces it with a token colour at run time.

    .venv/Scripts/python.exe scripts/dev/export_icons.py          write the files
    .venv/Scripts/python.exe scripts/dev/export_icons.py --check  fail if a file is missing or different
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'docs/design-prototype/app.js'
TARGET = ROOT / 'assets/icons2'
TEMPLATE = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" '
            'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="{0}"/></svg>\n')


def icons():
    text = SOURCE.read_text(encoding='utf-8')
    block = text[text.index('const ICONS = {'):text.index('};', text.index('const ICONS = {'))]
    return dict(re.findall(r"^\s*([a-z]+):\s*'([^']+)'", block, re.M))


def main(check):
    wanted = {name: TEMPLATE.format(path) for name, path in icons().items()}
    bad = []
    TARGET.mkdir(parents=True, exist_ok=True)
    for name, svg in sorted(wanted.items()):
        path = TARGET / (name + '.svg')
        if check:
            if not path.is_file() or path.read_bytes() != svg.encode('utf-8'):
                bad.append(name)
        else:
            path.write_bytes(svg.encode('utf-8'))
    if check and bad:
        print('different or missing:', ', '.join(bad))
        return 1
    print('%d icons %s' % (len(wanted), 'match' if check else 'written'))
    return 0


if __name__ == '__main__':
    sys.exit(main('--check' in sys.argv))
