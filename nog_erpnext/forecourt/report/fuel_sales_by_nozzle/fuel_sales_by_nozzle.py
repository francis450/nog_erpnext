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
		{"label": _("Pump"), "fieldname": "pump_no", "fieldtype": "Data", "width": 90},
		{"label": _("Nozzle"), "fieldname": "nozzle_no", "fieldtype": "Int", "width": 90},
		{"label": _("Fuel Type"), "fieldname": "fuel_type", "fieldtype": "Link", "options": "Item", "width": 140},
		{"label": _("Readings"), "fieldname": "reading_count", "fieldtype": "Int", "width": 100},
		{"label": _("Litres Sold"), "fieldname": "litres_sold", "fieldtype": "Float", "width": 130},
		{"label": _("Gross Amount"), "fieldname": "gross_amount", "fieldtype": "Currency", "width": 140},
		{"label": _("Average Price"), "fieldname": "average_price", "fieldtype": "Currency", "width": 130},
	]


def get_data(filters):
	conditions = ["docstatus = 1"]
	values = {}

	for field in ("from_date", "to_date", "fuel_type", "shift"):
		if not filters.get(field):
			continue
		if field == "from_date":
			conditions.append("date >= %(from_date)s")
		elif field == "to_date":
			conditions.append("date <= %(to_date)s")
		else:
			conditions.append(f"{field} = %({field})s")
		values[field] = filters[field]

	return frappe.db.sql(
		f"""
		select
			pump_no,
			nozzle_no,
			fuel_type,
			count(*) as reading_count,
			sum(litres_sold) as litres_sold,
			sum(gross_amount) as gross_amount,
			case
				when sum(litres_sold) = 0 then 0
				else sum(gross_amount) / sum(litres_sold)
			end as average_price
		from `tabPump Nozzle Reading`
		where {" and ".join(conditions)}
		group by pump_no, nozzle_no, fuel_type
		order by cast(pump_no as unsigned), nozzle_no
		""",
		values,
		as_dict=True,
	)


def get_report_summary(data):
	total_readings = sum(flt(row.get("reading_count")) for row in data)
	total_litres = sum(flt(row.get("litres_sold")) for row in data)
	total_sales = sum(flt(row.get("gross_amount")) for row in data)
	average_price = total_sales / total_litres if total_litres else 0
	top_nozzle = get_top_nozzle(data)

	return [
		{"value": total_readings, "label": _("Readings"), "datatype": "Int"},
		{
			"value": total_litres,
			"label": _("Total Litres"),
			"datatype": "Float",
			"indicator": "Blue",
		},
		{
			"value": total_sales,
			"label": _("Gross Sales"),
			"datatype": "Currency",
			"indicator": "Green" if total_sales else "Red",
		},
		{
			"value": average_price,
			"label": _("Average Price"),
			"datatype": "Currency",
		},
		{
			"value": top_nozzle,
			"label": _("Top Nozzle"),
			"datatype": "Data",
			"indicator": "Green" if top_nozzle else "Red",
		},
	]


def get_top_nozzle(data):
	if not data:
		return ""

	row = max(data, key=lambda item: flt(item.get("litres_sold")))
	if not flt(row.get("litres_sold")):
		return ""

	return _("Pump {0} / Nozzle {1}").format(row.get("pump_no"), row.get("nozzle_no"))


def get_chart_data(data):
	chart_rows = sorted(data, key=lambda row: flt(row.get("litres_sold")), reverse=True)[:20]
	labels = [
		_("P{0} N{1}").format(row.get("pump_no"), row.get("nozzle_no")) for row in chart_rows
	]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Litres Sold"), "values": [flt(row.get("litres_sold")) for row in chart_rows]}
			],
		},
		"type": "bar",
		"fieldtype": "Float",
	}
