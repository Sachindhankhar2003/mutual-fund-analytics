-- schema.sql: SQLite Star Schema DDL for Mutual Fund Analytics

-- Drop tables if they exist to start fresh
DROP TABLE IF EXISTS fact_transactions;
DROP TABLE IF EXISTS fact_nav;
DROP TABLE IF EXISTS fact_performance;
DROP TABLE IF EXISTS fact_aum;
DROP TABLE IF EXISTS dim_fund;
DROP TABLE IF EXISTS dim_date;

-- 1. dim_fund Table
CREATE TABLE dim_fund (
    scheme_code INTEGER PRIMARY KEY,
    scheme_name TEXT NOT NULL,
    scheme_category TEXT NOT NULL,
    fund_house TEXT NOT NULL
);

-- 2. dim_date Table
CREATE TABLE dim_date (
    date TEXT PRIMARY KEY, -- format: 'YYYY-MM-DD'
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    is_weekend INTEGER NOT NULL CHECK (is_weekend IN (0, 1))
);

-- 3. fact_nav Table
CREATE TABLE fact_nav (
    nav_id INTEGER PRIMARY KEY AUTOINCREMENT,
    scheme_code INTEGER NOT NULL,
    date TEXT NOT NULL,
    nav REAL NOT NULL CHECK (nav > 0),
    FOREIGN KEY (scheme_code) REFERENCES dim_fund(scheme_code),
    FOREIGN KEY (date) REFERENCES dim_date(date)
);

-- 4. fact_transactions Table
CREATE TABLE fact_transactions (
    transaction_id TEXT PRIMARY KEY,
    investor_id TEXT NOT NULL,
    scheme_code INTEGER NOT NULL,
    transaction_date TEXT NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('SIP', 'Lumpsum', 'Redemption')),
    amount REAL NOT NULL CHECK (amount > 0),
    units REAL NOT NULL CHECK (units >= 0),
    kyc_status TEXT NOT NULL CHECK (kyc_status IN ('Approved', 'Pending')),
    state TEXT NOT NULL,
    FOREIGN KEY (scheme_code) REFERENCES dim_fund(scheme_code),
    FOREIGN KEY (transaction_date) REFERENCES dim_date(date)
);

-- 5. fact_performance Table
CREATE TABLE fact_performance (
    scheme_code INTEGER PRIMARY KEY,
    returns_1y REAL,
    returns_3y REAL,
    returns_5y REAL,
    expense_ratio REAL NOT NULL,
    expense_ratio_anomaly INTEGER NOT NULL CHECK (expense_ratio_anomaly IN (0, 1)),
    FOREIGN KEY (scheme_code) REFERENCES dim_fund(scheme_code)
);

-- 6. fact_aum Table
CREATE TABLE fact_aum (
    scheme_code INTEGER NOT NULL,
    date TEXT NOT NULL,
    aum REAL NOT NULL CHECK (aum > 0),
    PRIMARY KEY (scheme_code, date),
    FOREIGN KEY (scheme_code) REFERENCES dim_fund(scheme_code),
    FOREIGN KEY (date) REFERENCES dim_date(date)
);

-- Indexes for performance optimization of joins
CREATE INDEX idx_nav_scheme_date ON fact_nav(scheme_code, date);
CREATE INDEX idx_transactions_scheme_date ON fact_transactions(scheme_code, transaction_date);
CREATE INDEX idx_transactions_investor ON fact_transactions(investor_id);
CREATE INDEX idx_transactions_state ON fact_transactions(state);
