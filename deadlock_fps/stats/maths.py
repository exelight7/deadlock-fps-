"""The few formulas the stats pages use. Pure functions, no state, defined for every input (no division by zero)."""
import math


def rate(part, whole):
    """part / whole as a fraction, 0.0 when there is no whole."""
    return part / whole if whole else 0.0


def kda(kills, deaths, assists):
    """(kills + assists) per death; a match without deaths counts as one death so the number stays finite."""
    return (kills + assists) / max(1, deaths)


def wilson(wins, matches, z=1.96):
    """The 95 % Wilson score interval of a win rate, as (low, high) fractions.

    A hero with 3 wins in 4 matches is not 75 %: the interval says how far the truth could be. With no matches it is the
    whole range, (0.0, 1.0). The interval is what stops a rarely played hero from topping a "best win rate" list.
    """
    if matches <= 0:
        return 0.0, 1.0
    wins = min(max(wins, 0), matches)
    p = wins / matches
    denominator = 1 + z * z / matches
    centre = (p + z * z / (2 * matches)) / denominator
    margin = z * math.sqrt(p * (1 - p) / matches + z * z / (4 * matches * matches)) / denominator
    return max(0.0, centre - margin), min(1.0, centre + margin)
