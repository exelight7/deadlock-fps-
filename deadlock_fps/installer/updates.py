"""Which installed mods have a newer version in their own repository?

Pure comparison of installed records against the catalogues the Repository Manager already holds, so it works offline.
A mod is only ever updated from the repository it was installed from: the same mod id in another repository is a
different source with a different trust label and is never substituted silently.
"""
from dataclasses import dataclass

from ..repos.compat import fit
from ..repos.errors import RepoError
from ..repos.model import GameFit
from ..repos.versions import Version


@dataclass(frozen=True)
class UpdateStatus:
    mod: object                      # InstalledMod
    state: str                       # 'current' | 'update' | 'ahead' | 'unavailable'
    latest: str = ''
    version: object = None           # the repository's ModVersion for `latest`
    catalogue_mod: object = None
    repository: object = None        # RepositoryView
    fit: GameFit = GameFit.UNKNOWN
    note: str = ''

    @property
    def updatable(self):
        """Offer the update: newer, installable, and not known to be incompatible with the installed game."""
        return self.state == 'update' and self.version is not None and self.version.installable and self.fit is not GameFit.INCOMPATIBLE


STORE_PREFIX = 'store:'                  # repository ids of mods installed from the Mod Store (they have no repository in the manager)


def update_status(installed, manager, game_build=None):
    """One UpdateStatus per installed mod."""
    result = []
    for mod in installed:
        if mod.repository_id.startswith(STORE_PREFIX):
            result.append(UpdateStatus(mod, 'unavailable', note='Installed from the Mod Store. Updates for store mods are not checked yet: open the mod in the store and install it again.'))
            continue
        try:
            found = manager.find_mod(mod.repository_id, mod.mod_id)
        except RepoError:
            found = None
        if found is None:
            result.append(UpdateStatus(mod, 'unavailable', note='Its repository was removed or no longer lists this mod.'))
            continue
        view, catalogue = found
        if not view.source.enabled:
            result.append(UpdateStatus(mod, 'unavailable', repository=view, catalogue_mod=catalogue, note='Its repository is disabled.'))
            continue
        latest = catalogue.latest()
        if latest is None:
            result.append(UpdateStatus(mod, 'unavailable', repository=view, catalogue_mod=catalogue, note='The repository offers no stable version.'))
            continue
        try:
            installed_version = Version.parse(mod.version)
        except RepoError:
            installed_version = None
        game_fit = fit(latest.game, game_build)
        if installed_version is None or latest.version > installed_version:
            note = latest.unsupported_reason or ('The newest version is not known to fit this game build.' if game_fit is GameFit.INCOMPATIBLE else '')
            result.append(UpdateStatus(mod, 'update', latest.version.text, latest, catalogue, view, game_fit, note))
        elif latest.version == installed_version:
            result.append(UpdateStatus(mod, 'current', latest.version.text, latest, catalogue, view, fit(latest.game, game_build)))
        else:
            result.append(UpdateStatus(mod, 'ahead', latest.version.text, latest, catalogue, view, fit(latest.game, game_build), 'The installed version is newer than the repository offers.'))
    return result
