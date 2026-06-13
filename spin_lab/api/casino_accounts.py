"""Casino accounts — server-side wallets with admin/player roles.

The wallet balance is NEVER trusted from the client: every change is made
server-side in a whitelisted method keyed off frappe.session.user. Admins
(Casino Admin role) manage players; players see and spend only their own."""

import frappe

START_CHIPS = 1000.0


def _is_admin():
    roles = frappe.get_roles()
    return "Casino Admin" in roles or "System Manager" in roles


def _account_name(user):
    return frappe.db.get_value("Casino Account", {"user": user}, "name")


def _ensure_account(user, color="#ffd86b"):
    if frappe.db.exists("Casino Account", {"user": user}):
        return
    doc = frappe.new_doc("Casino Account")
    doc.user = user
    doc.balance = START_CHIPS
    doc.color = color
    doc.insert(ignore_permissions=True)
    frappe.db.commit()


@frappe.whitelist()
def whoami():
    user = frappe.session.user
    if user == "Guest":
        return {"guest": True}
    if not frappe.db.exists("Casino Account", {"user": user}):
        # auto-provision a wallet for any logged-in user the first time
        _ensure_account(user)
    bal, color, name = frappe.db.get_value(
        "Casino Account", {"user": user}, ["balance", "color", "player_name"]) or (None, None, None)
    return {"guest": False, "user": user, "is_admin": _is_admin(),
            "balance": bal, "color": color or "#ffd86b",
            "name": name or user.split("@")[0]}


@frappe.whitelist()
def adjust(delta):
    """Apply a net change to the caller's own balance (server-authoritative)."""
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Login required")
    delta = float(delta)
    cur = frappe.db.get_value("Casino Account", {"user": user}, "balance")
    if cur is None:
        _ensure_account(user)
        cur = START_CHIPS
    new = round(max(0.0, cur + delta), 2)
    frappe.db.set_value("Casino Account", {"user": user}, "balance", new, update_modified=False)
    if delta < 0:
        frappe.db.set_value("Casino Account", {"user": user}, "lifetime_staked",
                            (frappe.db.get_value("Casino Account", {"user": user}, "lifetime_staked") or 0) - delta,
                            update_modified=False)
    frappe.db.commit()
    return {"balance": new}


# ── admin (dealer) tools ──
@frappe.whitelist()
def list_accounts():
    frappe.only_for("Casino Admin") if "Casino Admin" in frappe.get_roles() else frappe.only_for("System Manager")
    rows = frappe.get_all("Casino Account",
                          fields=["user", "player_name", "balance", "color"],
                          order_by="balance desc")
    return rows


@frappe.whitelist()
def admin_set_balance(user, amount):
    if not _is_admin():
        frappe.throw("Admins only", frappe.PermissionError)
    frappe.db.set_value("Casino Account", {"user": user}, "balance", round(float(amount), 2), update_modified=False)
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist()
def admin_credit(user, amount):
    if not _is_admin():
        frappe.throw("Admins only", frappe.PermissionError)
    cur = frappe.db.get_value("Casino Account", {"user": user}, "balance") or 0
    frappe.db.set_value("Casino Account", {"user": user}, "balance", round(cur + float(amount), 2), update_modified=False)
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist()
def admin_create_player(email, first_name, password, start=START_CHIPS):
    if not _is_admin():
        frappe.throw("Admins only", frappe.PermissionError)
    from frappe.utils.password import update_password
    if not frappe.db.exists("User", email):
        u = frappe.get_doc({"doctype": "User", "email": email, "first_name": first_name,
                            "send_welcome_email": 0, "enabled": 1, "user_type": "Website User"})
        u.flags.ignore_permissions = True
        u.insert(ignore_permissions=True)
        u.add_roles("Casino Player")
        update_password(email, password)
    _ensure_account(email)
    frappe.db.set_value("Casino Account", {"user": email}, "balance", float(start), update_modified=False)
    frappe.db.commit()
    return {"ok": True, "user": email}
