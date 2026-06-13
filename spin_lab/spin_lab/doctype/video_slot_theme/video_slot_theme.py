import json

import frappe
from frappe.model.document import Document

from spin_lab.engine.video_slot import REELS, analytic_rtp, theme_from_config


class VideoSlotTheme(Document):
    def validate(self):
        if self.megaways and (self.expanding_wilds or self.walking_wilds):
            frappe.throw("Megaways cannot be combined with expanding or walking wilds.")
        if self.expanding_wilds and self.walking_wilds:
            frappe.throw("Choose either expanding wilds or walking wilds, not both.")
        theme = self.as_engine_theme()  # raises on structural problems
        try:
            r = analytic_rtp(theme)
        except AssertionError:
            frappe.throw(
                "Free-spin expectation diverges (retrigger factor >= 1). "
                "Reduce scatter counts or free-spin awards."
            )
        if r["total_rtp"] <= 0:
            frappe.throw("Theme has zero RTP - add at least one winning pay rule.")
        if theme.wild in theme.strips[0]:
            frappe.msgprint(
                "Note: wild on reel 1 is unusual (standard designs omit it).",
                indicator="orange",
            )
        self.rtp_summary = json.dumps(
            {
                "base_ways_share": round(r["base_ways_rtp"] / r["total_rtp"], 4),
                "scatter_share": round(r["scatter_rtp"] / r["total_rtp"], 4),
                "free_spins_share": round(r["free_spins_rtp"] / r["total_rtp"], 4),
                "p_free_spin_trigger": round(r["p_free_spin_trigger"], 6),
                "note": "Profiles scale pays so total RTP hits 95/100/105% exactly."
                        + (" Expanding-wild respin RTP is Monte-Carlo calibrated at runtime."
                           if self.expanding_wilds else ""),
            },
            indent=1,
        )

    def as_engine_theme(self):
        reel_counts = [{} for _ in range(REELS)]
        for row in self.reel_symbols:
            if not 1 <= row.reel <= REELS:
                frappe.throw(f"Reel must be 1-{REELS}, got {row.reel}")
            if row.count > 0:
                reel_counts[row.reel - 1][row.symbol] = row.count
        for i, c in enumerate(reel_counts):
            if not c:
                frappe.throw(f"Reel {i + 1} has no symbols")
        pay_table = {}
        for row in self.pay_rules:
            pays = {k: getattr(row, f"pay_{k}") or 0 for k in (3, 4, 5, 6)}
            pay_table[row.symbol] = {k: v for k, v in pays.items() if v > 0}
        scatter_pays, free_spins = {}, {}
        for row in self.scatter_tiers:
            scatter_pays[row.scatters] = row.pay_multiplier or 0
            free_spins[row.scatters] = row.free_spins or 0
        if not scatter_pays:
            frappe.throw("Add at least one scatter tier (e.g. 3 scatters)")
        expanding_reels = ()
        if self.expanding_wilds and (self.expanding_reels or "").strip():
            try:
                expanding_reels = tuple(
                    int(x) - 1 for x in self.expanding_reels.split(",") if x.strip()
                )
            except ValueError:
                frappe.throw("Expanding Reels must be comma-separated reel numbers, e.g. 2,3,4,5")
            if any(not 0 <= r < REELS for r in expanding_reels):
                frappe.throw(f"Expanding reels must be between 1 and {REELS}")
        return theme_from_config(
            {
                "name": self.theme_name,
                "expanding_wilds": bool(self.expanding_wilds),
                "both_ways": bool(self.both_ways),
                "sticky_wilds_fs": bool(self.sticky_wilds_fs),
                "walking_wilds": bool(self.walking_wilds),
                "megaways": bool(self.megaways),
                "expanding_reels": expanding_reels,
                "max_respins": self.max_respins or 3,
                "wild": self.wild_symbol,
                "scatter": self.scatter_symbol,
                "fs_multiplier": self.fs_multiplier or 2.0,
                "reel_counts": reel_counts,
                "pay_table": pay_table,
                "scatter_pays": scatter_pays,
                "free_spins": free_spins,
            }
        )
