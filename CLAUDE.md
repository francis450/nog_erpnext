# CLAUDE.md — National Oil Githunguri ERPNext Project

## Project Overview

This is the ERPNext implementation for **National Oil Githunguri** — a multi-department petrol station and services complex in Githunguri, Kenya. The system is built as a custom Frappe app (`nog_erpnext`) that extends ERPNext with forecourt management, biometric attendance sync, and department-specific modules.

**Company:** National Oil Githunguri  
**ERPNext Company Name:** `National Oil Githunguri`  
**App Name:** `nog_erpnext`  
**Branch:** `main`  
**ERPNext Version:** v15 (Frappe v15)

---

## Repository Structure

```
nog_erpnext/
├── CLAUDE.md
├── setup.py
├── requirements.txt
├── nog_erpnext/
│   ├── __init__.py
│   ├── hooks.py
│   ├── modules.txt
│   ├── patches.txt
│   │
│   ├── forecourt/                    # Fuel management module
│   │   ├── doctype/
│   │   │   ├── pump_nozzle_reading/
│   │   │   ├── fuel_delivery/
│   │   │   ├── tank_dip_reading/
│   │   │   └── forecourt_shift/
│   │   ├── report/
│   │   │   ├── daily_forecourt_summary/
│   │   │   ├── meter_vs_tank_reconciliation/
│   │   │   └── fuel_sales_by_nozzle/
│   │   └── page/
│   │       └── forecourt_dashboard/
│   │
│   ├── biometric/                    # Hikvision attendance sync
│   │   ├── doctype/
│   │   │   └── biometric_sync_log/
│   │   ├── utils/
│   │   │   ├── hik_sync.py           # Device polling logic
│   │   │   └── erpnext_checkin.py    # ERPNext Employee Checkin writer
│   │   └── scheduled_tasks.py
│   │
│   ├── carwash/                      # Car wash module
│   │   └── doctype/
│   │       ├── carwash_job/
│   │       └── carwash_package/
│   │
│   ├── spa/                          # Spa module
│   │   └── doctype/
│   │       ├── spa_appointment/
│   │       └── spa_service/
│   │
│   ├── gym/                          # Gym module
│   │   └── doctype/
│   │       ├── gym_membership/
│   │       └── gym_checkin/
│   │
│   ├── laundry/                      # Laundry module
│   │   └── doctype/
│   │       └── laundry_job/
│   │
│   └── public/
│       ├── js/
│       └── css/
│
├── scripts/
│   ├── hik_sync.py                   # Standalone biometric sync (Windows)
│   └── get_employees.py              # Device employee export utility
```

---

## Development Commands

```bash
# Install app on bench
bench get-app nog_erpnext https://github.com/bigbrokenya/nog_erpnext
bench --site nationaloil.bigbro.co.ke install-app nog_erpnext

# Run development server
cd ~/frappe-bench
bench start

# Create new DocType
bench --site nationaloil.bigbro.co.ke console  # then frappe.new_doc(...)

# Run migrations after schema changes
bench --site nationaloil.bigbro.co.ke migrate

# Clear cache after JS/Python changes
bench --site nationaloil.bigbro.co.ke clear-cache
bench build --app nog_erpnext

# Run tests
bench --site nationaloil.bigbro.co.ke run-tests --app nog_erpnext

# Scheduler (runs background jobs including biometric sync)
bench --site nationaloil.bigbro.co.ke enable-scheduler
bench schedule  # development only

# Frappe console (Python REPL with full frappe context)
bench --site nationaloil.bigbro.co.ke console
```

---

## Architecture Principles

### 1. Native ERPNext First
Always use or extend existing ERPNext DocTypes before creating custom ones. Check before building:

| Need | Use This Native DocType |
|------|------------------------|
| Fuel stock | `Warehouse` + `Item` + `Stock Entry` |
| Fuel sales | `Sales Invoice` / `POS Invoice` |
| Fuel purchase | `Purchase Receipt` |
| Attendance | `Employee Checkin` → `Attendance` |
| Salary | `Salary Slip` via `Payroll Entry` |
| Expenses | `Expense Claim` / `Purchase Invoice` |
| Fleet customers | `Customer` with credit limit |
| Suppliers | `Supplier` (Kenya Power, G4S etc.) |
| Budgets | `Budget` with cost centre |

### 2. Custom DocTypes for Forecourt-Specific Data
ERPNext has no forecourt module. These DocTypes are custom to `nog_erpnext`:
- `Pump Nozzle Reading` — daily meter reading per nozzle
- `Tank Dip Reading` — daily physical tank measurement
- `Forecourt Shift` — shift open/close with attendant assignment
- `Fuel Delivery` — tanker delivery record linked to Purchase Receipt

### 3. Hooks over Monkey-patching
Never override core ERPNext Python methods directly. Use Frappe hooks:

```python
# hooks.py — correct pattern
doc_events = {
    "Employee Checkin": {
        "after_insert": "nog_erpnext.biometric.hooks.after_checkin_insert"
    },
    "Pump Nozzle Reading": {
        "on_submit": "nog_erpnext.forecourt.hooks.create_sales_invoice"
    }
}

scheduler_events = {
    "every_5_minutes": [
        "nog_erpnext.biometric.scheduled_tasks.sync_biometric_device"
    ],
    "daily_long": [
        "nog_erpnext.forecourt.scheduled_tasks.generate_daily_summary"
    ]
}
```

### 4. Frappe Permissions Model
Use ERPNext roles — do not build custom auth. Key roles for this project:

| Role | Access |
|------|--------|
| `Forecourt Supervisor` | Submit Pump Nozzle Reading, view daily summary |
| `Forecourt Attendant` | Create (not submit) Pump Nozzle Reading |
| `Station Manager` | All forecourt + all department reports |
| `HR Manager` | Attendance, payroll, employee records |
| `Accounts User` | Invoices, payments, reconciliation |

---

## Module Specifications

### Forecourt Module

**Pump layout:**
- Pump 1, 2, 3: 4 nozzles each (2× Petrol, 2× Diesel — one per side)
- Pump 4: 1 nozzle (Paraffin)
- Total: 13 nozzles

**Items (UOM = Litre):**
```
Petrol (Super)   → Item Code: FUEL-PMS
Diesel (AGO)     → Item Code: FUEL-AGO
Paraffin (IK)    → Item Code: FUEL-IK
```

**Warehouses:**
```
Forecourt - NOG
├── Petrol Tank - NOG      (feeds nozzles 1,3,5,7,9,11)
├── Diesel Tank - NOG      (feeds nozzles 2,4,6,8,10,12)
└── Paraffin Tank - NOG    (feeds nozzle 13)
```

**Pump Nozzle Reading DocType fields:**
```python
fields = [
    {"fieldname": "date",            "fieldtype": "Date",        "reqd": 1},
    {"fieldname": "shift",           "fieldtype": "Select",      "options": "Morning\nAfternoon\nNight", "reqd": 1},
    {"fieldname": "pump_no",         "fieldtype": "Select",      "options": "1\n2\n3\n4", "reqd": 1},
    {"fieldname": "nozzle_no",       "fieldtype": "Int",         "reqd": 1},
    {"fieldname": "fuel_type",       "fieldtype": "Link",        "options": "Item", "reqd": 1},
    {"fieldname": "attendant",       "fieldtype": "Link",        "options": "Employee"},
    {"fieldname": "opening_meter",   "fieldtype": "Float",       "reqd": 1},
    {"fieldname": "closing_meter",   "fieldtype": "Float",       "reqd": 1},
    {"fieldname": "litres_sold",     "fieldtype": "Float",       "read_only": 1},  # auto
    {"fieldname": "unit_price",      "fieldtype": "Currency",    "reqd": 1},
    {"fieldname": "gross_amount",    "fieldtype": "Currency",    "read_only": 1},  # auto
    {"fieldname": "payment_mode",    "fieldtype": "Select",      "options": "Cash\nM-Pesa\nVisa/Mastercard\nFleet Account"},
    {"fieldname": "customer",        "fieldtype": "Link",        "options": "Customer"},  # for fleet
    {"fieldname": "sales_invoice",   "fieldtype": "Link",        "options": "Sales Invoice", "read_only": 1},
]
```

**Key formula (Python controller):**
```python
def validate(self):
    if self.closing_meter < self.opening_meter:
        frappe.throw("Closing meter cannot be less than opening meter")
    self.litres_sold = self.closing_meter - self.opening_meter
    self.gross_amount = self.litres_sold * self.unit_price

def on_submit(self):
    # Create Sales Invoice for fleet; POS Invoice for cash/card/mpesa
    if self.payment_mode == "Fleet Account":
        self._create_fleet_invoice()
    else:
        self._create_pos_invoice()
    # Deduct stock from relevant tank warehouse
    self._post_stock_entry()
```

**Reconciliation formula:**
```
Tank variance = (Opening dip + Deliveries) - Closing dip - Sum(Meter litres sold)
Acceptable variance threshold = 0.3% of total litres sold
Cash variance = Sum(Gross amount) - (Cash collected + M-Pesa + Card + Fleet invoiced)
```

### Biometric Module

**Device:** Hikvision DS-K1T341AMF  
**IP:** 192.168.1.106  
**Auth:** HTTP Digest — admin / [stored in frappe.conf or Site Config, never hardcoded]  
**Timezone correction:** Device reports UTC+9, actual timezone UTC+3 → subtract 6 hours  
**Sync method:** Scheduled task every 5 minutes via `scheduler_events`

**State tracking:** Last synced `serialNo` stored in `Biometric Sync Log` DocType (not a file).

**Authentication event minor codes:**
```python
AUTH_MINOR_CODES = {
    75:  "face",         # Authenticated via Face
    104: "face",         # Face (alternate mode)
    38:  "fingerprint",  # Authenticated via Fingerprint
    8:   "card",         # Card
}
MAJOR_CODE_AUTH = 5  # Only process major=5 events
```

**ERPNext mapping:** Device `employeeNoString` → ERPNext `Employee.attendance_device_id`

**Produces:** `Employee Checkin` records. ERPNext's native HR module processes these into `Attendance` via Shift Type configuration.

### HR & Payroll (Native ERPNext — minimal customization)

Use standard ERPNext HR module. Configuration required:
- Shift Types: `Morning Shift`, `Afternoon Shift`, `Night Shift` per department
- Holiday List: `Kenya Public Holidays 2026` (apply to all employees)
- Salary Components: Basic, House Allowance, Transport, PAYE, NSSF (KES 200 employee / 200 employer post-2023 amendment), NHIF → SHA (KES 500+), Housing Levy (1.5% gross), HELB (if applicable)
- Payroll Period: Monthly, processed via `Payroll Entry`

### Accounts (Native ERPNext)

**Cost Centres** mirror departments:
```
National Oil Githunguri
├── Forecourt - NOG
├── Car Wash - NOG
├── Spa - NOG
├── Gym - NOG
├── Laundry - NOG
├── Minimart - NOG
├── Restaurant - NOG
├── Service Bay - NOG
├── Hotel - NOG
└── Admin - NOG
```

**Key Suppliers to create:**
```
Kenya Power and Lighting Co. (KPLC)
Ministry of Water
G4S Security Kenya
Texas Alarm
DSTV (MultiChoice Kenya)
National Oil Corporation of Kenya (NOCK)  # fuel supplier
Safaricom PLC  # airtime + M-Pesa charges
Catering Levy Trustees
```

---

## Coding Conventions

### Python (Frappe/ERPNext)

```python
# Always use frappe.get_doc / frappe.new_doc — never raw SQL inserts
doc = frappe.new_doc("Pump Nozzle Reading")
doc.date = frappe.utils.today()
doc.insert()

# Use frappe.db.get_value for single field lookups (faster than get_doc)
price = frappe.db.get_value("Item Price", 
    {"item_code": "FUEL-PMS", "price_list": "Standard Selling"}, 
    "price_list_rate")

# Transactions: always use frappe.db.savepoint or let Frappe handle via submit
# Never commit inside a loop

# Throw user-facing errors with frappe.throw (translatable)
frappe.throw(_("Closing meter {0} is less than opening meter {1}").format(
    self.closing_meter, self.opening_meter))

# Log system events (not user errors) with frappe.log_error
frappe.log_error(frappe.get_traceback(), "Biometric Sync Failed")

# Permissions: always check before data access in API endpoints
frappe.has_permission("Pump Nozzle Reading", "write", throw=True)
```

### JavaScript (Frappe Client)

```javascript
// Use frappe.call for server methods — never raw fetch to /api/resource
frappe.call({
    method: "nog_erpnext.forecourt.doctype.pump_nozzle_reading.pump_nozzle_reading.get_last_reading",
    args: { nozzle_no: frm.doc.nozzle_no, date: frm.doc.date },
    callback(r) {
        if (r.message) {
            frm.set_value("opening_meter", r.message.closing_meter);
        }
    }
});

// Auto-populate opening meter from previous reading
frappe.ui.form.on("Pump Nozzle Reading", {
    nozzle_no(frm) {
        if (frm.doc.nozzle_no && frm.doc.date) {
            frm.trigger("fetch_last_reading");
        }
    }
});

// Currency fields: always use frappe.format_currency
frappe.format_currency(frm.doc.gross_amount, "KES");
```

### DocType JSON (schema)
- Always set `is_submittable: 1` for transactional DocTypes (Pump Nozzle Reading, Laundry Job, etc.)
- Link fields to native DocTypes wherever possible (`Employee`, `Customer`, `Item`, `Warehouse`)
- Use `fetch_from` to auto-populate fields from linked docs (reduces user input errors)
- Every custom DocType needs `naming_rule` defined (e.g. `NOG-PMR-.YYYY.-.#####`)

---

## Environment & Configuration

### Site Config (`site_config.json`) — sensitive values
```json
{
    "hikvision_device_ip": "192.168.1.106",
    "hikvision_user": "admin",
    "hikvision_password": "<encrypted>",
    "hikvision_tz_offset_device": 9,
    "hikvision_tz_offset_actual": 3,
    "erc_pump_price_api": ""
}
```
Access in Python: `frappe.conf.hikvision_device_ip`  
**Never hardcode credentials in Python files.**

### Key Item Codes (do not change — used in controller logic)
```
FUEL-PMS   = Petrol (Super)
FUEL-AGO   = Diesel (AGO)
FUEL-IK    = Paraffin (IK)
```

### Key Warehouse Names (do not change)
```
Petrol Tank - NOG
Diesel Tank - NOG
Paraffin Tank - NOG
```

### POS Profiles
```
Forecourt POS - NOG     # Forecourt cash/mpesa/card sales
Car Wash POS - NOG      # Car wash walk-in billing
Minimart POS - NOG      # Minimart sales
```

---

## Integration Map

```
Hikvision DS-K1T341AMF (192.168.1.106)
    └── ISAPI /AccessControl/AcsEvent  (HTTP Digest, JSON, security=0)
        └── nog_erpnext.biometric.scheduled_tasks.sync_biometric_device (every 5 min)
            └── Employee Checkin (native ERPNext)
                └── Attendance (native ERPNext, processed by shift)
                    └── Payroll Entry → Salary Slip (native ERPNext)

Forecourt Supervisor (PDQ Android tablet)
    └── ERPNext Mobile / Desk → Pump Nozzle Reading (nog_erpnext custom)
        ├── Sales Invoice / POS Invoice (native ERPNext)
        └── Stock Entry — Material Issue from Tank Warehouse (native ERPNext)

Fuel Tanker Delivery
    └── Purchase Receipt (native ERPNext)
        └── Stock Entry — Material Receipt into Tank Warehouse (native ERPNext)
```

---

## Implementation Phases

| Phase | Module | Status | Priority |
|-------|--------|--------|----------|
| 0 | Employees, departments, biometric | ✅ Complete | — |
| 1 | Shifts, leave, payroll (PAYE/NSSF/NHIF) | 🔄 Next | High |
| 2 | Chart of accounts, suppliers, cost centres | 🔄 Next | High |
| 3 | Forecourt (Pump Nozzle Reading + reconciliation) | ⬜ Planned | High |
| 3 | Car Wash job cards + POS | ⬜ Planned | Medium |
| 3 | Spa appointments | ⬜ Planned | Medium |
| 3 | Gym memberships | ⬜ Planned | Medium |
| 3 | Laundry job tracking | ⬜ Planned | Medium |
| 3 | Service Bay job cards | ⬜ Planned | Medium |
| 4 | Minimart POS integration | ⬜ Planned | Medium |
| 5 | Restaurant (Samba POS migration) | ⬜ Planned | Low |
| 5 | Hotel room management | ⬜ Planned | Low |
| 5 | Cross-department analytics dashboard | ⬜ Planned | Low |

---

## Known Issues & Decisions

- **Device timezone:** Hikvision device clock is set to UTC+9 (Japan). Do NOT fix on device until confirmed — apply -6 hour correction in sync code. Track in `Biometric Sync Log`.
- **Employee 1000 (INTERGRATOR BIGBRO):** System integrator test account on device. Mapped to HR-EMP-00002. Exclude from attendance reports via `is_system_user` flag.
- **5 employees with no department:** HR-EMP-00005, 00006, 00008, 00011, 00053. Assign departments before running payroll.
- **Minimart POS:** Uses a local POS system. Integration deferred — manual daily journal entry until API is confirmed.
- **Restaurant:** Running Samba POS. Migration to ERPNext deferred to Phase 5.
- **Fuel dispenser brand:** Unknown at time of writing. Manual meter entry implemented first. Revisit for direct integration (RS-485 / Gilbarco / Tatsuno API) once confirmed.
