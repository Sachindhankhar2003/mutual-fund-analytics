import pandas as pd
import sqlite3
from pathlib import Path
from sqlalchemy import create_engine

# Paths
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "bluestock_mf.db"
SCHEMA_PATH = BASE_DIR / "sql" / "schema.sql"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

def execute_schema_ddl():
    print("--- Initializing Database Schema ---")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    with open(SCHEMA_PATH, "r") as f:
        ddl_script = f.read()
        
    cursor.executescript(ddl_script)
    conn.commit()
    conn.close()
    print("  Database tables and indexes created successfully.")

def populate_dimensions_and_facts():
    print("\n--- Populating Database Tables ---")
    
    # Connect with SQLAlchemy
    engine = create_engine(f"sqlite:///{DB_PATH}")
    
    # 1. Populate dim_fund
    # Read the 6 individual cleaned NAV files to extract fund details
    funds = []
    nav_files = sorted(PROCESSED_DIR.glob("*_nav.csv"))
    for file in nav_files:
        df = pd.read_csv(file)
        if not df.empty:
            first_row = df.iloc[0]
            funds.append({
                "scheme_code": int(first_row["scheme_code"]),
                "scheme_name": first_row["scheme_name"],
                "scheme_category": first_row["scheme_category"],
                "fund_house": first_row["fund_house"]
            })
            
    df_fund = pd.DataFrame(funds).drop_duplicates(subset=["scheme_code"])
    df_fund.to_sql("dim_fund", con=engine, if_exists="append", index=False)
    print(f"  Populated dim_fund: {len(df_fund)} rows")
    
    # 2. Populate dim_date
    # Collect all unique dates from nav_history and transactions
    df_nav = pd.read_csv(PROCESSED_DIR / "nav_history.csv")
    df_tx = pd.read_csv(PROCESSED_DIR / "investor_transactions.csv")
    
    unique_dates = pd.concat([df_nav["date"], df_tx["transaction_date"]]).dropna().unique()
    dates_dt = pd.to_datetime(unique_dates)
    
    dates_data = []
    for d in dates_dt:
        dates_data.append({
            "date": d.strftime("%Y-%m-%d"),
            "year": d.year,
            "month": d.month,
            "day": d.day,
            "quarter": (d.month - 1) // 3 + 1,
            "is_weekend": 1 if d.dayofweek in (5, 6) else 0
        })
        
    df_date = pd.DataFrame(dates_data).drop_duplicates(subset=["date"])
    df_date.to_sql("dim_date", con=engine, if_exists="append", index=False)
    print(f"  Populated dim_date: {len(df_date)} rows")
    
    # 3. Populate fact_nav
    df_fact_nav = df_nav[["scheme_code", "date", "nav"]].copy()
    df_fact_nav.to_sql("fact_nav", con=engine, if_exists="append", index=False)
    print(f"  Populated fact_nav: {len(df_fact_nav)} rows")
    
    # 4. Populate fact_transactions
    df_fact_tx = df_tx.copy()
    df_fact_tx = df_fact_tx.rename(columns={"transaction_date": "transaction_date"})
    df_fact_tx.to_sql("fact_transactions", con=engine, if_exists="append", index=False)
    print(f"  Populated fact_transactions: {len(df_fact_tx)} rows")
    
    # 5. Populate fact_performance
    df_perf = pd.read_csv(PROCESSED_DIR / "scheme_performance.csv")
    df_fact_perf = df_perf[["scheme_code", "returns_1y", "returns_3y", "returns_5y", "expense_ratio", "expense_ratio_anomaly"]].copy()
    df_fact_perf["expense_ratio_anomaly"] = df_fact_perf["expense_ratio_anomaly"].astype(int)
    df_fact_perf.to_sql("fact_performance", con=engine, if_exists="append", index=False)
    print(f"  Populated fact_performance: {len(df_fact_perf)} rows")
    
    # 6. Populate fact_aum
    # We assign AUM values on the last date of records, e.g. '2026-06-19'
    aum_data = []
    for idx, row in df_perf.iterrows():
        aum_data.append({
            "scheme_code": int(row["scheme_code"]),
            "date": "2026-06-19",
            "aum": float(row["aum"])
        })
    df_fact_aum = pd.DataFrame(aum_data)
    df_fact_aum.to_sql("fact_aum", con=engine, if_exists="append", index=False)
    print(f"  Populated fact_aum: {len(df_fact_aum)} rows")

def verify_row_counts():
    print("\n--- Verifying Row Counts (CSV vs Database) ---")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. dim_fund
    cursor.execute("SELECT COUNT(*) FROM dim_fund")
    db_fund_count = cursor.fetchone()[0]
    # Length of 6 (the files we processed)
    print(f"  dim_fund: Database={db_fund_count}, Expected=6 -> {'[PASS]' if db_fund_count == 6 else '[FAIL]'}")
    
    # 2. dim_date
    cursor.execute("SELECT COUNT(*) FROM dim_date")
    db_date_count = cursor.fetchone()[0]
    csv_nav = pd.read_csv(PROCESSED_DIR / "nav_history.csv")
    csv_tx = pd.read_csv(PROCESSED_DIR / "investor_transactions.csv")
    unique_dates_count = len(pd.concat([csv_nav["date"], csv_tx["transaction_date"]]).dropna().unique())
    print(f"  dim_date: Database={db_date_count}, Expected={unique_dates_count} -> {'[PASS]' if db_date_count == unique_dates_count else '[FAIL]'}")
    
    # 3. fact_nav
    cursor.execute("SELECT COUNT(*) FROM fact_nav")
    db_nav_count = cursor.fetchone()[0]
    expected_nav_count = len(csv_nav)
    print(f"  fact_nav: Database={db_nav_count}, Expected={expected_nav_count} -> {'[PASS]' if db_nav_count == expected_nav_count else '[FAIL]'}")
    
    # 4. fact_transactions
    cursor.execute("SELECT COUNT(*) FROM fact_transactions")
    db_tx_count = cursor.fetchone()[0]
    expected_tx_count = len(csv_tx)
    print(f"  fact_transactions: Database={db_tx_count}, Expected={expected_tx_count} -> {'[PASS]' if db_tx_count == expected_tx_count else '[FAIL]'}")
    
    # 5. fact_performance
    cursor.execute("SELECT COUNT(*) FROM fact_performance")
    db_perf_count = cursor.fetchone()[0]
    expected_perf_count = len(pd.read_csv(PROCESSED_DIR / "scheme_performance.csv"))
    print(f"  fact_performance: Database={db_perf_count}, Expected={expected_perf_count} -> {'[PASS]' if db_perf_count == expected_perf_count else '[FAIL]'}")
    
    # 6. fact_aum
    cursor.execute("SELECT COUNT(*) FROM fact_aum")
    db_aum_count = cursor.fetchone()[0]
    expected_aum_count = expected_perf_count
    print(f"  fact_aum: Database={db_aum_count}, Expected={expected_aum_count} -> {'[PASS]' if db_aum_count == expected_aum_count else '[FAIL]'}")
    
    conn.close()

def main():
    print("=" * 60)
    print("  Mutual Fund Analytics - SQLite Load & Validation")
    print("=" * 60)
    
    execute_schema_ddl()
    populate_dimensions_and_facts()
    verify_row_counts()
    
    print("\n" + "=" * 60)
    print("  Database load completed successfully.")
    print("=" * 60)

if __name__ == "__main__":
    main()
