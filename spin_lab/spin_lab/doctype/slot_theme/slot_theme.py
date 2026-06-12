import frappe
from frappe.model.document import Document

from spin_lab.engine.themes import Symbol, Theme, theoretical_rtp


class SlotTheme(Document):
    def validate(self):
        if not self.symbols:
            frappe.throw("A theme needs at least one symbol.")
        if not self.pay_rules:
            frappe.throw("A theme needs at least one pay rule.")
        symbols = {s.symbol for s in self.symbols}
        for rule in self.pay_rules:
            parts = rule.combination.split("|")
            if len(parts) != 3:
                frappe.throw(f"Combination must have 3 parts: {rule.combination}")
            for p in parts:
                if p != "*" and p not in symbols:
                    frappe.throw(f"Unknown symbol {p!r} in combination {rule.combination}")
        self.theoretical_rtp = theoretical_rtp(self.as_engine_theme())

    def as_engine_theme(self) -> Theme:
        return Theme(
            name=self.theme_name,
            volatility=self.volatility,
            description=self.description or "",
            symbols=tuple(Symbol(s.symbol, s.weight) for s in self.symbols),
            pay_table={r.combination: r.payout_multiplier for r in self.pay_rules},
        )
