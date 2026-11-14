"""Small, strict readers for numbers and text that came from an outside server. Anything unexpected becomes the default."""
import math
import re

_CONTROL = re.compile(r'[\x00-\x08\x0b-\x1f\x7f‪-‮⁦-⁩]')
_SPACES = re.compile(r'\s+')
HIGH = 2 ** 53


def clean(value, limit=80):
    """A single-line, bounded, control-free string; '' for anything that is not text."""
    if not isinstance(value, str):
        return ''
    return _SPACES.sub(' ', _CONTROL.sub('', value)).strip()[:limit]


def to_int(value, default=0, high=HIGH):
    """A non-negative integer no larger than `high`; booleans, negatives, fractions and text that is not plain digits give `default`."""
    if isinstance(value, bool):
        return default
    if isinstance(value, str) and value.isascii() and value.isdigit():
        value = int(value)
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, int) and 0 <= value <= high:
        return value
    return default


def to_float(value, default=0.0, high=1e15):
    """A finite, non-negative float no larger than `high`; everything else gives `default`."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    value = float(value)
    return value if math.isfinite(value) and 0 <= value <= high else default
