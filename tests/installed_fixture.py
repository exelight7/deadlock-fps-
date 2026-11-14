"""Helper for screenshots and demos: install a couple of mods into a throwaway game through the real engine."""
from installer_fixtures import view


def install_all(installer, manager):
    """Install crimson-skin 1.0.0 (so 1.2.0 is an update) and clean-hud 0.9.0 from the first repository."""
    repository = manager.list()[0]
    for ident, wanted in (('crimson-skin', '1.0.0'), ('clean-hud', '0.9.0')):
        found = manager.find_mod(repository.source.id, ident)
        mod = found[1]
        plan = installer.prepare(found[0], mod, mod.find(wanted))
        installer.commit(plan, acknowledged=True)
