from __future__ import annotations

from datetime import datetime, time, timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class ForecourtShift(Document):
	def validate(self):
		self.set_hr_shift_type()
		self.set_shift_times_from_hr_shift()
		if self.end_time and self.start_time and self.end_time <= self.start_time:
			frappe.throw(_("End time must be after start time."))

	def on_submit(self):
		self.create_or_update_shift_assignment()

	def on_cancel(self):
		self.cancel_shift_assignment()

	def set_hr_shift_type(self):
		self.hr_shift_type = get_hr_shift_type(self.shift)

	def set_shift_times_from_hr_shift(self):
		if not self.hr_shift_type or not self.date:
			return

		start_time, end_time = frappe.db.get_value(
			"Shift Type", self.hr_shift_type, ["start_time", "end_time"]
		)
		if not start_time or not end_time:
			return

		start_datetime, end_datetime = get_shift_datetimes(self.date, start_time, end_time)
		if not self.start_time:
			self.start_time = start_datetime
		if not self.end_time:
			self.end_time = end_datetime

	def create_or_update_shift_assignment(self):
		if not self.hr_shift_type:
			frappe.throw(
				_("No HR Shift Type is mapped for Forecourt Shift {0}. Configure it in Forecourt Settings.").format(
					frappe.bold(self.shift)
				)
			)

		if not self.attendant:
			return

		if self.shift_assignment and frappe.db.exists("Shift Assignment", self.shift_assignment):
			assignment = frappe.get_doc("Shift Assignment", self.shift_assignment)
			if assignment.docstatus == 1:
				return
		else:
			assignment = get_existing_shift_assignment(self.attendant, self.hr_shift_type, self.date)
			if assignment:
				self.db_set("shift_assignment", assignment, update_modified=False)
				return

			assignment = frappe.new_doc("Shift Assignment")
			assignment.employee = self.attendant
			assignment.company = frappe.db.get_value("Employee", self.attendant, "company")
			assignment.shift_type = self.hr_shift_type
			assignment.start_date = self.date
			assignment.end_date = self.date
			assignment.status = "Active"
			assignment.flags.ignore_permissions = True
			assignment.insert()
			assignment.submit()

		self.db_set("shift_assignment", assignment.name, update_modified=False)

	def cancel_shift_assignment(self):
		if not self.shift_assignment or not frappe.db.exists("Shift Assignment", self.shift_assignment):
			return

		assignment = frappe.get_doc("Shift Assignment", self.shift_assignment)
		if assignment.docstatus != 1:
			return

		try:
			assignment.flags.ignore_permissions = True
			assignment.cancel()
		except Exception:
			frappe.msgprint(
				_(
					"Forecourt Shift was cancelled, but HR Shift Assignment {0} could not be cancelled because it is already linked to HR attendance/checkins."
				).format(frappe.bold(self.shift_assignment)),
				indicator="orange",
			)


def get_hr_shift_type(forecourt_shift: str | None) -> str | None:
	if not forecourt_shift:
		return None

	settings_shift = get_hr_shift_type_from_settings(forecourt_shift)
	if settings_shift:
		return settings_shift

	if frappe.db.exists("Shift Type", forecourt_shift):
		return forecourt_shift

	return None


def get_hr_shift_type_from_settings(forecourt_shift: str) -> str | None:
	if not frappe.db.exists("DocType", "Forecourt Settings"):
		return None

	settings = frappe.get_single("Forecourt Settings")
	for mapping in settings.get("shift_mappings"):
		if mapping.forecourt_shift == forecourt_shift:
			return mapping.hr_shift_type

	return None


def get_existing_shift_assignment(employee: str, shift_type: str, shift_date: str):
	existing = frappe.db.sql(
		"""
		select name
		from `tabShift Assignment`
		where employee = %s
			and shift_type = %s
			and docstatus = 1
			and status = 'Active'
			and start_date <= %s
			and (end_date is null or end_date >= %s)
		order by start_date desc
		limit 1
		""",
		(employee, shift_type, shift_date, shift_date),
		pluck=True,
	)
	return existing[0] if existing else None


def get_shift_datetimes(shift_date, start_time, end_time):
	shift_date = getdate(shift_date)
	start_datetime = datetime.combine(shift_date, time.min) + start_time
	end_datetime = datetime.combine(shift_date, time.min) + end_time
	if end_datetime <= start_datetime:
		end_datetime += timedelta(days=1)

	return start_datetime, end_datetime


@frappe.whitelist()
def get_forecourt_shift_defaults(forecourt_shift: str, date: str | None = None):
	hr_shift_type = get_hr_shift_type(forecourt_shift)
	if not hr_shift_type:
		return {}

	start_time, end_time = frappe.db.get_value("Shift Type", hr_shift_type, ["start_time", "end_time"])
	result = {"hr_shift_type": hr_shift_type}
	if date and start_time and end_time:
		start_datetime, end_datetime = get_shift_datetimes(date, start_time, end_time)
		result.update({"start_time": start_datetime, "end_time": end_datetime})

	return result
