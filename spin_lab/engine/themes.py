"""Theme definitions: symbols, weights, and pay tables.

The RNG is always pure and uniform over virtual stops; the *only* source of
house edge is the pay table, optionally scaled by a scoring profile.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product


@dataclass(frozen=True)
class Symbol:
    symbol: str
    weight: int  # number of virtual stops on each reel


@dataclass(frozen=True)
class Theme:
    name: str
    volatility: str
    description: str
    symbols: tuple[Symbol, ...]
    # combination key "A|A|A" or wildcard "CHERRY|*|*" -> payout multiplier
    pay_table: dict[str, float] = field(default_factory=dict)

    @property
    def total_weight(self) -> int:
        return sum(s.weight for s in self.symbols)

    def symbol_probability(self, symbol: str) -> float:
        w = next((s.weight for s in self.symbols if s.symbol == symbol), 0)
        return w / self.total_weight


# Scoring profiles: target RTP (return to player). RNG is identical for all;
# profiles only scale the pay table.
# Scoring profiles span real-world jurisdictional reality:
#   nevada_min  0.75 - US Nevada legal minimum RTP (regulated floor, certified)
#   loose_85    0.85 - loose/under-regulated market (e.g. MX has no mandated floor)
#   tight_90    0.90 - tight but legal in stricter US states (NJ floor is 0.83)
#   casino_edge 0.95 - typical competitive RTP
#   fair        1.00 - zero house edge (study pure variance)
#   player_edge 1.05 - hypothetical +EV (never offered commercially)
SCORING_PROFILES = {
    "nevada_min": 0.75,
    "loose_85": 0.85,
    "tight_90": 0.90,
    "casino_edge": 0.95,
    "fair": 1.00,
    "player_edge": 1.05,
}


def _theme(name, volatility, description, symbols, pay_table):
    return Theme(
        name=name,
        volatility=volatility,
        description=description,
        symbols=tuple(Symbol(s, w) for s, w in symbols),
        pay_table=pay_table,
    )


DEFAULT_THEMES: dict[str, Theme] = {
    t.name: t
    for t in (
        _theme(
            "Classic Fruits",
            "Low",
            "Frequent small wins",
            [("CHERRY", 12), ("LEMON", 10), ("PLUM", 8), ("ORANGE", 6), ("GRAPE", 4)],
            {
                "GRAPE|GRAPE|GRAPE": 40.0,
                "ORANGE|ORANGE|ORANGE": 20.0,
                "PLUM|PLUM|PLUM": 12.0,
                "LEMON|LEMON|LEMON": 8.0,
                "CHERRY|CHERRY|CHERRY": 6.0,
                "CHERRY|CHERRY|*": 2.0,
                "CHERRY|*|*": 0.5,
            },
        ),
        _theme(
            "Lucky Sevens",
            "High",
            "Rare large payouts",
            [("BLANK", 20), ("BELL", 8), ("BAR", 6), ("SEVEN", 4), ("DIAMOND", 2)],
            {
                "SEVEN|SEVEN|SEVEN": 300.0,
                "DIAMOND|DIAMOND|DIAMOND": 500.0,
                "BAR|BAR|BAR": 50.0,
                "BELL|BELL|BELL": 25.0,
                "SEVEN|SEVEN|*": 5.0,
            },
        ),
        _theme(
            "Stars & Bars",
            "Extreme",
            "Very rare, very large payouts",
            [("BLANK", 30), ("STAR", 4), ("BAR1", 3), ("BAR2", 2), ("BAR3", 1)],
            {
                "BAR3|BAR3|BAR3": 5000.0,
                "BAR2|BAR2|BAR2": 1000.0,
                "BAR1|BAR1|BAR1": 300.0,
                "STAR|STAR|STAR": 100.0,
                "STAR|STAR|*": 10.0,
            },
        ),
    )
}


def match_combination(reels: tuple[str, str, str], combo_key: str) -> bool:
    """Check whether a reel result matches a pay-table key.

    '*' is a wildcard. Wildcard positions must NOT contain the literal symbol
    used in the non-wildcard positions (so 'CHERRY|CHERRY|*' does not also
    fire on triple cherries - the more specific rule handles that).
    """
    parts = combo_key.split("|")
    literal = next((p for p in parts if p != "*"), None)
    for reel, part in zip(reels, parts):
        if part == "*":
            if reel == literal:
                return False
        elif reel != part:
            return False
    return True


def base_payout(theme: Theme, reels: tuple[str, str, str]) -> float:
    """Payout multiplier before profile scaling. Most specific rule wins."""
    best = 0.0
    best_specificity = -1
    for combo, mult in theme.pay_table.items():
        if match_combination(reels, combo):
            specificity = sum(1 for p in combo.split("|") if p != "*")
            if specificity > best_specificity:
                best, best_specificity = mult, specificity
    return best


def theoretical_rtp(theme: Theme) -> float:
    """Exact expected payout per unit stake under the unscaled pay table."""
    total = theme.total_weight
    rtp = 0.0
    syms = [(s.symbol, s.weight) for s in theme.symbols]
    for (a, wa), (b, wb), (c, wc) in product(syms, repeat=3):
        p = (wa * wb * wc) / total**3
        rtp += p * base_payout(theme, (a, b, c))
    return rtp


def profile_scale(theme: Theme, profile: str) -> float:
    """Multiplier applied to every payout so the theme hits the profile's RTP."""
    if profile not in SCORING_PROFILES:
        raise ValueError(f"Unknown scoring profile: {profile}")
    base = theoretical_rtp(theme)
    if base <= 0:
        raise ValueError(f"Theme {theme.name} has zero base RTP")
    return SCORING_PROFILES[profile] / base


def event_probability(theme: Theme, combo_key: str) -> float:
    """Exact probability that a spin matches a pay-table combination key."""
    total = theme.total_weight
    p = 0.0
    syms = [(s.symbol, s.weight) for s in theme.symbols]
    for (a, wa), (b, wb), (c, wc) in product(syms, repeat=3):
        if match_combination((a, b, c), combo_key):
            p += (wa * wb * wc) / total**3
    return p
