"""Post-install setup: seed the three default themes."""

import frappe

from spin_lab.engine.themes import DEFAULT_THEMES
from spin_lab.engine.video_slot import deep_sea_config


def after_install():
    seed_all()


def after_migrate():
    seed_all()


def seed_all():
    seed_classic_themes()
    seed_video_themes()


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
    """Seed the built-in video theme as an editable Video Slot Theme record."""
    if not frappe.db.exists("DocType", "Video Slot Theme"):
        return  # first migrate not done yet
    cfg = deep_sea_config()
    doc_name = cfg["name"] + " (DB)"  # distinct from the code-defined original
    if frappe.db.exists("Video Slot Theme", doc_name):
        return
    doc = frappe.new_doc("Video Slot Theme")
    doc.theme_name = doc_name
    doc.wild_symbol = cfg["wild"]
    doc.scatter_symbol = cfg["scatter"]
    doc.fs_multiplier = cfg["fs_multiplier"]
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
