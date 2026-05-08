frappe.ui.form.on("Tank Dip Reading", {
	fuel_type(frm) {
		const warehouseMap = {
			"FUEL-PMS": "Petrol Tank - NOG",
			"FUEL-AGO": "Diesel Tank - NOG",
			"FUEL-IK": "Paraffin Tank - NOG",
		};

		if (warehouseMap[frm.doc.fuel_type]) {
			frm.set_value("tank_warehouse", warehouseMap[frm.doc.fuel_type]);
		}
	},
});

