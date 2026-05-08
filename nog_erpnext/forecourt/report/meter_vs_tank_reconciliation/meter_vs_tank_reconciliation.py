from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	data = get_data(filters)
	chart = get_chart_data(data)
	report_summary = get_report_summary(data)
	return get_columns(), data, None, chart, report_summary


def get_columns():
	return [
		{"label": _("Fuel Type"), "fieldname": "fuel_type", "fieldtype": "Link", "options": "Item", "width": 140},
		{"label": _("Opening Dip"), "fieldname": "opening_dip", "fieldtype": "Float", "width": 120},
		{"label": _("Deliveries"), "fieldname": "deliveries", "fieldtype": "Float", "width": 120},
		{"label": _("Closing Dip"), "fieldname": "closing_dip", "fieldtype": "Float", "width": 120},
		{"label": _("Meter Sales"), "fieldname": "meter_sales", "fieldtype": "Float", "width": 120},
		{"label": _("Expected Closing"), "fieldname": "expected_closing", "fieldtype": "Float", "width": 140},
		{"label": _("Variance"), "fieldname": "variance", "fieldtype": "Float", "width": 120},
		{"label": _("Variance %"), "fieldname": "variance_percent", "fieldtype": "Percent", "width": 110},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
	]


def get_data(filters):
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	if not from_date or not to_date:
		frappe.throw(_("From Date and To Date are required."))

	fuel_types = filters.get("fuel_type")
	if fuel_types:
		fuel_types = [fuel_types]
	else:
		fuel_types = frappe.get_all(
			"Pump Nozzle Reading",
			filters={"docstatus": 1, "date": ["between", [from_date, to_date]]},
			pluck="fuel_type",
			distinct=True,
		)

	data = []
	for fuel_type in fuel_types:
		opening_dip = get_boundary_dip(fuel_type, from_date, "asc")
		closing_dip = get_boundary_dip(fuel_type, to_date, "desc")
		deliveries = get_delivery_litres(fuel_type, from_date, to_date)
		meter_sales = get_meter_sales(fuel_type, from_date, to_date)
		expected_closing = (opening_dip or 0) + deliveries - meter_sales
		variance = (closing_dip or 0) - expected_closing
		variance_percent = (variance / meter_sales * 100) if meter_sales else 0
		status = "OK" if abs(variance_percent) <= 0.3 else "Review"

		data.append(
			{
				"fuel_type": fuel_type,
				"opening_dip": opening_dip,
				"deliveries": deliveries,
				"closing_dip": closing_dip,
				"meter_sales": meter_sales,
				"expected_closing": expected_closing,
				"variance": variance,
				"variance_percent": variance_percent,
				"status": status,
			}
		)

	return data


def get_report_summary(data):
	total_meter_sales = sum(flt(row.get("meter_sales")) for row in data)
	total_deliveries = sum(flt(row.get("deliveries")) for row in data)
	total_variance = sum(flt(row.get("variance")) for row in data)
	review_count = sum(1 for row in data if row.get("status") == "Review")
	variance_percent = (total_variance / total_meter_sales * 100) if total_meter_sales else 0

	return [
		{
			"value": total_meter_sales,
			"label": _("Meter Sales"),
			"datatype": "Float",
			"indicator": "Blue",
		},
		{
			"value": total_deliveries,
			"label": _("Deliveries"),
			"datatype": "Float",
		},
		{
			"value": total_variance,
			"label": _("Net Variance"),
			"datatype": "Float",
			"indicator": "Green" if abs(variance_percent) <= 0.3 else "Red",
		},
		{
			"value": variance_percent,
			"label": _("Net Variance %"),
			"datatype": "Percent",
			"indicator": "Green" if abs(variance_percent) <= 0.3 else "Red",
		},
		{
			"value": review_count,
			"label": _("Rows to Review"),
			"datatype": "Int",
			"indicator": "Red" if review_count else "Green",
		},
	]


def get_chart_data(data):
	return {
		"data": {
			"labels": [row.get("fuel_type") for row in data],
			"datasets": [
				{"name": _("Variance"), "values": [flt(row.get("variance")) for row in data]}
			],
		},
		"type": "bar",
		"fieldtype": "Float",
	}


def get_boundary_dip(fuel_type: str, date: str, order: str):
	operator = ">=" if order == "asc" else "<="
	return frappe.db.get_value(
		"Tank Dip Reading",
		{"docstatus": 1, "fuel_type": fuel_type, "date": [operator, date]},
		"dip_litres",
		order_by=f"date {order}, creation {order}",
	)


def get_delivery_litres(fuel_type: str, from_date: str, to_date: str) -> float:
	return (
		frappe.db.sql(
			"""
			select sum(delivered_litres)
			from `tabFuel Delivery`
			where docstatus = 1 and fuel_type = %s and date between %s and %s
			""",
			(fuel_type, from_date, to_date),
		)[0][0]
		or 0
	)


def get_meter_sales(fuel_type: str, from_date: str, to_date: str) -> float:
	return (
		frappe.db.sql(
			"""
			select sum(litres_sold)
			from `tabPump Nozzle Reading`
			where docstatus = 1 and fuel_type = %s and date between %s and %s
			""",
			(fuel_type, from_date, to_date),
		)[0][0]
		or 0
	)
