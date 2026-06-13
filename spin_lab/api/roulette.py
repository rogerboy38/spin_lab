"""Multiplayer roulette — shared table state in a single DocType.

All bets for the current round live as JSON in the Roulette State single.
Students place bets from their seats; every client polls roulette_state to
see everyone's chips on the shared table. roulette_spin settles the round.
Virtual points only."""

import json

import frappe

from spin_lab.engine import roulette as rl
from spin_lab.engine.rng import make_rng

RECENT_CAP = 60


def _state():
    return frappe.get_single("Roulette State")


def _load(s, field, default):
    try:
        return json.loads(s.get(field) or "")
    except Exception:
        return default


@frappe.whitelist(allow_guest=True)
def roulette_state():
    s = _state()
    recent = _load(s, "recent", [])
    bets = _load(s, "live_bets", [])
    variant = s.variant or "european"
    hc = rl.hot_cold(recent, variant)
    return {
        "variant": variant,
        "round_no": s.round_no or 1,
        "last_number": s.last_number if s.last_number is not None else -1,
        "recent": recent[:18],
        "hot": hc["hot"], "cold": hc["cold"],
        "bets": bets,
        "rtp": round(rl.theoretical_rtp(variant), 5),
    }


@frappe.whitelist(allow_guest=True)
def roulette_bet(player, color, kind, amount, target=None):
    amount = float(amount)
    if amount <= 0 or amount > 100000:
        frappe.throw("Bad amount")
    if kind == "inside":
        if isinstance(target, str):
            target = json.loads(target)
        if not isinstance(target, list) or not (1 <= len(target) <= 6):
            frappe.throw("Bad inside group")
        target = [(37 if str(t) in ("00", "37") else int(t)) for t in target]
    elif kind not in rl.PAYOUT:
        frappe.throw("Bad bet kind")
    s = _state()
    bets = _load(s, "live_bets", [])
    if kind in ("red", "black", "odd", "even", "low", "high"):
        target = kind
    # server-authoritative wallet: deduct now, in the same call that records
    # the bet — so a stake can never be lost without a bet on the table.
    user = frappe.session.user
    balance = None
    if user != "Guest":
        from spin_lab.api.casino_accounts import _ensure_account
        if not frappe.db.exists("Casino Account", {"user": user}):
            _ensure_account(user)
        cur = frappe.db.get_value("Casino Account", {"user": user}, "balance") or 0
        if amount > cur:
            frappe.throw("Insufficient credits")
        balance = round(cur - amount, 2)
        frappe.db.set_value("Casino Account", {"user": user}, "balance", balance, update_modified=False)
    bets.append({"player": str(player)[:24], "color": str(color)[:16],
                 "kind": kind, "target": target, "amount": amount,
                 "user": None if user == "Guest" else user})
    s.db_set("live_bets", json.dumps(bets), update_modified=False)
    frappe.db.commit()
    return {"ok": True, "bets": bets, "balance": balance}


@frappe.whitelist(allow_guest=True)
def roulette_clear(player):
    s = _state()
    all_bets = _load(s, "live_bets", [])
    mine = [b for b in all_bets if b.get("player") == player]
    rest = [b for b in all_bets if b.get("player") != player]
    user = frappe.session.user
    balance = None
    if user != "Guest":
        refund = sum(b["amount"] for b in mine if b.get("user") == user)
        cur = frappe.db.get_value("Casino Account", {"user": user}, "balance") or 0
        balance = round(cur + refund, 2)
        frappe.db.set_value("Casino Account", {"user": user}, "balance", balance, update_modified=False)
    s.db_set("live_bets", json.dumps(rest), update_modified=False)
    frappe.db.commit()
    return {"ok": True, "bets": rest, "balance": balance}


@frappe.whitelist(allow_guest=True)
def roulette_set_variant(variant):
    if variant not in ("european", "american"):
        frappe.throw("bad variant")
    s = _state()
    s.db_set("variant", variant, update_modified=False)
    s.db_set("live_bets", json.dumps([]), update_modified=False)
    s.db_set("recent", json.dumps([]), update_modified=False)
    frappe.db.commit()
    return {"ok": True, "variant": variant}


@frappe.whitelist(allow_guest=True)
def roulette_spin():
    s = _state()
    bets = _load(s, "live_bets", [])
    variant = s.variant or "european"
    n = rl.spin(variant, make_rng())
    settled = rl.settle(bets, n)
    # credit each bet's owning account server-side (atomic with the spin)
    for b in settled:
        u = b.get("user")
        if u and b["won"] > 0:
            cur = frappe.db.get_value("Casino Account", {"user": u}, "balance") or 0
            frappe.db.set_value("Casino Account", {"user": u}, "balance",
                                round(cur + b["won"], 2), update_modified=False)
    players = {}
    for b in settled:
        p = players.setdefault(b["player"], {"staked": 0.0, "won": 0.0, "color": b.get("color"), "user": b.get("user")})
        p["staked"] += b["amount"]
        p["won"] += b["won"]
    recent = ([n] + _load(s, "recent", []))[:RECENT_CAP]
    s.db_set("last_number", n, update_modified=False)
    s.db_set("recent", json.dumps(recent), update_modified=False)
    s.db_set("round_no", (s.round_no or 1) + 1, update_modified=False)
    s.db_set("live_bets", json.dumps([]), update_modified=False)
    frappe.db.commit()
    return {
        "number": n, "color": rl.color(n),
        "settled": settled,
        "players": [{"player": k, "staked": round(v["staked"], 2),
                     "won": round(v["won"], 2), "net": round(v["won"] - v["staked"], 2),
                     "color": v["color"],
                     "balance": (frappe.db.get_value("Casino Account", {"user": v["user"]}, "balance")
                                 if v.get("user") else None)}
                    for k, v in players.items()],
    }
