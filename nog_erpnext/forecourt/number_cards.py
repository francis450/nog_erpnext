from __future__ import annotations

import frappe
from frappe.utils import get_first_day, today


def get_value(sql: str, values: dict | None = None):
	return frappe.db.sql(sql, values or {}, as_dict=True)[0].value or 0


@frappe.whitelist()
def today_litres_sold():
	return {
		"value": get_value(
			"""
			select sum(litres_sold) as value
			from `tabPump Nozzle Reading`
			where docstatus = 1 and date = %(date)s
			""",
			{"date": today()},
		),
		"fieldtype": "Float",
		"route": ["query-report", "Daily Forecourt Summary"],
		"route_options": {"from_date": today(), "to_date": today()},
	}


@frappe.whitelist()
def today_gross_sales():
	return {
		"value": get_value(
			"""
			select sum(gross_amount) as value
			from `tabPump Nozzle Reading`
			where docstatus = 1 and date = %(date)s
			""",
			{"date": today()},
		),
		"fieldtype": "Currency",
		"route": ["query-report", "Daily Forecourt Summary"],
		"route_options": {"from_date": today(), "to_date": today()},
	}


@frappe.whitelist()
def open_shifts():
	return {
		"value": get_value(
			"""
			select count(*) as value
			from `tabForecourt Shift`
			where docstatus < 2 and status = 'Open'
			"""
		),
		"fieldtype": "Int",
		"route": ["List", "Forecourt Shift"],
		"route_options": {"status": "Open"},
	}


@frappe.whitelist()
def month_delivery_litres():
	first_day = get_first_day(today())
	return {
		"value": get_value(
			"""
			select sum(delivered_litres) as value
			from `tabFuel Delivery`
			where docstatus = 1 and date >= %(from_date)s
			""",
			{"from_date": first_day},
		),
		"fieldtype": "Float",
		"route": ["List", "Fuel Delivery"],
		"route_options": {"date": [">=", first_day]},
	}

