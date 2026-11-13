"""Design tokens for the Toolbox interface. Pure data: no Qt imports.

The rules behind these values are written down in docs/DESIGN.md. Both the
running app (design.py, motion.py) and scripts/make_assets.py read them, so
the artwork and the widgets can never drift apart.
"""

# Surfaces: ink black rising into dark teal.
INK = '#07090b'          # the void behind everything, intro curtain
BASE = '#0b1114'         # window background
SIDEBAR = '#0a0f12'      # directory rail
SURFACE = '#0f1b1e'      # panels
RAISED = '#14262a'       # hovered rows, table header, raised controls
SUNKEN = '#091013'       # inputs, wells, tracks
ACTIVE = '#1b3539'       # pressed / strongest teal

# Lines.
LINE = '#213739'         # hairline around panels and inputs
LINE_STRONG = '#35585a'  # hovered hairline, dividers that must read
TEAL = '#4f8f8c'         # teal used as ink (rules, cold accents)

# Aged brass.
BRASS = '#c9a45c'        # the accent
BRASS_BRIGHT = '#e7c08a' # polished edge, selected fills, key text
BRASS_DEEP = '#8a6f3b'   # brass as a border on dark
BRASS_SHADE = '#3b3427'  # brass-tinted surface (selected row)
BRASS_WASH = '#231f16'   # faint brass surface (active control)
ON_BRASS = '#17120a'     # text on a brass fill

# Text: warm parchment, never pure white.
TEXT = '#ede6d6'
TEXT_SOFT = '#b9b4a3'
TEXT_MUTED = '#8e948c'
TEXT_OFF = '#59625f'     # disabled only

# States.
CRIMSON = '#b3262e'      # restrained alert fill
CRIMSON_TEXT = '#ec7f86' # alert text on dark surfaces
CRIMSON_LINE = '#7a2a30'
CRIMSON_WASH = '#261114'
VERDIGRIS = '#74c7ad'    # success, oxidised copper
VERDIGRIS_LINE = '#2e6b5e'
VERDIGRIS_WASH = '#0f2a26'
AMBER = '#d9a45c'        # waiting / not yet connected

# Type.
DISPLAY = ('Reem Kufi', 'Noto Sans Arabic', 'Noto Sans', 'Segoe UI')
BODY = ('Noto Sans Arabic', 'Noto Sans', 'Segoe UI')
MONO = ('Cascadia Mono', 'Consolas', 'DejaVu Sans Mono', 'monospace')
FONT_FILES = ('NotoSansArabic.ttf', 'NotoSans.ttf', 'ReemKufi.ttf')
SIZE = {'hero': 26, 'title': 24, 'heading': 17, 'subheading': 14, 'body': 13, 'label': 12, 'caption': 11, 'kicker': 10}

# Space: a 4px grid.
SPACE = (4, 8, 12, 16, 24, 32)
GUTTER = 28              # page margin
PANEL_PAD = 20
CHAMFER = 10             # the cut corner of every panel
CONTROL = 36             # control height
RAIL = 232               # directory rail width

# Icons: one 24px grid, one 1.5px stroke, square caps, mitred joins.
ICON_GRID = 24
ICON_STROKE = 1.5


def family(stack):
    """A font stack as a stylesheet value."""
    return ','.join('"%s"' % name if name != 'monospace' else name for name in stack)


def has_arabic(text):
    """Joined scripts must never be letter-spaced; widgets ask this before tracking."""
    return any('؀' <= c <= 'ۿ' or 'ݐ' <= c <= 'ݿ' or 'ﭐ' <= c <= 'ﻼ' for c in text or '')
