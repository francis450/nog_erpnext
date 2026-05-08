from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class ForecourtShift(Document):
	def validate(self):
		if self.end_time and self.start_time and self.end_time <= self.start_time:
			frappe.throw(_("End time must be after start time."))

