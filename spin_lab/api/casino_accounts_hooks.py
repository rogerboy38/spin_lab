import frappe


def on_user_insert(doc, method=None):
    """Give any new Casino Player a wallet automatically."""
    roles = [r.role for r in (doc.get("roles") or [])]
    if "Casino Player" in roles and not frappe.db.exists("Casino Account", {"user": doc.name}):
        from spin_lab.api.casino_accounts import _ensure_account
        _ensure_account(doc.name)
