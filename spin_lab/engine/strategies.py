"""Gambler strategies. All strategies see the SAME outcome sequence; only the
stake differs. This proves empirically that strategy cannot change the odds."""

from __future__ import annotations

from .rng import make_rng, spin_reels
from .slot_engine import resolve_theme
from .themes import Theme, base_payout, profile_scale

MIN_STAKE = 0.01
MAX_STAKE = 100.0


def naive_stake(prev_stake: float, prev_net: float) -> float:
    """Gambler's fallacy: double after a loss ('it's due'), reset after a win."""
    if prev_net < 0:
        return min(prev_stake * 2, MAX_STAKE)
    return 1.0


def advised_stake(prev_stake: float, prev_net: float) -> float:
    """Coach guidance: keep stake minimal, especially when chasing feelings hit."""
    return MIN_STAKE


def rational_stake(prev_stake: float, prev_net: float) -> float:
    """Flat stake; spins are independent so there is nothing to react to."""
    return 1.0


STRATEGIES = {
    "naive": naive_stake,
    "advised": advised_stake,
    "rational": rational_stake,
}


def compare_strategies(
    theme: str | Theme,
    n_spins: int,
    profile: str = "fair",
    seed: int | None = None,
) -> dict:
    """Run all strategies against one shared outcome sequence."""
    t = resolve_theme(theme)
    rng = make_rng(seed)
    scale = profile_scale(t, profile)

    # one shared outcome sequence — identical randomness for every strategy
    outcomes = [spin_reels(t, rng) for _ in range(n_spins)]
    multipliers = [base_payout(t, r) * scale for r in outcomes]

    results = {}
    for name, policy in STRATEGIES.items():
        stake, bankroll, prev_net = 1.0, 0.0, 0.0
        path = []
        total_staked = total_paid = 0.0
        for mult in multipliers:
            stake = policy(stake, prev_net)
            payout = mult * stake
            prev_net = payout - stake
            bankroll += prev_net
            total_staked += stake
            total_paid += payout
            path.append(round(bankroll, 4))
        results[name] = {
            "final_bankroll": round(bankroll, 4),
            "total_staked": round(total_staked, 4),
            "empirical_rtp": round(total_paid / total_staked, 6) if total_staked else 0,
            "bankroll_path": path[:: max(1, n_spins // 1000)],
        }

    wins = sum(1 for m in multipliers if m > 0)
    return {
        "shared_outcomes": {
            "hit_rate": round(wins / n_spins, 6) if n_spins else 0,
            "mean_multiplier": round(sum(multipliers) / n_spins, 6) if n_spins else 0,
            "note": "Identical for every strategy by construction.",
        },
        "theme": t.name,
        "profile": profile,
        "n_spins": n_spins,
        "seed": seed,
        "note": "All strategies received identical outcomes; only stakes differed.",
        "strategies": results,
    }
