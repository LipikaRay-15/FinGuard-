# FinGuard — Intelligent Financial Fraud & Risk Monitoring Platform

FinGuard is an enterprise-grade, clean-architecture platform written in Python and backed by MySQL. It is built to monitor, detect, and audit financial fraud and transaction risks in real-time.

---

## Technical Stack
* **Language:** Python (3.13.14)
* **Database:** MySQL
* **Key Libraries:** `mysql-connector-python`, `pandas`, `numpy`, `faker`, `schedule`, `tabulate`, `colorama`, `python-dotenv`

---

## Architectural Principles
1. **SOLID Design & OOP:** Strictly follow Object-Oriented Design and SOLID principles for testability, scalability, and clarity.
2. **Layered Architecture:** Clear division of concerns across presentation, service, rule engine, data mapping (repository), and persistence layers.
3. **Config-Driven Design:** System settings and connection parameters are loaded via environment variables (`.env`) through `config/settings.py` instead of hardcoding credentials.
4. **Resilient Exception Handling & Structured Logging:** Isolated logging channels for normal application flow, error auditing, and security/fraud triggers.

---

## Folder Structure
```text
FinGuard/
├── config/             # Environment loading and system settings
├── database/           # Connection pooling and basic drivers
├── models/             # Business domain entities (OOP models)
├── repositories/       # Data Access Object pattern / Repository patterns
├── services/           # Core business logic orchestrators
├── engines/            # Processing engines (e.g., rule matcher)
├── rules/              # Fraud detection rules (individual logic units)
├── analytics/          # Risk analytical engines and metrics calculations
├── scheduler/          # Chron jobs and scheduling orchestrations
├── simulator/          # Transaction generators and telemetry stream simulations
├── reports/            # PDF/CSV statement compilers
├── exceptions/         # Application custom enterprise exceptions
├── logs/               # Log outputs (application, error, and fraud)
├── tests/              # Unit, integration, and regression test suites
├── sql/                # SQL schema creation and migrations
├── main.py             # Entry point / System validation launcher
├── requirements.txt    # External dependencies
├── .env                # Private local environment credentials (ignored by git)
├── .gitignore          # File ignoring specifications
└── README.md           # Documentation
```

---

## Local Development Setup

### 1. Prerequisites
Ensure you have Python 3.8+ and MySQL Server (e.g., 8.0 or 8.4) installed and running on your system.

### 2. Configuration (`.env`)
Create a `.env` file in the root folder (or use the populated template):
```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_secure_password
MYSQL_DATABASE=finguard_db
```

### 3. Execution & Verification
To test the local installation, verify environment variables, database connectivity, and required packages, run:
```bash
python main.py
```
This script will execute startup checks, print a formatted status report to the terminal, and initialize the system logs.
