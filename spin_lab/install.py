"""Post-install setup: seed the three default themes."""

import frappe

from spin_lab.engine.themes import DEFAULT_THEMES


def after_install():
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
