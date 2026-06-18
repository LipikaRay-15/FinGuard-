# FinGuard

Intelligent Financial Fraud & Risk Monitoring Platform

FinGuard is a high-performance, enterprise-grade transaction laundering and security audit platform. Engineered using Clean-Architecture design, FinGuard leverages a hybrid validation logic that connects a high-integrity MySQL schema with a strategy-driven python dynamic rules engine. It enables financial institutions to validate customer profiles, score transaction risks in real-time, route alerts, manage remediation cases, audit activity logs, and run telemetry-simulated stress tests.

---

## Table of Contents
1. [Overview](#overview)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Tech Stack](#tech-stack)
5. [Folder Structure](#folder-structure)
6. [Database Schema](#database-schema)
7. [Setup Instructions](#setup-instructions)
8. [Screenshots](#screenshots)
9. [Sample Fraud Scenarios](#sample-fraud-scenarios)
10. [Future Enhancements](#future-enhancements)
11. [Author](#author)

---

## Overview

In the modern financial ecosystem, real-time risk assessment is critical to mitigating carding, account takeover, coordinate jumps, and velocity laundering. FinGuard draws real-world inspiration from modern banking fraud engines. The platform parses transaction attributes (amounts, geographical coordinates, device fingerprints, merchant categories, merchant category codes) in real-time. It validates transactions against whitelists and blacklists at the database boundary, scans them against active risk rules, aggregates scores, and automatically assigns suspicious activity to investigation queues.

---

## Features

- **Customer Management**: Performs validation audits of customer names, email structure, Indian PAN card formats, mobile phone patterns, and unique bank accounts.
- **Device Tracking**: Tracks browser and device hardware fingerprints (SHA-256 hashes), mapping operating systems, IPs, and user agents. Updates connection logs with a `last_seen` historical timeline.
- **Transaction Engine**: Registers transactions, maps location coordinates by city, verifies customer states, calls the risk stored procedures, and handles payment status updates.
- **Dynamic Rule Engine**: Employs the **Strategy Pattern** to compare transaction parameters using operators like `>`, `<`, `=`, `between`, `in`, `contains` dynamically loaded from database records.
- **Fraud Detection Engine**: Runs parallel detection scans for all 11 core fraud rules, saving rules logs and dispatching alerts if rules are triggered.
- **Explainable Risk Analysis**: Generates formatted, human-readable risk summaries and recommended actions (e.g. Auto-Decline, Manual Review) suitable for fraud analysts.
- **Alert Management**: Manages alert lifecycles (statuses: OPEN, UNDER_REVIEW, RESOLVED, FALSE_POSITIVE, CLOSED; severities: LOW, MEDIUM, HIGH, CRITICAL) and logs list changes.
- **Case Management**: Uses the **State Pattern** to coordinate case transitions (OPEN -> UNDER_REVIEW -> ESCALATED -> RESOLVED -> CLOSED), recording investigator notes, remarks, resolutions, and timestamps.
- **Investigation Engine**: Compiles customer trust profiles, average transaction values, declined attempts, geographical centroids, device mappings, and chronological timelines.
- **Risk Profiles**: Computes and caches customer risk scores, triggering automatic risk history updates in MySQL database logs.
- **Analytics Engine**: Aggregates system metrics dashboards, compiling fraud percentage rates, top risky cities, risky merchants, and daily/hourly trends.
- **Report Generator**: Generates operations report summaries (Daily, Weekly, Monthly) and outputs raw transaction logs to formatted CSV streams.
- **Audit Logs**: Automatically saves historical change records (old vs. new value JSON snapshots) for rules toggles, case state changes, alert close notes, and customer creations.
- **Fraud Simulator**: Streams configurable, high-fidelity synthetic customers and transactions to stress-test rule thresholds.
- **CLI Management Terminal**: Provides a formatted command shell interface to run verification checks and perform operations.

---

## Architecture

FinGuard processes datasets sequentially through a layered, clean architecture pipeline to ensure strict data auditing:

```
Customer (Profile and device registration)
   ↓
Transaction Engine (Verifies status, saves pending entry)
   ↓
Event Store (Dispatches TRANSACTION_CREATED / TRANSACTION_FAILED events)
   ↓
Dynamic Rule Engine (Runs evaluations against active rules list)
   ↓
Risk Calculator (Aggregates risk points, determines severity level & data confidence)
   ↓
Rule Execution Logs (Persists snapshotted rules outputs to database)
   ↓
Alert Manager (Determines bypass/blocklist overrides, routes alerts if risk score >= 50)
   ↓
Case Management (Automatically spawns investigation cases, tracks analyst workflow states)
   ↓
Investigation Engine (Compiles customer behavioral summaries and chronological timelines)
   ↓
Analytics (Groups city metrics, category risks, daily and hourly trends)
   ↓
Reports (Compiles Daily/Weekly/Monthly operation summaries and CSV data exports)
```

---

## Tech Stack

- **Python**: Core programming language utilizing modular packages and thread-safe operations.
- **MySQL**: Relational database managing storage engine, stored procedures, constraints, views, and database triggers.
- **Object-Oriented Programming (OOP)**: Models system entities as rich domain classes (Customer, Transaction, Alert, Case, Device, FraudRule) with encapsulations.
- **SOLID Principles**: Strict adherence to SOLID principles (Single Responsibility, Open/Closed rules, Liskov Substitution, Interface Segregation, Dependency Inversion) to maximize maintainability.
- **Design Patterns**:
  - **Repository Pattern**: Abstract data queries mapped in repositories, decoupling services from raw SQL statements.
  - **Strategy Pattern**: Evaluates rules strategies dynamically using operator comparators without hardcoded values.
  - **State Pattern**: Enforces valid case workflow transitions (e.g. prevents closed cases from returning to open).
  - **Singleton Pattern**: Ensures single, thread-safe database connection instances.
  - **Observer Pattern**: Event manager publishing events asynchronously to notify decoupled auditing stores.

---

## Folder Structure

```text
FinGuard/
│
├── config/                 # Configurations & Logging setups
│   ├── __init__.py
│   └── settings.py
│
├── database/               # Database Singleton client
│   ├── __init__.py
│   └── database.py
│
├── models/                 # Domain Object Entities
│   ├── __init__.py
│   ├── customer.py
│   ├── device.py
│   ├── transaction.py
│   ├── alert.py
│   ├── case.py
│   └── fraud_rule.py
│
├── repositories/           # Repository Pattern Persistence Mappings
│   ├── __init__.py
│   ├── base_repository.py
│   ├── customer_repository.py
│   ├── device_repository.py
│   ├── transaction_repository.py
│   └── case_repository.py
│
├── services/               # Orchestrating Business Logic Services
│   ├── __init__.py
│   ├── customer_service.py
│   ├── device_service.py
│   ├── transaction_service.py
│   ├── alert_service.py
│   ├── case_service.py
│   ├── investigation_service.py
│   ├── analytics_service.py
│   └── audit_log_service.py
│
├── engines/                # Decision Computation Engines
│   ├── __init__.py
│   ├── transaction_engine.py
│   ├── fraud_detector.py
│   ├── fraud_detection_engine.py
│   ├── risk_calculator.py
│   ├── case_state_machine.py
│   ├── explainable_risk_engine.py
│   └── analytics_engine.py
│
├── reports/                # Statement compilers
│   ├── __init__.py
│   └── report_generator.py
│
├── scheduler/              # Chron workers tasks
│   ├── __init__.py
│   └── scheduler.py
│
├── simulator/              # Telemetry streams generator
│   ├── __init__.py
│   ├── customer_generator.py
│   ├── transaction_generator.py
│   └── fraud_simulator.py
│
├── exceptions/             # Central enterprise custom exceptions
│   ├── __init__.py
│   └── custom_exceptions.py
│
├── sql/                    # SQL DB creation scripts
│   └── schema.sql
│
├── tests/                  # Verification test suite
│   ├── __init__.py
│   ├── test_unit_models.py
│   ├── test_unit_risk_calculator.py
│   ├── test_integration_flow.py
│   ├── run_all_tests.py
│   └── test_simulator.py
│
└── main.py                 # Startup checker & CLI menu loop
```

---

## Database Schema

The platform contains 16 normalized tables and 3 reporting views in the MySQL schema:
1. `customers`: Customer accounts profiles.
2. `merchant_profiles`: Stores merchant trust and MCC codes (e.g. Supermarket, Casino).
3. `devices`: Browser fingerprints and last seen timestamps.
4. `fraud_rules`: Holds rule criteria, thresholds, and priority weights.
5. `transactions`: Historical ledger transactions.
6. `blacklisted_customers`: Blocked customer profiles.
7. `blacklisted_devices`: Stolen browser fingerprints registry.
8. `blocked_pans`: Card PAN blacklist table.
9. `blocked_accounts`: Blocked bank accounts.
10. `whitelisted_customers`: Exempted customer profile list.
11. `whitelisted_devices`: Trusted hardware signatures bypass list.
12. `events`: Central event auditing log timeline.
13. `alerts`: Security alert indexes.
14. `cases`: Investigation workflow board cases.
15. `risk_profiles`: Customer current risk registers cache.
16. `risk_history`: Risk change logs (audited by trigger).
17. `rule_execution_logs`: Historical rules scan logs.
18. `audit_logs`: Detailed JSON modification changes log.
19. `v_active_alerts` (View): Aggregates alerts with active open states.
20. `v_customer_risk_summary` (View): Links customers with current risk tiers.
21. `v_transaction_fraud_details` (View): Links transactions with trigger names.

---

## Setup Instructions

### 1. Prerequisites
Ensure you have Python 3.8+ and MySQL Server (8.0 or 8.4) installed and running locally.

### 2. Configuration Settings
Create a `.env` file in the `FinGuard` directory:
```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_secure_password
MYSQL_DATABASE=finguard_db
```

### 3. Setup Virtual Environment
Run the following commands in your terminal:
```bash
# Navigate to the FinGuard folder
cd FinGuard

# Create Python virtual environment
python -m venv venv

# Activate Virtual Environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate Virtual Environment (Linux / macOS)
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Running the Tests Suite
```bash
python tests/run_all_tests.py
```

### 6. Starting the CLI Management Terminal
```bash
python main.py
```

---

## Screenshots

*Placeholder section: visually capture interactive CLI menu flows, tabular analytics dashboards, and analyst human-readable risk summaries when running.*

---

## Sample Fraud Scenarios

1. **High Amount Fraud**: A transaction is processed with value `$15,000` (threshold `$10,000`). It triggers `High Transaction Amount`, adding `75` risk points (HIGH severity).
2. **Velocity Fraud**: A customer attempts 4 transactions in 10 minutes (threshold `3` per hour). It triggers `Rapid Velocity Limit`, adding `80` risk points (CRITICAL severity).
3. **New Device Fraud**: A transaction uses fingerprint hash `e3b0c442...` which is not in the customer's device list. It triggers `New Device` rule (severity: MEDIUM).
4. **Night Transactions**: A customer makes a cash checkout at `23:45`. It triggers `Night Transaction` rule (+40 points).
5. **Different City Fraud**: A Mumbai-based customer processes a payment with London coordinates. It triggers `Different City` rule (severity: MEDIUM).

---

## Future Enhancements

- **REST APIs**: Implement FastAPI/Flask integrations to allow external banking channels to ingest transactions.
- **Redis Caching**: Cache whitelist databases and customer risk scores in Redis for sub-millisecond lookups.
- **Docker**: Containerize the python engine and MySQL instances to run anywhere.
- **Kafka Pipeline**: Stream transactions using Apache Kafka topics for asynchronous processing.
- **Microservices**: Decouple the rules evaluation scanner into a microservices pattern.

---

## Author

**FinGuard Engineering & Architecture Group**  
*Enterprise Financial Risk Systems division.*
