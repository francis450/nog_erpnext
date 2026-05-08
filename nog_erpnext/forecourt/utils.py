from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint


COMPANY = "National Oil Githunguri"
FORECOURT_COST_CENTER = "Forecourt - NOG"
DEFAULT_WALK_IN_CUSTOMER = "Walk-in Customer"

FUEL_TANK_WAREHOUSE = {
	"PETROL": "Petrol Tank - NOG",
	"DIESEL": "Diesel Tank - NOG",
	"PARAFFIN": "Paraffin Tank - NOG",
}

FUEL_ITEM_ALIASES = {
	"FUEL-PMS": "PETROL",
	"PETROL": "PETROL",
	"Petrol": "PETROL",
	"PMS": "PETROL",
	"SUPER": "PETROL",
	"Super Petrol": "PETROL",
	"FUEL-AGO": "DIESEL",
	"DIESEL": "DIESEL",
	"Diesel": "DIESEL",
	"AGO": "DIESEL",
	"FUEL-IK": "PARAFFIN",
	"PARAFFIN": "PARAFFIN",
	"Paraffin": "PARAFFIN",
	"KEROSENE": "PARAFFIN",
	"Kerosene": "PARAFFIN",
	"IK": "PARAFFIN",
}

NOZZLE_ITEM = {
	1: "PETROL",
	2: "DIESEL",
	3: "PETROL",
	4: "DIESEL",
	5: "PETROL",
	6: "DIESEL",
	7: "PETROL",
	8: "DIESEL",
	9: "PETROL",
	10: "DIESEL",
	11: "PETROL",
	12: "DIESEL",
	13: "PARAFFIN",
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


@frappe.whitelist()
def get_tank_warehouse(item_code: str) -> str:
	settings_warehouse = get_tank_warehouse_from_settings(item_code)
	if settings_warehouse:
		return settings_warehouse

	canonical_item_code = get_canonical_fuel_item(item_code)
	warehouse = FUEL_TANK_WAREHOUSE.get(canonical_item_code)
	if not warehouse:
		frappe.throw(
			_(
				"No tank warehouse is configured for fuel item {0}. Add it under Forecourt Settings > Fuel Mappings."
			).format(frappe.bold(item_code))
		)
	return get_existing_warehouse(warehouse)


def get_tank_warehouse_from_settings(item_code: str | None) -> str | None:
	if not item_code or not frappe.db.exists("DocType", "Forecourt Settings"):
		return None

	try:
		settings = frappe.get_single("Forecourt Settings")
	except Exception:
		return None

	normalized_item = normalize_name(item_code).casefold()
	for mapping in settings.get("fuel_mappings"):
		fuel_item = normalize_name(mapping.fuel_item).casefold()
		aliases = get_mapping_aliases(mapping.aliases)

		if normalized_item == fuel_item or normalized_item in aliases:
			return mapping.tank_warehouse

	return None


def get_mapping_aliases(aliases: str | None) -> set[str]:
	return {
		normalize_name(alias).casefold()
		for alias in (aliases or "").replace("\n", ",").split(",")
		if normalize_name(alias)
	}


def get_existing_warehouse(warehouse: str) -> str:
	if frappe.db.exists("Warehouse", warehouse):
		return warehouse

	normalized_warehouse = normalize_name(warehouse)
	for candidate in frappe.get_all("Warehouse", pluck="name"):
		if normalize_name(candidate) == normalized_warehouse:
			return candidate

	return warehouse


def is_same_warehouse(left: str | None, right: str | None) -> bool:
	if not left or not right:
		return left == right

	return normalize_name(left) == normalize_name(right)


def normalize_name(value: str | None) -> str:
	return " ".join(str(value or "").split())


def get_canonical_fuel_item(item_code: str | None) -> str | None:
	if not item_code:
		return item_code

	return FUEL_ITEM_ALIASES.get(item_code) or FUEL_ITEM_ALIASES.get(str(item_code).strip()) or item_code


def get_nozzle_mapping(nozzle_no: int | str | None) -> dict[str, str] | None:
	nozzle_no = cint(nozzle_no)
	if not nozzle_no:
		return None

	settings_mapping = get_nozzle_mapping_from_settings(nozzle_no)
	if settings_mapping:
		return settings_mapping

	fuel_item = NOZZLE_ITEM.get(nozzle_no)
	pump_no = NOZZLE_PUMP.get(nozzle_no)
	if not fuel_item or not pump_no:
		return None

	return {"nozzle_no": nozzle_no, "pump_no": pump_no, "fuel_item": fuel_item}


def get_nozzle_mapping_from_settings(nozzle_no: int) -> dict[str, str] | None:
	if not frappe.db.exists("DocType", "Forecourt Settings"):
		return None

	try:
		settings = frappe.get_single("Forecourt Settings")
	except Exception:
		return None

	for mapping in settings.get("nozzle_mappings"):
		if cint(mapping.nozzle_no) == nozzle_no:
			return {
				"nozzle_no": nozzle_no,
				"pump_no": str(mapping.pump_no),
				"fuel_item": mapping.fuel_item,
			}

	return None


def get_default_customer() -> str:
	return frappe.conf.get("nog_forecourt_walk_in_customer") or DEFAULT_WALK_IN_CUSTOMER


def validate_nozzle_fuel_mapping(nozzle_no: int, pump_no: str | None, fuel_type: str | None) -> None:
	nozzle_mapping = get_nozzle_mapping(nozzle_no)
	if not nozzle_mapping:
		frappe.throw(_("Nozzle number must be between 1 and 13."))

	expected_item = nozzle_mapping["fuel_item"]
	canonical_fuel_type = get_canonical_fuel_item(fuel_type)
	canonical_expected_item = get_canonical_fuel_item(expected_item)
	if canonical_fuel_type and canonical_fuel_type != canonical_expected_item:
		frappe.throw(
			_("Nozzle {0} is configured for {1}, but this reading uses {2}.").format(
				nozzle_no, frappe.bold(expected_item), frappe.bold(fuel_type)
			)
		)

	expected_pump = nozzle_mapping["pump_no"]
	if pump_no and str(pump_no) != expected_pump:
		frappe.throw(_("Nozzle {0} belongs to Pump {1}.").format(nozzle_no, expected_pump))
