"""What a graphics level writes, explained. The list behind the "What does this level change?" window. Qt-free.

`explain(settings)` returns every setting the level would write (and the ones the user chose to leave out), each with
what Toolbox writes, where it goes, what the setting controls, and whether Valve's data says the game applies it.
"""
from dataclasses import dataclass, replace

from ..i18n import tr
from ..settings import values
from .knowledge import ENTRIES, CATEGORIES, Entry, ACTIVE, CHEAT, UNVERIFIED, IGNORED

_ORDER = {name: position for position, name in enumerate(CATEGORIES)}


@dataclass(frozen=True)
class Item:
    name: str
    value: str          # what Toolbox writes
    where: str          # 'gameinfo.gi', 'video.txt' or 'both'
    entry: Entry
    skipped: bool       # the user left it out: it is not written anywhere


@dataclass(frozen=True)
class Report:
    items: tuple
    written: int        # settings that would be written
    ignored: int        # of those, the ones Valve's data says the game ignores (removed or blocked)
    uncertain: int      # of those, cheat-only or unverified: the effect cannot be confirmed
    sight: int          # of those, the ones that can change how much of the world you can see
    left_out: int       # settings the user chose not to write

    @property
    def confirmed(self):
        return self.written - self.ignored - self.uncertain


def _entry(name):
    known = ENTRIES.get(name)
    if known is not None:
        return known
    # A setting added to the recipe without an explanation yet: shown honestly instead of crashing the window.
    return Entry(name, 'screen', tr('(no explanation written yet)'), UNVERIFIED, 0, '', False)


def explain(settings):
    """Every setting `settings` would write, plus those it leaves out, grouped by category and sorted by name."""
    video, convars, scene = values(replace(settings, skip=()))        # the whole level, before anything is left out
    left_out = set(settings.skip)
    found = {}
    for name, value in convars.items():
        found[name] = [value, 'gameinfo.gi']
    for name, value in scene.items():
        found[name] = [value, 'gameinfo.gi']
    for key, value in video.items():
        name = key.removeprefix('setting.')
        if name in found:
            found[name][1] = 'both'
        else:
            found[name] = [value, 'video.txt']
    items = [Item(name, value, where, _entry(name), name in left_out) for name, (value, where) in found.items()]
    items.sort(key=lambda i: (_ORDER.get(i.entry.category, 99), i.name.lower()))
    live = [i for i in items if not i.skipped]
    return Report(
        items=tuple(items), written=len(live),
        ignored=sum(1 for i in live if i.entry.status in IGNORED),
        uncertain=sum(1 for i in live if i.entry.status in (CHEAT, UNVERIFIED)),
        sight=sum(1 for i in live if i.entry.sight),
        left_out=len(items) - len(live))


def ignored_names(settings):
    """The settings this level writes that Valve's data says the game ignores, minus the ones with their own controls."""
    return tuple(i.name for i in explain(settings).items if i.entry.status in IGNORED and not i.entry.protected)
