# Data Dictionary - Mutual Fund Analytics Star Schema

This document details the database schema, table definitions, field descriptions, and source data mapping for the SQLite database `bluestock_mf.db`.

---

## 📊 Schema Overview

The database is designed using a **Star Schema** architecture optimized for analytics, grouping dimensions and transactional facts for performance optimization.

```mermaid
erDiagram
    dim_fund ||--o{ fact_nav : "holds history of"
    dim_fund ||--o{ fact_transactions : "is targeted by"
    dim_fund ||--o| fact_performance : "has metrics for"
    dim_fund ||--o{ fact_aum : "tracks size of"
    dim_date ||--o{ fact_nav : "documents date of"
    dim_date ||--o{ fact_transactions : "documents date of"
    dim_date ||--o{ fact_aum : "documents date of"

    dim_fund {
        int scheme_code PK
        varchar scheme_name
        varchar scheme_category
        varchar fund_house
    }
    dim_date {
        varchar date PK
        int year
        int month
        int day
        int quarter
        int is_weekend
    }
    fact_nav {
        int nav_id PK
        int scheme_code FK
        varchar date FK
        float nav
    }
    fact_transactions {
        varchar transaction_id PK
        varchar investor_id
        int scheme_code FK
        varchar transaction_date FK
        varchar transaction_type
        float amount
        float units
        varchar kyc_status
        varchar state
    }
    fact_performance {
        int scheme_code PK_FK
        float returns_1y
        float returns_3y
        float returns_5y
        float expense_ratio
        int expense_ratio_anomaly
    }
    fact_aum {
        int scheme_code PK_FK
        varchar date PK_FK
        float aum
    }
```

---

## 🗂️ Table Definitions

### 1. `dim_fund` (Dimension Table)
Stores descriptive master metadata for the mutual fund schemes.
* **Source Reference:** Compiled from the metadata headers of fetched AMFI NAV history CSV files.

| Column Name | Data Type | Key / Constraint | Business Definition |
|-------------|-----------|------------------|---------------------|
| `scheme_code` | `INTEGER` | `PRIMARY KEY` | Unique 6-digit AMFI identifier code for the fund scheme. |
| `scheme_name` | `TEXT` | `NOT NULL` | The official name of the mutual fund scheme. |
| `scheme_category` | `TEXT` | `NOT NULL` | The investment category (e.g., Equity Scheme - Large Cap Fund). |
| `fund_house` | `TEXT` | `NOT NULL` | The Asset Management Company (AMC) managing the fund. |

---

### 2. `dim_date` (Dimension Table)
A standard calendar dimension table supporting time-series aggregation and weekend filtering.
* **Source Reference:** Programmatically generated from the union of all unique dates in the fact tables.

| Column Name | Data Type | Key / Constraint | Business Definition |
|-------------|-----------|------------------|---------------------|
| `date` | `TEXT` | `PRIMARY KEY` | Calendar date formatted as `YYYY-MM-DD`. |
| `year` | `INTEGER` | `NOT NULL` | Calendar year (e.g., 2026). |
| `month` | `INTEGER` | `NOT NULL` | Calendar month number (1 to 12). |
| `day` | `INTEGER` | `NOT NULL` | Day of the month (1 to 31). |
| `quarter` | `INTEGER` | `NOT NULL` | Calendar quarter (1 to 4). |
| `is_weekend` | `INTEGER` | `CHECK (0, 1)` | Boolean flag indicating whether the day is Saturday/Sunday (1) or Weekday (0). |

---

### 3. `fact_nav` (Fact Table)
Stores historical daily Net Asset Value (NAV) snapshots for each fund.
* **Source Reference:** Compiled and cleaned from the individual scheme NAV CSV files (e.g. `hdfc_top100_nav.csv`).

| Column Name | Data Type | Key / Constraint | Business Definition |
|-------------|-----------|------------------|---------------------|
| `nav_id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Internal system-generated surrogate key. |
| `scheme_code` | `INTEGER` | `FOREIGN KEY -> dim_fund` | Reference to the scheme code. |
| `date` | `TEXT` | `FOREIGN KEY -> dim_date` | Date of the NAV record. |
| `nav` | `REAL` | `CHECK (nav > 0)` | Net Asset Value per unit of the scheme on that date. |

---

### 4. `fact_transactions` (Fact Table)
Records all transactions (Purchases, SIPs, and Redemptions) initiated by investors.
* **Source Reference:** Cleaned from `data/raw/investor_transactions.csv`.

| Column Name | Data Type | Key / Constraint | Business Definition |
|-------------|-----------|------------------|---------------------|
| `transaction_id` | `TEXT` | `PRIMARY KEY` | Unique transaction ID format `TXNXXXXX`. |
| `investor_id` | `TEXT` | `NOT NULL` | Unique identifier code for the investor format `INVXXXXX`. |
| `scheme_code` | `INTEGER` | `FOREIGN KEY -> dim_fund` | Target fund scheme code. |
| `transaction_date` | `TEXT` | `FOREIGN KEY -> dim_date` | Date of transaction execution. |
| `transaction_type` | `TEXT` | `CHECK (SIP, Lumpsum, Redemption)` | Type of transaction executed. |
| `amount` | `REAL` | `CHECK (amount > 0)` | Transaction value in INR. |
| `units` | `REAL` | `CHECK (units >= 0)` | Units allocated or redeemed (calculated as `amount / nav` on transaction date). |
| `kyc_status` | `TEXT` | `CHECK (Approved, Pending)` | KYC compliance status of the investor. |
| `state` | `TEXT` | `NOT NULL` | Geographic state of residence of the investor. |

---

### 5. `fact_performance` (Fact Table)
Contains key performance metrics, returns over multiple periods, and expense ratios.
* **Source Reference:** Compiled and cleaned from `data/raw/scheme_performance.csv`.

| Column Name | Data Type | Key / Constraint | Business Definition |
|-------------|-----------|------------------|---------------------|
| `scheme_code` | `INTEGER` | `PRIMARY KEY, FOREIGN KEY` | Scheme code identifying the fund. |
| `returns_1y` | `REAL` | `NULLABLE` | 1-Year annualized historical returns in %. |
| `returns_3y` | `REAL` | `NULLABLE` | 3-Year annualized historical returns in %. |
| `returns_5y` | `REAL` | `NULLABLE` | 5-Year annualized historical returns in %. |
| `expense_ratio` | `REAL` | `NOT NULL` | Annual operating expense fee charged by the fund in %. |
| `expense_ratio_anomaly` | `INTEGER` | `CHECK (0, 1)` | Flag identifying if the expense ratio falls outside standard SEBI/project bounds of `[0.1%, 2.5%]`. |

---

### 6. `fact_aum` (Fact Table)
Tracks Assets Under Management values for each scheme.
* **Source Reference:** Compiled from `data/raw/scheme_performance.csv`.

| Column Name | Data Type | Key / Constraint | Business Definition |
|-------------|-----------|------------------|---------------------|
| `scheme_code` | `INTEGER` | `PRIMARY KEY, FOREIGN KEY` | Scheme code identifying the fund. |
| `date` | `TEXT` | `PRIMARY KEY, FOREIGN KEY` | Valuation snapshot date. |
| `aum` | `REAL` | `CHECK (aum > 0)` | Total Assets Under Management in Crores (INR). |
