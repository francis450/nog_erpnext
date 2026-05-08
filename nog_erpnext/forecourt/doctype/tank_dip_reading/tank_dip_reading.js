frappe.ui.form.on("Tank Dip Reading", {
	fuel_type(frm) {
		if (!frm.doc.fuel_type) return;

		frappe.call({
			method: "nog_erpnext.forecourt.utils.get_tank_warehouse",
			args: {
				item_code: frm.doc.fuel_type,
			},
			callback(r) {
				if (r.message) {
					frm.set_value("tank_warehouse", r.message);
				}
			},
		});
	},
});
