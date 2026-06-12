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
