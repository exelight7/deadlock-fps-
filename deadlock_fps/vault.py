"""Reader for the project's Obsidian vault (Markdown with YAML-ish frontmatter and [[wikilinks]]). Qt-free.

Used by `scripts/check_vault.py` to verify the notes and by the knowledge graph to draw them. Only the small subset of
frontmatter the vault actually uses is understood: `key: value` and inline lists `key: [a, b]`.
"""
import re
from dataclasses import dataclass, field
from pathlib import Path

LINK = re.compile(r'\[\[([^\]\|#]+)(?:#([^\]\|]+))?(?:\|[^\]]*)?\]\]')
CODE = re.compile(r'```.*?```|`[^`\n]*`', re.DOTALL)
MAX_NOTE = 512 * 1024


@dataclass(frozen=True)
class Note:
    title: str                 # the file name without .md: what [[links]] use
    path: Path
    meta: dict
    body: str
    links: tuple = field(default=())       # ((target title, anchor or ''), ...) from prose, code spans excluded

    @property
    def type(self):
        return self.meta.get('type', '')

    @property
    def status(self):
        return self.meta.get('status', '')

    def listed(self, key):
        value = self.meta.get(key, [])
        return value if isinstance(value, list) else ([value] if value else [])


def frontmatter(text):
    if not text.startswith('---\n'):
        return {}, text
    end = text.find('\n---\n', 4)
    if end < 0:
        return {}, text
    data = {}
    for line in text[4:end].splitlines():
        key, _, value = line.partition(':')
        value = value.strip()
        if value.startswith('[') and value.endswith(']'):
            data[key.strip()] = [v.strip() for v in value[1:-1].split(',') if v.strip()]
        else:
            data[key.strip()] = value
    return data, text[end + 5:]


def headings(body):
    return {re.sub(r'\s+', ' ', m.group(1).strip()) for m in re.finditer(r'^#{1,6}\s+(.+?)\s*$', body, re.MULTILINE)}


def links_in(body):
    return tuple((t.strip(), (a or '').strip()) for t, a in LINK.findall(CODE.sub('', body)))


def read_vault(folder):
    """{title: Note} for every .md file under `folder`. Unreadable or oversized files are skipped."""
    notes = {}
    for path in sorted(Path(folder).rglob('*.md')):
        try:
            if path.stat().st_size > MAX_NOTE:
                continue
            meta, body = frontmatter(path.read_text(encoding='utf-8'))
        except (OSError, UnicodeDecodeError):
            continue
        notes[path.stem] = Note(path.stem, path, meta, body, links_in(body))
    return notes
