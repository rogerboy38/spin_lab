"""Gambler's Ruin Lab — the theorem that completes the story.

Give a bankroll B (in stakes) and a cash-out goal G. Play until you either
reach G or hit 0. Classical result for a fair single-unit game: the
probability of reaching G before ruin is exactly B/G — and the expected
number of bets is B*(G-B). With ANY house edge, P(reach goal) collapses
toward zero and ruin becomes near-certain as you keep playing.

This module Monte-Carlos the ACTUAL slot (lumpy, real payouts) and reports
the empirical ruin/goal split, then prints the clean theory as a reference.
Pure Python, no Frappe imports.
"""

from __future__ import annotations

from random import Random

from .slot_engine import resolve_theme
from .rng import make_rng, spin_reels
from .themes import base_payout, profile_scale


def fair_ruin_probability(bankroll_units: float, goal_units: float) -> float:
    """P(reach goal before ruin) for a FAIR game (no edge): exactly B/G."""
    if goal_units <= 0:
        return 0.0
    return min(1.0, bankroll_units / goal_units)


def biased_ruin_probability(bankroll_units: int, goal_units: int, p: float) -> float:
    """Classical asymmetric single-unit gambler's ruin, win prob p per bet.
    P(goal | start=B) = (1-(q/p)^B) / (1-(q/p)^G). For reference/intuition."""
    if p <= 0:
        return 0.0
    if abs(p - 0.5) < 1e-12:
        return fair_ruin_probability(bankroll_units, goal_units)
    q = 1 - p
    r = q / p
    return (1 - r**bankroll_units) / (1 - r**goal_units)


def simulate_ruin(
    theme: str,
    bankroll: float,
    goal: float,
    profile: str = "casino_edge",
    stake: float = 1.0,
    sessions: int = 2000,
    max_spins: int = 100_000,
    seed: int | None = None,
) -> dict:
    """Run many sessions of the real game to ruin or goal.

    Returns the empirical P(cash out), P(ruin), spin-count stats, a sample of
    bankroll trajectories (for charting), and the fair-game theory baseline.
    """
    t = resolve_theme(theme)
    rng = make_rng(seed)
    scale = profile_scale(t, profile)

    reached = 0
    busted = 0
    timeout = 0
    spins_to_end = []
    sample_paths = []          # a handful of trajectories for the chart
    keep_paths = min(40, sessions)

    for s in range(sessions):
        money = bankroll
        spins = 0
        record = s < keep_paths
        path = [money] if record else None
        while 0 < money < goal and spins < max_spins:
            reels = spin_reels(t, rng)
            payout = base_payout(t, reels) * scale * stake
            money += payout - stake
            spins += 1
            if record and spins % max(1, int(max_spins / 400)) == 0:
                path.append(round(money, 2))
        spins_to_end.append(spins)
        if money <= 0:
            busted += 1
            outcome = "bust"
        elif money >= goal:
            reached += 1
            outcome = "goal"
        else:
            timeout += 1
            outcome = "timeout"
        if record:
            path.append(round(money, 2))
            sample_paths.append({"outcome": outcome, "path": path})

    n = sessions
    spins_to_end.sort()
    median_spins = spins_to_end[n // 2]
    bankroll_units = bankroll / stake
    goal_units = goal / stake

    return {
        "theme": t.name,
        "profile": profile,
        "bankroll": bankroll,
        "goal": goal,
        "stake": stake,
        "sessions": n,
        "p_reach_goal": round(reached / n, 4),
        "p_ruin": round(busted / n, 4),
        "p_timeout": round(timeout / n, 4),
        "median_spins": median_spins,
        "mean_spins": round(sum(spins_to_end) / n, 1),
        "fair_p_reach_goal": round(fair_ruin_probability(bankroll_units, goal_units), 4),
        "sample_paths": sample_paths,
        "note": (
            "Fair game: P(reach goal) = bankroll/goal exactly. Any house edge "
            "pushes the real probability below that, and ruin toward certainty "
            "the longer you play."
        ),
    }
