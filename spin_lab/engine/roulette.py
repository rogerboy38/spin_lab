"""Roulette engine — European (single-zero) and American (double-zero).

The only difference is the green pocket count, and it is the whole lesson:
- European: 37 pockets, straight pays 35:1 -> RTP = 36/37 = 97.30%
- American: 38 pockets (adds 00), same 35:1 payout -> RTP = 36/38 = 94.74%
That extra green 00 almost doubles the house edge (2.70% -> 5.26%) without
changing a single payout. Internally 00 is represented as 37.
"""

from __future__ import annotations

from random import Random

from .rng import make_rng

WHEEL_EU = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23,
            10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26]
# American single-zero/double-zero order (37 == "00")
WHEEL_AM = [0, 28, 9, 26, 30, 11, 7, 20, 32, 17, 5, 22, 34, 15, 3, 24, 36, 13, 1,
            37, 27, 10, 25, 29, 12, 8, 19, 31, 18, 6, 21, 33, 16, 4, 23, 35, 14, 2]
RED = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
DOUBLE_ZERO = 37


def label(n: int) -> str:
    return "00" if n == DOUBLE_ZERO else str(n)


def color(n: int) -> str:
    if n == 0 or n == DOUBLE_ZERO:
        return "green"
    return "red" if n in RED else "black"


def pockets(variant: str) -> int:
    return 38 if variant == "american" else 37


def wheel(variant: str):
    return WHEEL_AM if variant == "american" else WHEEL_EU


def spin(variant: str = "european", rng: Random | None = None) -> int:
    rng = rng or make_rng()
    return rng.randrange(pockets(variant))   # european 0..36, american adds 37(=00)


def _norm_target(target):
    if target in ("00", DOUBLE_ZERO, "37"):
        return DOUBLE_ZERO
    return int(target)


def _wins(kind: str, target, n: int) -> bool:
    green = n == 0 or n == DOUBLE_ZERO
    if green and kind not in ("straight", "inside"):
        return False
    if kind == "straight":
        return n == _norm_target(target)
    if kind == "red":
        return color(n) == "red"
    if kind == "black":
        return color(n) == "black"
    if kind == "odd":
        return n % 2 == 1
    if kind == "even":
        return n % 2 == 0 and not green
    if kind == "low":
        return 1 <= n <= 18
    if kind == "high":
        return 19 <= n <= 36
    if kind == "dozen":
        d = int(target)
        return (d - 1) * 12 + 1 <= n <= d * 12
    if kind == "column":
        c = int(target)
        return not green and n % 3 == (c % 3)
    if kind == "inside":
        return n in set(_norm_target(t) for t in target)
    raise ValueError(f"unknown bet kind {kind!r}")


PAYOUT = {"straight": 36, "red": 2, "black": 2, "odd": 2, "even": 2,
          "low": 2, "high": 2, "dozen": 3, "column": 3}
# inside bet: total return by group size (split=2 ->18x, street=3 ->12x,
# corner=4 ->9x, basket=5 ->7x [the worst bet], six-line=6 ->6x)
GROUP_PAYOUT = {1: 36, 2: 18, 3: 12, 4: 9, 5: 7, 6: 6}


def settle(bets: list[dict], n: int) -> list[dict]:
    out = []
    for b in bets:
        win = _wins(b["kind"], b.get("target"), n)
        if b["kind"] == "inside":
            mult = GROUP_PAYOUT.get(len(b["target"]), 0)
        else:
            mult = PAYOUT[b["kind"]]
        ret = b["amount"] * mult if win else 0.0
        out.append({**b, "win": win, "won": round(ret, 4),
                    "net": round(ret - b["amount"], 4)})
    return out


def hot_cold(recent: list[int], variant: str = "european", top: int = 4) -> dict:
    P = pockets(variant)
    counts = {i: 0 for i in range(P)}
    for n in recent:
        if 0 <= n < P:
            counts[n] += 1
    order = sorted(range(P), key=lambda i: (-counts[i], i))
    hot = [{"n": i, "c": counts[i]} for i in order[:top] if counts[i] > 0]
    cold = [{"n": i, "c": counts[i]} for i in sorted(range(P), key=lambda i: (counts[i], i))[:top]]
    return {"hot": hot, "cold": cold}


def theoretical_rtp(variant: str = "european") -> float:
    return 36 / pockets(variant)
