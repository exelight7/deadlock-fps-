"""Small lossless Valve KeyValues editor. Comments and unrelated values survive."""
import re
from dataclasses import dataclass, field
TOKEN = re.compile(r'//[^\n]*|"(?:\\.|[^"\\])*"|[{}]|[^\s{}"]+')
@dataclass
class Node:
    key: str
    start: int
    end: int
    value: str | None = None
    value_start: int = 0
    value_end: int = 0
    close: int = 0
    children: list = field(default_factory=list)

def parse(text):
    tokens = [m for m in TOKEN.finditer(text) if not m[0].startswith('//')]
    pos = 0
    def decode(s):
        return s[1:-1] if s.startswith('"') else s
    def block(nested=False):
        nonlocal pos
        nodes = []
        while pos < len(tokens):
            k = tokens[pos]; pos += 1
            if k[0] == '}':
                if not nested: raise ValueError('Unexpected closing brace')
                return nodes, k.start()
            if k[0] == '{' or pos >= len(tokens): raise ValueError('Invalid KeyValues')
            v = tokens[pos]; pos += 1
            if v[0] == '{':
                children, close = block(True)
                nodes.append(Node(decode(k[0]), k.start(), close+1, close=close, children=children))
            elif v[0] == '}': raise ValueError('Missing value')
            else: nodes.append(Node(decode(k[0]), k.start(), v.end(), decode(v[0]), v.start(), v.end()))
        if nested: raise ValueError('Unclosed block')
        return nodes, len(text)
    return block()[0]

def section(text, path):
    nodes = parse(text); node = None
    for name in path:
        matches = [n for n in nodes if n.key.lower() == name.lower() and n.value is None]
        if len(matches) != 1: raise ValueError(f'Missing or ambiguous section: {name}')
        node = matches[0]; nodes = node.children
    return node

def update(text, path, values):
    node = section(text, path); edits = []; found = set()
    for n in node.children:
        if n.key in values and n.value is not None:
            edits.append((n.value_start,n.value_end,'"'+str(values[n.key])+'"')); found.add(n.key)
    extra = ''.join(f'\n\t\t"{k}" "{v}"' for k,v in values.items() if k not in found)
    if extra: edits.append((node.close,node.close,extra+'\n\t'))
    for a,b,v in sorted(edits,reverse=True): text=text[:a]+v+text[b:]
    parse(text)
    return text

def add_search_path(text):
    n=section(text,['GameInfo','FileSystem','SearchPaths'])
    if any(c.key.lower()=='game' and c.value=='citadel/fps_studio' for c in n.children): return text
    at=n.children[0].start if n.children else n.close
    return text[:at]+'Game "citadel/fps_studio" // Deadlock FPS Studio\n\t\t\t'+text[at:]
