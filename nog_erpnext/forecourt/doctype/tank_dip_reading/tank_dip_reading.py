from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nog_erpnext.forecourt.utils import get_tank_warehouse, is_same_warehouse


class TankDipReading(Document):
	def validate(self):
		if self.dip_litres < 0:
			frappe.throw(_("Dip litres cannot be negative."))

		if self.fuel_type:
			expected_warehouse = get_tank_warehouse(self.fuel_type)
			if self.tank_warehouse and not is_same_warehouse(self.tank_warehouse, expected_warehouse):
				frappe.throw(
					_("Fuel item {0} should use tank warehouse {1}.").format(
						frappe.bold(self.fuel_type), frappe.bold(expected_warehouse)
					)
				)
			self.tank_warehouse = self.tank_warehouse or expected_warehouse
