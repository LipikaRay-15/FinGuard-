-- FinGuard Database Schema

-- Drop tables in reverse order of foreign keys
DROP TABLE IF EXISTS cases;
DROP TABLE IF EXISTS alerts;
DROP TABLE IF EXISTS rules;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS accounts;
DROP TABLE IF EXISTS users;

-- 1. Users Table
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    risk_level ENUM('LOW', 'MEDIUM', 'HIGH') DEFAULT 'LOW',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Accounts Table
CREATE TABLE accounts (
    account_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    account_number VARCHAR(30) UNIQUE NOT NULL,
    account_type ENUM('SAVINGS', 'CHECKING', 'CREDIT') DEFAULT 'CHECKING',
    balance DECIMAL(15, 2) DEFAULT 0.00,
    daily_limit DECIMAL(15, 2) DEFAULT 5000.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 3. Transactions Table
CREATE TABLE transactions (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    account_id INT NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    merchant VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    type ENUM('DEPOSIT', 'WITHDRAWAL', 'TRANSFER', 'PAYMENT') NOT NULL,
    channel ENUM('ATM', 'ONLINE', 'POS') NOT NULL,
    location VARCHAR(100) NOT NULL, -- Format: 'City, Country'
    ip_address VARCHAR(45),
    device VARCHAR(100),
    status ENUM('APPROVED', 'DECLINED', 'BLOCKED') DEFAULT 'APPROVED',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE
);

-- 4. Rules Table
CREATE TABLE rules (
    rule_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    criteria_json TEXT, -- Store dynamic parameters (e.g., {"limit": 10000})
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Alerts Table
CREATE TABLE alerts (
    alert_id INT AUTO_INCREMENT PRIMARY KEY,
    transaction_id INT NOT NULL,
    rule_id INT NOT NULL,
    risk_score INT NOT NULL, -- 0-100 scale
    reason TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id) ON DELETE CASCADE,
    FOREIGN KEY (rule_id) REFERENCES rules(rule_id) ON DELETE CASCADE
);

-- 6. Cases Table
CREATE TABLE cases (
    case_id INT AUTO_INCREMENT PRIMARY KEY,
    alert_id INT UNIQUE NOT NULL,
    status ENUM('OPEN', 'UNDER_REVIEW', 'RESOLVED_FRAUD', 'RESOLVED_FALSE_POSITIVE') DEFAULT 'OPEN',
    notes TEXT,
    assigned_to VARCHAR(50) DEFAULT 'System Engine',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id) ON DELETE CASCADE
);
