from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from nog_erpnext.forecourt.utils import get_tank_warehouse, is_same_warehouse


class FuelDelivery(Document):
	def validate(self):
		if self.delivered_litres <= 0:
			frappe.throw(_("Delivered litres must be greater than zero."))

		if self.fuel_type:
			expected_warehouse = get_tank_warehouse(self.fuel_type)
			if self.tank_warehouse and not is_same_warehouse(self.tank_warehouse, expected_warehouse):
				frappe.throw(
					_("Fuel item {0} should use tank warehouse {1}.").format(
						frappe.bold(self.fuel_type), frappe.bold(expected_warehouse)
					)
				)
			self.tank_warehouse = self.tank_warehouse or expected_warehouse

		if self.purchase_receipt:
			pr_docstatus = frappe.db.get_value("Purchase Receipt", self.purchase_receipt, "docstatus")
			if pr_docstatus != 1:
				frappe.throw(_("Linked Purchase Receipt must be submitted."))
