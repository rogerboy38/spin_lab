"""EventHeat: true-probability heat bands + empirical deviation labels.

Bands depend ONLY on the true designed probability. Deviation labels are
finite-sample diagnostics - descriptive of history, never predictive."""

from __future__ import annotations

import math

from .slot_engine import resolve_theme
from .themes import Theme, event_probability

HEAT_BANDS = [
    # (upper bound on true_p, label, color)
    (0.001, "Frozen", "#eaf6ff"),
    (0.01, "Cold", "#2f7ed8"),
    (0.05, "Cool", "#3fc1c9"),
    (0.20, "Warm", "#f5c518"),
    (0.50, "Hot", "#f2622e"),
    (1.01, "Max", "#1a1a1a"),
]


def band_for(true_p: float) -> tuple[str, str]:
    for upper, label, color in HEAT_BANDS:
        if true_p < upper:
            return label, color
    return "Max", "#1a1a1a"


def deviation_label(true_p: float, hits: int, window: int, z_threshold: float = 2.0) -> str:
    """Normal-approximation z-test of empirical frequency vs true_p."""
    if window == 0 or true_p in (0.0, 1.0):
        return "as expected"
    sd = math.sqrt(true_p * (1 - true_p) / window)
    z = (hits / window - true_p) / sd
    if z > z_threshold:
        return "currently above expectation (looks hot)"
    if z < -z_threshold:
        return "currently below expectation (looks cold)"
    return "as expected"


def event_heat(
    theme: str | Theme,
    combo_key: str,
    hits: int = 0,
    window: int = 0,
) -> dict:
    t = resolve_theme(theme)
    true_p = event_probability(t, combo_key)
    label, color = band_for(true_p)
    return {
        "theme": t.name,
        "event": combo_key,
        "true_p": round(true_p, 8),
        "empirical_p": round(hits / window, 8) if window else None,
        "band_label": label,
        "band_color": color,
        "deviation_label": deviation_label(true_p, hits, window),
        "disclaimer": (
            "Heat bands reflect designed probabilities. Deviation labels describe "
            "past samples only; they do not change the next-spin probability."
        ),
    }


def theme_heat_map(theme: str | Theme, hits_by_event: dict | None = None, window: int = 0) -> list[dict]:
    t = resolve_theme(theme)
    hits_by_event = hits_by_event or {}
    return [
        event_heat(t, combo, hits_by_event.get(combo, 0), window)
        for combo in t.pay_table
    ]
