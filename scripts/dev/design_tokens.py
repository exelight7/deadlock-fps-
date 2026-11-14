"""Phase 1 design tokens: one source, three outputs (tokens.json, tokens.css, a Markdown table) and a contrast report.

Usage: .venv/Scripts/python.exe scripts/dev/design_tokens.py [--write]

Prints every colour pair that fails its contrast minimum. --write regenerates docs/design-prototype/tokens.css and
tokens.json and prints the Markdown tables used in vault/Design/New Design/03 Visual Language.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs' / 'design-prototype'

# name: (dark, light)
COLOR = {
    'color.bg.app':            ('#0F1115', '#F4F5F7'),
    'color.bg.sidebar':        ('#0A0C0F', '#EBEDF1'),
    'color.bg.surface':        ('#171A20', '#FFFFFF'),
    'color.bg.raised':         ('#1F232B', '#FFFFFF'),
    'color.bg.sunken':         ('#0C0E12', '#ECEEF2'),
    'color.bg.hover':          ('#222733', '#E9ECF1'),
    'color.bg.pressed':        ('#2A3040', '#DEE2E9'),
    'color.bg.selected':       ('#1B2440', '#E3EBFF'),
    'color.bg.scrim':          ('#000000A6', '#14171C73'),
    'color.border.subtle':     ('#232833', '#E2E5EA'),
    'color.border.default':    ('#303646', '#D2D6DE'),
    'color.border.control':    ('#6F788B', '#7B8290'),
    'color.border.focus':      ('#8FB0FF', '#1D4FD8'),
    'color.text.primary':      ('#ECEEF2', '#14171C'),
    'color.text.secondary':    ('#B0B7C3', '#454C5A'),
    'color.text.muted':        ('#8B93A2', '#5F6877'),
    'color.text.disabled':     ('#596070', '#A0A6B2'),
    'color.text.on-accent':    ('#FFFFFF', '#FFFFFF'),
    'color.text.link':         ('#8FB0FF', '#1D4FD8'),
    'color.accent.fill':       ('#2F62EA', '#2459E0'),
    'color.accent.fill-hover': ('#3866EA', '#1D4FD8'),
    'color.accent.fill-pressed': ('#2553D0', '#1843BD'),
    'color.accent.text':       ('#8FB0FF', '#1D4FD8'),
    'color.accent.tint':       ('#1B2440', '#E3EBFF'),
    'color.success.text':      ('#58D394', '#136C41'),
    'color.success.tint':      ('#11261C', '#E2F5EA'),
    'color.success.border':    ('#1F5A3D', '#9FD8B8'),
    'color.warning.text':      ('#F0C24F', '#7A5200'),
    'color.warning.tint':      ('#2A2310', '#FFF3D1'),
    'color.warning.border':    ('#6B5518', '#E5C566'),
    'color.danger.text':       ('#FF8585', '#B02020'),
    'color.danger.tint':       ('#2D1417', '#FDE7E7'),
    'color.danger.border':     ('#7A2A30', '#EDA5A5'),
    'color.danger.fill':       ('#C92F2F', '#C62828'),
    'color.danger.fill-hover': ('#D03838', '#B02020'),
    'color.info.text':         ('#8FB0FF', '#1D4FD8'),
    'color.info.tint':         ('#1B2440', '#E3EBFF'),
    'color.info.border':       ('#2E4690', '#A9C0FA'),
    'color.shadow':            ('#00000080', '#14171C29'),
}

# Optional accents the user may pick instead of blue (same slots, dark/light).
ACCENTS = {
    'blue':   {},
    'violet': {'color.accent.fill': ('#6D4FE0', '#5B3FD0'), 'color.accent.fill-hover': ('#7558E4', '#4E34BC'),
               'color.accent.fill-pressed': ('#5C40C8', '#4029A3'), 'color.accent.text': ('#B3A2FF', '#5235C4'),
               'color.accent.tint': ('#231C40', '#ECE7FF'), 'color.bg.selected': ('#231C40', '#ECE7FF'),
               'color.border.focus': ('#B3A2FF', '#5235C4'), 'color.text.link': ('#B3A2FF', '#5235C4')},
    'orange': {'color.accent.fill': ('#C2470A', '#B8430A'), 'color.accent.fill-hover': ('#C94C0C', '#A33A07'),
               'color.accent.fill-pressed': ('#A93C06', '#8C3105'), 'color.accent.text': ('#FF9C66', '#A33A07'),
               'color.accent.tint': ('#33190B', '#FFE9DC'), 'color.bg.selected': ('#33190B', '#FFE9DC'),
               'color.border.focus': ('#FF9C66', '#A33A07'), 'color.text.link': ('#FF9C66', '#A33A07')},
}

# name: value (same in both themes)
SCALE = {
    'space.1': '4px', 'space.2': '8px', 'space.3': '12px', 'space.4': '16px', 'space.5': '20px',
    'space.6': '24px', 'space.8': '32px', 'space.10': '40px', 'space.12': '48px',
    'radius.sm': '6px', 'radius.md': '10px', 'radius.lg': '14px', 'radius.pill': '999px',
    'size.control.sm': '28px', 'size.control.md': '36px', 'size.control.lg': '44px',
    'size.icon.sm': '16px', 'size.icon.md': '20px', 'size.icon.lg': '24px',
    'size.sidebar': '216px', 'size.sidebar.collapsed': '64px', 'size.topbar': '56px',
    'size.content.max': '1120px', 'size.sheet': '420px', 'size.dialog.sm': '440px', 'size.dialog.md': '600px',
    'size.window.min-width': '940px', 'size.window.min-height': '680px',
    'border.width': '1px', 'border.width.focus': '2px',
    'font.family.ui': "'IBM Plex Sans Arabic', 'IBM Plex Sans', 'Noto Sans Arabic', 'Noto Sans', 'Segoe UI', sans-serif",
    'font.family.mono': "'IBM Plex Mono', 'Cascadia Mono', Consolas, monospace",
    'font.size.caption': '12px', 'font.size.body': '14px', 'font.size.body-sm': '13px',
    'font.size.subtitle': '16px', 'font.size.title': '20px', 'font.size.display': '28px',
    'font.weight.regular': '400', 'font.weight.medium': '500', 'font.weight.semibold': '600',
    'font.line.tight': '1.25', 'font.line.body': '1.5', 'font.line.arabic': '1.7',
    'motion.fast': '120ms', 'motion.base': '180ms', 'motion.slow': '260ms',
    'motion.ease': 'cubic-bezier(0.2, 0, 0, 1)',
    'shadow.popover': '0 8px 24px', 'shadow.dialog': '0 20px 56px',
    'scale.options': '90, 100, 115, 130',
}


def var(name):
    return '--' + name.replace('.', '-')


def rgb(value):
    value = value.lstrip('#')[:6]
    return tuple(int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))


def luminance(value):
    parts = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb(value)]
    return 0.2126 * parts[0] + 0.7152 * parts[1] + 0.0722 * parts[2]


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# (foreground, background, minimum, what)
PAIRS = [
    ('color.text.primary', 'color.bg.app', 4.5, 'body text on the window'),
    ('color.text.primary', 'color.bg.surface', 4.5, 'body text on a card'),
    ('color.text.secondary', 'color.bg.surface', 4.5, 'descriptions on a card'),
    ('color.text.secondary', 'color.bg.app', 4.5, 'descriptions on the window'),
    ('color.text.muted', 'color.bg.surface', 4.5, 'captions on a card'),
    ('color.text.muted', 'color.bg.app', 4.5, 'captions on the window'),
    ('color.text.muted', 'color.bg.sidebar', 4.5, 'captions on the sidebar'),
    ('color.text.muted', 'color.bg.hover', 4.5, 'captions on a hovered row'),
    ('color.text.primary', 'color.bg.selected', 4.5, 'text on a selected row'),
    ('color.text.secondary', 'color.bg.sunken', 4.5, 'placeholder in a field'),
    ('color.text.on-accent', 'color.accent.fill', 4.5, 'primary button label'),
    ('color.text.on-accent', 'color.accent.fill-hover', 4.5, 'primary button label, hover'),
    ('color.text.on-accent', 'color.danger.fill', 4.5, 'danger button label'),
    ('color.text.on-accent', 'color.danger.fill-hover', 4.5, 'danger button label, hover'),
    ('color.accent.text', 'color.bg.surface', 4.5, 'link on a card'),
    ('color.accent.text', 'color.bg.app', 4.5, 'link on the window'),
    ('color.accent.text', 'color.accent.tint', 4.5, 'selected nav label'),
    ('color.success.text', 'color.success.tint', 4.5, 'success badge'),
    ('color.success.text', 'color.bg.surface', 4.5, 'success text on a card'),
    ('color.warning.text', 'color.warning.tint', 4.5, 'warning badge'),
    ('color.warning.text', 'color.bg.surface', 4.5, 'warning text on a card'),
    ('color.danger.text', 'color.danger.tint', 4.5, 'danger badge'),
    ('color.danger.text', 'color.bg.surface', 4.5, 'danger text on a card'),
    ('color.info.text', 'color.info.tint', 4.5, 'info badge'),
    ('color.border.control', 'color.bg.surface', 3.0, 'field and checkbox outline on a card'),
    ('color.border.control', 'color.bg.app', 3.0, 'field and checkbox outline on the window'),
    ('color.border.control', 'color.bg.sunken', 3.0, 'field outline on its own fill'),
    ('color.border.focus', 'color.bg.surface', 3.0, 'focus ring on a card'),
    ('color.border.focus', 'color.bg.app', 3.0, 'focus ring on the window'),
    ('color.accent.fill', 'color.bg.surface', 3.0, 'slider fill, switch on, progress'),
]


def themed(accent, index):
    values = {name: pair[index] for name, pair in COLOR.items()}
    values.update({name: pair[index] for name, pair in ACCENTS[accent].items()})
    return values


def report():
    lines, failed = [], 0
    for accent in ACCENTS:
        for index, theme in enumerate(('dark', 'light')):
            values = themed(accent, index)
            for fg, bg, minimum, what in PAIRS:
                if accent != 'blue' and not any(n in ACCENTS[accent] for n in (fg, bg)):
                    continue
                ratio = contrast(values[fg], values[bg])
                ok = ratio >= minimum
                failed += not ok
                lines.append((accent, theme, fg, bg, ratio, minimum, what, ok))
    return lines, failed


def css():
    out = ['/* Generated from the Phase 1 token list (vault/Design/New Design/03 Visual Language). Do not edit by hand. */',
           ':root {']
    out += ['  %s: %s;' % (var(n), v) for n, v in SCALE.items()]
    out.append('}')
    for index, theme in enumerate(('dark', 'light')):
        out.append(':root[data-theme="%s"] {' % theme)
        out += ['  %s: %s;' % (var(n), pair[index]) for n, pair in COLOR.items()]
        out.append('}')
        for accent, change in ACCENTS.items():
            if change:
                out.append(':root[data-theme="%s"][data-accent="%s"] {' % (theme, accent))
                out += ['  %s: %s;' % (var(n), pair[index]) for n, pair in change.items()]
                out.append('}')
    return '\n'.join(out) + '\n'


def document():
    return json.dumps({
        'version': 1,
        'note': 'Deadlock Toolbox redesign tokens (Phase 1). Colours are #RRGGBB or #RRGGBBAA.',
        'themes': {theme: {n: pair[i] for n, pair in COLOR.items()} for i, theme in enumerate(('dark', 'light'))},
        'accents': {accent: {theme: {n: pair[i] for n, pair in change.items()}
                             for i, theme in enumerate(('dark', 'light'))} for accent, change in ACCENTS.items()},
        'scale': SCALE,
    }, indent=2, ensure_ascii=False) + '\n'


def tables():
    out = ['| Token | Dark | Light |', '|---|---|---|']
    out += ['| `%s` | `%s` | `%s` |' % (n, d, l) for n, (d, l) in COLOR.items()]
    out += ['', '| Token | Value |', '|---|---|']
    out += ['| `%s` | `%s` |' % (n, v) for n, v in SCALE.items()]
    lines, _ = report()
    out += ['', '| Accent | Theme | Pair | Ratio | Needs | Used for |', '|---|---|---|---|---|---|']
    out += ['| %s | %s | `%s` on `%s` | %.2f | %.1f | %s |' % (a, t, fg, bg, r, m, w) for a, t, fg, bg, r, m, w, _ in lines]
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    lines, failed = report()
    for a, t, fg, bg, r, m, w, ok in lines:
        if not ok:
            print('FAIL %-6s %-5s %.2f < %.1f  %s on %s (%s)' % (a, t, r, m, fg, bg, w))
    print('%d pairs, %d failed, lowest %.2f' % (len(lines), failed, min(l[4] - l[5] for l in lines)))
    if '--write' in sys.argv:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / 'tokens.css').write_bytes(css().encode('utf-8'))
        (OUT / 'tokens.json').write_bytes(document().encode('utf-8'))
        sys.stdout.reconfigure(encoding='utf-8')
        print(tables())

