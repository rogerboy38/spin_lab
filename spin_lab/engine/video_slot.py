"""Video slot engine: 6x4 grid, 4096 ways-to-win, wilds, scatters, free spins.

Implements the industry-standard model documented in the research phase:

- Strip + window reel model (Turner & Horbay 2004; Harrigan & Dixon 2009
  PAR-sheet literature): each reel is an ordered cyclic strip; the RNG picks
  a stop uniformly; the window shows `rows` consecutive symbols (wrapping).
- Ways-to-win evaluation (4096 = 4^6): a symbol pays when it lands on
  adjacent reels starting from reel 1 (any row). Ways = product of per-reel
  match counts (wilds substitute). Only the highest match length pays per
  symbol per spin.
- Scatters pay anywhere x total bet; 3+ trigger free spins. Free spins run
  at the triggering bet with a global win multiplier and can retrigger
  (E[spins] = n0 / (1 - R), capped).
- RTP is decomposed analytically into base-ways + scatter + free-spins and
  auto-scaled so each scoring profile hits its exact target RTP.

Pure Python - no Frappe imports - fully unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from random import Random

from .rng import make_rng
from .themes import SCORING_PROFILES

ROWS = 4
REELS = 6
TOTAL_WAYS = ROWS**REELS  # 4096
FS_CAP = 100  # hard cap on free spins per bonus round (E[spins] must converge anyway)


# --------------------------------------------------------------------------
# Theme definition
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class VideoTheme:
    name: str
    strips: tuple[tuple[str, ...], ...]      # one ordered strip per reel
    pay_table: dict[str, dict[int, float]]   # symbol -> {match_len: per-way pay}
    wild: str
    scatter: str
    scatter_pays: dict[int, float]           # n scatters -> multiplier of total bet
    free_spins: dict[int, int]               # n scatters -> spins awarded
    fs_multiplier: float = 2.0

    @property
    def rows(self) -> int:
        return ROWS

    @property
    def reels(self) -> int:
        return len(self.strips)


def _build_strip(counts: dict[str, int]) -> tuple[str, ...]:
    """Interleave symbols round-robin by frequency so identical symbols
    (especially scatters) are spread out along the strip."""
    pools = sorted(counts.items(), key=lambda kv: -kv[1])
    slots: list[list[str]] = [[] for _ in range(max(c for _, c in pools))]
    for sym, c in pools:
        for k in range(c):
            slots[k % len(slots)].append(sym)
    strip = [s for slot in slots for s in slot]
    return tuple(strip)


_BASE = {"TEN": 9, "JACK": 8, "QUEEN": 7, "KING": 6, "ACE": 6,
         "CRAB": 4, "OCTOPUS": 3, "SHARK": 2, "KRAKEN": 1, "PEARL": 1}

_REEL_COUNTS = [
    {**_BASE, "TEN": 11},                 # reel 1: no wild (avoids wild-on-reel-1 ambiguity)
    {**_BASE, "WILD": 2},
    {**_BASE, "WILD": 2},
    {**_BASE, "WILD": 2},
    {**_BASE, "WILD": 2},
    {**_BASE, "WILD": 1, "TEN": 10},      # reel 6: fewer wilds (standard outer-reel design)
]

DEEP_SEA = VideoTheme(
    name="Deep Sea 4096",
    strips=tuple(_build_strip(c) for c in _REEL_COUNTS),
    pay_table={
        "KRAKEN":  {3: 500.0, 4: 1500.0, 5: 4000.0, 6: 10000.0},
        "SHARK":   {3: 250.0, 4: 800.0, 5: 2000.0, 6: 5000.0},
        "OCTOPUS": {3: 150.0, 4: 500.0, 5: 1200.0, 6: 3000.0},
        "CRAB":    {3: 100.0, 4: 300.0, 5: 800.0, 6: 2000.0},
        "ACE":     {3: 50.0, 4: 150.0, 5: 400.0, 6: 1000.0},
        "KING":    {3: 40.0, 4: 120.0, 5: 300.0, 6: 800.0},
        "QUEEN":   {3: 30.0, 4: 100.0, 5: 250.0, 6: 600.0},
        "JACK":    {3: 25.0, 4: 80.0, 5: 200.0, 6: 500.0},
        "TEN":     {3: 20.0, 4: 60.0, 5: 150.0, 6: 400.0},
    },
    wild="WILD",
    scatter="PEARL",
    scatter_pays={3: 1.0, 4: 5.0, 5: 20.0, 6: 100.0},
    free_spins={3: 8, 4: 12, 5: 15, 6: 20},
    fs_multiplier=2.0,
)

VIDEO_THEMES = {DEEP_SEA.name: DEEP_SEA}


def resolve_video_theme(theme: str | VideoTheme) -> VideoTheme:
    if isinstance(theme, VideoTheme):
        return theme
    try:
        return VIDEO_THEMES[theme]
    except KeyError:
        raise ValueError(
            f"Unknown video theme {theme!r}. Available: {', '.join(VIDEO_THEMES)}"
        ) from None


# --------------------------------------------------------------------------
# Spin mechanics: strip + window
# --------------------------------------------------------------------------

def spin_grid(theme: VideoTheme, rng: Random) -> list[list[str]]:
    """grid[reel] = list of `rows` visible symbols (strip window, wrapping)."""
    grid = []
    for strip in theme.strips:
        stop = rng.randrange(len(strip))
        grid.append([strip[(stop + r) % len(strip)] for r in range(ROWS)])
    return grid


def evaluate_ways(theme: VideoTheme, grid: list[list[str]]) -> tuple[float, list[dict]]:
    """4096-ways evaluation. Returns (total per-way pay units, win details).

    Rules (verified in research):
    - adjacent reels from leftmost; any row; wilds substitute (not for scatter)
    - ways = product of per-reel match counts
    - only the highest match length pays per symbol
    """
    total = 0.0
    wins = []
    for symbol, pays in theme.pay_table.items():
        counts = []
        for reel in grid:
            c = sum(1 for s in reel if s == symbol or s == theme.wild)
            if c == 0:
                break
            counts.append(c)
        run = len(counts)
        best = max((k for k in pays if k <= run), default=0)
        if best:
            ways = 1
            for c in counts[:best]:
                ways *= c
            amount = pays[best] * ways
            total += amount
            wins.append({"symbol": symbol, "count": best, "ways": ways, "pay": amount})
    return total, wins


def count_scatters(theme: VideoTheme, grid: list[list[str]]) -> int:
    return sum(1 for reel in grid for s in reel if s == theme.scatter)


# --------------------------------------------------------------------------
# Analytic RTP decomposition
# --------------------------------------------------------------------------

def _window_count_dist(strip: tuple[str, ...], symbols: set[str]) -> list[float]:
    """Exact distribution of how many of `symbols` appear in a ROWS-high
    window, over all uniform stops of the strip."""
    n = len(strip)
    dist = [0.0] * (ROWS + 1)
    for stop in range(n):
        c = sum(1 for r in range(ROWS) if strip[(stop + r) % n] in symbols)
        dist[c] += 1 / n
    return dist


def _ways_rtp(theme: VideoTheme) -> float:
    """Exact expected per-way pay per spin (in units of total bet / TOTAL_WAYS
    before normalization - see analytic_rtp for the bet normalization)."""
    rtp = 0.0
    for symbol, pays in theme.pay_table.items():
        match = {symbol, theme.wild}
        dists = [_window_count_dist(s, match) for s in theme.strips]
        e = [sum(c * p for c, p in enumerate(d)) for d in dists]   # E[count]
        p0 = [d[0] for d in dists]                                  # P(count=0)
        for k, pay in pays.items():
            ev_prod = 1.0
            for i in range(k):
                ev_prod *= e[i]
            p_stop = p0[k] if k < theme.reels else 1.0
            rtp += pay * ev_prod * p_stop
    return rtp / TOTAL_WAYS


def _scatter_dist(theme: VideoTheme) -> list[float]:
    """Distribution of total scatters on screen (convolution across reels)."""
    total = [1.0]
    for strip in theme.strips:
        d = _window_count_dist(strip, {theme.scatter})
        new = [0.0] * (len(total) + len(d) - 1)
        for a, pa in enumerate(total):
            for b, pb in enumerate(d):
                new[a + b] += pa * pb
        total = new
    return total


def analytic_rtp(theme: VideoTheme) -> dict:
    """Exact RTP decomposition per unit total bet (unscaled pay table)."""
    base_ways = _ways_rtp(theme)
    sdist = _scatter_dist(theme)

    def stier(n):  # map scatter count to its pay/award tier (6+ uses 6)
        return min(n, max(theme.scatter_pays))

    scatter_ev = sum(p * theme.scatter_pays.get(stier(n), 0.0)
                     for n, p in enumerate(sdist) if n >= 3)
    p_trigger = sum(p for n, p in enumerate(sdist) if n >= 3)
    n_avg = (sum(p * theme.free_spins.get(stier(n), 0) for n, p in enumerate(sdist) if n >= 3)
             / p_trigger) if p_trigger else 0.0

    # Retrigger factor R = expected extra spins awarded per free spin
    R = sum(p * theme.free_spins.get(stier(n), 0) for n, p in enumerate(sdist) if n >= 3)
    assert R < 1, "free-spin expectation diverges; reduce scatters or awards"
    e_spins = n_avg / (1 - R)  # E[spins incl. retriggers] per trigger

    fs_ev_per_spin = theme.fs_multiplier * (base_ways + scatter_ev)
    fs_rtp = p_trigger * e_spins * fs_ev_per_spin

    total = base_ways + scatter_ev + fs_rtp
    return {
        "base_ways_rtp": base_ways,
        "scatter_rtp": scatter_ev,
        "free_spins_rtp": fs_rtp,
        "total_rtp": total,
        "p_free_spin_trigger": p_trigger,
        "expected_free_spins_per_trigger": e_spins,
        "hit_data": {"retrigger_factor": R},
    }


def video_profile_scale(theme: VideoTheme, profile: str) -> float:
    """Scale applied to all pays so total RTP hits the profile target exactly.
    (Pays scale linearly through base, scatter and free-spin terms.)"""
    if profile not in SCORING_PROFILES:
        raise ValueError(f"Unknown scoring profile: {profile}")
    return SCORING_PROFILES[profile] / analytic_rtp(theme)["total_rtp"]


# --------------------------------------------------------------------------
# Playable spin (resolves free spins inline) and simulation
# --------------------------------------------------------------------------

def video_spin(
    theme: str | VideoTheme,
    stake: float = 1.0,
    profile: str = "fair",
    rng: Random | None = None,
) -> dict:
    """One paid spin. If scatters trigger free spins, the whole bonus round
    is resolved immediately and included in the result."""
    t = resolve_video_theme(theme)
    if stake <= 0:
        raise ValueError("stake must be positive")
    rng = rng or make_rng()
    scale = video_profile_scale(t, profile)
    unit = stake / TOTAL_WAYS  # bet per way

    grid = spin_grid(t, rng)
    way_pay, wins = evaluate_ways(t, grid)
    n_sc = count_scatters(t, grid)
    tier = min(n_sc, max(t.scatter_pays)) if n_sc >= 3 else 0
    scatter_pay = t.scatter_pays.get(tier, 0.0) * stake if tier else 0.0
    base_win = way_pay * unit * scale + scatter_pay * scale

    fs_result = None
    if tier:
        fs_result = _play_free_spins(t, t.free_spins[tier], stake, scale, rng)

    total_win = base_win + (fs_result["total_win"] if fs_result else 0.0)
    return {
        "theme": t.name,
        "grid": grid,
        "rows": ROWS,
        "reels": t.reels,
        "total_ways": TOTAL_WAYS,
        "stake": stake,
        "wins": wins,
        "scatters": n_sc,
        "base_win": round(base_win, 6),
        "free_spins": fs_result,
        "total_win": round(total_win, 6),
        "net": round(total_win - stake, 6),
    }


def _play_free_spins(t: VideoTheme, n: int, stake: float, scale: float, rng: Random) -> dict:
    unit = stake / TOTAL_WAYS
    remaining, played, total = n, 0, 0.0
    retriggers = 0
    while remaining > 0 and played < FS_CAP:
        remaining -= 1
        played += 1
        grid = spin_grid(t, rng)
        way_pay, _ = evaluate_ways(t, grid)
        n_sc = count_scatters(t, grid)
        tier = min(n_sc, max(t.scatter_pays)) if n_sc >= 3 else 0
        win = way_pay * unit * scale
        if tier:
            win += t.scatter_pays[tier] * stake * scale
            remaining += t.free_spins[tier]
            retriggers += 1
        total += win * t.fs_multiplier
    return {"awarded": n, "played": played, "retriggers": retriggers,
            "multiplier": t.fs_multiplier, "total_win": round(total, 6)}


def video_simulate(
    theme: str | VideoTheme,
    n_spins: int,
    profile: str = "fair",
    stake: float = 1.0,
    seed: int | None = None,
) -> dict:
    t = resolve_video_theme(theme)
    rng = make_rng(seed)
    scale = video_profile_scale(t, profile)
    unit = stake / TOTAL_WAYS

    staked = paid = base_paid = fs_paid = scatter_paid = 0.0
    hits = triggers = 0
    bankroll, path = 0.0, []

    for _ in range(n_spins):
        staked += stake
        grid = spin_grid(t, rng)
        way_pay, _ = evaluate_ways(t, grid)
        n_sc = count_scatters(t, grid)
        tier = min(n_sc, max(t.scatter_pays)) if n_sc >= 3 else 0
        win = way_pay * unit * scale
        base_paid += win
        if tier:
            sp = t.scatter_pays[tier] * stake * scale
            scatter_paid += sp
            win += sp
            fs = _play_free_spins(t, t.free_spins[tier], stake, scale, rng)
            fs_paid += fs["total_win"]
            win += fs["total_win"]
            triggers += 1
        if win > 0:
            hits += 1
        paid += win
        bankroll += win - stake
        path.append(round(bankroll, 4))

    return {
        "theme": t.name, "profile": profile, "n_spins": n_spins, "seed": seed,
        "target_rtp": SCORING_PROFILES[profile],
        "empirical_rtp": round(paid / staked, 6),
        "rtp_decomposition": {
            "base_ways": round(base_paid / staked, 6),
            "scatter": round(scatter_paid / staked, 6),
            "free_spins": round(fs_paid / staked, 6),
        },
        "hit_rate": round(hits / n_spins, 6),
        "fs_trigger_rate": round(triggers / n_spins, 6),
        "final_bankroll": round(bankroll, 4),
        "bankroll_path": path[:: max(1, n_spins // 1000)],
    }


def theme_from_config(cfg: dict) -> VideoTheme:
    """Build a VideoTheme from a plain dict (used by the Video Slot Theme
    DocType so themes can be defined in the Frappe desk).

    cfg = {
      "name": str,
      "wild": str, "scatter": str, "fs_multiplier": float,
      "reel_counts": [ {symbol: count, ...} x REELS ],
      "pay_table": {symbol: {3: pay, 4: pay, 5: pay, 6: pay}},
      "scatter_pays": {3: x, ...}, "free_spins": {3: n, ...},
    }
    """
    if len(cfg["reel_counts"]) != REELS:
        raise ValueError(f"need symbol counts for exactly {REELS} reels")
    return VideoTheme(
        name=cfg["name"],
        strips=tuple(_build_strip(c) for c in cfg["reel_counts"]),
        pay_table={s: {int(k): float(v) for k, v in p.items()}
                   for s, p in cfg["pay_table"].items()},
        wild=cfg["wild"],
        scatter=cfg["scatter"],
        scatter_pays={int(k): float(v) for k, v in cfg["scatter_pays"].items()},
        free_spins={int(k): int(v) for k, v in cfg["free_spins"].items()},
        fs_multiplier=float(cfg.get("fs_multiplier", 2.0)),
    )


def deep_sea_config() -> dict:
    """The built-in theme as a plain config dict (used for DB seeding)."""
    return {
        "name": DEEP_SEA.name,
        "wild": DEEP_SEA.wild,
        "scatter": DEEP_SEA.scatter,
        "fs_multiplier": DEEP_SEA.fs_multiplier,
        "reel_counts": [dict(c) for c in _REEL_COUNTS],
        "pay_table": {s: dict(p) for s, p in DEEP_SEA.pay_table.items()},
        "scatter_pays": dict(DEEP_SEA.scatter_pays),
        "free_spins": dict(DEEP_SEA.free_spins),
    }
