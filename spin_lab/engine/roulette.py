"""European (single-zero) roulette engine — pure, testable.

House edge comes from the single green 0: 37 pockets, but straight bets pay
35:1 (a fair game would pay 36:1). Result: RTP = 36/37 = 97.297% on every
bet type — the cleanest demonstration of a built-in edge in the whole lab.
"""

from __future__ import annotations

from random import Random

from .rng import make_rng

# Physical wheel order, single zero (European)
WHEEL = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23,
         10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26]
RED = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
POCKETS = 37


def color(n: int) -> str:
    if n == 0:
        return "green"
    return "red" if n in RED else "black"


def spin(rng: Random | None = None) -> int:
    rng = rng or make_rng()
    return rng.randrange(POCKETS)   # 0..36, uniform


def _wins(kind: str, target, n: int) -> bool:
    """Does a bet of (kind,target) win on number n?"""
    if n == 0 and kind != "straight":
        return False  # zero loses every outside/even-money bet
    if kind == "straight":
        return n == int(target)
    if kind == "red":
        return color(n) == "red"
    if kind == "black":
        return color(n) == "black"
    if kind == "odd":
        return n % 2 == 1
    if kind == "even":
        return n % 2 == 0 and n != 0
    if kind == "low":
        return 1 <= n <= 18
    if kind == "high":
        return 19 <= n <= 36
    if kind == "dozen":
        d = int(target)            # 1,2,3
        return (d - 1) * 12 + 1 <= n <= d * 12
    if kind == "column":
        c = int(target)            # 1,2,3
        return n != 0 and n % 3 == (c % 3)
    raise ValueError(f"unknown bet kind {kind!r}")


# total payout multiplier (includes the stake) when a bet wins
PAYOUT = {"straight": 36, "red": 2, "black": 2, "odd": 2, "even": 2,
          "low": 2, "high": 2, "dozen": 3, "column": 3}


def settle(bets: list[dict], n: int) -> list[dict]:
    """bets: [{player,kind,target,amount,...}]. Returns each bet annotated
    with won (total returned, 0 if lost) and net."""
    out = []
    for b in bets:
        win = _wins(b["kind"], b.get("target"), n)
        ret = b["amount"] * PAYOUT[b["kind"]] if win else 0.0
        out.append({**b, "win": win, "won": round(ret, 4),
                    "net": round(ret - b["amount"], 4)})
    return out


def hot_cold(recent: list[int], top: int = 4) -> dict:
    counts = {i: 0 for i in range(POCKETS)}
    for n in recent:
        if 0 <= n < POCKETS:
            counts[n] += 1
    order = sorted(range(POCKETS), key=lambda i: (-counts[i], i))
    hot = [{"n": i, "c": counts[i]} for i in order[:top] if counts[i] > 0]
    cold = [{"n": i, "c": counts[i]} for i in sorted(range(POCKETS), key=lambda i: (counts[i], i))[:top]]
    return {"hot": hot, "cold": cold}


def theoretical_rtp() -> float:
    """Same for every bet type on a single-zero wheel: 36/37."""
    return 36 / 37
