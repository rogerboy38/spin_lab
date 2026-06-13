"""Core spin & simulation engine. Pure Python - no Frappe imports - so it can
be unit-tested standalone and reused by the API layer."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from random import Random

from .rng import make_rng, spin_reels
from .themes import (
    DEFAULT_THEMES,
    SCORING_PROFILES,
    Theme,
    base_payout,
    profile_scale,
)


@dataclass
class SpinResult:
    reels: tuple[str, str, str]
    stake: float
    payout: float
    net: float

    def to_dict(self):
        d = asdict(self)
        d["reels"] = list(self.reels)
        return d


def resolve_theme(theme: str | Theme) -> Theme:
    if isinstance(theme, Theme):
        return theme
    try:
        return DEFAULT_THEMES[theme]
    except KeyError:
        raise ValueError(
            f"Unknown theme {theme!r}. Available: {', '.join(DEFAULT_THEMES)}"
        ) from None


def spin_once(
    theme: str | Theme,
    stake_points: float = 1.0,
    profile: str = "fair",
    rng: Random | None = None,
) -> SpinResult:
    """One spin. Stake scales the payout linearly; it never alters probabilities."""
    if stake_points <= 0:
        raise ValueError("stake_points must be positive")
    t = resolve_theme(theme)
    rng = rng or make_rng()
    reels = spin_reels(t, rng)
    payout = base_payout(t, reels) * profile_scale(t, profile) * stake_points
    return SpinResult(reels=reels, stake=stake_points, payout=payout, net=payout - stake_points)


def simulate(
    theme: str | Theme,
    n_spins: int,
    profile: str = "fair",
    stake_points: float = 1.0,
    seed: int | None = None,
) -> dict:
    """Run n_spins with a flat stake; return aggregate statistics."""
    t = resolve_theme(theme)
    rng = make_rng(seed)
    scale = profile_scale(t, profile)

    total_staked = 0.0
    total_paid = 0.0
    wins = 0
    ldw = 0  # losses disguised as wins: 0 < payout < stake
    outcome_counts: dict[str, int] = {}
    bankroll_path: list[float] = []
    bankroll = 0.0

    for _ in range(n_spins):
        reels = spin_reels(t, rng)
        payout = base_payout(t, reels) * scale * stake_points
        total_staked += stake_points
        total_paid += payout
        if payout > 0:
            wins += 1
            if payout < stake_points:
                ldw += 1
        key = "|".join(reels)
        outcome_counts[key] = outcome_counts.get(key, 0) + 1
        bankroll += payout - stake_points
        bankroll_path.append(bankroll)

    return {
        "theme": t.name,
        "profile": profile,
        "target_rtp": SCORING_PROFILES[profile],
        "n_spins": n_spins,
        "seed": seed,
        "total_staked": total_staked,
        "total_paid": round(total_paid, 6),
        "empirical_rtp": round(total_paid / total_staked, 6) if total_staked else 0,
        "hit_rate": round(wins / n_spins, 6) if n_spins else 0,
        "ldw_rate": round(ldw / n_spins, 6) if n_spins else 0,
        "final_bankroll": round(bankroll, 6),
        "outcome_counts": outcome_counts,
        # downsample path to <=1000 points for charting
        "bankroll_path": bankroll_path[:: max(1, n_spins // 1000)],
    }
