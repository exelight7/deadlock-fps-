"""Photograph the static redesign prototype (docs/design-prototype) with Qt WebEngine.

    .venv/Scripts/python.exe scripts/dev/design_shots.py            the reference set into docs/design-prototype/shots
    .venv/Scripts/python.exe scripts/dev/design_shots.py OUT name=page=mods&tab=health&state=error&lang=ar ...

A job is `name=fragment`; the fragment is what follows `#` in the prototype's address (page, tab, state, lang, theme,
accent, size, over). `components` as the fragment's first word photographs components.html instead.
"""
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'docs' / 'design-prototype'
VIEWS = ['home', 'mods&tab=browse', 'mods&tab=installed', 'mods&tab=health', 'mods&tab=activity',
         'performance&tab=level', 'performance&tab=all', 'stats&tab=heroes', 'stats&tab=ranks', 'stats&tab=me',
         'crosshair', 'servers', 'backups', 'settings&tab=general', 'settings&tab=game', 'settings&tab=update',
         'settings&tab=sources', 'map']


def reference():
    jobs = []
    for view in VIEWS:
        name = view.replace('&tab=', '-')
        jobs.append((name + '.en-dark', 'page=' + view))
        jobs.append((name + '.ar-light', 'page=' + view + '&lang=ar&theme=light'))
    jobs += [('home.empty', 'page=home&state=empty'), ('mods-browse.empty', 'page=mods&tab=browse&state=empty'),
             ('mods-browse.loading', 'page=mods&tab=browse&state=loading'), ('mods-browse.error', 'page=mods&tab=browse&state=error'),
             ('stats-heroes.empty', 'page=stats&tab=heroes&state=empty'), ('performance-level.error', 'page=performance&state=error'),
             ('overlay-mod', 'page=mods&tab=browse&over=mod'), ('overlay-review', 'page=mods&tab=browse&over=review'),
             ('overlay-apply.ar-light', 'page=performance&over=apply&lang=ar&theme=light'),
             ('minimum-window.ar', 'page=mods&tab=installed&size=min&lang=ar'),
             ('components.en-dark', 'components'), ('components.ar-light', 'components&lang=ar&theme=light')]
    return jobs


def main():
    custom = len(sys.argv) > 2
    out = Path(sys.argv[1]) if custom else SOURCE / 'shots'
    jobs = [tuple(a.split('=', 1)) for a in sys.argv[2:]] if custom else reference()
    out.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv[:1] + ['--disable-gpu'])
    view = QWebEngineView()
    view.setAttribute(Qt.WA_DontShowOnScreen, True)
    position = {'index': -1}

    def advance():
        position['index'] += 1
        if position['index'] >= len(jobs):
            print('%d pictures in %s' % (len(jobs), out))
            app.quit()
            return
        name, fragment = jobs[position['index']]
        gallery = fragment.startswith('components')
        fragment = fragment.replace('components&', '').replace('components', '')
        view.resize(*((1040, 2700) if gallery else (940, 680) if 'size=min' in fragment else (1180, 760)))
        url = QUrl.fromLocalFile(str(SOURCE / ('components.html' if gallery else 'index.html')))
        url.setFragment(fragment + ('' if gallery else '&shot=1'))
        view.load(QUrl('about:blank'))
        QTimer.singleShot(150, lambda: view.load(url))
        QTimer.singleShot(1500, lambda: (view.grab().save(str(out / (name + '.png'))), advance()))

    view.show()
    QTimer.singleShot(0, advance)
    app.exec()


if __name__ == '__main__':
    main()
