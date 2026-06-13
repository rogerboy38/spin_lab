"""Scoring profiles as editable DocType records (shared, desk-editable).

The pure engine keeps a hardcoded default set (so tests run без Frappe);
this layer merges any enabled Scoring Profile documents on top, so adding
or tuning a profile in the desk flows to every dropdown and calculation."""

import frappe

from spin_lab.engine.themes import SCORING_PROFILES

_ENGINE_DEFAULTS = dict(SCORING_PROFILES)   # snapshot before any DB override


def sync_profiles():
    """Merge enabled Scoring Profile records into the live SCORING_PROFILES
    dict (mutated in place so the pure engine sees the changes)."""
    if not frappe.db.exists("DocType", "Scoring Profile"):
        return
    rows = frappe.get_all("Scoring Profile", filters={"enabled": 1},
                          fields=["profile_key", "target_rtp"])
    if not rows:
        return
    merged = dict(_ENGINE_DEFAULTS)
    for r in rows:
        merged[r.profile_key] = r.target_rtp
    SCORING_PROFILES.clear()
    SCORING_PROFILES.update(merged)


@frappe.whitelist(allow_guest=True)
def list_profiles():
    """Display list for the frontend dropdowns (ordered by RTP)."""
    sync_profiles()
    if frappe.db.exists("DocType", "Scoring Profile"):
        rows = frappe.get_all(
            "Scoring Profile", filters={"enabled": 1},
            fields=["profile_key", "label", "target_rtp", "jurisdiction_note"],
            order_by="target_rtp asc")
        if rows:
            return [{"key": r.profile_key, "label": r.label,
                     "rtp": r.target_rtp, "note": r.jurisdiction_note}
                    for r in rows]
    return [{"key": k, "label": f"{k} · {round(v*100)}%", "rtp": v, "note": None}
            for k, v in sorted(_ENGINE_DEFAULTS.items(), key=lambda kv: kv[1])]
