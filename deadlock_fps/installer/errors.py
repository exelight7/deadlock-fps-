"""Errors of the installation engine. `code` is stable (the interface translates it); `message` is for logs and details."""


class InstallError(Exception):
    def __init__(self, code, message=''):
        super().__init__(message or code)
        self.code = code
        self.message = message or code

    def __str__(self):
        return self.message


# Codes
NO_GAME = 'no-game'                  # no valid Deadlock folder
GAME_RUNNING = 'game-running'        # the game must be closed first
NOT_INSTALLABLE = 'not-installable'  # yanked, unsupported format, no package
DOWNLOAD = 'download'                # transfer failed
HASH_MISMATCH = 'hash-mismatch'      # downloaded bytes differ from the published SHA-256
SIZE_MISMATCH = 'size-mismatch'
BAD_PACKAGE = 'bad-package'          # archive or VPK failed inspection
DISK = 'disk'                        # not enough free space or a write failed
BLOCKED = 'blocked'                  # dependency missing or declared conflict
ACK_REQUIRED = 'ack-required'        # the user must acknowledge warnings first
VERIFY = 'verify'                    # installed files did not verify; rolled back
STALE = 'stale-plan'                 # staged files changed after the preview
NOT_FOUND = 'not-found'              # no such installed mod
IN_USE = 'in-use'                    # other mods depend on it
CANCELLED = 'cancelled'
JOURNAL = 'journal'                  # an interrupted installation needs recovery
