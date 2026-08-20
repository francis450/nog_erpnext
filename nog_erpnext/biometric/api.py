from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, now_datetime


DEFAULT_DEVICE_ID = "Hik-K1T341AMF"


@frappe.whitelist(methods=["POST"])
def sync_events(events: str | list[dict[str, Any]] | None = None, device_id: str | None = None):
	"""Receive Hikvision attendance events and create Employee Checkin records.

	The Windows sync script keeps polling the local device. ERPNext receives only
	the normalized event stream, stores an audit log, and deduplicates by event key.
	"""
	frappe.has_permission("Employee Checkin", "create", throw=True)

	payload = get_request_payload(events, device_id)
	device_id = payload.get("device_id") or DEFAULT_DEVICE_ID
	events = payload.get("events") or []

	if not isinstance(events, list):
		frappe.throw(_("events must be a list."))

	results = [process_event(event, device_id) for event in events]
	summary = {
		"received": len(events),
		"created": count_status(results, "Created"),
		"duplicates": count_status(results, "Duplicate"),
		"skipped": count_status(results, "Skipped"),
		"failed": count_status(results, "Failed"),
	}
	frappe.db.commit()

	return {"summary": summary, "results": results}


def get_request_payload(events, device_id):
	if events:
		return {
			"device_id": device_id,
			"events": frappe.parse_json(events) if isinstance(events, str) else events,
		}

	request_data = {}
	if getattr(frappe.local, "request", None):
		request_data = frappe.local.request.get_json(silent=True) or {}

	if isinstance(request_data, list):
		return {"device_id": device_id, "events": request_data}

	return request_data or {"device_id": device_id, "events": []}


def process_event(event: dict[str, Any], default_device_id: str):
	if not isinstance(event, dict):
		return {"status": "Failed", "error": _("Event must be an object.")}

	normalized = normalize_event(event, default_device_id)
	event_key = normalized["event_key"]
	existing_log = frappe.db.exists("Biometric Sync Log", {"event_key": event_key})
	if existing_log:
		return {"status": "Duplicate", "event_key": event_key, "sync_log": existing_log}

	if not normalized["employee_device_id"]:
		return insert_sync_log(normalized, "Skipped", error=_("Missing employee device ID."))

	if not normalized["event_time"]:
		return insert_sync_log(normalized, "Failed", error=_("Missing event timestamp."))

	employee = get_employee(normalized)
	if not employee:
		return insert_sync_log(
			normalized,
			"Skipped",
			error=_("No Employee found with attendance_device_id {0}.").format(
				frappe.bold(normalized["employee_device_id"])
			),
		)

	normalized["employee"] = employee

	duplicate_checkin = get_duplicate_checkin(normalized)
	if duplicate_checkin:
		return insert_sync_log(normalized, "Duplicate", employee_checkin=duplicate_checkin)

	try:
		checkin = frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": employee,
				"time": normalized["event_time"],
				"log_type": normalized["log_type"],
				"device_id": normalized["device_id"],
				"skip_auto_attendance": 0,
			}
		)
		checkin.insert(ignore_permissions=False)
	except Exception as exc:
		return insert_sync_log(normalized, "Failed", error=str(exc))

	return insert_sync_log(normalized, "Created", employee_checkin=checkin.name)


def normalize_event(event: dict[str, Any], default_device_id: str) -> dict[str, Any]:
	serial_no = cint(first_present(event, "serial_no", "serialNo", "event_serial_no"))
	employee_device_id = str(
		first_present(event, "employee_device_id", "employee_no", "employeeNoString", "biometric_user_id") or ""
	).strip()
	device_id = str(first_present(event, "device_id", "deviceID") or default_device_id or DEFAULT_DEVICE_ID)
	event_time = get_event_time(event)
	log_type = str(first_present(event, "log_type", "logType") or "IN").upper()
	if log_type not in {"IN", "OUT"}:
		log_type = "IN"

	method = first_present(event, "authentication_method", "method", "verify_mode", "currentVerifyMode")
	event_key = make_event_key(device_id, serial_no, employee_device_id, event_time)

	return {
		"event_key": event_key,
		"device_id": device_id,
		"serial_no": serial_no,
		"employee_device_id": employee_device_id,
		"employee": first_present(event, "employee"),
		"event_time": event_time,
		"log_type": log_type,
		"authentication_method": method,
		"raw_event": event,
	}


def get_event_time(event: dict[str, Any]):
	value = first_present(event, "timestamp", "time", "event_time")
	if not value:
		return None

	return get_datetime(value)


def make_event_key(device_id: str, serial_no: int, employee_device_id: str, event_time) -> str:
	if serial_no:
		return f"{device_id}:{serial_no}"

	time_key = event_time.strftime("%Y%m%d%H%M%S") if event_time else now_datetime().strftime("%Y%m%d%H%M%S%f")
	return f"{device_id}:{employee_device_id}:{time_key}"


def first_present(source: dict[str, Any], *keys: str):
	for key in keys:
		value = source.get(key)
		if value not in (None, ""):
			return value
	return None


def get_employee(event: dict[str, Any]):
	if event.get("employee") and frappe.db.exists("Employee", event["employee"]):
		return event["employee"]

	return frappe.db.get_value("Employee", {"attendance_device_id": event["employee_device_id"]}, "name")


def get_duplicate_checkin(event: dict[str, Any]):
	return frappe.db.exists(
		"Employee Checkin",
		{
			"employee": event["employee"],
			"time": event["event_time"],
			"log_type": event["log_type"],
		},
	)


def insert_sync_log(event: dict[str, Any], status: str, employee_checkin: str | None = None, error: str | None = None):
	log = frappe.get_doc(
		{
			"doctype": "Biometric Sync Log",
			"event_key": event["event_key"],
			"status": status,
			"device_id": event["device_id"],
			"serial_no": event["serial_no"],
			"employee_device_id": event["employee_device_id"],
			"employee": event.get("employee"),
			"event_time": event["event_time"],
			"log_type": event["log_type"],
			"authentication_method": event.get("authentication_method"),
			"employee_checkin": employee_checkin,
			"error": error,
			"raw_event": json.dumps(event["raw_event"], indent=2, default=str),
		}
	)
	log.insert(ignore_permissions=True)

	return {
		"status": status,
		"event_key": event["event_key"],
		"sync_log": log.name,
		"employee": event.get("employee"),
		"employee_checkin": employee_checkin,
		"error": error,
	}


def count_status(results: list[dict[str, Any]], status: str) -> int:
	return sum(1 for result in results if result.get("status") == status)
