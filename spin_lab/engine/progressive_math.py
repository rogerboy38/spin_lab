"""Progressive jackpot math (pure, unit-testable).

Research-verified formulas (Wizard of Odds Megabucks/must-hit-by analyses):
- meter feeds:      meter += c * bet
- player EV:        RTP(J)  = base + p*J/bet - c     (per unit bet)
- break-even meter: J*      = bet * (c + 1 - base) / p
- must-hit-by:      hidden trigger ~ Uniform(seed, max); fires on crossing.
"""

from __future__ import annotations

from random import Random


def rtp_at(base: float, c: float, p: float, J: float, bet: float = 1.0) -> float:
    """Total player return per unit bet at meter level J.

    base = designed RTP of the underlying game (e.g. 1.0 for 'fair'),
    c    = contribution rate carved out of the player's bet,
    p    = jackpot hit probability per unit bet.
    """
    return base - c + p * J / bet


def break_even_meter(base: float, c: float, p: float, bet: float = 1.0) -> float:
    """Meter level J* at which RTP(J*) == 1 (player break-even)."""
    if p <= 0:
        return float("inf")
    return bet * (c + 1.0 - base) / p


def draw_mhb_trigger(seed_value: float, must_hit_max: float, rng: Random) -> float:
    """Must-hit-by: the hidden trigger point, uniform in [seed, max]."""
    return seed_value + rng.random() * (must_hit_max - seed_value)


def mhb_expected_hit(seed_value: float, must_hit_max: float) -> float:
    """E[meter at hit] for a must-hit-by jackpot (uniform trigger)."""
    return (seed_value + must_hit_max) / 2.0


def average_jackpot(seed_value: float, c: float, p: float, bet: float = 1.0) -> float:
    """Long-run average RNG-progressive jackpot at hit:
    seed + expected contributions over the geometric waiting time (1/p bets)."""
    if p <= 0:
        return float("inf")
    return seed_value + c * bet / p
