"""Interface language: English by default, Arabic as the second language.

Strings in the code are written in the language their module was born in
(Arabic for most of the app, English for the crosshair workspace) and pass
through `tr()`. `LANGUAGE` picks the catalogue:

    'en'      Arabic source strings are shown in English
    'ar'      English source strings are shown in Arabic
    'source'  nothing is translated (tests and tools read the code's own text)

`load()` runs once in main.py, before any interface module is imported,
because many strings are built at import time. Changing the language in
Settings therefore takes effect after a restart.
"""
import json
from pathlib import Path

LANGUAGES = {'en': 'English', 'ar': 'العربية'}
LANGUAGE = 'source'
_catalogue = {}


def tr(text):
    """Translate one source string (or template) for the active language; unknown text is returned unchanged."""
    return _catalogue.get(text, text)


def rtl():
    return LANGUAGE == 'ar' or (LANGUAGE == 'source')


def activate(code):
    """Switch catalogue. Only strings built after this call are affected."""
    global LANGUAGE, _catalogue
    LANGUAGE = code if code in LANGUAGES else 'source'
    if LANGUAGE == 'en':
        from .lang_en import TEXT
    elif LANGUAGE == 'ar':
        from .lang_ar import TEXT
    else:
        TEXT = {}
    _catalogue = TEXT


def system_language():
    try:
        from PySide6.QtCore import QLocale
        return 'ar' if QLocale.system().language() == QLocale.Language.Arabic else 'en'
    except Exception:
        return 'en'


def preferred(preferences_file):
    """The saved choice, or the system language when it is Arabic, otherwise English."""
    try:
        saved = json.loads(Path(preferences_file).read_text(encoding='utf-8')).get('language')
        if saved in LANGUAGES:
            return saved
    except (OSError, ValueError, AttributeError):
        pass
    return system_language()


def load():
    """Called by main.py before the interface is imported."""
    from PySide6.QtCore import QCoreApplication, QStandardPaths
    QCoreApplication.setOrganizationName('exelight7')
    QCoreApplication.setApplicationName('DeadlockToolbox')
    activate(preferred(Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / 'workspace.json'))
    return LANGUAGE
