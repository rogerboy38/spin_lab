import frappe
from frappe.model.document import Document

from spin_lab.engine.progressive_math import draw_mhb_trigger
from spin_lab.engine.rng import make_rng


class ProgressiveMeter(Document):
    def validate(self):
        if self.meter_type == "Must-Hit-By":
            if not self.must_hit_max or self.must_hit_max <= (self.seed or 0):
                frappe.throw("Must-Hit-By maximum must exceed the seed.")
            if not self.trigger_threshold or not (
                self.seed <= self.trigger_threshold <= self.must_hit_max
            ):
                self.trigger_threshold = draw_mhb_trigger(
                    self.seed, self.must_hit_max, make_rng()
                )
        elif not self.hit_probability or self.hit_probability <= 0:
            frappe.throw("RNG progressives need a positive hit probability.")
        if not self.current_value:
            self.current_value = self.seed
