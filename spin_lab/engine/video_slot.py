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
    # Expanding-wild respin feature (Starburst-style; see research notes):
    # a wild visible on an eligible reel expands to cover the reel, locks,
    # and grants a respin of the unlocked reels (chain capped at max_respins).
    expanding_wilds: bool = False
    expanding_reels: tuple[int, ...] = ()   # 0-based reel indices
    max_respins: int = 3
    # v3 features (research notes: DoA2, Jack & the Beanstalk, BTG Megaways)
    both_ways: bool = False          # ways evaluated L2R and R2L (dedup full runs)
    sticky_wilds_fs: bool = False    # wilds lock for remainder of free spins
    walking_wilds: bool = False      # wilds walk left 1 reel/respin while on screen
    megaways: bool = False           # per-reel height drawn 2..7 each spin
    megaways_rows: tuple[int, int] = (2, 7)

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

def _classic_video(name, symbols, wild_counts=(0, 2, 2, 2, 2, 1)):
    """Build a 6x4 video theme from a classic-style symbol list.

    symbols: [(symbol, base_count, (pay3, pay4, pay5, pay6)), ...] low->high
    """
    base = {sym: c for sym, c, _ in symbols}
    base["SCATTER"] = 1
    reel_counts = []
    for i in range(REELS):
        c = dict(base)
        if wild_counts[i]:
            c["WILD"] = wild_counts[i]
        reel_counts.append(c)
    return theme_from_config({
        "name": name,
        "wild": "WILD",
        "scatter": "SCATTER",
        "fs_multiplier": 2.0,
        "reel_counts": reel_counts,
        "pay_table": {sym: dict(zip((3, 4, 5, 6), p)) for sym, _, p in symbols},
        "scatter_pays": {3: 1.0, 4: 5.0, 5: 20.0, 6: 100.0},
        "free_spins": {3: 8, 4: 12, 5: 15, 6: 20},
    })


# NOTE: theme_from_config is defined below; build lazily on first access
_CLASSIC_VIDEO_SPECS = [
    ("Classic Fruits 4096", [
        ("CHERRY", 11, (20, 60, 150, 400)),
        ("LEMON", 9, (25, 80, 200, 500)),
        ("PLUM", 8, (30, 100, 250, 600)),
        ("ORANGE", 6, (40, 120, 300, 800)),
        ("GRAPE", 4, (50, 150, 400, 1000)),
        ("BELL", 3, (100, 300, 800, 2000)),
        ("STRAWBERRY", 2, (250, 800, 2000, 5000)),
    ]),
    ("Lucky Sevens 4096", [
        ("BLANK", 14, (10, 30, 80, 200)),
        ("BELL", 8, (30, 100, 250, 600)),
        ("BAR", 6, (50, 150, 400, 1000)),
        ("SEVEN", 3, (250, 800, 2000, 5000)),
        ("DIAMOND", 1, (500, 1500, 4000, 10000)),
    ]),
    ("Stars & Bars 4096", [
        ("BLANK", 18, (5, 15, 40, 100)),
        ("STAR", 5, (50, 150, 400, 1000)),
        ("BAR1", 4, (100, 300, 800, 2000)),
        ("BAR2", 2, (250, 800, 2000, 5000)),
        ("BAR3", 1, (500, 1500, 4000, 10000)),
    ]),
]


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


def spin_grid_megaways(theme: VideoTheme, rng: Random) -> list[list[str]]:
    """BTG Megaways model (research-verified): per-reel height drawn
    independently each spin (uniform 2..7); window read from the strip."""
    lo, hi = theme.megaways_rows
    grid = []
    for strip in theme.strips:
        h = rng.randint(lo, hi)
        stop = rng.randrange(len(strip))
        grid.append([strip[(stop + r) % len(strip)] for r in range(h)])
    return grid


def _make_grid(theme: VideoTheme, rng: Random) -> list[list[str]]:
    return spin_grid_megaways(theme, rng) if theme.megaways else spin_grid(theme, rng)


def grid_ways(grid: list[list[str]]) -> int:
    w = 1
    for col in grid:
        w *= len(col)
    return w


def evaluate_ways_both(theme: VideoTheme, grid: list[list[str]]) -> tuple[float, list[dict]]:
    """Both-ways ways evaluation. Industry rule (research-verified): evaluate
    L2R and R2L independently; if a symbol's two runs overlap (lenL + lenR >
    reels) pay only the better direction once - full-board runs never pay twice."""
    n = theme.reels
    _, wins_l = evaluate_ways(theme, grid)
    _, wins_r = evaluate_ways(theme, grid[::-1])
    by_sym_l = {w["symbol"]: w for w in wins_l}
    by_sym_r = {w["symbol"]: w for w in wins_r}
    total = 0.0
    wins = []
    for sym in set(by_sym_l) | set(by_sym_r):
        L, R = by_sym_l.get(sym), by_sym_r.get(sym)
        if L and R and L["count"] + R["count"] > n:
            best = L if L["pay"] >= R["pay"] else {**R, "direction": "R2L"}
            wins.append(best)
            total += best["pay"]
        else:
            if L:
                wins.append(L)
                total += L["pay"]
            if R:
                wins.append({**R, "direction": "R2L"})
                total += R["pay"]
    return total, wins


def _eval(theme: VideoTheme, grid: list[list[str]]) -> tuple[float, list[dict]]:
    if theme.both_ways:
        return evaluate_ways_both(theme, grid)
    return evaluate_ways(theme, grid)


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


_MC_RTP_CACHE: dict[str, float] = {}
_MC_CALIBRATION_SPINS = 120_000


def base_total_rtp(theme: VideoTheme) -> float:
    """Total RTP at scale=1. Exact for plain themes; Monte-Carlo (fixed seed,
    industry-standard approach for respin features per GLI practice) when the
    expanding-wild respin chain makes exact enumeration intractable."""
    needs_mc = (theme.expanding_wilds or theme.both_ways or theme.sticky_wilds_fs
                or theme.walking_wilds or theme.megaways)
    if not needs_mc:
        return analytic_rtp(theme)["total_rtp"]
    if theme.name not in _MC_RTP_CACHE:
        rng = make_rng(20260612)
        paid = 0.0
        for _ in range(_MC_CALIBRATION_SPINS):
            paid += _resolve_chain(theme, 1.0, 1.0, rng)["total_win"]
        _MC_RTP_CACHE[theme.name] = paid / _MC_CALIBRATION_SPINS
    return _MC_RTP_CACHE[theme.name]


def video_profile_scale(theme: VideoTheme, profile: str) -> float:
    """Scale applied to all pays so total RTP hits the profile target.
    (Pays scale linearly through base, scatter, free-spin and respin terms.)"""
    if profile not in SCORING_PROFILES:
        raise ValueError(f"Unknown scoring profile: {profile}")
    return SCORING_PROFILES[profile] / base_total_rtp(theme)


# --------------------------------------------------------------------------
# Playable spin (resolves free spins inline) and simulation
# --------------------------------------------------------------------------

def apply_expanding_wilds(theme: VideoTheme, grid: list[list[str]],
                          locked: set[int]) -> set[int]:
    """Expand any eligible reel showing a wild to a full wild reel.
    Mutates grid; returns the set of NEWLY locked reel indices.
    (Per research: expansion happens after reels stop, BEFORE win evaluation.)"""
    newly: set[int] = set()
    if not theme.expanding_wilds:
        return newly
    for r in theme.expanding_reels:
        if r not in locked and any(sym == theme.wild for sym in grid[r]):
            grid[r] = [theme.wild] * ROWS
            newly.add(r)
    return newly


def _spin_masked(theme: VideoTheme, rng: Random, locked: set[int]) -> list[list[str]]:
    """Spin unlocked reels; locked reels stay full wild (feature-assigned)."""
    grid = spin_grid(theme, rng)
    for r in locked:
        grid[r] = [theme.wild] * ROWS
    return grid


WALK_CAP = 24  # safety cap on walking-wild respins per paid spin


def _resolve_chain(theme: VideoTheme, stake: float, scale: float, rng: Random) -> dict:
    """One paid spin including feature chains (expanding-wild respins OR
    walking-wild respins) and free-spin rounds. Single source of truth for
    video_spin and video_simulate. Pays are per-way units of
    stake/grid_ways(grid) so Megaways grids price each way correctly."""
    locked: set[int] = set()
    walkers: list[tuple[int, int]] = []   # (reel, row) walking wilds
    respins_used = 0
    chain = []
    ways_total = scatter_total = fs_total = 0.0
    fs_info = None

    while True:
        grid = _make_grid(theme, rng)
        for r in locked:
            grid[r] = [theme.wild] * len(grid[r])
        for (r, row) in walkers:                      # inject walking wilds
            grid[r][min(row, len(grid[r]) - 1)] = theme.wild
        newly = apply_expanding_wilds(theme, grid, locked)
        locked |= newly

        unit = stake / grid_ways(grid)
        way_pay, wins = _eval(theme, grid)
        n_sc = count_scatters(theme, grid)
        tier = min(n_sc, max(theme.scatter_pays)) if n_sc >= 3 else 0
        ways_win = way_pay * unit * scale
        sc_win = theme.scatter_pays.get(tier, 0.0) * stake * scale if tier else 0.0
        ways_total += ways_win
        scatter_total += sc_win
        chain.append({"grid": grid, "wins": wins, "scatters": n_sc,
                      "win": round(ways_win + sc_win, 6),
                      "ways": grid_ways(grid),
                      "locked_reels": sorted(locked),
                      "walking_wilds": list(walkers)})
        if tier:
            fs = _play_free_spins(theme, theme.free_spins[tier], stake, scale, rng)
            fs_total += fs["total_win"]
            fs_info = fs if fs_info is None else {
                **fs_info,
                "awarded": fs_info["awarded"] + fs["awarded"],
                "played": fs_info["played"] + fs["played"],
                "retriggers": fs_info["retriggers"] + fs["retriggers"],
                "total_win": round(fs_info["total_win"] + fs["total_win"], 6),
            }

        if theme.walking_wilds:
            # all wild cells walk one reel LEFT; respin while any remain (JatB rule)
            cells = [(r, i) for r, col in enumerate(grid)
                     for i, sym in enumerate(col) if sym == theme.wild]
            walkers = [(r - 1, i) for (r, i) in cells if r - 1 >= 0]
            if walkers and respins_used < WALK_CAP:
                respins_used += 1
                continue
            break
        if newly and respins_used < theme.max_respins:
            respins_used += 1
            continue
        break

    total = ways_total + scatter_total + fs_total
    return {
        "chain": chain,
        "respins_used": respins_used,
        "locked_reels": sorted(locked),
        "ways_win": ways_total,
        "scatter_win": scatter_total,
        "fs_win": fs_total,
        "free_spins": fs_info,
        "total_win": total,
    }


def video_spin(
    theme: str | VideoTheme,
    stake: float = 1.0,
    profile: str = "fair",
    rng: Random | None = None,
) -> dict:
    """One paid spin (resolves expanding-wild respins and free spins inline)."""
    t = resolve_video_theme(theme)
    if stake <= 0:
        raise ValueError("stake must be positive")
    rng = rng or make_rng()
    scale = video_profile_scale(t, profile)
    r = _resolve_chain(t, stake, scale, rng)
    last = r["chain"][-1]
    return {
        "theme": t.name,
        "grid": last["grid"],
        "rows": ROWS,
        "reels": t.reels,
        "total_ways": TOTAL_WAYS,
        "ways": r["chain"][-1]["ways"],
        "stake": stake,
        "wins": last["wins"],
        "scatters": last["scatters"],
        "base_win": round(r["ways_win"] + r["scatter_win"], 6),
        "respins_used": r["respins_used"],
        "locked_reels": r["locked_reels"],
        "chain_wins": [c["win"] for c in r["chain"]],
        "free_spins": r["free_spins"],
        "total_win": round(r["total_win"], 6),
        "net": round(r["total_win"] - stake, 6),
    }


def _play_free_spins(t: VideoTheme, n: int, stake: float, scale: float, rng: Random) -> dict:
    """Free-spin round. With sticky_wilds_fs (DoA2-style): wilds lock in place
    for the remainder of the round; one-time +5 spins when every reel holds
    at least one sticky wild."""
    remaining, played, total = n, 0, 0.0
    retriggers = 0
    sticky: set[tuple[int, int]] = set()
    sticky_bonus_awarded = False
    while remaining > 0 and played < FS_CAP:
        remaining -= 1
        played += 1
        grid = _make_grid(t, rng)
        for (r, row) in sticky:
            grid[r][min(row, len(grid[r]) - 1)] = t.wild
        apply_expanding_wilds(t, grid, set())
        if t.sticky_wilds_fs:
            for r, col in enumerate(grid):
                for i, sym in enumerate(col):
                    if sym == t.wild:
                        sticky.add((r, i))
            if (not sticky_bonus_awarded
                    and all(any(c[0] == r for c in sticky) for r in range(t.reels))):
                remaining += 5     # research: one-time bonus, all reels sticky
                sticky_bonus_awarded = True
        unit = stake / grid_ways(grid)
        way_pay, _ = _eval(t, grid)
        n_sc = count_scatters(t, grid)
        tier = min(n_sc, max(t.scatter_pays)) if n_sc >= 3 else 0
        win = way_pay * unit * scale
        if tier:
            win += t.scatter_pays[tier] * stake * scale
            remaining += t.free_spins[tier]
            retriggers += 1
        total += win * t.fs_multiplier
    return {"awarded": n, "played": played, "retriggers": retriggers,
            "multiplier": t.fs_multiplier,
            "sticky_wilds": len(sticky) if t.sticky_wilds_fs else None,
            "total_win": round(total, 6)}


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

    staked = paid = base_paid = fs_paid = scatter_paid = 0.0
    hits = triggers = respin_events = 0
    bankroll, path = 0.0, []

    for _ in range(n_spins):
        staked += stake
        r = _resolve_chain(t, stake, scale, rng)
        base_paid += r["ways_win"]
        scatter_paid += r["scatter_win"]
        fs_paid += r["fs_win"]
        if r["free_spins"]:
            triggers += 1
        if r["respins_used"]:
            respin_events += 1
        if r["total_win"] > 0:
            hits += 1
        paid += r["total_win"]
        bankroll += r["total_win"] - stake
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
        "respin_rate": round(respin_events / n_spins, 6),
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
        expanding_wilds=bool(cfg.get("expanding_wilds", False)),
        expanding_reels=tuple(int(r) for r in cfg.get("expanding_reels", ())),
        max_respins=int(cfg.get("max_respins", 3)),
        both_ways=bool(cfg.get("both_ways", False)),
        sticky_wilds_fs=bool(cfg.get("sticky_wilds_fs", False)),
        walking_wilds=bool(cfg.get("walking_wilds", False)),
        megaways=bool(cfg.get("megaways", False)),
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


for _name, _syms in _CLASSIC_VIDEO_SPECS:
    _t = _classic_video(_name, _syms)
    VIDEO_THEMES[_t.name] = _t


def star_nova_config() -> dict:
    """Starburst-inspired low-volatility theme: STAR wild on reels 2-5 only,
    expands to a full wild reel, locks, and grants up to 3 chained respins."""
    gems = {"PURPLE": 9, "BLUE": 8, "GREEN": 7, "ORANGE": 6, "YELLOW": 5,
            "SEVEN": 3, "BAR": 2, "SCATTER": 1}
    reel_counts = []
    for i in range(REELS):
        c = dict(gems)
        if i in (1, 2, 3, 4):  # STAR wild only on reels 2-5 (0-based 1..4)
            c["STAR"] = 1
        reel_counts.append(c)
    return {
        "name": "Star Nova 4096",
        "wild": "STAR",
        "scatter": "SCATTER",
        "fs_multiplier": 2.0,
        "expanding_wilds": True,
        "expanding_reels": (1, 2, 3, 4),
        "max_respins": 3,
        "reel_counts": reel_counts,
        "pay_table": {
            "BAR":    {3: 250, 4: 800, 5: 2000, 6: 5000},
            "SEVEN":  {3: 120, 4: 400, 5: 1000, 6: 2500},
            "YELLOW": {3: 60, 4: 150, 5: 400, 6: 1000},
            "GREEN":  {3: 50, 4: 120, 5: 300, 6: 800},
            "ORANGE": {3: 40, 4: 100, 5: 250, 6: 600},
            "BLUE":   {3: 25, 4: 60, 5: 150, 6: 400},
            "PURPLE": {3: 25, 4: 60, 5: 150, 6: 400},
        },
        "scatter_pays": {3: 1.0, 4: 5.0, 5: 20.0, 6: 100.0},
        "free_spins": {3: 8, 4: 12, 5: 15, 6: 20},
    }


_STAR_NOVA = theme_from_config(star_nova_config())
VIDEO_THEMES[_STAR_NOVA.name] = _STAR_NOVA


def _v3_base_counts(extra: dict) -> list[dict]:
    base = {"TEN": 9, "JACK": 8, "QUEEN": 7, "KING": 6, "ACE": 6, "SCATTER": 1}
    base.update(extra)
    counts = []
    for i in range(REELS):
        c = dict(base)
        if i not in (0,):           # no wild on reel 1
            c["WILD"] = 2 if i < 5 else 1
        counts.append(c)
    return counts


def outlaw_trail_config() -> dict:
    """DoA2-inspired: sticky wilds in free spins + both-ways pays."""
    return {
        "name": "Outlaw Trail 4096",
        "wild": "WILD", "scatter": "SCATTER", "fs_multiplier": 2.0,
        "sticky_wilds_fs": True, "both_ways": True,
        "reel_counts": _v3_base_counts({"WHISKEY": 4, "HORSE": 3, "MONEYBAG": 2, "SHERIFF": 1}),
        "pay_table": {
            "SHERIFF":  {3: 250, 4: 800, 5: 2000, 6: 5000},
            "MONEYBAG": {3: 120, 4: 400, 5: 1000, 6: 2500},
            "HORSE":    {3: 60, 4: 150, 5: 400, 6: 1000},
            "WHISKEY":  {3: 40, 4: 100, 5: 250, 6: 600},
            "ACE":      {3: 25, 4: 60, 5: 150, 6: 400},
            "KING":     {3: 20, 4: 50, 5: 120, 6: 300},
            "QUEEN":    {3: 15, 4: 40, 5: 100, 6: 250},
            "JACK":     {3: 12, 4: 30, 5: 80, 6: 200},
            "TEN":      {3: 10, 4: 25, 5: 60, 6: 150},
        },
        "scatter_pays": {3: 1.0, 4: 5.0, 5: 20.0, 6: 100.0},
        "free_spins": {3: 8, 4: 12, 5: 15, 6: 20},
    }


def beanstalk_walk_config() -> dict:
    """Jack & the Beanstalk-inspired: walking wilds (left, respin while on screen)."""
    return {
        "name": "Beanstalk Walk 4096",
        "wild": "WILD", "scatter": "SCATTER", "fs_multiplier": 2.0,
        "walking_wilds": True,
        "reel_counts": _v3_base_counts({"BEAN": 4, "GOOSE": 3, "HARP": 2, "GIANT": 1}),
        "pay_table": {
            "GIANT": {3: 250, 4: 800, 5: 2000, 6: 5000},
            "HARP":  {3: 120, 4: 400, 5: 1000, 6: 2500},
            "GOOSE": {3: 60, 4: 150, 5: 400, 6: 1000},
            "BEAN":  {3: 40, 4: 100, 5: 250, 6: 600},
            "ACE":   {3: 25, 4: 60, 5: 150, 6: 400},
            "KING":  {3: 20, 4: 50, 5: 120, 6: 300},
            "QUEEN": {3: 15, 4: 40, 5: 100, 6: 250},
            "JACK":  {3: 12, 4: 30, 5: 80, 6: 200},
            "TEN":   {3: 10, 4: 25, 5: 60, 6: 150},
        },
        "scatter_pays": {3: 1.0, 4: 5.0, 5: 20.0, 6: 100.0},
        "free_spins": {3: 8, 4: 12, 5: 15, 6: 20},
    }


def mega_vines_config() -> dict:
    """BTG Megaways-inspired: per-reel height 2-7 each spin, up to 117,649 ways."""
    return {
        "name": "Mega Vines",
        "wild": "WILD", "scatter": "SCATTER", "fs_multiplier": 2.0,
        "megaways": True,
        "reel_counts": _v3_base_counts({"MONKEY": 4, "PARROT": 3, "JAGUAR": 2, "IDOL": 1}),
        "pay_table": {
            "IDOL":   {3: 250, 4: 800, 5: 2000, 6: 5000},
            "JAGUAR": {3: 120, 4: 400, 5: 1000, 6: 2500},
            "PARROT": {3: 60, 4: 150, 5: 400, 6: 1000},
            "MONKEY": {3: 40, 4: 100, 5: 250, 6: 600},
            "ACE":    {3: 25, 4: 60, 5: 150, 6: 400},
            "KING":   {3: 20, 4: 50, 5: 120, 6: 300},
            "QUEEN":  {3: 15, 4: 40, 5: 100, 6: 250},
            "JACK":   {3: 12, 4: 30, 5: 80, 6: 200},
            "TEN":    {3: 10, 4: 25, 5: 60, 6: 150},
        },
        "scatter_pays": {3: 1.0, 4: 5.0, 5: 20.0, 6: 100.0},
        "free_spins": {3: 8, 4: 12, 5: 15, 6: 20},
    }


for _cfg_fn in (outlaw_trail_config, beanstalk_walk_config, mega_vines_config):
    _t3 = theme_from_config(_cfg_fn())
    VIDEO_THEMES[_t3.name] = _t3


def all_video_configs() -> list[dict]:
    """Plain configs for every code-defined theme (for DB seeding)."""
    configs = [deep_sea_config(), star_nova_config(),
               outlaw_trail_config(), beanstalk_walk_config(), mega_vines_config()]
    for name, syms in _CLASSIC_VIDEO_SPECS:
        t = VIDEO_THEMES[name]
        base = {sym: c for sym, c, _ in syms}
        base["SCATTER"] = 1
        wild_counts = (0, 2, 2, 2, 2, 1)
        reel_counts = []
        for i in range(REELS):
            c = dict(base)
            if wild_counts[i]:
                c["WILD"] = wild_counts[i]
            reel_counts.append(c)
        configs.append({
            "name": name, "wild": "WILD", "scatter": "SCATTER",
            "fs_multiplier": t.fs_multiplier,
            "reel_counts": reel_counts,
            "pay_table": {s2: dict(p) for s2, p in t.pay_table.items()},
            "scatter_pays": dict(t.scatter_pays),
            "free_spins": dict(t.free_spins),
        })
    return configs
