from __future__ import annotations

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 110},
		{"label": _("Shift"), "fieldname": "shift", "fieldtype": "Data", "width": 110},
		{"label": _("Fuel Type"), "fieldname": "fuel_type", "fieldtype": "Link", "options": "Item", "width": 130},
		{"label": _("Litres Sold"), "fieldname": "litres_sold", "fieldtype": "Float", "width": 120},
		{"label": _("Gross Amount"), "fieldname": "gross_amount", "fieldtype": "Currency", "width": 140},
		{"label": _("Cash"), "fieldname": "cash_amount", "fieldtype": "Currency", "width": 120},
		{"label": _("M-Pesa"), "fieldname": "mpesa_amount", "fieldtype": "Currency", "width": 120},
		{"label": _("Card"), "fieldname": "card_amount", "fieldtype": "Currency", "width": 120},
		{"label": _("Fleet"), "fieldname": "fleet_amount", "fieldtype": "Currency", "width": 120},
	]


def get_data(filters):
	conditions = ["docstatus = 1"]
	values = {}

	if filters.get("from_date"):
		conditions.append("date >= %(from_date)s")
		values["from_date"] = filters.from_date

	if filters.get("to_date"):
		conditions.append("date <= %(to_date)s")
		values["to_date"] = filters.to_date

	if filters.get("fuel_type"):
		conditions.append("fuel_type = %(fuel_type)s")
		values["fuel_type"] = filters.fuel_type

	if filters.get("shift"):
		conditions.append("shift = %(shift)s")
		values["shift"] = filters.shift

	return frappe.db.sql(
		f"""
		select
			date,
			shift,
			fuel_type,
			sum(litres_sold) as litres_sold,
			sum(gross_amount) as gross_amount,
			sum(case when payment_mode = 'Cash' then gross_amount else 0 end) as cash_amount,
			sum(case when payment_mode = 'M-Pesa' then gross_amount else 0 end) as mpesa_amount,
			sum(case when payment_mode = 'Visa/Mastercard' then gross_amount else 0 end) as card_amount,
			sum(case when payment_mode = 'Fleet Account' then gross_amount else 0 end) as fleet_amount
		from `tabPump Nozzle Reading`
		where {" and ".join(conditions)}
		group by date, shift, fuel_type
		order by date desc, shift, fuel_type
		""",
		values,
		as_dict=True,
	)

