"""Plain sentences for what the installer and the mod service report when something does not work.

This file used to hold the Mod Hub page. The page now lives in Mods > Browse (`pages/sources.py`, "My sources"); what stayed is the
one table every mod page shares: an engine failure code in, one plain sentence out.
"""
from .i18n import tr


def failure_text(code, message):
    """One plain sentence for an engine failure, with the engine's own detail after it."""
    lead = {
        'game-running': tr('Close Deadlock first, then try again.'),
        'no-game': tr('Link your Deadlock folder on the Home page first.'),
        'hash-mismatch': tr('The download did not match the checksum in the source, so it was thrown away.'),
        'download': tr('The download failed.'),
        'bad-package': tr('The package did not pass inspection, so nothing was installed.'),
        'disk': tr('There is not enough disk space or the disk could not be written.'),
        'blocked': tr('This cannot be installed right now.'),
        'ack-required': tr('Please read and acknowledge the warnings first.'),
        'verify': tr('The files did not verify after copying, so everything was put back as it was.'),
        'stale-plan': tr('Something changed since the preview, so nothing was installed. Please try again.'),
        'not-installable': tr('This version cannot be installed.'),
        'in-use': tr('Other installed mods need this one.'),
        'cancelled': tr('Cancelled. Nothing was changed.'),
        'journal': tr('An earlier operation was interrupted and needs recovery. Restart Toolbox.'),
        'gameinfo': tr('Deadlock\'s gameinfo.gi could not be prepared.'),
        'not-found': tr('That is no longer available.'),
    }.get(code, tr('Something went wrong.'))
    return lead if code in ('cancelled', 'game-running', 'no-game', 'ack-required') else lead + '\n' + message
