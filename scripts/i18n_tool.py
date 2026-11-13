"""Maintain the translation layer.

    python scripts/i18n_tool.py wrap      wrap interface strings in deadlock_fps/ with tr() (idempotent)
    python scripts/i18n_tool.py list      print every source string that tr() receives, one JSON list
    python scripts/i18n_tool.py check     fail when a catalogue misses a string or breaks a template

Source strings stay in the language their module was written in: Arabic
everywhere except the crosshair workspace, which is English. f-strings become
`tr('template {0}').format(value)` so word order can change per language.
"""
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'deadlock_fps'
SKIP_FILES = {'i18n.py', 'lang_en.py', 'lang_ar.py', 'theme.py', '__init__.py', 'crosshair_style.py'}
ENGLISH_FILES = {'crosshair_ui.py', 'crosshair.py', 'crosshair_catalog.py'}
ARABIC = re.compile(r'[ء-ي]{2,}')
# English text is only wrapped where it is shown: as an argument of these calls (or inside a list/dict/concat that is).
ENGLISH_CALLS = {'note', 'panel', 'QPushButton', 'QCheckBox', 'QLabel', 'Kicker', 'setText', 'setToolTip', 'setPlaceholderText', 'setWindowTitle',
                 'addTab', 'addItem', 'addItems', 'addAction', 'addButton', 'ValueError', 'question', 'warning', 'information', 'getText', 'getItem',
                 'getMultiLineText', 'getOpenFileName', 'getSaveFileName', 'getColor', 'empty_state', 'Entry', 'setAccessibleName'}
ENGLISH_TEXT = re.compile(r'[A-Za-z]{2,}')
OBJECT_NAMES = re.compile(r'^[a-z][A-Za-z]*$|^#|^\.|^[a-z_]+:|^JSON|^Images \(')


def wants(value, english):
    if not isinstance(value, str):
        return False
    if ARABIC.search(value):
        return True
    return bool(english and ENGLISH_TEXT.search(value) and not OBJECT_NAMES.search(value.strip()) and (' ' in value.strip() or value.strip()[:1].isupper()))


def call_name(node):
    func = node.func
    return func.attr if isinstance(func, ast.Attribute) else getattr(func, 'id', '')


def transform(source, english_file):
    """One pass. Returns (new source, strings wrapped this pass)."""
    tree = ast.parse(source)
    parents = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    lines = source.encode('utf-8').split(b'\n')

    def offset(line, column):
        return sum(len(l) + 1 for l in lines[:line - 1]) + column

    def segment(node):
        return source.encode('utf-8')[offset(node.lineno, node.col_offset):offset(node.end_lineno, node.end_col_offset)].decode('utf-8')

    def shown(node):
        """Is this (English) string displayed? Climb through containers and concatenation to a known call."""
        current = node
        while current in parents:
            parent = parents[current]
            if isinstance(parent, ast.Call):
                return call_name(parent) in ENGLISH_CALLS and current is not parent.func
            if isinstance(parent, ast.Dict):
                if current in parent.keys:
                    return False
            elif not isinstance(parent, (ast.BinOp, ast.IfExp, ast.List, ast.Tuple, ast.JoinedStr, ast.FormattedValue, ast.Starred, ast.keyword)):
                if isinstance(parent, ast.Assign) and isinstance(parents.get(parent), ast.Module):
                    return True                      # module-level tables such as LABELS
                return False
            current = parent
        return False

    def skip(node):
        parent = parents.get(node)
        if isinstance(parent, ast.Expr):
            return True                               # docstring
        if isinstance(parent, ast.Call) and call_name(parent) == 'tr':
            return True
        if isinstance(parent, ast.Subscript) and parent.slice is node:
            return True                               # lookup key, not text
        if isinstance(parent, ast.Dict) and node in parent.keys:
            return True
        ancestor = parent
        while ancestor is not None:
            if isinstance(ancestor, ast.FormattedValue) and ancestor.format_spec is not None and node in ast.walk(ancestor.format_spec):
                return True
            if isinstance(ancestor, ast.Call) and call_name(ancestor) in ('setObjectName', 'setProperty', 'property', 'setStyleSheet', 'findData', 'encode', 'search', 'compile', 'strftime'):
                return True
            ancestor = parents.get(ancestor)
        return False

    edits, wrapped, covered = [], [], set()
    for node in ast.walk(tree):
        if id(node) in covered or not isinstance(node, (ast.Constant, ast.JoinedStr)):
            continue
        if isinstance(node, ast.JoinedStr):
            if isinstance(parents.get(node), ast.FormattedValue) and parents[node].format_spec is node:
                continue
            literal = ''.join(v.value for v in node.values if isinstance(v, ast.Constant))
            english = english_file and shown(node)
            if not wants(literal, english) or skip(node):
                continue
            template, arguments, plain = '', [], True
            for value in node.values:
                if isinstance(value, ast.Constant):
                    template += value.value.replace('{', '{{').replace('}', '}}')
                    continue
                spec = ''
                if value.format_spec is not None:
                    if not all(isinstance(v, ast.Constant) for v in value.format_spec.values):
                        plain = False
                        break
                    spec = ':' + ''.join(v.value for v in value.format_spec.values)
                conversion = {115: '!s', 114: '!r', 97: '!a'}.get(value.conversion, '')
                template += '{%d%s%s}' % (len(arguments), conversion, spec)
                arguments.append(segment(value.value))
            if not plain:
                continue
            for child in ast.walk(node):
                covered.add(id(child))
            edits.append((offset(node.lineno, node.col_offset), offset(node.end_lineno, node.end_col_offset), 'tr(%r).format(%s)' % (template, ','.join(arguments))))
            wrapped.append(template)
        elif isinstance(node.value, str):
            if isinstance(parents.get(node), ast.JoinedStr):
                continue
            english = english_file and shown(node)
            if not wants(node.value, english) or skip(node):
                continue
            edits.append((offset(node.lineno, node.col_offset), offset(node.end_lineno, node.end_col_offset), 'tr(%s)' % segment(node)))
            wrapped.append(node.value)
    data = source.encode('utf-8')
    for start, end, text in sorted(edits, reverse=True):
        data = data[:start] + text.encode('utf-8') + data[end:]
    return data.decode('utf-8'), wrapped


def add_import(source):
    if re.search(r'^from \.i18n import tr$', source, re.MULTILINE):
        return source
    tree = ast.parse(source)
    first = next(n for n in tree.body if not (isinstance(n, ast.Expr) and isinstance(getattr(n, 'value', None), ast.Constant)))
    lines = source.split('\n')
    lines.insert(first.lineno - 1, 'from .i18n import tr')
    return '\n'.join(lines)


def files():
    return [p for p in sorted(PACKAGE.glob('*.py')) if p.name not in SKIP_FILES]


def wrap():
    total = 0
    for path in files():
        source = original = path.read_text(encoding='utf-8')
        for _ in range(6):                            # inner strings of a wrapped f-string surface on the next pass
            source, wrapped = transform(source, path.name in ENGLISH_FILES)
            total += len(wrapped)
            if not wrapped:
                break
        if source != original:
            path.write_text(add_import(source), encoding='utf-8', newline='\n')
            print('%-24s wrapped' % path.name)
    print('%d strings wrapped' % total)


def sources():
    """Every string literal passed to tr(), split by the language it is written in."""
    arabic, english = set(), set()
    for path in files():
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            if isinstance(node, ast.Call) and call_name(node) == 'tr' and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                (arabic if ARABIC.search(node.args[0].value) else english).add(node.args[0].value)
    return sorted(arabic), sorted(english)


def placeholders(text):
    return sorted(re.findall(r'\{(\d+)[^}]*\}', text.replace('{{', '').replace('}}', '')))


def check():
    sys.path.insert(0, str(ROOT))
    from deadlock_fps.lang_ar import TEXT as to_arabic
    from deadlock_fps.lang_en import TEXT as to_english
    arabic, english = sources()
    problems = []
    for source, catalogue, name in [(arabic, to_english, 'lang_en'), (english, to_arabic, 'lang_ar')]:
        for text in source:
            if text not in catalogue:
                problems.append('%s: missing %r' % (name, text))
            elif placeholders(text) != placeholders(catalogue[text]):
                problems.append('%s: placeholders differ for %r' % (name, text))
        if name == 'lang_en':
            problems += ['lang_en: Arabic left in the translation of %r' % k for k, v in catalogue.items() if k in source and ARABIC.search(v)]
    print('\n'.join(problems) if problems else 'catalogues complete: %d Arabic and %d English source strings' % (len(arabic), len(english)))
    return not problems


if __name__ == '__main__':
    command = sys.argv[1] if len(sys.argv) > 1 else ''
    if command == 'wrap':
        wrap()
    elif command == 'list':
        arabic, english = sources()
        sys.stdout.reconfigure(encoding='utf-8')
        print(json.dumps({'arabic': arabic, 'english': english}, ensure_ascii=False, indent=0))
    elif command == 'check':
        sys.exit(0 if check() else 1)
    else:
        print(__doc__)
