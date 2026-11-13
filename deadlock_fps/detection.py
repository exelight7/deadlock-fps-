"""Is Deadlock on this machine? One read-only answer for the interface.

`core.detect_games()` finds candidate folders (Steam registry, every Steam
library, common folders on every drive, the running game). This module turns
that into a state the interface can explain: installed, still downloading,
Steam present but the game missing, or no Steam at all. Nothing here writes.
"""
from dataclasses import dataclass
from pathlib import Path
import re
import psutil
from .core import steam_roots, steam_libraries, GAME_PROCESSES

APP_ID = '1422450'
INSTALL_URL = 'steam://install/' + APP_ID
STORE_URL = 'https://store.steampowered.com/app/' + APP_ID


@dataclass(frozen=True)
class GameStatus:
    state: str                 # 'installed' | 'updating' | 'missing' | 'no_steam'
    path: Path | None = None
    build: str = ''
    size: int = 0              # bytes on disk, from the Steam manifest
    running: bool = False
    libraries: int = 0         # Steam libraries that were searched

    @property
    def found(self):
        return self.path is not None


def manifest(root):
    """Fields of Steam's appmanifest for a game folder, or {} when it is not a Steam install."""
    try:
        text = (Path(root).parent.parent / ('appmanifest_%s.acf' % APP_ID)).read_text(encoding='utf-8', errors='replace')
    except OSError:
        return {}
    return dict(re.findall(r'^\s*"(\w+)"\s+"([^"]*)"\s*$', text, re.MULTILINE))


def game_running():
    try:
        return any((p.info['name'] or '').lower() in GAME_PROCESSES for p in psutil.process_iter(['name']))
    except psutil.Error:
        return False


def pending_download():
    """True when a Steam library lists the game in its manifest but the files are not there yet."""
    for library in steam_libraries():
        if (library / ('steamapps/appmanifest_%s.acf' % APP_ID)).is_file():
            return True
    return False


def scan(games):
    """Describe the result of `core.detect_games()` (passed in, so callers and tests control the search)."""
    running = game_running()
    libraries = len(steam_libraries())
    if games:
        root = Path(games[0])
        fields = manifest(root)
        size = int(fields['SizeOnDisk']) if fields.get('SizeOnDisk', '').isdigit() else 0
        # StateFlags 4 is "fully installed"; anything else means Steam is still downloading or patching.
        state = 'updating' if fields.get('StateFlags', '4') != '4' else 'installed'
        return GameStatus(state, root, fields.get('buildid', ''), size, running, libraries)
    if not steam_roots():
        return GameStatus('no_steam', running=running)
    return GameStatus('updating' if pending_download() else 'missing', running=running, libraries=libraries)
