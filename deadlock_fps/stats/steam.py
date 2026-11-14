"""Steam account numbers.

Deadlock's statistics are keyed by the 32-bit account number (the folder name under Steam's `userdata`). People know
three other spellings of the same thing, and this module turns all of them into the 32-bit number:

    123456789                                       the number itself
    76561198083722517                               the 64-bit SteamID (the number plus 76561197960265728)
    [U:1:123456789]                                 the bracket form
    https://steamcommunity.com/profiles/7656119...  a profile address with the 64-bit id

A vanity address (steamcommunity.com/id/name) cannot be turned into a number without asking Steam, so it is refused with
a message that says how to find the number. Nothing here touches the network.
"""
import re
from urllib.parse import urlsplit

STEAM64_BASE = 76561197960265728
MAX_ACCOUNT = 0xFFFFFFFF


class SteamIdError(ValueError):
    """`code` is one of: empty, vanity, format, range."""

    def __init__(self, code, message=''):
        super().__init__(message or code)
        self.code = code


def _checked(number):
    if not 1 <= number <= MAX_ACCOUNT:
        raise SteamIdError('range', 'an account number is between 1 and %d' % MAX_ACCOUNT)
    return number


def account_id(value):
    """The 32-bit account number for any of the spellings above, or SteamIdError."""
    text = str(value if value is not None else '').strip()
    if not text:
        raise SteamIdError('empty')
    bracket = re.fullmatch(r'\[U:1:(\d{1,10})\]', text)
    if bracket:
        return _checked(int(bracket.group(1)))
    if '/' in text or '.' in text or ':' in text:
        address = text if '//' in text else 'https://' + text
        try:
            parts = urlsplit(address)
            host = (parts.hostname or '').lower()
        except ValueError:
            raise SteamIdError('format', 'this is not an account number or a steamcommunity.com address') from None
        if parts.scheme not in ('http', 'https') or host not in ('steamcommunity.com', 'www.steamcommunity.com'):
            raise SteamIdError('format', 'only a steamcommunity.com profile address is understood')
        segments = [s for s in parts.path.split('/') if s]
        if len(segments) >= 2 and segments[0] == 'profiles' and segments[1].isascii() and segments[1].isdigit():
            return account_id(segments[1])
        if segments and segments[0] == 'id':
            raise SteamIdError('vanity', 'a vanity address has no number in it')
        raise SteamIdError('format', 'this address has no account number in it')
    if not (text.isascii() and text.isdigit()):
        raise SteamIdError('format', 'an account number is made of digits only')
    number = int(text)
    return _checked(number - STEAM64_BASE if number >= STEAM64_BASE else number)


def from_userdata_path(path):
    """The account number in a path like `.../Steam/userdata/<number>/1422450/...`, or None."""
    parts = str(path or '').replace('\\', '/').split('/')
    for position, part in enumerate(parts[:-1]):
        if part.lower() == 'userdata':
            candidate = parts[position + 1]
            if candidate.isascii() and candidate.isdigit() and 1 <= int(candidate) <= MAX_ACCOUNT:
                return int(candidate)
    return None
