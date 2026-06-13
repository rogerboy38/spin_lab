"""Progressive jackpot processing: shared machine-level state in Frappe.

Educational model: the meters are server-side documents shared by every
player of the site - exactly how a real linked/wide-area progressive works.
All values are virtual points."""

import frappe

from spin_lab.engine.progressive_math import (
    average_jackpot,
    break_even_meter,
    draw_mhb_trigger,
    rtp_at,
)
from spin_lab.engine.rng import make_rng
from spin_lab.engine.themes import SCORING_PROFILES


def _meters():
    if not frappe.db.exists("DocType", "Progressive Meter"):
        return []
    return frappe.get_all(
        "Progressive Meter",
        filters={"enabled": 1},
        fields=["name", "meter_type", "current_value", "seed", "contribution_rate",
                "hit_probability", "must_hit_max", "trigger_threshold",
                "hits", "total_contributed", "last_hit_value"],
        order_by="seed asc",
    )


def process_spin(stake: float) -> dict:
    """Contribute stake to every enabled meter, evaluate hits.
    Returns {'meters': [...], 'jackpot_wins': [...], 'jackpot_total': float}."""
    rng = make_rng()
    wins = []
    for m in _meters():
        contrib = (m.contribution_rate or 0) * stake
        new_value = m.current_value + contrib
        hit = False
        if m.meter_type == "Must-Hit-By":
            hit = new_value >= (m.trigger_threshold or m.must_hit_max)
        else:
            p = (m.hit_probability or 0) * stake
            hit = rng.random() < p
        if hit:
            wins.append({"meter": m.name, "type": m.meter_type,
                         "amount": round(new_value, 4)})
            updates = {
                "current_value": m.seed,
                "hits": (m.hits or 0) + 1,
                "last_hit_value": new_value,
                "total_contributed": (m.total_contributed or 0) + contrib,
            }
            if m.meter_type == "Must-Hit-By":
                updates["trigger_threshold"] = draw_mhb_trigger(
                    m.seed, m.must_hit_max, rng)
            frappe.db.set_value("Progressive Meter", m.name, updates,
                                update_modified=False)
        else:
            frappe.db.set_value("Progressive Meter", m.name, {
                "current_value": new_value,
                "total_contributed": (m.total_contributed or 0) + contrib,
            }, update_modified=False)
    frappe.db.commit()
    return {
        "meters": meter_analysis(),
        "jackpot_wins": wins,
        "jackpot_total": round(sum(w["amount"] for w in wins), 4),
    }


@frappe.whitelist(allow_guest=True)
def meter_analysis(profile: str = "fair", stake: float = 1.0):
    """The analysis variables for every meter (the page's table)."""
    base = SCORING_PROFILES.get(profile, 1.0)
    stake = float(stake) or 1.0
    out = []
    for m in _meters():
        c, p, J = m.contribution_rate or 0, m.hit_probability or 0, m.current_value
        row = {
            "name": m.name, "type": m.meter_type, "value": round(J, 2),
            "seed": m.seed, "c": c, "p": p,
            "hits": m.hits or 0, "last_hit": m.last_hit_value,
            "total_contributed": round(m.total_contributed or 0, 2),
        }
        if m.meter_type == "Must-Hit-By":
            row.update({
                "must_hit_max": m.must_hit_max,
                "progress_pct": round(100 * (J - m.seed) / (m.must_hit_max - m.seed), 2),
                "expected_hit": round((m.seed + m.must_hit_max) / 2, 2),
                "note": "EV rises as the meter nears the maximum (trigger is hidden, uniform).",
            })
        else:
            j_star = break_even_meter(base, c, p, stake)
            row.update({
                "jackpot_ev_pct": round(100 * p * J / stake, 4),
                "rtp_at_J_pct": round(100 * rtp_at(base, c, p, J, stake), 4),
                "break_even_J": round(j_star, 2),
                "progress_to_breakeven_pct": round(100 * J / j_star, 2) if j_star else None,
                "avg_jackpot_at_hit": round(average_jackpot(m.seed, c, p, stake), 2),
                "odds": f"1 in {round(1 / (p * stake)):,}" if p else "-",
            })
        out.append(row)
    return out
