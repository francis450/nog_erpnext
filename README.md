### Nog Erpnext

This is the ERPNext implementation for National Oil Githunguri — a multi-department petrol station and services complex in Githunguri, Kenya. The system is built as a custom Frappe app (nog_erpnext) that extends ERPNext with forecourt management, biometric attendance sync, and department-specific modules.

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app nog_erpnext
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/nog_erpnext
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
