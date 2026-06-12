"""Scheduled maintenance jobs."""

import frappe

RETENTION_DAYS = 30


def prune_old_spins():
    """Delete simulation spins older than RETENTION_DAYS to keep the DB lean."""
    frappe.db.delete(
        "Slot Spin",
        {"creation": ("<", frappe.utils.add_days(frappe.utils.now(), -RETENTION_DAYS))},
    )
    frappe.db.commit()
