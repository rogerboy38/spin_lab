"""Whitelisted Frappe API endpoints for Spin Lab.

Thin wrappers over the pure-python engine; persistence is optional and
records are virtual-credit research data only."""

import json

import frappe

from spin_lab.engine import heat as heat_engine
from spin_lab.engine import slot_engine as engine
from spin_lab.engine import strategies as strategy_engine

MAX_SIM_SPINS = 1_000_000


@frappe.whitelist()
def spin_once(theme: str = "Classic Fruits", stake_points: float = 1.0, profile: str = "fair"):
    result = engine.spin_once(theme, float(stake_points), profile)
    doc = frappe.new_doc("Slot Spin")
    doc.theme = theme
    doc.profile = profile
    doc.stake_points = result.stake
    doc.reel_1, doc.reel_2, doc.reel_3 = result.reels
    doc.payout = result.payout
    doc.net = result.net
    doc.insert(ignore_permissions=True)
    frappe.publish_realtime("spin_lab_spin", result.to_dict(), user=frappe.session.user)
    return result.to_dict()


@frappe.whitelist()
def simulate(theme: str, n_spins: int = 10000, profile: str = "fair",
             stake_points: float = 1.0, seed: int | None = None):
    n_spins = min(int(n_spins), MAX_SIM_SPINS)
    summary = engine.simulate(theme, n_spins, profile, float(stake_points),
                              int(seed) if seed is not None else None)
    run = frappe.new_doc("Slot Simulation Run")
    run.theme = theme
    run.profile = profile
    run.n_spins = n_spins
    run.seed = seed
    run.empirical_rtp = summary["empirical_rtp"]
    run.results_json = json.dumps(summary)
    run.insert(ignore_permissions=True)
    summary["run_name"] = run.name
    return summary


@frappe.whitelist()
def compare_strategies(theme: str, n_spins: int = 10000, profile: str = "fair",
                       seed: int | None = None):
    n_spins = min(int(n_spins), MAX_SIM_SPINS)
    return strategy_engine.compare_strategies(
        theme, n_spins, profile, int(seed) if seed is not None else None
    )


@frappe.whitelist()
def get_event_heat(theme: str, event: str | None = None,
                   hits: int = 0, window: int = 0):
    if event:
        return heat_engine.event_heat(theme, event, int(hits), int(window))
    return heat_engine.theme_heat_map(theme)


# --------------------------------------------------------------------------
# Video slot (6x4, 4096 ways) endpoints
# --------------------------------------------------------------------------

from spin_lab.engine import video_slot as video_engine


def _resolve_any_video_theme(theme: str):
    """Code-defined themes first, then Video Slot Theme records from the DB."""
    try:
        return video_engine.resolve_video_theme(theme)
    except ValueError:
        if frappe.db.exists("Video Slot Theme", theme):
            return frappe.get_doc("Video Slot Theme", theme).as_engine_theme()
        raise


@frappe.whitelist()
def video_themes():
    """All available video themes (code-defined + DB records)."""
    names = list(video_engine.VIDEO_THEMES)
    if frappe.db.exists("DocType", "Video Slot Theme"):
        names += [d.name for d in frappe.get_all("Video Slot Theme")
                  if d.name not in names]
    return names


@frappe.whitelist()
def video_spin(theme: str = "Deep Sea 4096", stake: float = 1.0, profile: str = "fair"):
    result = video_engine.video_spin(_resolve_any_video_theme(theme), float(stake), profile)
    # progressive meters: shared machine-level state (see api/progressive.py)
    from spin_lab.api.progressive import process_spin
    prog = process_spin(float(stake))
    result["progressives"] = prog
    if prog["jackpot_total"]:
        result["total_win"] = round(result["total_win"] + prog["jackpot_total"], 6)
        result["net"] = round(result["net"] + prog["jackpot_total"], 6)
    frappe.publish_realtime("spin_lab_video_spin", result, user=frappe.session.user)
    return result


@frappe.whitelist()
def video_simulate(theme: str = "Deep Sea 4096", n_spins: int = 10000,
                   profile: str = "fair", stake: float = 1.0, seed: int | None = None):
    n_spins = min(int(n_spins), 200_000)  # free-spin resolution is heavier per spin
    summary = video_engine.video_simulate(
        _resolve_any_video_theme(theme), n_spins, profile, float(stake),
        int(seed) if seed is not None else None)
    run = frappe.new_doc("Slot Simulation Run")
    run.theme = None  # video themes are code-defined, not Slot Theme records
    run.profile = profile
    run.n_spins = n_spins
    run.empirical_rtp = summary["empirical_rtp"]
    run.results_json = json.dumps(summary)
    run.flags.ignore_mandatory = True
    run.insert(ignore_permissions=True)
    return summary


@frappe.whitelist()
def video_info(theme: str = "Deep Sea 4096", profile: str = "fair"):
    """Theme metadata + exact analytic RTP decomposition for the UI."""
    t = _resolve_any_video_theme(theme)
    r = video_engine.analytic_rtp(t)
    scale = video_engine.video_profile_scale(t, profile)
    return {
        "name": t.name,
        "reels": t.reels,
        "rows": t.rows,
        "total_ways": video_engine.TOTAL_WAYS,
        "wild": t.wild,
        "scatter": t.scatter,
        "pay_table": t.pay_table,
        "scatter_pays": t.scatter_pays,
        "free_spins": t.free_spins,
        "fs_multiplier": t.fs_multiplier,
        "strip_lengths": [len(s) for s in t.strips],
        "rtp": {
            "target": video_engine.SCORING_PROFILES[profile],
            "base_ways": round(r["base_ways_rtp"] * scale, 6),
            "scatter": round(r["scatter_rtp"] * scale, 6),
            "free_spins": round(r["free_spins_rtp"] * scale, 6),
            "p_free_spin_trigger": round(r["p_free_spin_trigger"], 6),
            "expected_free_spins_per_trigger": round(r["expected_free_spins_per_trigger"], 3),
        },
    }


@frappe.whitelist(allow_guest=True)
def meter_analysis_api(profile: str = "fair", stake: float = 1.0):
    from spin_lab.api.progressive import meter_analysis
    return meter_analysis(profile, stake)
