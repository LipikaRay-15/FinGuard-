-- ========================================================================
-- FinGuard – Intelligent Financial Fraud & Risk Monitoring Platform
-- Module 1: Complete Enterprise-Grade Database Schema Design
-- Target Database: MySQL 8.0+ / 8.4+ (InnoDB Engine)
-- ========================================================================

-- Disable foreign key checks temporarily during setup
SET FOREIGN_KEY_CHECKS = 0;

-- Drop existing database assets if they exist (Reverse dependency order)
DROP TABLE IF EXISTS rule_execution_logs;
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS risk_history;
DROP TABLE IF EXISTS risk_profiles;
DROP TABLE IF EXISTS cases;
DROP TABLE IF EXISTS alerts;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS whitelisted_devices;
DROP TABLE IF EXISTS whitelisted_customers;
DROP TABLE IF EXISTS blacklisted_devices;
DROP TABLE IF EXISTS blacklisted_customers;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS fraud_rules;
DROP TABLE IF EXISTS devices;
DROP TABLE IF EXISTS merchant_profiles;
DROP TABLE IF EXISTS customers;

DROP VIEW IF EXISTS v_transaction_fraud_details;
DROP VIEW IF EXISTS v_customer_risk_summary;
DROP VIEW IF EXISTS v_active_alerts;

DROP PROCEDURE IF EXISTS sp_assess_transaction_risk;

-- Re-enable foreign key checks
SET FOREIGN_KEY_CHECKS = 1;

-- ========================================================================
-- 1. TABLE CREATIONS
-- ========================================================================

-- Table: customers
CREATE TABLE customers (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_customer_email UNIQUE (email),
    CONSTRAINT uq_customer_phone UNIQUE (phone),
    CONSTRAINT chk_customer_status CHECK (status IN ('ACTIVE', 'SUSPENDED', 'BLOCKED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: merchant_profiles
CREATE TABLE merchant_profiles (
    merchant_id INT AUTO_INCREMENT PRIMARY KEY,
    merchant_name VARCHAR(100) NOT NULL,
    merchant_category_code VARCHAR(4) NOT NULL, -- MCC (e.g. 7995 for gambling)
    risk_level VARCHAR(10) DEFAULT 'LOW',
    trust_score INT DEFAULT 100,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_merchant_risk_level CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH')),
    CONSTRAINT chk_merchant_trust_score CHECK (trust_score BETWEEN 0 AND 100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: devices
CREATE TABLE devices (
    device_id INT AUTO_INCREMENT PRIMARY KEY,
    device_fingerprint VARCHAR(64) NOT NULL, -- SHA-256 fingerprint hash
    ip_address VARCHAR(45) NOT NULL,
    operating_system VARCHAR(50),
    user_agent VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_device_fingerprint UNIQUE (device_fingerprint)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: fraud_rules
CREATE TABLE fraud_rules (
    rule_id INT AUTO_INCREMENT PRIMARY KEY,
    rule_name VARCHAR(100) NOT NULL,
    description TEXT,
    criteria_json JSON NOT NULL, -- Store rule-specific numeric variables
    risk_score INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_rule_name UNIQUE (rule_name),
    CONSTRAINT chk_rule_risk_score CHECK (risk_score BETWEEN 0 AND 100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: transactions
CREATE TABLE transactions (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    merchant_id INT,
    device_id INT,
    amount DECIMAL(15, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    transaction_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'PENDING',
    location_latitude DECIMAL(10, 8),
    location_longitude DECIMAL(11, 8),
    transaction_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_tx_customer FOREIGN KEY (customer_id) REFERENCES customers (customer_id) ON DELETE RESTRICT,
    CONSTRAINT fk_tx_merchant FOREIGN KEY (merchant_id) REFERENCES merchant_profiles (merchant_id) ON DELETE SET NULL,
    CONSTRAINT fk_tx_device FOREIGN KEY (device_id) REFERENCES devices (device_id) ON DELETE SET NULL,
    CONSTRAINT chk_tx_amount CHECK (amount >= 0.00),
    CONSTRAINT chk_tx_type CHECK (transaction_type IN ('PURCHASE', 'WITHDRAWAL', 'TRANSFER', 'DEPOSIT')),
    CONSTRAINT chk_tx_status CHECK (status IN ('PENDING', 'APPROVED', 'DECLINED', 'FLAGGED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: blacklisted_customers
CREATE TABLE blacklisted_customers (
    blacklist_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    reason VARCHAR(255) NOT NULL,
    listed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_bl_customer UNIQUE (customer_id),
    CONSTRAINT fk_bl_customer FOREIGN KEY (customer_id) REFERENCES customers (customer_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: blacklisted_devices
CREATE TABLE blacklisted_devices (
    blacklist_id INT AUTO_INCREMENT PRIMARY KEY,
    device_id INT NOT NULL,
    reason VARCHAR(255) NOT NULL,
    listed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_bl_device UNIQUE (device_id),
    CONSTRAINT fk_bl_device FOREIGN KEY (device_id) REFERENCES devices (device_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: whitelisted_customers
CREATE TABLE whitelisted_customers (
    whitelist_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    reason VARCHAR(255),
    listed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_wl_customer UNIQUE (customer_id),
    CONSTRAINT fk_wl_customer FOREIGN KEY (customer_id) REFERENCES customers (customer_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: whitelisted_devices
CREATE TABLE whitelisted_devices (
    whitelist_id INT AUTO_INCREMENT PRIMARY KEY,
    device_id INT NOT NULL,
    reason VARCHAR(255),
    listed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_wl_device UNIQUE (device_id),
    CONSTRAINT fk_wl_device FOREIGN KEY (device_id) REFERENCES devices (device_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: events
CREATE TABLE events (
    event_id INT AUTO_INCREMENT PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL, -- e.g. LOGIN, LOGOUT, PASSWORD_RESET
    customer_id INT,
    ip_address VARCHAR(45),
    details JSON,
    event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_event_customer FOREIGN KEY (customer_id) REFERENCES customers (customer_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: alerts
CREATE TABLE alerts (
    alert_id INT AUTO_INCREMENT PRIMARY KEY,
    transaction_id INT NOT NULL,
    customer_id INT NOT NULL,
    risk_score INT NOT NULL,
    status VARCHAR(20) DEFAULT 'OPEN',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_alert_transaction UNIQUE (transaction_id),
    CONSTRAINT fk_alert_transaction FOREIGN KEY (transaction_id) REFERENCES transactions (transaction_id) ON DELETE CASCADE,
    CONSTRAINT fk_alert_customer FOREIGN KEY (customer_id) REFERENCES customers (customer_id) ON DELETE CASCADE,
    CONSTRAINT chk_alert_risk_score CHECK (risk_score BETWEEN 0 AND 100),
    CONSTRAINT chk_alert_status CHECK (status IN ('OPEN', 'UNDER_REVIEW', 'RESOLVED_FALSE_POSITIVE', 'RESOLVED_TRUE_POSITIVE'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: cases
CREATE TABLE cases (
    case_id INT AUTO_INCREMENT PRIMARY KEY,
    alert_id INT NOT NULL,
    assigned_to VARCHAR(100) DEFAULT NULL, -- Analyst assigning
    status VARCHAR(20) DEFAULT 'NEW',
    priority VARCHAR(10) DEFAULT 'MEDIUM',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_case_alert UNIQUE (alert_id),
    CONSTRAINT fk_case_alert FOREIGN KEY (alert_id) REFERENCES alerts (alert_id) ON DELETE CASCADE,
    CONSTRAINT chk_case_status CHECK (status IN ('NEW', 'INVESTIGATING', 'CLOSED_RESOLVED', 'CLOSED_ESCALATED')),
    CONSTRAINT chk_case_priority CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: risk_profiles
CREATE TABLE risk_profiles (
    profile_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    current_risk_score INT DEFAULT 0,
    risk_tier VARCHAR(15) DEFAULT 'LOW',
    last_evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_risk_profile_customer UNIQUE (customer_id),
    CONSTRAINT fk_risk_profile_customer FOREIGN KEY (customer_id) REFERENCES customers (customer_id) ON DELETE CASCADE,
    CONSTRAINT chk_risk_profile_score CHECK (current_risk_score BETWEEN 0 AND 100),
    CONSTRAINT chk_risk_profile_tier CHECK (risk_tier IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: risk_history
CREATE TABLE risk_history (
    history_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    previous_risk_score INT NOT NULL,
    new_risk_score INT NOT NULL,
    reason VARCHAR(255),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_risk_history_customer FOREIGN KEY (customer_id) REFERENCES customers (customer_id) ON DELETE CASCADE,
    CONSTRAINT chk_risk_hist_prev CHECK (previous_risk_score BETWEEN 0 AND 100),
    CONSTRAINT chk_risk_hist_new CHECK (new_risk_score BETWEEN 0 AND 100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: audit_logs
CREATE TABLE audit_logs (
    audit_id INT AUTO_INCREMENT PRIMARY KEY,
    user_action VARCHAR(100) NOT NULL, -- Action description
    affected_table VARCHAR(50),
    record_id INT,
    old_values JSON,
    new_values JSON,
    performed_by VARCHAR(100) NOT NULL,
    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: rule_execution_logs
CREATE TABLE rule_execution_logs (
    execution_id INT AUTO_INCREMENT PRIMARY KEY,
    transaction_id INT NOT NULL,
    rule_id INT NOT NULL,
    triggered BOOLEAN NOT NULL,
    risk_score_awarded INT NOT NULL,
    execution_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_rel_transaction FOREIGN KEY (transaction_id) REFERENCES transactions (transaction_id) ON DELETE CASCADE,
    CONSTRAINT fk_rel_rule FOREIGN KEY (rule_id) REFERENCES fraud_rules (rule_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ========================================================================
-- 2. INDEX OPTIMIZATIONS
-- ========================================================================

-- Optimization indexes for rapid lookups and range scans on transactional timelines
CREATE INDEX idx_tx_customer_time ON transactions (customer_id, transaction_time);
CREATE INDEX idx_tx_merchant ON transactions (merchant_id);
CREATE INDEX idx_tx_status ON transactions (status);
CREATE INDEX idx_tx_time ON transactions (transaction_time);

-- Optimizations for case management and alert queues
CREATE INDEX idx_alerts_status_score ON alerts (status, risk_score);
CREATE INDEX idx_cases_status_priority ON cases (status, priority);

-- Event timeline indexation
CREATE INDEX idx_events_customer_type ON events (customer_id, event_type);

-- Auditing & logs indexing
CREATE INDEX idx_audit_table_record ON audit_logs (affected_table, record_id);
CREATE INDEX idx_rule_execution_tx ON rule_execution_logs (transaction_id);


-- ========================================================================
-- 3. REPORTING VIEWS
-- ========================================================================

-- View: v_active_alerts (Displays active alerts needing resolution)
CREATE VIEW v_active_alerts AS
SELECT 
    a.alert_id,
    a.transaction_id,
    t.amount,
    t.currency,
    t.transaction_type,
    t.transaction_time,
    c.customer_id,
    CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
    c.email AS customer_email,
    a.risk_score,
    a.status AS alert_status,
    cs.case_id,
    cs.status AS case_status,
    cs.assigned_to,
    cs.priority AS case_priority
FROM alerts a
JOIN transactions t ON a.transaction_id = t.transaction_id
JOIN customers c ON a.customer_id = c.customer_id
LEFT JOIN cases cs ON a.alert_id = cs.alert_id
WHERE a.status IN ('OPEN', 'UNDER_REVIEW');

-- View: v_customer_risk_summary (Aggregates transacting behaviors and risk indicators)
CREATE VIEW v_customer_risk_summary AS
SELECT 
    c.customer_id,
    CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
    c.email,
    rp.current_risk_score,
    rp.risk_tier,
    COUNT(t.transaction_id) AS total_transactions,
    COALESCE(SUM(t.amount), 0.00) AS total_spent,
    SUM(CASE WHEN t.status = 'APPROVED' THEN 1 ELSE 0 END) AS approved_count,
    SUM(CASE WHEN t.status = 'DECLINED' THEN 1 ELSE 0 END) AS declined_count,
    SUM(CASE WHEN t.status = 'FLAGGED' THEN 1 ELSE 0 END) AS flagged_count
FROM customers c
LEFT JOIN risk_profiles rp ON c.customer_id = rp.customer_id
LEFT JOIN transactions t ON c.customer_id = t.customer_id
GROUP BY c.customer_id, rp.current_risk_score, rp.risk_tier;

-- View: v_transaction_fraud_details (Links transactions to rule evaluations and alert triggers)
CREATE VIEW v_transaction_fraud_details AS
SELECT 
    t.transaction_id,
    t.customer_id,
    CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
    t.amount,
    t.transaction_type,
    t.transaction_time,
    m.merchant_name,
    d.device_fingerprint,
    d.ip_address,
    fr.rule_name,
    fr.description AS rule_description,
    rel.triggered AS rule_triggered,
    rel.risk_score_awarded,
    a.alert_id,
    a.status AS alert_status
FROM transactions t
JOIN customers c ON t.customer_id = c.customer_id
LEFT JOIN merchant_profiles m ON t.merchant_id = m.merchant_id
LEFT JOIN devices d ON t.device_id = d.device_id
LEFT JOIN rule_execution_logs rel ON t.transaction_id = rel.transaction_id
LEFT JOIN fraud_rules fr ON rel.rule_id = fr.rule_id
LEFT JOIN alerts a ON t.transaction_id = a.transaction_id;


-- ========================================================================
-- 4. DB TRIGGERS
-- ========================================================================

-- Trigger to record history when risk scores update
CREATE TRIGGER trg_after_risk_profile_update
AFTER UPDATE ON risk_profiles
FOR EACH ROW
BEGIN
    IF OLD.current_risk_score <> NEW.current_risk_score THEN
        INSERT INTO risk_history (customer_id, previous_risk_score, new_risk_score, reason)
        VALUES (NEW.customer_id, OLD.current_risk_score, NEW.current_risk_score, 'Risk Profile Updated');
    END IF;
END;

-- Trigger to log customer blacklisting audits
CREATE TRIGGER trg_after_customer_blacklist
AFTER INSERT ON blacklisted_customers
FOR EACH ROW
BEGIN
    INSERT INTO audit_logs (user_action, affected_table, record_id, old_values, new_values, performed_by)
    VALUES ('CUSTOMER_BLACKLISTED', 'blacklisted_customers', NEW.blacklist_id, NULL, JSON_OBJECT('customer_id', NEW.customer_id, 'reason', NEW.reason), 'SYSTEM_TRIGGER');
END;

-- Trigger to log device blacklisting audits
CREATE TRIGGER trg_after_device_blacklist
AFTER INSERT ON blacklisted_devices
FOR EACH ROW
BEGIN
    INSERT INTO audit_logs (user_action, affected_table, record_id, old_values, new_values, performed_by)
    VALUES ('DEVICE_BLACKLISTED', 'blacklisted_devices', NEW.blacklist_id, NULL, JSON_OBJECT('device_id', NEW.device_id, 'reason', NEW.reason), 'SYSTEM_TRIGGER');
END;


-- ========================================================================
-- 5. RISK ASSESSMENT STORED PROCEDURE
-- ========================================================================

CREATE PROCEDURE sp_assess_transaction_risk(
    IN p_transaction_id INT,
    OUT p_risk_score INT,
    OUT p_decision VARCHAR(20)
)
sp_block: BEGIN
    DECLARE v_customer_id INT;
    DECLARE v_device_id INT;
    DECLARE v_merchant_id INT;
    DECLARE v_amount DECIMAL(15,2);
    DECLARE v_tx_type VARCHAR(20);
    DECLARE v_mcc VARCHAR(4);
    DECLARE v_blacklist_count INT DEFAULT 0;
    DECLARE v_whitelist_count INT DEFAULT 0;
    
    DECLARE v_rule_high_amount_active BOOLEAN DEFAULT FALSE;
    DECLARE v_rule_high_amount_score INT DEFAULT 0;
    DECLARE v_rule_high_amount_val DECIMAL(15,2) DEFAULT 10000.0;
    
    DECLARE v_rule_velocity_active BOOLEAN DEFAULT FALSE;
    DECLARE v_rule_velocity_score INT DEFAULT 0;
    DECLARE v_rule_velocity_limit INT DEFAULT 3;
    DECLARE v_rule_velocity_window INT DEFAULT 60; -- mins
    
    DECLARE v_rule_mcc_active BOOLEAN DEFAULT FALSE;
    DECLARE v_rule_mcc_score INT DEFAULT 0;
    
    DECLARE v_recent_tx_count INT DEFAULT 0;
    DECLARE v_max_rule_score INT DEFAULT 0;
    DECLARE v_alert_id INT;
    DECLARE v_tx_time TIMESTAMP;
    
    -- 1. Fetch transaction metadata
    SELECT customer_id, device_id, merchant_id, amount, transaction_type, transaction_time
    INTO v_customer_id, v_device_id, v_merchant_id, v_amount, v_tx_type, v_tx_time
    FROM transactions
    WHERE transaction_id = p_transaction_id;
    
    -- Check if transaction exists
    IF v_customer_id IS NULL THEN
        SET p_risk_score = 0;
        SET p_decision = 'ERROR_NO_TX';
        LEAVE sp_block;
    END IF;
    
    -- 2. Check Customer/Device Blacklists (Instant Decline: Max Risk 100)
    SELECT COUNT(*) INTO v_blacklist_count FROM blacklisted_customers WHERE customer_id = v_customer_id;
    IF v_blacklist_count > 0 THEN
        SET p_risk_score = 100;
        SET p_decision = 'DECLINED';
        UPDATE transactions SET status = 'DECLINED' WHERE transaction_id = p_transaction_id;
        
        -- Insert alert and case
        INSERT INTO alerts (transaction_id, customer_id, risk_score, status)
        VALUES (p_transaction_id, v_customer_id, 100, 'OPEN');
        SET v_alert_id = LAST_INSERT_ID();
        INSERT INTO cases (alert_id, assigned_to, status, priority, notes)
        VALUES (v_alert_id, 'System Queue', 'NEW', 'CRITICAL', 'Instant decline: Customer resides on Blacklist.');
        
        LEAVE sp_block;
    END IF;
    
    SELECT COUNT(*) INTO v_blacklist_count FROM blacklisted_devices WHERE device_id = v_device_id;
    IF v_blacklist_count > 0 THEN
        SET p_risk_score = 100;
        SET p_decision = 'DECLINED';
        UPDATE transactions SET status = 'DECLINED' WHERE transaction_id = p_transaction_id;
        
        -- Insert alert and case
        INSERT INTO alerts (transaction_id, customer_id, risk_score, status)
        VALUES (p_transaction_id, v_customer_id, 100, 'OPEN');
        SET v_alert_id = LAST_INSERT_ID();
        INSERT INTO cases (alert_id, assigned_to, status, priority, notes)
        VALUES (v_alert_id, 'System Queue', 'NEW', 'CRITICAL', 'Instant decline: Device fingerprint resides on Blacklist.');
        
        LEAVE sp_block;
    END IF;
    
    -- 3. Check Customer/Device Whitelists (Instant Approval: 0 Risk)
    SELECT COUNT(*) INTO v_whitelist_count FROM whitelisted_customers WHERE customer_id = v_customer_id;
    IF v_whitelist_count > 0 THEN
        SET p_risk_score = 0;
        SET p_decision = 'APPROVED';
        UPDATE transactions SET status = 'APPROVED' WHERE transaction_id = p_transaction_id;
        LEAVE sp_block;
    END IF;
    
    SELECT COUNT(*) INTO v_whitelist_count FROM whitelisted_devices WHERE device_id = v_device_id;
    IF v_whitelist_count > 0 THEN
        SET p_risk_score = 0;
        SET p_decision = 'APPROVED';
        UPDATE transactions SET status = 'APPROVED' WHERE transaction_id = p_transaction_id;
        LEAVE sp_block;
    END IF;
    
    -- 4. Evaluate Fraud Rules
    
    -- Fetch config for High Amount Rule
    SELECT is_active, risk_score, CAST(JSON_UNQUOTE(JSON_EXTRACT(criteria_json, '$.max_amount')) AS DECIMAL(15,2))
    INTO v_rule_high_amount_active, v_rule_high_amount_score, v_rule_high_amount_val
    FROM fraud_rules
    WHERE rule_name = 'High Transaction Amount' LIMIT 1;
    
    -- Fetch config for Velocity Rule
    SELECT is_active, risk_score, CAST(JSON_UNQUOTE(JSON_EXTRACT(criteria_json, '$.max_transactions')) AS SIGNED), CAST(JSON_UNQUOTE(JSON_EXTRACT(criteria_json, '$.time_window_minutes')) AS SIGNED)
    INTO v_rule_velocity_active, v_rule_velocity_score, v_rule_velocity_limit, v_rule_velocity_window
    FROM fraud_rules
    WHERE rule_name = 'Rapid Velocity Limit' LIMIT 1;
    
    -- Fetch config for MCC Merchant Rule
    SELECT is_active, risk_score
    INTO v_rule_mcc_active, v_rule_mcc_score
    FROM fraud_rules
    WHERE rule_name = 'High-Risk Merchant Category' LIMIT 1;
    
    -- Run Check 1: High Transaction Amount
    IF v_rule_high_amount_active AND v_amount > v_rule_high_amount_val THEN
        INSERT INTO rule_execution_logs (transaction_id, rule_id, triggered, risk_score_awarded)
        VALUES (p_transaction_id, (SELECT rule_id FROM fraud_rules WHERE rule_name = 'High Transaction Amount'), TRUE, v_rule_high_amount_score);
        IF v_rule_high_amount_score > v_max_rule_score THEN
            SET v_max_rule_score = v_rule_high_amount_score;
        END IF;
    ELSE
        INSERT INTO rule_execution_logs (transaction_id, rule_id, triggered, risk_score_awarded)
        VALUES (p_transaction_id, (SELECT rule_id FROM fraud_rules WHERE rule_name = 'High Transaction Amount'), FALSE, 0);
    END IF;
    
    -- Run Check 2: Transaction Velocity Check
    IF v_rule_velocity_active THEN
        SELECT COUNT(*) INTO v_recent_tx_count
        FROM transactions
        WHERE customer_id = v_customer_id
          AND transaction_time >= DATE_SUB(v_tx_time, INTERVAL v_rule_velocity_window MINUTE)
          AND status IN ('APPROVED', 'PENDING');
        
        IF v_recent_tx_count > v_rule_velocity_limit THEN
            INSERT INTO rule_execution_logs (transaction_id, rule_id, triggered, risk_score_awarded)
            VALUES (p_transaction_id, (SELECT rule_id FROM fraud_rules WHERE rule_name = 'Rapid Velocity Limit'), TRUE, v_rule_velocity_score);
            IF v_rule_velocity_score > v_max_rule_score THEN
                SET v_max_rule_score = v_rule_velocity_score;
            END IF;
        ELSE
            INSERT INTO rule_execution_logs (transaction_id, rule_id, triggered, risk_score_awarded)
            VALUES (p_transaction_id, (SELECT rule_id FROM fraud_rules WHERE rule_name = 'Rapid Velocity Limit'), FALSE, 0);
        END IF;
    END IF;
    
    -- Run Check 3: High-Risk MCC Merchant check
    IF v_rule_mcc_active AND v_merchant_id IS NOT NULL THEN
        SELECT merchant_category_code INTO v_mcc FROM merchant_profiles WHERE merchant_id = v_merchant_id;
        -- Standard MCC codes: 7995 (betting/gambling), 5933 (pawnshops), 5967 (direct marketing outbound call/adult)
        IF v_mcc IN ('7995', '5933', '5967') THEN
            INSERT INTO rule_execution_logs (transaction_id, rule_id, triggered, risk_score_awarded)
            VALUES (p_transaction_id, (SELECT rule_id FROM fraud_rules WHERE rule_name = 'High-Risk Merchant Category'), TRUE, v_rule_mcc_score);
            IF v_rule_mcc_score > v_max_rule_score THEN
                SET v_max_rule_score = v_rule_mcc_score;
            END IF;
        ELSE
            INSERT INTO rule_execution_logs (transaction_id, rule_id, triggered, risk_score_awarded)
            VALUES (p_transaction_id, (SELECT rule_id FROM fraud_rules WHERE rule_name = 'High-Risk Merchant Category'), FALSE, 0);
        END IF;
    END IF;
    
    -- 5. Set outcomes based on score limits
    SET p_risk_score = v_max_rule_score;
    
    IF p_risk_score >= 80 THEN
        SET p_decision = 'DECLINED';
        UPDATE transactions SET status = 'DECLINED' WHERE transaction_id = p_transaction_id;
    ELSEIF p_risk_score >= 50 THEN
        SET p_decision = 'FLAGGED';
        UPDATE transactions SET status = 'FLAGGED' WHERE transaction_id = p_transaction_id;
    ELSE
        SET p_decision = 'APPROVED';
        UPDATE transactions SET status = 'APPROVED' WHERE transaction_id = p_transaction_id;
    END IF;
    
    -- 6. Insert alerts and cases if risk parameters met
    IF p_decision IN ('FLAGGED', 'DECLINED') THEN
        INSERT INTO alerts (transaction_id, customer_id, risk_score, status)
        VALUES (p_transaction_id, v_customer_id, p_risk_score, 'OPEN');
        SET v_alert_id = LAST_INSERT_ID();
        
        INSERT INTO cases (alert_id, assigned_to, status, priority, notes)
        VALUES (
            v_alert_id,
            'System Queue',
            'NEW',
            CASE WHEN p_risk_score >= 80 THEN 'HIGH' ELSE 'MEDIUM' END,
            CONCAT('Auto-triggered risk assessment case. Risk rating: ', p_risk_score)
        );
        
        -- Record to customer risk profiles
        INSERT INTO risk_profiles (customer_id, current_risk_score, risk_tier)
        VALUES (v_customer_id, p_risk_score, CASE WHEN p_risk_score >= 80 THEN 'HIGH' ELSE 'MEDIUM' END)
        ON DUPLICATE KEY UPDATE 
            current_risk_score = p_risk_score,
            risk_tier = CASE WHEN p_risk_score >= 80 THEN 'HIGH' ELSE 'MEDIUM' END;
    END IF;
    
END;


-- ========================================================================
-- 6. SEED RECORDS (DEFAULT CONFIGS & SAMPLE DATA)
-- ========================================================================

-- Seed active rule configurations
INSERT INTO fraud_rules (rule_name, description, criteria_json, risk_score, is_active) VALUES
('High Transaction Amount', 'Flags single transactions exceeding the max amount threshold.', '{"max_amount": 10000.00}', 75, TRUE),
('Rapid Velocity Limit', 'Flags frequent transaction volumes over brief durations.', '{"max_transactions": 3, "time_window_minutes": 60}', 80, TRUE),
('High-Risk Merchant Category', 'Flags activities at merchants flagged with high-risk MCC codes.', '{"flagged_mcc": ["7995", "5933", "5967"]}', 60, TRUE);

-- Seed Customers
INSERT INTO customers (first_name, last_name, email, phone, status) VALUES
('Alice', 'Smith', 'alice.smith@example.com', '+1555010011', 'ACTIVE'),
('Bob', 'Johnson', 'bob.johnson@example.com', '+1555010022', 'ACTIVE'),
('Charlie', 'Brown', 'charlie.brown@example.com', '+1555010033', 'ACTIVE'),
('David', 'Miller', 'david.miller@example.com', '+1555010044', 'BLOCKED');

-- Seed Merchant Profiles
INSERT INTO merchant_profiles (merchant_name, merchant_category_code, risk_level, trust_score) VALUES
('Supermarket Mall', '5411', 'LOW', 100),
('Vegas Crypto Casino', '7995', 'HIGH', 20),
('Golden Pawn Shop', '5933', 'MEDIUM', 70);

-- Seed Devices
INSERT INTO devices (device_fingerprint, ip_address, operating_system, user_agent) VALUES
('dfa658db41fca9456abf21f1d1982b6cc355523a1a1fde56adbf1a561bcdefa1', '192.168.1.10', 'Windows 10', 'Mozilla/5.0'),
('dfa658db41fca9456abf21f1d1982b6cc355523a1a1fde56adbf1a561bcdefa2', '10.0.0.5', 'iOS 15', 'Mobile Safari'),
('dfa658db41fca9456abf21f1d1982b6cc355523a1a1fde56adbf1a561bcdefa3', '172.16.2.3', 'Android 12', 'Chrome Mobile');

-- Seed Blacklist/Whitelist Lists
INSERT INTO blacklisted_customers (customer_id, reason) VALUES
(4, 'Linked to known prior chargeback syndicates');

INSERT INTO blacklisted_devices (device_id, reason) VALUES
(3, 'Device hash identified in credential stuffing alerts');

INSERT INTO whitelisted_customers (customer_id, reason) VALUES
(3, 'Corporate Treasurer account exempt from basic velocity checks');

-- Seed Transactions (to run SP testing against)
-- TX 1: Under limits (Should be Approved)
INSERT INTO transactions (customer_id, merchant_id, device_id, amount, transaction_type, status) VALUES
(1, 1, 1, 150.00, 'PURCHASE', 'PENDING');

-- TX 2: High Amount (Should trigger Rule 1 -> FLAGGED)
INSERT INTO transactions (customer_id, merchant_id, device_id, amount, transaction_type, status) VALUES
(2, 1, 1, 12000.00, 'PURCHASE', 'PENDING');

-- TX 3: Casino MCC (Should trigger Rule 3 -> FLAGGED)
INSERT INTO transactions (customer_id, merchant_id, device_id, amount, transaction_type, status) VALUES
(1, 2, 2, 500.00, 'PURCHASE', 'PENDING');

-- TX 4: Blacklisted Customer (Should instantly DECLINE)
INSERT INTO transactions (customer_id, merchant_id, device_id, amount, transaction_type, status) VALUES
(4, 1, 1, 25.00, 'PURCHASE', 'PENDING');
