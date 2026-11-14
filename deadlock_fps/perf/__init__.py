"""Performance knowledge: what each graphics setting does, and whether Valve's data says the game applies it. Qt-free.

    explain(settings)   every setting a level writes, with its meaning and status (the "What does this level change?" window)
    ignored_names()     the settings the game should ignore, so the user can leave them out
    facts.py            GENERATED from Valve's data by scripts/dev/perf_facts.py (names, flags, defaults)
    knowledge.py        the explanations, written for this project
"""
from .explain import explain, ignored_names, Item, Report
from .knowledge import ENTRIES, CATEGORIES, STATUS_LABELS, STATUS_TEXT, PROTECTED, Entry
from .facts import CONVAR_BUILD, STOCK_BUILD, CHECKED_ON
