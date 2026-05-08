from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.document import Document

from nog_erpnext.forecourt.utils import (
	FORECOURT_COST_CENTER,
	get_company,
	get_default_customer,
	get_nozzle_mapping,
	get_tank_warehouse,
	validate_nozzle_fuel_mapping,
)


class PumpNozzleReading(Document):
	def validate(self):
		self.validate_meter_values()
		validate_nozzle_fuel_mapping(self.nozzle_no, self.pump_no, self.fuel_type)
		self.calculate_totals()
		self.validate_payment_details()

	def on_submit(self):
		if not self.sales_invoice:
			self.db_set("sales_invoice", self.create_sales_invoice().name, update_modified=False)

		if not self.stock_entry:
			self.db_set("stock_entry", self.create_stock_entry().name, update_modified=False)

	def on_cancel(self):
		self.cancel_linked_doc("Stock Entry", self.stock_entry)
		self.cancel_linked_doc("Sales Invoice", self.sales_invoice)

	def validate_meter_values(self):
		opening_meter = flt(self.opening_meter)
		closing_meter = flt(self.closing_meter)

		if closing_meter >= opening_meter:
			return

		if not self.meter_rollover:
			frappe.throw(
				_(
					"Closing meter {0} cannot be less than opening meter {1}. "
					"If the physical meter rolled over, tick Meter Rollover and set the rollover limit."
				).format(
					closing_meter, opening_meter
				)
			)

		rollover_limit = flt(self.meter_rollover_limit)
		if rollover_limit <= opening_meter:
			frappe.throw(
				_("Rollover Limit must be greater than Opening Meter when Meter Rollover is ticked.")
			)

	def calculate_totals(self):
		opening_meter = flt(self.opening_meter)
		closing_meter = flt(self.closing_meter)

		if self.meter_rollover and closing_meter < opening_meter:
			self.litres_sold = flt(self.meter_rollover_limit) - opening_meter + closing_meter
		else:
			self.litres_sold = closing_meter - opening_meter

		self.gross_amount = self.litres_sold * (self.unit_price or 0)

	def validate_payment_details(self):
		if self.payment_mode == "Fleet Account" and not self.customer:
			frappe.throw(_("Customer is required when payment mode is Fleet Account."))

	def create_sales_invoice(self):
		company = get_company()
		is_fleet = self.payment_mode == "Fleet Account"
		customer = self.customer if is_fleet else self.customer or get_default_customer()

		invoice = frappe.new_doc("Sales Invoice")
		invoice.company = company
		invoice.customer = customer
		invoice.posting_date = self.date
		invoice.due_date = self.date
		invoice.is_pos = 0 if is_fleet else 1
		invoice.update_stock = 0
		invoice.append(
			"items",
			{
				"item_code": self.fuel_type,
				"qty": self.litres_sold,
				"rate": self.unit_price,
				"cost_center": FORECOURT_COST_CENTER,
			},
		)

		if not is_fleet:
			self.add_pos_payment(invoice)

		invoice.flags.ignore_permissions = True
		invoice.insert()
		invoice.submit()
		return invoice

	def add_pos_payment(self, invoice):
		mode_of_payment = self.get_mode_of_payment()
		if not mode_of_payment:
			return

		invoice.append(
			"payments",
			{
				"mode_of_payment": mode_of_payment,
				"amount": self.gross_amount,
			},
		)

	def get_mode_of_payment(self):
		if self.payment_mode == "M-Pesa":
			return frappe.conf.get("nog_forecourt_mpesa_mode_of_payment") or "M-Pesa"
		if self.payment_mode == "Visa/Mastercard":
			return frappe.conf.get("nog_forecourt_card_mode_of_payment") or "Visa/Mastercard"
		if self.payment_mode == "Cash":
			return frappe.conf.get("nog_forecourt_cash_mode_of_payment") or "Cash"
		return None

	def create_stock_entry(self):
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.company = get_company()
		stock_entry.stock_entry_type = "Material Issue"
		stock_entry.posting_date = self.date
		stock_entry.append(
			"items",
			{
				"item_code": self.fuel_type,
				"qty": self.litres_sold,
				"s_warehouse": get_tank_warehouse(self.fuel_type),
				"cost_center": FORECOURT_COST_CENTER,
			},
		)
		stock_entry.flags.ignore_permissions = True
		stock_entry.insert()
		stock_entry.submit()
		return stock_entry

	def cancel_linked_doc(self, doctype: str, name: str | None):
		if not name:
			return

		doc = frappe.get_doc(doctype, name)
		if doc.docstatus == 1:
			doc.flags.ignore_permissions = True
			doc.cancel()


@frappe.whitelist()
def get_nozzle_defaults(nozzle_no: int):
	frappe.has_permission("Pump Nozzle Reading", "read", throw=True)
	return get_nozzle_mapping(nozzle_no)


@frappe.whitelist()
def get_last_reading(nozzle_no: int, date: str | None = None, shift: str | None = None):
	frappe.has_permission("Pump Nozzle Reading", "read", throw=True)

	filters = {"nozzle_no": nozzle_no, "docstatus": ["<", 2]}
	if date:
		filters["date"] = ["<=", date]

	fields = ["name", "date", "shift", "closing_meter", "fuel_type", "unit_price"]
	readings = frappe.get_all(
		"Pump Nozzle Reading",
		filters=filters,
		fields=fields,
		order_by="date desc, creation desc",
		limit=5,
	)

	if not readings:
		return None

	if shift and date:
		for reading in readings:
			if reading.date == date and reading.shift == shift:
				continue
			return reading

	return readings[0]
