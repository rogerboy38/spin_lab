"""La Lotería del Enganche — the 'free food' stage, in Mexican-lottery form.

Models Stage 1 of the hook: a high-RTP (default 120%) game where the player
keeps winning small, festive prizes — while the progressive jackpots dangled
above it (handled by the Progressive Meter bank) almost never land. The point
is the bait: the base game pays back MORE than you stake, so you feel like a
winner and stay; the life-changing prize stays mathematically out of reach.

Pure Python, no Frappe imports. Virtual points only.
"""

from __future__ import annotations

from .rng import make_rng

# 16 traditional Lotería cards (name, emoji) — a 4x4 tabla
CARDS = [
    ("El Gallo", "🐓"), ("La Dama", "💃"), ("El Catrín", "🎩"), ("La Sirena", "🧜"),
    ("La Luna", "🌙"), ("El Sol", "☀️"), ("La Estrella", "⭐"), ("El Mundo", "🌎"),
    ("El Corazón", "❤️"), ("La Rosa", "🌹"), ("El Pájaro", "🐦"), ("El Árbol", "🌳"),
    ("El Nopal", "🌵"), ("La Palma", "🌴"), ("El Músico", "🎸"), ("La Campana", "🔔"),
]

# Base (non-jackpot) prize tiers: probability, unscaled pay multiplier, label.
# Tuned to be FREQUENT and small — the "free food" feel.
BASE_TIERS = [
    (0.45, 1.5, "Centro"),           # the centre bean
    (0.12, 4.0, "Línea"),            # a line
    (0.05, 8.0, "Cuatro Esquinas"),  # four corners
    (0.02, 20.0, "Patrón Doble"),    # two patterns at once
]


def base_rtp_unscaled() -> float:
    return sum(p * m for p, m, _ in BASE_TIERS)


def scale_for(target_rtp: float) -> float:
    """Scale applied to every pay so the base game hits the target RTP exactly."""
    base = base_rtp_unscaled()
    if base <= 0:
        raise ValueError("base RTP is zero")
    return target_rtp / base


def play(stake: float = 1.0, target_rtp: float = 1.20, rng=None) -> dict:
    """One tabla. Returns the marked cells (for the canvas), the prize tier and win."""
    rng = rng or make_rng()
    scale = scale_for(target_rtp)
    n_marked = rng.randint(6, 12)
    marked = sorted(rng.sample(range(16), n_marked))
    roll = rng.random()
    cum, win, label = 0.0, 0.0, None
    for p, m, lbl in BASE_TIERS:
        cum += p
        if roll < cum:
            win, label = m * scale * stake, lbl
            break
    return {"marked": marked, "tier": label, "win": round(win, 6),
            "net": round(win - stake, 6)}


def simulate(n: int, stake: float = 1.0, target_rtp: float = 1.20, seed=None) -> dict:
    """Bulk run for honest statistics (base game only; jackpots are separate)."""
    rng = make_rng(seed)
    scale = scale_for(target_rtp)
    staked = paid = 0.0
    hits = 0
    tier_counts: dict[str, int] = {}
    for _ in range(n):
        roll, cum, win, lbl = rng.random(), 0.0, 0.0, None
        for p, m, l in BASE_TIERS:
            cum += p
            if roll < cum:
                win, lbl = m * scale * stake, l
                break
        staked += stake
        paid += win
        if win > 0:
            hits += 1
        if lbl:
            tier_counts[lbl] = tier_counts.get(lbl, 0) + 1
    return {
        "n": n, "target_rtp": target_rtp,
        "empirical_rtp": round(paid / staked, 6) if staked else 0,
        "hit_rate": round(hits / n, 6) if n else 0,
        "final_net": round(paid - staked, 4),
        "tier_counts": tier_counts,
    }


def config() -> dict:
    """Front-end mirror: cards, tiers, scale — single source of truth."""
    return {
        "cards": [{"name": n, "emoji": e} for n, e in CARDS],
        "tiers": [{"p": p, "pay": m, "label": l} for p, m, l in BASE_TIERS],
        "base_rtp_unscaled": round(base_rtp_unscaled(), 6),
    }
