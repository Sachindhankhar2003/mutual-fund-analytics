-- sql/queries.sql: 10 Analytical SQL Queries for Mutual Fund Analytics

-- 1. Top 5 Funds by AUM
-- Lists the top funds based on their Assets Under Management.
SELECT 
    f.scheme_code,
    f.scheme_name,
    a.aum AS aum_in_crores
FROM fact_aum a
JOIN dim_fund f ON a.scheme_code = f.scheme_code
ORDER BY a.aum DESC
LIMIT 5;

-- 2. Average NAV Per Month for Each Scheme
-- Computes the average NAV grouped by scheme and calendar month.
SELECT 
    f.scheme_name,
    d.year,
    d.month,
    ROUND(AVG(n.nav), 4) AS avg_nav
FROM fact_nav n
JOIN dim_fund f ON n.scheme_code = f.scheme_code
JOIN dim_date d ON n.date = d.date
GROUP BY f.scheme_name, d.year, d.month
ORDER BY f.scheme_name, d.year, d.month;

-- 3. SIP Year-over-Year (YoY) Growth
-- Calculates the YoY growth percentage of total SIP investments.
WITH sip_annual AS (
    SELECT 
        d.year,
        SUM(t.amount) AS total_sip_amount
    FROM fact_transactions t
    JOIN dim_date d ON t.transaction_date = d.date
    WHERE t.transaction_type = 'SIP'
    GROUP BY d.year
)
SELECT 
    curr.year AS current_year,
    curr.total_sip_amount AS current_year_amount,
    prev.year AS previous_year,
    prev.total_sip_amount AS previous_year_amount,
    ROUND(((curr.total_sip_amount - prev.total_sip_amount) / prev.total_sip_amount) * 100, 2) AS yoy_growth_pct
FROM sip_annual curr
LEFT JOIN sip_annual prev ON curr.year = prev.year + 1
ORDER BY curr.year;

-- 4. Transactions by State
-- Summarizes total transaction count and total transaction amount by investor state.
SELECT 
    state,
    COUNT(*) AS total_transactions,
    ROUND(SUM(amount), 2) AS total_amount
FROM fact_transactions
GROUP BY state
ORDER BY total_amount DESC;

-- 5. Funds with Expense Ratio < 1%
-- Retrieves schemes with expense ratio less than 1%.
SELECT 
    f.scheme_code,
    f.scheme_name,
    p.expense_ratio
FROM fact_performance p
JOIN dim_fund f ON p.scheme_code = f.scheme_code
WHERE p.expense_ratio < 1.0
ORDER BY p.expense_ratio ASC;

-- 6. KYC Status Distribution
-- Shows the count and total value of transactions grouped by KYC status.
SELECT 
    kyc_status,
    COUNT(*) AS transaction_count,
    ROUND(SUM(amount), 2) AS total_investment
FROM fact_transactions
GROUP BY kyc_status;

-- 7. High-Value Transactions
-- Identifies transactions greater than 1.5 Lakhs (150,000 INR) for compliance monitoring.
SELECT 
    transaction_id,
    investor_id,
    transaction_type,
    amount,
    state,
    transaction_date
FROM fact_transactions
WHERE amount > 150000
ORDER BY amount DESC;

-- 8. Top 5 Investors by Total Investment
-- Ranks investors by their cumulative transaction amount across all funds.
SELECT 
    investor_id,
    COUNT(*) AS transaction_count,
    ROUND(SUM(CASE WHEN transaction_type = 'Redemption' THEN -amount ELSE amount END), 2) AS net_investment
FROM fact_transactions
GROUP BY investor_id
ORDER BY net_investment DESC
LIMIT 5;

-- 9. Transaction Volume and Type Breakdown
-- Analyzes transaction counts and volumes across different transaction types.
SELECT 
    transaction_type,
    COUNT(*) AS transaction_count,
    ROUND(AVG(amount), 2) AS avg_amount,
    ROUND(SUM(amount), 2) AS total_amount
FROM fact_transactions
GROUP BY transaction_type;

-- 10. Scheme Performance Overview with Expense Ratio Anomalies
-- Lists fund returns and flags funds with expense ratio anomalies.
SELECT 
    f.scheme_name,
    p.returns_1y,
    p.returns_3y,
    p.returns_5y,
    p.expense_ratio,
    CASE WHEN p.expense_ratio_anomaly = 1 THEN 'Yes (Out of Range)' ELSE 'No' END AS is_expense_anomaly
FROM fact_performance p
JOIN dim_fund f ON p.scheme_code = f.scheme_code
ORDER BY p.returns_3y DESC;
