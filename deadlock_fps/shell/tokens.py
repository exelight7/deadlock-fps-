"""Design tokens of the redesign (Phase 1): load, resolve, scale, convert. No Qt here.

`tokens.json` next to this file is a copy of `docs/design-prototype/tokens.json` (a test keeps them
identical). Never retype a value: ask a `Theme` for it by name.

    theme = Theme('dark', accent='blue', scale=100)
    theme['color.bg.surface']   -> '#171A20'
    theme.px('space.4')         -> 16 (scaled by the text size)
    theme.qss('color.bg.scrim') -> 'rgba(0, 0, 0, 166)'
    theme.render('QFrame { background: {color.bg.surface}; padding: {space.4}; }')
"""
import json
import re
from pathlib import Path

TOKENS_FILE = Path(__file__).with_name('tokens.json')
MODES = ('dark', 'light')
_PLACEHOLDER = re.compile(r'\{([a-z][a-z0-9.-]*)\}')
_PIXELS = re.compile(r'\d+(\.\d+)?px')
# Text size multiplies these families of sizes (06 Handoff to Build, section 1).
_SCALED = ('font.size.', 'size.control.', 'size.icon.', 'space.')
_cache = {}


def load(path=TOKENS_FILE):
    key = str(path)
    if key not in _cache:
        _cache[key] = json.loads(Path(path).read_text(encoding='utf-8'))
    return _cache[key]


def scales(data=None):
    data = data or load()
    return tuple(int(v) for v in data['scale']['scale.options'].split(','))


def accents(data=None):
    return tuple((data or load())['accents'])


def rgba(value):
    """'#RRGGBB' or '#RRGGBBAA' → (r, g, b, a)."""
    text = value.lstrip('#')
    if not re.fullmatch(r'[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?', text):
        raise ValueError('not a colour: %s' % value)
    r, g, b = (int(text[i:i + 2], 16) for i in (0, 2, 4))
    return r, g, b, int(text[6:8], 16) if len(text) == 8 else 255


def qss_color(value):
    """A colour as a Qt stylesheet wants it: '#RRGGBB' or 'rgba(r, g, b, a)'."""
    r, g, b, a = rgba(value)
    return '#%02X%02X%02X' % (r, g, b) if a == 255 else 'rgba(%d, %d, %d, %d)' % (r, g, b, a)


def argb(value):
    """A colour as QColor's string constructor wants it: '#AARRGGBB'."""
    r, g, b, a = rgba(value)
    return '#%02X%02X%02X%02X' % (a, r, g, b)


class Theme:
    """Resolves token names for one (mode, accent, text scale)."""

    def __init__(self, mode='dark', accent='blue', scale=100, data=None):
        data = data or load()
        if mode not in MODES:
            raise ValueError('unknown theme: %s' % mode)
        if accent not in data['accents']:
            raise ValueError('unknown accent: %s' % accent)
        if scale not in scales(data):
            raise ValueError('unknown text size: %s' % scale)
        self.mode, self.accent, self.scale = mode, accent, scale
        self.values = dict(data['themes'][mode])
        self.values.update(data['accents'][accent][mode])
        self.values.update(data['scale'])

    def __getitem__(self, name):
        return self.values[name]

    def __contains__(self, name):
        return name in self.values

    def names(self):
        return sorted(self.values)

    def px(self, name):
        """A size token as whole pixels, multiplied by the text scale where the design says so."""
        value = self.values[name]
        if not _PIXELS.fullmatch(value):
            raise ValueError('not a size: %s' % name)
        number = float(value[:-2])
        if name.startswith(_SCALED):
            number = number * self.scale / 100
        return int(round(number))

    def ms(self, name):
        return int(self.values[name].removesuffix('ms'))

    def qss(self, name):
        """A value ready to drop into a stylesheet."""
        value = self.values[name]
        if name.startswith('color.'):
            return qss_color(value)
        if _PIXELS.fullmatch(value):
            return '%dpx' % self.px(name)
        return value

    def render(self, template):
        """Fill `{token.name}` placeholders. An unknown name raises KeyError (typos fail loudly)."""
        return _PLACEHOLDER.sub(lambda m: self.qss(m.group(1)), template)

    def families(self, name='font.family.ui'):
        return [part.strip().strip("'\"") for part in self.values[name].split(',') if part.strip() not in ('sans-serif', 'monospace')]
