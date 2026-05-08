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

	unit_price(frm) {
		frm.trigger("calculate_totals");
	},

	payment_mode(frm) {
		frm.toggle_reqd("customer", frm.doc.payment_mode === "Fleet Account");
	},

	apply_nozzle_defaults(frm) {
		const nozzleMap = {
			1: ["1", "FUEL-PMS"],
			2: ["1", "FUEL-AGO"],
			3: ["1", "FUEL-PMS"],
			4: ["1", "FUEL-AGO"],
			5: ["2", "FUEL-PMS"],
			6: ["2", "FUEL-AGO"],
			7: ["2", "FUEL-PMS"],
			8: ["2", "FUEL-AGO"],
			9: ["3", "FUEL-PMS"],
			10: ["3", "FUEL-AGO"],
			11: ["3", "FUEL-PMS"],
			12: ["3", "FUEL-AGO"],
			13: ["4", "FUEL-IK"],
		};

		const defaults = nozzleMap[frm.doc.nozzle_no];
		if (!defaults) return;

		frm.set_value("pump_no", defaults[0]);
		frm.set_value("fuel_type", defaults[1]);
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

	calculate_totals(frm) {
		const litres = flt(frm.doc.closing_meter) - flt(frm.doc.opening_meter);
		frm.set_value("litres_sold", Math.max(litres, 0));
		frm.set_value("gross_amount", Math.max(litres, 0) * flt(frm.doc.unit_price));
	},
});
