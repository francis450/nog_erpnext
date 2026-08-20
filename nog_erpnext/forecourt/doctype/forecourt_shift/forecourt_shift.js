frappe.ui.form.on("Forecourt Shift", {
	date(frm) {
		frm.trigger("set_hr_shift_defaults");
	},

	shift(frm) {
		frm.trigger("set_hr_shift_defaults");
	},

	set_hr_shift_defaults(frm) {
		if (!frm.doc.shift) return;

		frappe.call({
			method:
				"nog_erpnext.forecourt.doctype.forecourt_shift.forecourt_shift.get_forecourt_shift_defaults",
			args: {
				forecourt_shift: frm.doc.shift,
				date: frm.doc.date,
			},
			callback(r) {
				if (!r.message) return;

				if (r.message.hr_shift_type) {
					frm.set_value("hr_shift_type", r.message.hr_shift_type);
				}
				if (r.message.start_time && !frm.doc.start_time) {
					frm.set_value("start_time", r.message.start_time);
				}
				if (r.message.end_time && !frm.doc.end_time) {
					frm.set_value("end_time", r.message.end_time);
				}
			},
		});
	},
});
