"""Generate every visual asset of Deadlock Toolbox from code (PySide6 only).

    python scripts/make_assets.py              write assets/, docs/contact-sheet.png and docs/banner.png
    python scripts/make_assets.py --contrast   print the WCAG contrast table and exit

All artwork is original and drawn here: an art-deco keyhole emblem, a skyline
banner, one line-icon set, three tile patterns and the empty-state
illustrations. Output is deterministic, so a second run changes nothing.
"""
import math
import os
import random
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from deadlock_fps import theme as T  # noqa: E402

ASSETS = ROOT / 'assets'
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256, 512)
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)


def n(value):
    """Short, stable number formatting for SVG."""
    return ('%.2f' % value).rstrip('0').rstrip('.')


def svg(width, height, body, attributes=''):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%s" height="%s" viewBox="0 0 %s %s"%s>\n%s\n</svg>\n'
            % (width, height, width, height, ' ' + attributes if attributes else '', body))


def shapes(items, indent='  '):
    """Icon shorthand: 'M…' is a path, ('c',cx,cy,r) a circle, ('r',x,y,w,h) a rect, ('d',cx,cy,r) a solid dot."""
    out = []
    for item in items:
        if isinstance(item, str):
            out.append('<path d="%s"/>' % item)
        elif item[0] == 'c':
            out.append('<circle cx="%s" cy="%s" r="%s"/>' % item[1:])
        elif item[0] == 'r':
            out.append('<rect x="%s" y="%s" width="%s" height="%s"/>' % item[1:])
        else:
            out.append('<circle cx="%s" cy="%s" r="%s" fill="currentColor" stroke="none"/>' % item[1:])
    return '\n'.join(indent + line for line in out)


# --- Line icons: 24px grid, 1.5px stroke, square caps, mitred joins -----------------------------

ICONS = {
    # Destinations.
    'overview': ['M3 20h18', 'M5 20a7 7 0 0 1 14 0', 'M9 20a3 3 0 0 1 6 0', 'M12 10.5V5.5', 'M5.3 13.3 2.5 10.5', 'M18.7 13.3l2.8-2.8'],
    'graphics': ['M6 3v5', 'M6 13v8', 'M12 3v10', 'M12 18v3', 'M18 3v2', 'M18 10v11',
                 'M6 8l2.5 2.5L6 13l-2.5-2.5z', 'M12 13l2.5 2.5L12 18l-2.5-2.5z', 'M18 5l2.5 2.5L18 10l-2.5-2.5z'],
    'mods': ['M3 7.5 12 3l9 4.5v9L12 21l-9-4.5z', 'M3 7.5l9 4.5 9-4.5', 'M12 12v9'],
    'backups': [('r', 3, 4, 18, 15), ('c', 12, 11.5, 3.5), 'M12 6.5V8', 'M12 15v1.5', 'M7 11.5h1.5', 'M15.5 11.5H17', 'M6 19v2', 'M18 19v2'],
    'servers': ['M12 9.5 7.5 21h9z', 'M9.5 16h5', ('c', 12, 6.5, 1.5), 'M7.5 2.5a6 6 0 0 0 0 8', 'M16.5 2.5a6 6 0 0 1 0 8'],
    'crosshair': [('c', 12, 12, 6), 'M12 2v5', 'M12 17v5', 'M2 12h5', 'M17 12h5', ('d', 12, 12, 1.1)],
    'updates': ['M12 3v11', 'M7 9.5l5 5 5-5', 'M4 17v4h16v-4'],
    'inspector': [('c', 10, 10, 6.5), 'M15 15l6 6', 'M7 10l2.2 2.2L13 8.2'],
    # Mods.
    'daylock': [('c', 12, 12, 4), 'M12 2v3', 'M12 19v3', 'M2 12h3', 'M19 12h3', 'M4.9 4.9 7 7', 'M17 17l2.1 2.1', 'M4.9 19.1 7 17', 'M17 7l2.1-2.1'],
    'names': ['M3 6h11l7 6-7 6H3z', ('c', 14, 12, 1.5), 'M6 10h4', 'M6 14h3'],
    'health': [('r', 2, 8, 20, 8), 'M5.5 12h4', 'M7.5 10v4', 'M13 10.5v3', 'M16 10.5v3', 'M19 10.5v3'],
    'sinner': ['M19 12a7 7 0 1 1-2.6-5.4', 'M19 3.5V8h-4.5', 'M8.5 12.2l2.4 2.4 4.6-4.8'],
    # Actions and states.
    'folder': ['M3 5h6l2 3h10v11H3z'],
    'search': [('c', 10.5, 10.5, 6.5), 'M15.5 15.5 21 21'],
    'external': ['M10 5H5v14h14v-5', 'M14 4h6v6', 'M20 4l-8.5 8.5'],
    'check': ['M4.5 12.5l5 5L19.5 7'],
    'chevron-down': ['M5.5 9l6.5 6.5L18.5 9'],
    'refresh': ['M19 12a7 7 0 1 1-2.6-5.4', 'M19 3.5V8h-4.5'],
    'shield': ['M12 3l8 3v6l-8 9-8-9V6z', 'M8.5 11.6l2.4 2.4 4.6-4.8'],
    'warning': ['M12 3.5 21.5 20h-19z', 'M12 10v5', 'M12 17.3v.2'],
    'info': [('c', 12, 12, 8.5), 'M12 11v5.5', 'M12 7.6v.2'],
    'help': [('c', 12, 12, 8.5), 'M9.5 9.8a2.5 2.5 0 1 1 3.6 2.2c-.8.4-1.1.9-1.1 1.8', 'M12 16.6v.2'],
    'plus': ['M12 5v14', 'M5 12h14'],
    'close': ['M6 6l12 12', 'M18 6 6 18'],
    'save': ['M4 4h12.5L20 7.5V20H4z', 'M8 4v5h7V4', 'M8 20v-6h8v6'],
    'share': ['M12 14V3', 'M7.5 7.5 12 3l4.5 4.5', 'M4 13v8h16v-8'],
    'undo': ['M8 5 4 9l4 4', 'M4 9h10.5a5.5 5.5 0 0 1 0 11H9'],
    'ping': ['M2 12h5l2.5-7 4 14 2.5-7h6'],
    'block': [('c', 12, 12, 8.5), 'M6 6l12 12'],
    'lock': [('r', 5, 11, 14, 10), 'M8 11V7.5a4 4 0 0 1 8 0V11', 'M12 15v2.5'],
    'unlock': [('r', 5, 11, 14, 10), 'M8 11V7.5a4 4 0 0 1 7.6-1.7', 'M12 15v2.5'],
    'sort': ['M4 6h16', 'M7 12h10', 'M10 18h4'],
    'gallery': [('r', 4, 4, 6.5, 6.5), ('r', 13.5, 4, 6.5, 6.5), ('r', 4, 13.5, 6.5, 6.5), ('r', 13.5, 13.5, 6.5, 6.5)],
    'gauge': ['M4 18a8 8 0 0 1 16 0', 'M12 18l4.2-5.6', 'M3 18h18'],
    'aspect': [('r', 2.5, 6, 19, 12), 'M7 12h10', 'M9 9.5 6.5 12 9 14.5', 'M15 9.5l2.5 2.5-2.5 2.5'],
    'link': ['M10 14l4-4', 'M11 6.5l1.8-1.8a4 4 0 0 1 5.7 5.7L16.7 12.2', 'M13 17.5l-1.8 1.8a4 4 0 0 1-5.7-5.7L7.3 11.8'],
    'copy': [('r', 8, 8, 12, 12), 'M16 8V4H4v12h4'],
    'trash': ['M4 7h16', 'M9 7V4h6v3', 'M6.5 7l1 13h9l1-13', 'M10 11v5.5', 'M14 11v5.5'],
    'filter': ['M3.5 5h17L14 13v6l-4 1.5V13z'],
    'clock': [('c', 12, 12, 8.5), 'M12 7v5l3.5 2'],
    'file': ['M6 3h8l4 4v14H6z', 'M14 3v4h4', 'M9 12h6', 'M9 16h6'],
    'diamond': ['M12 4l8 8-8 8-8-8z'],
}


def icon_svg(name, color=None, stroke=T.ICON_STROKE):
    color = color or T.BRASS
    return svg(24, 24, shapes(ICONS[name]),
               'fill="none" stroke="%s" color="%s" stroke-width="%s" stroke-linecap="square" stroke-linejoin="miter"' % (color, color, n(stroke)))


def stylesheet_glyphs():
    """Small fixed-colour images the Qt stylesheet points at (it cannot tint an SVG itself)."""
    handle = '<path d="M9 1.5 16.5 9 9 16.5 1.5 9z" fill="%s" stroke="%s" stroke-width="1.5"/>\n  <path d="M9 6l3 3-3 3-3-3z" fill="%s"/>'
    return {
        'check': icon_svg('check', T.ON_BRASS, 2.6),
        'check-off': icon_svg('check', T.TEXT_OFF, 2.6),
        'chevron-down': icon_svg('chevron-down', T.BRASS, 1.8),
        'chevron-down-off': icon_svg('chevron-down', T.TEXT_OFF, 1.8),
        'handle': svg(18, 18, '  ' + handle % (T.BRASS, T.ON_BRASS, T.ON_BRASS)),
        'handle-hover': svg(18, 18, '  ' + handle % (T.BRASS_BRIGHT, T.ON_BRASS, T.ON_BRASS)),
        'handle-off': svg(18, 18, '  ' + handle % (T.ACTIVE, T.SUNKEN, T.SUNKEN)),
    }


# --- Emblem and app icon ---------------------------------------------------------------------------

def emblem_parts(color=T.BRASS, frame=True, rays=True):
    """The mark on a 96px square: a keyhole on a stepped plinth under a sunburst, in a cut-corner frame."""
    out = []
    if frame:
        out.append('<path d="M22 5h52l17 17v52L74 91H22L5 74V22z" fill="none" stroke="%s" stroke-width="2.5"/>' % color)
        out.append('<path d="M25 12h46l13 13v46L71 84H25L12 71V25z" fill="none" stroke="%s" stroke-width="1" stroke-opacity=".55"/>' % color)
    if rays:
        for index, angle in enumerate(range(-150, -29, 20)):
            a = math.radians(angle)
            far = 28 if index % 2 == 0 else 22.5
            out.append('<path d="M%s %s %s %s" fill="none" stroke="%s" stroke-width="2" stroke-linecap="butt"/>' % (
                n(48 + 13.5 * math.cos(a)), n(44.5 + 13.5 * math.sin(a)), n(48 + far * math.cos(a)), n(44.5 + far * math.sin(a)), color))
    out.append('<path d="M48 35a9.5 9.5 0 0 1 5.2 17.4L56 70H40l2.8-17.6A9.5 9.5 0 0 1 48 35z" fill="%s"/>' % color)
    out.append('<path d="M36 74.5h24M31 79.5h34" fill="none" stroke="%s" stroke-width="2.5" stroke-linecap="butt"/>' % color)
    return out


def emblem_svg(color=T.BRASS):
    return svg(96, 96, '\n'.join('  ' + part for part in emblem_parts(color)))


def app_icon_svg(detail=True):
    """Full icon for 48px and up; a bolder cut for the small sizes where hairlines would vanish."""
    out = []
    if detail:
        out.append('<path d="M21 2h54l19 19v54L75 94H21L2 75V21z" fill="%s"/>' % T.INK)
        out.append('<path d="M22 5h52l17 17v52L74 91H22L5 74V22z" fill="%s"/>' % T.SURFACE)
        for radius in (26, 34, 42):
            out.append('<path d="M%s 44.5a%s %s 0 0 1 %s 0" fill="none" stroke="%s" stroke-width="1"/>' % (n(48 - radius), radius, radius, 2 * radius, T.LINE_STRONG))
        out.extend(emblem_parts())
    else:
        out.append('<path d="M24 3h48l21 21v48L72 93H24L3 72V24z" fill="%s" stroke="%s" stroke-width="6"/>' % (T.SURFACE, T.BRASS))
        out.append('<path d="M48 20a15 15 0 0 1 8 27.7L61 76H35l5-28.3A15 15 0 0 1 48 20z" fill="%s"/>' % T.BRASS_BRIGHT)
    return svg(96, 96, '\n'.join('  ' + part for part in out))


# --- Banner artwork ---------------------------------------------------------------------------------

def tower(rnd, x, width, height, ground, fill, lit):
    """One stepped deco tower as SVG: body, two or three setbacks, an optional spire and window lines."""
    out = []
    points = [(x, ground), (x, ground - height)]
    left, right, top = x, x + width, ground - height
    for _ in range(rnd.choice((2, 2, 3))):
        inset = rnd.randint(6, 12)
        rise = rnd.randint(12, 26)
        if right - left - 2 * inset < 12:
            break
        left += inset
        right -= inset
        points += [(left, top), (left, top - rise)]
        top -= rise
    mirrored = [(x + width - (px - x), py) for px, py in reversed(points[1:])]
    polygon = points + mirrored + [(x + width, ground)]
    out.append('<path d="M%s z" fill="%s"%s/>' % (' L'.join('%s %s' % (n(px), n(py)) for px, py in polygon), fill, ' stroke="%s" stroke-width="1"' % T.LINE_STRONG if lit else ''))
    middle = x + width / 2
    if rnd.random() < .6:
        out.append('<path d="M%s %s V%s" fill="none" stroke="%s" stroke-width="1.5"/>' % (n(middle), n(top), n(top - rnd.randint(18, 46)), fill))
    column = x + 8
    while column < x + width - 6:
        out.append('<path d="M%s %s V%s" fill="none" stroke="%s" stroke-width="1" stroke-opacity=".12"/>' % (n(column), n(ground - height + 10), n(ground), T.BRASS))
        if lit and rnd.random() < .55:
            y = ground - rnd.randint(14, max(15, int(height) - 16))
            out.append('<rect x="%s" y="%s" width="3" height="5" fill="%s" fill-opacity=".55"/>' % (n(column - 1.5), n(y), T.BRASS_BRIGHT))
        column += 10
    return out


def banner_svg(motif, seed=1931):
    """A deco skyline under a rising sunburst disc. The far half stays calm for the page's own text."""
    width, height, ground = 1600, 300, 262
    cx, cy, disc = 300, 158, 92
    rnd = random.Random(seed)
    out = ['<rect width="%s" height="%s" fill="%s"/>' % (width, height, T.BASE)]
    for radius in range(disc + 34, 900, 40):
        out.append('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="1"/>' % (cx, cy, radius, T.LINE))
    for index, angle in enumerate(range(0, 360, 9)):
        a = math.radians(angle)
        out.append('<path d="M%s %s L%s %s" fill="none" stroke="%s" stroke-width="1" stroke-opacity="%s"/>' % (
            n(cx + (disc + 14) * math.cos(a)), n(cy + (disc + 14) * math.sin(a)), n(cx + 1200 * math.cos(a)), n(cy + 1200 * math.sin(a)), T.BRASS, '.26' if index % 4 == 0 else '.10'))
    for _ in range(40):
        x, y, size = rnd.randint(20, 1150), rnd.randint(10, 150), rnd.choice((2, 2, 3))
        out.append('<path d="M%s %sl%s %s-%s %s-%s-%sz" fill="%s" fill-opacity="%s"/>' % (x, y - size, size, size, size, size, size, size, T.BRASS_BRIGHT, rnd.choice(('.3', '.5', '.75'))))
    x = -20
    while x < 1240:                                   # far towers, hazed lighter than the sky
        tower_width = rnd.randint(40, 84)
        out += tower(rnd, x, tower_width, rnd.randint(56, 150), ground, T.RAISED, False)
        x += tower_width + rnd.randint(2, 14)
    out.append('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="%s" stroke-width="2"/>' % (cx, cy, disc, T.SURFACE, T.BRASS))
    out.append('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="1"/>' % (cx, cy, disc - 12, T.BRASS_DEEP))
    for angle in range(0, 360, 6):
        a = math.radians(angle)
        inner = disc - (9 if angle % 30 else 12)
        out.append('<path d="M%s %s L%s %s" fill="none" stroke="%s" stroke-width="1"/>' % (
            n(cx + inner * math.cos(a)), n(cy + inner * math.sin(a)), n(cx + (disc - 4) * math.cos(a)), n(cy + (disc - 4) * math.sin(a)), T.BRASS))
    if motif == 'emblem':
        out.append('<g transform="translate(%s %s) scale(1.4)">%s</g>' % (n(cx - 67.2), n(cy - 70), ''.join(emblem_parts(frame=False))))
    else:
        out.append('<g transform="translate(%s %s) scale(4.2)" fill="none" stroke="%s" color="%s" stroke-width=".5" stroke-linecap="square">\n%s\n</g>' % (
            n(cx - 50.4), n(cy - 50.4), T.BRASS_BRIGHT, T.BRASS_BRIGHT, shapes(ICONS[motif])))
    x = -30
    while x < 1060:                                   # near towers: darker than the sky, lit windows
        tower_width = rnd.randint(50, 96)
        if not cx - disc - 6 < x + tower_width / 2 < cx + disc + 6:   # leave the medallion clear
            out += tower(rnd, x, tower_width, rnd.randint(44, 170), ground, T.SUNKEN, True)
        x += tower_width + rnd.randint(4, 26)
    out.append('<rect x="0" y="%s" width="%s" height="%s" fill="%s"/>' % (ground, width, height - ground, T.INK))
    out.append('<path d="M0 %s.5H%s" fill="none" stroke="%s" stroke-width="1.5"/>' % (ground, width, T.BRASS))
    out.append('<path d="M0 %s.5H%s" fill="none" stroke="%s" stroke-width="1"/>' % (ground + 6, width, T.BRASS_DEEP))
    for x in range(8, width, 16):
        out.append('<path d="M%s %s l8 9 8-9" fill="none" stroke="%s" stroke-width="1"/>' % (x - 8, ground + 15, T.LINE_STRONG))
    out.append('<defs><linearGradient id="scrim" x1="0" x2="1" y1="0" y2="0"><stop offset=".40" stop-color="%s" stop-opacity="0"/>'
               '<stop offset=".68" stop-color="%s" stop-opacity=".92"/><stop offset="1" stop-color="%s" stop-opacity="1"/></linearGradient></defs>' % (T.BASE, T.BASE, T.BASE))
    out.append('<rect width="%s" height="%s" fill="url(#scrim)"/>' % (width, ground))
    return svg(width, height, '\n'.join('  ' + part for part in out))


BANNERS = {'emblem': 1931, 'mods': 1927, 'backups': 1929, 'servers': 1933}


# --- Patterns --------------------------------------------------------------------------------------

def pattern_fan():
    arcs = []
    for cx, cy in ((24, 24), (0, 48), (48, 48)):
        for radius in (24, 17, 10):
            arcs.append('<path d="M%s %sa%s %s 0 0 1 %s 0"/>' % (cx - radius, cy, radius, radius, 2 * radius))
    return svg(48, 48, '\n'.join('  ' + arc for arc in arcs), 'fill="none" stroke="%s" stroke-opacity=".5" stroke-width="1"' % T.LINE)


def pattern_lattice():
    body = '  <path d="M0 16 16 0l16 16-16 16z" fill="none" stroke="%s" stroke-opacity=".7" stroke-width="1"/>\n  <path d="M16 13.5l2.5 2.5-2.5 2.5-2.5-2.5z" fill="%s" fill-opacity=".16"/>' % (T.LINE, T.BRASS)
    return svg(32, 32, body)


def pattern_chevron():
    body = '  <path d="M0 14 20 4l20 10M0 22l20-10 20 10" fill="none" stroke="%s" stroke-opacity=".6" stroke-width="1"/>' % T.LINE
    return svg(40, 20, body)


PATTERNS = {'fan': pattern_fan, 'lattice': pattern_lattice, 'chevron': pattern_chevron}


# --- Empty-state illustrations --------------------------------------------------------------------

ILLUSTRATIONS = {'empty-library': 'mods', 'empty-inspection': 'inspector', 'empty-regions': 'servers',
                 'empty-crosshair': 'crosshair', 'empty-notes': 'file', 'empty-search': 'search'}


def illustration_svg(motif):
    """A motif on a cut-corner plate in front of a sunburst arch: one family for every empty state."""
    cx, base = 120, 128
    out = []
    for radius in range(40, 112, 18):
        out.append('<path d="M%s %sa%s %s 0 0 1 %s 0" fill="none" stroke="%s" stroke-width="1"/>' % (cx - radius, base, radius, radius, 2 * radius, T.LINE_STRONG))
    for index, angle in enumerate(range(180, 361, 12)):
        a = math.radians(angle)
        far = 118 if index % 2 == 0 else 112
        out.append('<path d="M%s %s L%s %s" fill="none" stroke="%s" stroke-width="1.5" stroke-opacity=".7"/>' % (
            n(cx + 102 * math.cos(a)), n(base + 102 * math.sin(a)), n(cx + far * math.cos(a)), n(base + far * math.sin(a)), T.BRASS_DEEP))
    out.append('<path d="M10 %s.5h220" fill="none" stroke="%s" stroke-width="1.5"/>' % (base, T.BRASS))
    out.append('<path d="M40 %s.5h160" fill="none" stroke="%s" stroke-width="1"/>' % (base + 6, T.BRASS_DEEP))
    for x in (10, 230):
        out.append('<path d="M%s %sl4 4-4 4-4-4z" fill="%s"/>' % (x, base - 3.5, T.BRASS))
    out.append('<path d="M98 52h44l10 10v44l-10 10H98l-10-10V62z" fill="%s" stroke="%s" stroke-width="1.5"/>' % (T.SURFACE, T.BRASS))
    out.append('<path d="M100 57h40l7 7v40l-7 7h-40l-7-7V64z" fill="none" stroke="%s" stroke-width="1"/>' % T.LINE_STRONG)
    out.append('<g transform="translate(99 63) scale(1.75)" fill="none" stroke="%s" color="%s" stroke-width=".95" stroke-linecap="square">\n%s\n  </g>' % (
        T.BRASS_BRIGHT, T.BRASS_BRIGHT, shapes(ICONS[motif], '    ')))
    return svg(240, 144, '\n'.join('  ' + part for part in out))


# --- Contrast -----------------------------------------------------------------------------------

def luminance(color):
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return sum(weight * (c / 12.92 if c <= .03928 else ((c + .055) / 1.055) ** 2.4) for weight, c in zip((.2126, .7152, .0722), channels))


def contrast(a, b):
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + .05) / (low + .05)


CONTRAST_PAIRS = [('TEXT', 'BASE'), ('TEXT', 'SURFACE'), ('TEXT', 'RAISED'), ('TEXT', 'BRASS_SHADE'), ('TEXT_SOFT', 'SURFACE'), ('TEXT_SOFT', 'BASE'),
                  ('TEXT_MUTED', 'SURFACE'), ('TEXT_MUTED', 'BASE'), ('TEXT_MUTED', 'SIDEBAR'), ('TEXT_MUTED', 'RAISED'), ('BRASS', 'SURFACE'), ('BRASS', 'BASE'),
                  ('BRASS_BRIGHT', 'BRASS_WASH'), ('BRASS_BRIGHT', 'BRASS_SHADE'), ('ON_BRASS', 'BRASS'), ('ON_BRASS', 'BRASS_BRIGHT'),
                  ('CRIMSON_TEXT', 'SURFACE'), ('CRIMSON_TEXT', 'CRIMSON_WASH'), ('TEXT', 'CRIMSON'), ('VERDIGRIS', 'SURFACE'), ('VERDIGRIS', 'VERDIGRIS_WASH'), ('AMBER', 'SURFACE')]


def contrast_table():
    rows = [(fg, bg, contrast(getattr(T, fg), getattr(T, bg))) for fg, bg in CONTRAST_PAIRS]
    for fg, bg, ratio in rows:
        print('%-13s on %-15s %5.2f:1  %s' % (fg, bg, ratio, 'AA' if ratio >= 4.5 else 'FAIL'))
    return all(ratio >= 4.5 for _, _, ratio in rows)


# --- Rendering ------------------------------------------------------------------------------------

def render(svg_text, width, height):
    from PySide6.QtCore import QByteArray, QRectF, Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer
    renderer = QSvgRenderer(QByteArray(svg_text.encode('utf-8')))
    assert renderer.isValid(), 'invalid SVG'
    image = QImage(width, height, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
    renderer.render(painter, QRectF(0, 0, width, height))
    painter.end()
    return image


def png_bytes(image):
    from PySide6.QtCore import QBuffer, QIODevice
    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    image.save(buffer, 'PNG')
    return bytes(buffer.data())


def ico_bytes(images):
    """A Windows .ico: 32-bit bitmaps for the small sizes and a PNG for 256px, as Explorer expects."""
    entries, blobs = [], []
    for image in images:
        size = image.width()
        if size >= 256:
            blob = png_bytes(image)
        else:
            pixels = image.convertToFormat(image.Format.Format_ARGB32)
            rows = [bytes(pixels.constScanLine(y))[:size * 4] for y in range(size - 1, -1, -1)]
            mask = b'\0' * (((size + 31) // 32) * 4 * size)
            blob = struct.pack('<IiiHHIIiiII', 40, size, size * 2, 1, 32, 0, size * size * 4 + len(mask), 0, 0, 0, 0) + b''.join(rows) + mask
        entries.append((size, blob))
    offset = 6 + 16 * len(entries)
    header = struct.pack('<HHH', 0, 1, len(entries))
    for size, blob in entries:
        header += struct.pack('<BBBBHHII', size % 256, size % 256, 0, 0, 1, 32, len(blob), offset)
        offset += len(blob)
        blobs.append(blob)
    return header + b''.join(blobs)


def write(path, data):
    """Write only when the content changed, so a second run leaves the tree untouched."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = data.encode('utf-8') if isinstance(data, str) else data
    if not path.exists() or path.read_bytes() != data:
        path.write_bytes(data)
    return path


def build():
    written = []
    for name in ICONS:
        written.append(write(ASSETS / 'icons' / (name + '.svg'), icon_svg(name)))
    for name, text in stylesheet_glyphs().items():
        written.append(write(ASSETS / 'icons/qss' / (name + '.svg'), text))
    written.append(write(ASSETS / 'brand/emblem.svg', emblem_svg()))
    written.append(write(ASSETS / 'app.svg', app_icon_svg()))
    written.append(write(ASSETS / 'brand/app-small.svg', app_icon_svg(False)))
    images = {size: render(app_icon_svg(size >= 48), size, size) for size in ICON_SIZES}
    for size, image in images.items():
        written.append(write(ASSETS / 'brand' / ('icon-%d.png' % size), png_bytes(image)))
    written.append(write(ASSETS / 'app.png', png_bytes(images[512])))
    written.append(write(ASSETS / 'app.ico', ico_bytes([images[size] for size in ICO_SIZES])))
    for motif, seed in BANNERS.items():
        written.append(write(ASSETS / 'art' / ('banner-%s.svg' % motif), banner_svg(motif, seed)))
    for name, make in PATTERNS.items():
        written.append(write(ASSETS / 'patterns' / (name + '.svg'), make()))
    for name, motif in ILLUSTRATIONS.items():
        written.append(write(ASSETS / 'illustrations' / (name + '.svg'), illustration_svg(motif)))
    return written


# --- Contact sheet -------------------------------------------------------------------------------

def contact_sheet(target):
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter, QPen, QPixmap
    for name in T.FONT_FILES:
        QFontDatabase.addApplicationFont(str(ASSETS / 'fonts' / name))
    width, height, margin = 1800, 2420, 48
    sheet = QImage(width, height, QImage.Format_ARGB32)
    sheet.fill(QColor(T.BASE))
    p = QPainter(sheet)
    p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)

    def font(stack, size, weight=400, spacing=0):
        f = QFont()
        f.setFamilies(list(stack))
        f.setPixelSize(size)
        f.setWeight(QFont.Weight(weight))
        if spacing:
            f.setLetterSpacing(QFont.AbsoluteSpacing, spacing)
        return f

    def text(x, y, value, stack=T.BODY, size=13, color=T.TEXT_SOFT, weight=400, spacing=0, w=900, align=Qt.AlignLeft):
        p.setFont(font(stack, size, weight, spacing))
        p.setPen(QColor(color))
        p.drawText(QRectF(x, y, w, size * 1.7), int(align | Qt.AlignVCenter), value)

    def heading(y, kicker, title):
        text(margin, y, kicker, T.BODY, 11, T.BRASS, 600, 3)
        text(margin, y + 20, title, T.DISPLAY, 24, T.TEXT, 600)
        p.setPen(QPen(QColor(T.BRASS_DEEP), 1))
        p.drawLine(margin, y + 66, width - margin, y + 66)
        return y + 84

    def draw(svg_text, x, y, w, h):
        p.drawImage(QRectF(x, y, w, h), render(svg_text, int(w * 2), int(h * 2)))

    text(margin, 34, 'DEADLOCK TOOLBOX  ·  ASSET CONTACT SHEET', T.BODY, 12, T.BRASS, 600, 4)
    text(margin, 58, 'Brass and ink', T.DISPLAY, 40, T.TEXT, 600)
    text(margin, 116, 'Original code-generated artwork from scripts/make_assets.py. Independent community utility; not affiliated with Valve.', T.BODY, 13, T.TEXT_MUTED)

    y = heading(170, '01  APP ICON', 'Keyhole and sunburst')
    x = margin
    for size in (256, 128, 64, 48, 32, 24, 16):
        p.drawImage(QRectF(x, y + (256 - size), size, size), render(app_icon_svg(size >= 48), size * 2, size * 2))
        text(x, y + 262, '%d px' % size, size=11, color=T.TEXT_MUTED, w=max(size, 60))
        x += size + 36
    draw(emblem_svg(), x + 30, y + 40, 200, 200)
    text(x + 30, y + 262, 'emblem.svg', size=11, color=T.TEXT_MUTED)
    draw(emblem_svg(T.TEXT), x + 280, y + 40, 200, 200)
    text(x + 280, y + 262, 'one-colour', size=11, color=T.TEXT_MUTED)

    y = heading(y + 312, '02  HEADER ARTWORK', 'Skyline banners')
    for index, motif in enumerate(BANNERS):
        bx, by = margin + (index % 2) * 864, y + (index // 2) * 184
        draw(banner_svg(motif, BANNERS[motif]), bx, by, 840, 157.5)
        p.setPen(QPen(QColor(T.LINE), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(QRectF(bx + .5, by + .5, 839, 156.5))
        text(bx + 560, by + 60, 'banner-%s.svg' % motif, size=11, color=T.TEXT_MUTED)

    y = heading(y + 392, '03  LINE ICONS', '24 px grid · 1.5 px stroke · square caps · mitred joins')
    names = list(ICONS)
    columns = 14
    cell = (width - 2 * margin) / columns
    for index, name in enumerate(names):
        cx, cy = margin + (index % columns) * cell, y + (index // columns) * 104
        p.setPen(QPen(QColor(T.LINE), 1))
        p.setBrush(QColor(T.SURFACE))
        p.drawRect(QRectF(cx + .5, cy + .5, cell - 12, 72))
        draw(icon_svg(name, T.BRASS_BRIGHT if index < 8 else T.BRASS), cx + (cell - 12) / 2 - 18, cy + 18, 36, 36)
        text(cx, cy + 76, name, size=11, color=T.TEXT_MUTED, w=cell - 12, align=Qt.AlignHCenter)
    rows = (len(names) + columns - 1) // columns
    gy = y + rows * 104
    gx = margin
    text(gx, gy, 'Stylesheet glyphs', size=11, color=T.TEXT_MUTED)
    for name, glyph in stylesheet_glyphs().items():
        p.setPen(QPen(QColor(T.LINE), 1))
        p.setBrush(QColor(T.BRASS if name == 'check' else T.SURFACE))
        p.drawRect(QRectF(gx + 150.5, gy + .5, 30, 30))
        draw(glyph, gx + 156, gy + 6, 18, 18)
        gx += 44

    y = heading(gy + 56, '04  PATTERNS', 'Fan · lattice · chevron')
    for index, (name, make) in enumerate(PATTERNS.items()):
        px = margin + index * 576
        tile = render(make(), *[int(v) * 2 for v in {'fan': (48, 48), 'lattice': (32, 32), 'chevron': (40, 20)}[name]])
        pixmap = QPixmap.fromImage(tile)
        pixmap.setDevicePixelRatio(2)
        p.fillRect(QRectF(px, y, 552, 150), QColor(T.SURFACE if index != 1 else T.SIDEBAR))
        p.drawTiledPixmap(QRectF(px, y, 552, 150), pixmap)
        text(px + 12, y + 122, name + '.svg', size=11, color=T.TEXT_SOFT)

    y = heading(y + 190, '05  EMPTY STATES', 'One plate, six subjects')
    for index, (name, motif) in enumerate(ILLUSTRATIONS.items()):
        ix = margin + index * 288
        p.fillRect(QRectF(ix, y, 264, 200), QColor(T.SURFACE))
        draw(illustration_svg(motif), ix + 12, y + 14, 240, 144)
        text(ix, y + 166, name + '.svg', size=11, color=T.TEXT_MUTED, w=264, align=Qt.AlignHCenter)

    y = heading(y + 240, '06  PALETTE AND TYPE', 'Ink, teal, aged brass, a restrained crimson')
    swatches = ['INK', 'BASE', 'SURFACE', 'RAISED', 'ACTIVE', 'LINE', 'LINE_STRONG', 'BRASS_DEEP', 'BRASS', 'BRASS_BRIGHT', 'TEXT', 'TEXT_SOFT', 'TEXT_MUTED', 'CRIMSON', 'CRIMSON_TEXT', 'VERDIGRIS']
    swatch = (width - 2 * margin) / len(swatches)
    for index, name in enumerate(swatches):
        sx = margin + index * swatch
        p.setPen(QPen(QColor(T.LINE_STRONG), 1))
        p.setBrush(QColor(getattr(T, name)))
        p.drawRect(QRectF(sx + .5, y + .5, swatch - 10, 64))
        text(sx, y + 68, name, size=10, color=T.TEXT_SOFT, w=swatch - 10)
        text(sx, y + 84, getattr(T, name), size=10, color=T.TEXT_MUTED, w=swatch - 10)
    y += 130
    text(margin, y, 'Reem Kufi', T.DISPLAY, 34, T.TEXT, 600, w=500)
    text(margin + 300, y, 'لعبتك، على طريقتك.', T.DISPLAY, 34, T.BRASS_BRIGHT, 600, w=520)
    text(margin + 840, y, 'Crosshair Designer  0123456789', T.DISPLAY, 34, T.TEXT, 500, w=900)
    y += 70
    text(margin, y, 'Noto Sans + Noto Sans Arabic', T.BODY, 16, T.TEXT, 600, w=500)
    text(margin + 300, y, 'أداء أخف. تجربة أقرب لك. كل أدواتك في مكان واحد.', T.BODY, 16, T.TEXT_SOFT, w=520)
    text(margin + 840, y, 'Preview, customize and apply. Review before every change.', T.BODY, 16, T.TEXT_SOFT, w=900)
    p.end()
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(str(target))
    return target


def readme_banner(target):
    """The README masthead: the emblem banner with the name and tagline set on its calm half."""
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPen
    for name in T.FONT_FILES:
        QFontDatabase.addApplicationFont(str(ASSETS / 'fonts' / name))
    image = render(banner_svg('emblem', BANNERS['emblem']), 1600, 300)
    p = QPainter(image)
    p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)

    def text(y, height, value, stack, size, color, weight=400, spacing=0):
        f = QFont()
        f.setFamilies(list(stack))
        f.setPixelSize(size)
        f.setWeight(QFont.Weight(weight))
        if spacing:
            f.setLetterSpacing(QFont.AbsoluteSpacing, spacing)
        p.setFont(f)
        p.setPen(QColor(color))
        p.drawText(QRectF(700, y, 840, height), int(Qt.AlignRight | Qt.AlignVCenter), value)

    text(40, 24, 'COMMUNITY TOOL  ·  WINDOWS + LINUX', T.BODY, 13, T.BRASS, 600, 4)
    text(66, 92, 'Deadlock Toolbox', T.DISPLAY, 76, T.TEXT, 600)
    p.setPen(QPen(QColor(T.BRASS_DEEP), 1.5))
    p.drawLine(1180, 166, 1540, 166)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(T.BRASS))
    p.drawPolygon([__import__('PySide6.QtCore', fromlist=['QPointF']).QPointF(x, y) for x, y in ((1540, 160), (1546, 166), (1540, 172), (1534, 166))])
    text(178, 44, 'خلّ Deadlock أخف، واضبطها على ذوقك.', T.BODY, 26, T.TEXT_SOFT, 500)
    text(222, 26, 'Independent project. Not affiliated with Valve.', T.BODY, 13, T.TEXT_MUTED)
    p.end()
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(str(target))
    return target


def main():
    if '--contrast' in sys.argv:
        sys.exit(0 if contrast_table() else 1)
    from PySide6.QtGui import QGuiApplication
    app = QGuiApplication.instance() or QGuiApplication([])
    written = build()
    sheet = contact_sheet(ROOT / 'docs/contact-sheet.png')
    print('readme banner: %s' % readme_banner(ROOT / 'docs/banner.png'))
    print('%d assets in %s' % (len(written), ASSETS))
    print('contact sheet: %s' % sheet)
    del app


if __name__ == '__main__':
    main()
