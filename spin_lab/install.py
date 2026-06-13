"""Post-install setup: seed the three default themes."""

import frappe

from spin_lab.engine.themes import DEFAULT_THEMES
from spin_lab.engine.video_slot import all_video_configs


def after_install():
    seed_all()


def after_migrate():
    seed_all()


def seed_all():
    seed_casino_roles()
    seed_scoring_profiles()
    seed_classic_themes()
    seed_video_themes()
    seed_progressive_meters()


def seed_classic_themes():
    for theme in DEFAULT_THEMES.values():
        if frappe.db.exists("Slot Theme", theme.name):
            continue
        doc = frappe.new_doc("Slot Theme")
        doc.theme_name = theme.name
        doc.volatility = theme.volatility
        doc.description = theme.description
        for sym in theme.symbols:
            doc.append("symbols", {"symbol": sym.symbol, "weight": sym.weight})
        for combo, mult in theme.pay_table.items():
            doc.append("pay_rules", {"combination": combo, "payout_multiplier": mult})
        doc.insert(ignore_permissions=True)
    frappe.db.commit()


def seed_video_themes():
    """Seed every built-in video theme as an editable Video Slot Theme record."""
    if not frappe.db.exists("DocType", "Video Slot Theme"):
        return  # first migrate not done yet
    for cfg in all_video_configs():
        _seed_one_video_theme(cfg)


def _seed_one_video_theme(cfg):
    doc_name = cfg["name"] + " (DB)"  # distinct from the code-defined original
    if frappe.db.exists("Video Slot Theme", doc_name):
        return
    doc = frappe.new_doc("Video Slot Theme")
    doc.theme_name = doc_name
    doc.wild_symbol = cfg["wild"]
    doc.scatter_symbol = cfg["scatter"]
    doc.fs_multiplier = cfg["fs_multiplier"]
    doc.expanding_wilds = 1 if cfg.get("expanding_wilds") else 0
    doc.both_ways = 1 if cfg.get("both_ways") else 0
    doc.sticky_wilds_fs = 1 if cfg.get("sticky_wilds_fs") else 0
    doc.walking_wilds = 1 if cfg.get("walking_wilds") else 0
    doc.megaways = 1 if cfg.get("megaways") else 0
    doc.expanding_reels = ",".join(str(r + 1) for r in cfg.get("expanding_reels", ()))
    doc.max_respins = cfg.get("max_respins", 3)
    for i, counts in enumerate(cfg["reel_counts"], start=1):
        for sym, n in counts.items():
            doc.append("reel_symbols", {"reel": i, "symbol": sym, "count": n})
    for sym, pays in cfg["pay_table"].items():
        doc.append("pay_rules", {"symbol": sym,
                                 **{f"pay_{k}": v for k, v in pays.items()}})
    for n in sorted(cfg["scatter_pays"]):
        doc.append("scatter_tiers", {
            "scatters": n,
            "pay_multiplier": cfg["scatter_pays"][n],
            "free_spins": cfg["free_spins"].get(n, 0),
        })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()


DEMO_METERS = [
    # name, type, seed, c, p (per unit bet), must_hit_max
    ("MINI", "Standalone", 20.0, 0.005, 1 / 2_000, None),
    ("MINOR", "Linked", 100.0, 0.01, 1 / 20_000, None),
    ("MAJOR", "Wide Area", 1_000.0, 0.015, 1 / 200_000, None),
    ("GRAND", "Must-Hit-By", 5_000.0, 0.02, 0, 10_000.0),
]


def seed_progressive_meters():
    if not frappe.db.exists("DocType", "Progressive Meter"):
        return
    for name, mtype, seed, c, p, mhb in DEMO_METERS:
        if frappe.db.exists("Progressive Meter", name):
            continue
        doc = frappe.new_doc("Progressive Meter")
        doc.meter_name = name
        doc.meter_type = mtype
        doc.seed = seed
        doc.contribution_rate = c
        doc.hit_probability = p
        doc.must_hit_max = mhb
        doc.enabled = 1
        doc.insert(ignore_permissions=True)
    frappe.db.commit()


DEMO_PROFILES = [
    # key, label, rtp, note
    ("nevada_min", "Nevada min · 75%", 0.75, "US Nevada legal MINIMUM RTP (regulated, certified)."),
    ("loose_85", "loose market · 85%", 0.85, "Loose/under-regulated market — e.g. Mexico has no mandated payout floor."),
    ("tight_90", "tight · 90%", 0.90, "Tight but legal in stricter US states (NJ floor is 83%)."),
    ("casino_edge", "casino_edge · 95%", 0.95, "Typical competitive commercial RTP."),
    ("fair", "fair · 100%", 1.00, "Zero house edge — study pure variance."),
    ("player_edge", "player_edge · 105%", 1.05, "Hypothetical +EV; never offered commercially."),
]


def seed_scoring_profiles():
    if not frappe.db.exists("DocType", "Scoring Profile"):
        return
    for key, label, rtp, note in DEMO_PROFILES:
        if frappe.db.exists("Scoring Profile", key):
            continue
        doc = frappe.new_doc("Scoring Profile")
        doc.profile_key = key
        doc.label = label
        doc.target_rtp = rtp
        doc.jurisdiction_note = note
        doc.enabled = 1
        doc.insert(ignore_permissions=True)
    frappe.db.commit()


def seed_casino_roles():
    for role, desk in (("Casino Admin", 1), ("Casino Player", 0)):
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role,
                            "desk_access": desk}).insert(ignore_permissions=True)
    # the existing Administrator becomes the dealer/admin
    if frappe.db.exists("User", "Administrator"):
        try:
            frappe.get_doc("User", "Administrator").add_roles("Casino Admin")
        except Exception:
            pass
    frappe.db.commit()
