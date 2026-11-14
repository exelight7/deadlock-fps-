"""Does a mod version fit the installed game build?

Deadlock builds are the Steam build id (an integer that only grows). A mod
version may declare the range it supports and the build it was tested on.
When the game build or the declaration is missing the answer is UNKNOWN, never
a guess in either direction.
"""
from .model import GameFit


def fit(game_support, build):
    """GameFit of `game_support` (a GameSupport) against `build` (int or None)."""
    if build is None:
        return GameFit.UNKNOWN
    low, high, tested = game_support.min_build, game_support.max_build, game_support.tested_build
    if low is None and high is None and tested is None:
        return GameFit.UNKNOWN
    if low is not None and build < low:
        return GameFit.INCOMPATIBLE
    if high is not None and build > high:
        return GameFit.INCOMPATIBLE
    if high is not None or (tested is not None and build <= tested):
        return GameFit.COMPATIBLE
    # A lower bound (or an older test) with no upper bound: it may still work, but nobody has said so.
    return GameFit.UNTESTED
