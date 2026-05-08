frappe.ui.form.on("Pump Nozzle Reading", {
	date(frm) {
		frm.trigger("fetch_last_reading");
	},

	shift(frm) {
		frm.trigger("fetch_last_reading");
	},

	nozzle_no(frm) {
		frm.trigger("apply_nozzle_defaults");
		frm.trigger("fetch_last_reading");
	},

	opening_meter(frm) {
		frm.trigger("calculate_totals");
	},

	closing_meter(frm) {
		frm.trigger("calculate_totals");
	},

	meter_rollover(frm) {
		frm.trigger("set_default_rollover_limit");
		frm.trigger("calculate_totals");
	},

	meter_rollover_limit(frm) {
		frm.trigger("calculate_totals");
	},

	unit_price(frm) {
		frm.trigger("calculate_totals");
	},

	payment_mode(frm) {
		frm.toggle_reqd("customer", frm.doc.payment_mode === "Fleet Account");
	},

	apply_nozzle_defaults(frm) {
		if (!frm.doc.nozzle_no) return;

		frappe.call({
			method:
				"nog_erpnext.forecourt.doctype.pump_nozzle_reading.pump_nozzle_reading.get_nozzle_defaults",
			args: {
				nozzle_no: frm.doc.nozzle_no,
			},
			callback(r) {
				if (!r.message) return;

				frm.set_value("pump_no", r.message.pump_no);
				frm.set_value("fuel_type", r.message.fuel_item);
			},
		});
	},

	fetch_last_reading(frm) {
		if (!frm.doc.nozzle_no || !frm.doc.date || frm.doc.__islocal === 0) return;

		frappe.call({
			method:
				"nog_erpnext.forecourt.doctype.pump_nozzle_reading.pump_nozzle_reading.get_last_reading",
			args: {
				nozzle_no: frm.doc.nozzle_no,
				date: frm.doc.date,
				shift: frm.doc.shift,
			},
			callback(r) {
				if (!r.message) return;

				if (!frm.doc.opening_meter) {
					frm.set_value("opening_meter", r.message.closing_meter);
				}
				if (!frm.doc.fuel_type && r.message.fuel_type) {
					frm.set_value("fuel_type", r.message.fuel_type);
				}
				if (!frm.doc.unit_price && r.message.unit_price) {
					frm.set_value("unit_price", r.message.unit_price);
				}
			},
		});
	},

	set_default_rollover_limit(frm) {
		if (!frm.doc.meter_rollover || frm.doc.meter_rollover_limit) return;

		frappe.db
			.get_single_value("Forecourt Settings", "default_meter_rollover_limit")
			.then((value) => {
				if (value && !frm.doc.meter_rollover_limit) {
					frm.set_value("meter_rollover_limit", value);
				}
			});
	},

	calculate_totals(frm) {
		const opening = flt(frm.doc.opening_meter);
		const closing = flt(frm.doc.closing_meter);
		let litres = closing - opening;

		if (frm.doc.meter_rollover && closing < opening) {
			litres = flt(frm.doc.meter_rollover_limit) - opening + closing;
		}

		frm.set_value("litres_sold", Math.max(litres, 0));
		frm.set_value("gross_amount", Math.max(litres, 0) * flt(frm.doc.unit_price));
	},
});
