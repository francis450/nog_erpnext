from __future__ import annotations

import frappe
from frappe import _


COMPANY = "National Oil Githunguri"
FORECOURT_COST_CENTER = "Forecourt - NOG"
DEFAULT_WALK_IN_CUSTOMER = "Walk-in Customer"

FUEL_TANK_WAREHOUSE = {
	"FUEL-PMS": "Petrol Tank - NOG",
	"FUEL-AGO": "Diesel Tank - NOG",
	"FUEL-IK": "Paraffin Tank - NOG",
}

NOZZLE_ITEM = {
	1: "FUEL-PMS",
	2: "FUEL-AGO",
	3: "FUEL-PMS",
	4: "FUEL-AGO",
	5: "FUEL-PMS",
	6: "FUEL-AGO",
	7: "FUEL-PMS",
	8: "FUEL-AGO",
	9: "FUEL-PMS",
	10: "FUEL-AGO",
	11: "FUEL-PMS",
	12: "FUEL-AGO",
	13: "FUEL-IK",
}

NOZZLE_PUMP = {
	1: "1",
	2: "1",
	3: "1",
	4: "1",
	5: "2",
	6: "2",
	7: "2",
	8: "2",
	9: "3",
	10: "3",
	11: "3",
	12: "3",
	13: "4",
}


def get_company() -> str:
	return frappe.db.get_default("company") or COMPANY


def get_tank_warehouse(item_code: str) -> str:
	warehouse = FUEL_TANK_WAREHOUSE.get(item_code)
	if not warehouse:
		frappe.throw(_("No tank warehouse is configured for fuel item {0}.").format(frappe.bold(item_code)))
	return warehouse


def get_default_customer() -> str:
	return frappe.conf.get("nog_forecourt_walk_in_customer") or DEFAULT_WALK_IN_CUSTOMER


def validate_nozzle_fuel_mapping(nozzle_no: int, pump_no: str | None, fuel_type: str | None) -> None:
	expected_item = NOZZLE_ITEM.get(nozzle_no)
	if not expected_item:
		frappe.throw(_("Nozzle number must be between 1 and 13."))

	if fuel_type and fuel_type != expected_item:
		frappe.throw(
			_("Nozzle {0} is configured for {1}, but this reading uses {2}.").format(
				nozzle_no, frappe.bold(expected_item), frappe.bold(fuel_type)
			)
		)

	expected_pump = NOZZLE_PUMP[nozzle_no]
	if pump_no and str(pump_no) != expected_pump:
		frappe.throw(_("Nozzle {0} belongs to Pump {1}.").format(nozzle_no, expected_pump))

