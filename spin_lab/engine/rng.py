"""Pure, memoryless RNG -> reel-stop mapping.

Guarantees (enforced by tests):
- Uniform over virtual stops.
- Independent of stake, strategy, player, and history.
"""

from __future__ import annotations

import secrets
from random import Random

from .themes import Theme


def make_rng(seed: int | None = None) -> Random:
    """Seedable for reproducible research runs; cryptographic seed otherwise."""
    return Random(seed if seed is not None else secrets.randbits(64))


def spin_reels(theme: Theme, rng: Random) -> tuple[str, str, str]:
    """Sample 3 independent reel stops, uniform over virtual stops."""
    population = [s.symbol for s in theme.symbols]
    weights = [s.weight for s in theme.symbols]
    a, b, c = rng.choices(population, weights=weights, k=3)
    return (a, b, c)
