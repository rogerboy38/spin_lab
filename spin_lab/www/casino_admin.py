import frappe


def get_context(context):
    context.no_cache = 1
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/casino-admin"
        raise frappe.Redirect
    roles = frappe.get_roles()
    context.is_admin = "Casino Admin" in roles or "System Manager" in roles
    context.user = frappe.session.user
    return context
