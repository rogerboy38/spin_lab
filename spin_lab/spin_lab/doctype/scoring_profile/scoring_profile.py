import frappe
from frappe.model.document import Document


class ScoringProfile(Document):
    def validate(self):
        if self.target_rtp <= 0:
            frappe.throw("Target RTP must be positive.")
        if self.target_rtp > 2:
            frappe.throw("Target RTP looks wrong (>200%). Use 0.95 for 95%, not 95.")
