import pandas as pd
import numpy as np
import os
from pathlib import Path

# Paths
RAW_DIR = Path(__file__).parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).parent / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# 6 Major Large Cap Mutual Fund Schemes
SCHEME_FILES = {
    119018: "hdfc_top100_nav.csv",
    119598: "sbi_bluechip_nav.csv",
    120586: "icici_bluechip_nav.csv",
    118632: "nippon_largecap_nav.csv",
    120465: "axis_bluechip_nav.csv",
    120152: "kotak_bluechip_nav.csv",
}

def clean_individual_nav_files():
    print("--- Cleaning Individual NAV CSV Files ---")
    for code, fname in SCHEME_FILES.items():
        raw_path = RAW_DIR / fname
        proc_path = PROCESSED_DIR / fname
        
        if not raw_path.exists():
            print(f"  [ERROR] Raw file {fname} not found!")
            continue
            
        df = pd.read_csv(raw_path)
        
        # 1. Parse date to datetime
        df["date"] = pd.to_datetime(df["date"])
        
        # 2. Sort by date
        df = df.sort_values("date").reset_index(drop=True)
        
        # 3. Drop duplicate dates/rows
        df = df.drop_duplicates(subset=["date"], keep="last")
        
        # 4. Validate NAV > 0
        df = df[df["nav"] > 0]
        
        # Save cleaned file
        df.to_csv(proc_path, index=False)
        print(f"  Cleaned {fname} -> {len(df)} rows saved to processed/")

def clean_and_combine_nav_history():
    print("\n--- Creating and Cleaning Combined nav_history.csv ---")
    all_dfs = []
    
    for code, fname in SCHEME_FILES.items():
        raw_path = RAW_DIR / fname
        if not raw_path.exists():
            continue
        df = pd.read_csv(raw_path)
        df["date"] = pd.to_datetime(df["date"])
        all_dfs.append(df)
        
    if not all_dfs:
        print("  [ERROR] No raw NAV files found to combine!")
        return
        
    combined_raw = pd.concat(all_dfs, ignore_index=True)
    
    # Let's perform forward-fill for weekends/holidays for each fund independently
    filled_dfs = []
    for code, group in combined_raw.groupby("scheme_code"):
        group = group.sort_values("date").drop_duplicates(subset=["date"])
        
        # Create full daily range
        min_date = group["date"].min()
        max_date = group["date"].max()
        all_dates = pd.date_range(start=min_date, end=max_date, freq="D")
        
        # Reindex group
        group = group.set_index("date").reindex(all_dates)
        group.index.name = "date"
        group = group.reset_index()
        
        # Forward fill fields
        group["scheme_code"] = group["scheme_code"].ffill().astype(int)
        group["scheme_name"] = group["scheme_name"].ffill()
        group["scheme_category"] = group["scheme_category"].ffill()
        group["fund_house"] = group["fund_house"].ffill()
        group["nav"] = group["nav"].ffill()  # Forward fill missing NAV for holidays/weekends
        
        # If any NAV remains NaN at the start, drop them
        group = group.dropna(subset=["nav"])
        
        filled_dfs.append(group)
        
    nav_history_clean = pd.concat(filled_dfs, ignore_index=True)
    
    # Sort by scheme_code and date
    nav_history_clean = nav_history_clean.sort_values(["scheme_code", "date"]).reset_index(drop=True)
    
    # Validate NAV > 0
    nav_history_clean = nav_history_clean[nav_history_clean["nav"] > 0]
    
    # Save to processed
    nav_history_clean.to_csv(PROCESSED_DIR / "nav_history.csv", index=False)
    print(f"  Created nav_history.csv with {len(nav_history_clean)} rows (forward-filled weekends/holidays)")
    return nav_history_clean

def clean_fund_master():
    print("\n--- Cleaning fund_master.csv ---")
    raw_path = RAW_DIR / "fund_master.csv"
    proc_path = PROCESSED_DIR / "fund_master.csv"
    
    if not raw_path.exists():
        print("  [ERROR] raw/fund_master.csv not found!")
        return
        
    df = pd.read_csv(raw_path)
    df = df.drop_duplicates(subset=["scheme_code"])
    
    # Parse date if possible
    if "nav_date" in df.columns:
        df["nav_date"] = pd.to_datetime(df["nav_date"], errors="coerce")
        
    df.to_csv(proc_path, index=False)
    print(f"  Cleaned fund_master.csv -> {len(df)} rows saved to processed/")

def parse_messy_date(val):
    if pd.isnull(val):
        return pd.NaT
    val = str(val).strip()
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%m/%d/%Y'):
        try:
            return pd.to_datetime(val, format=fmt)
        except ValueError:
            continue
    try:
        return pd.to_datetime(val)
    except ValueError:
        return pd.NaT

def clean_investor_transactions(nav_history):
    print("\n--- Cleaning investor_transactions.csv ---")
    raw_path = RAW_DIR / "investor_transactions.csv"
    proc_path = PROCESSED_DIR / "investor_transactions.csv"
    
    if not raw_path.exists():
        print("  [ERROR] raw/investor_transactions.csv not found!")
        return
        
    df = pd.read_csv(raw_path)
    initial_rows = len(df)
    
    # 1. Parse dates using multiple formats
    df["transaction_date"] = df["transaction_date"].apply(parse_messy_date)
    df = df.dropna(subset=["transaction_date"])
    
    # 2. Standardise transaction_type values
    type_map = {
        'sip': 'SIP', 'Sip': 'SIP', 'SIP': 'SIP',
        'lumpsum': 'Lumpsum', 'Lumpsum': 'Lumpsum', 'LUMP-SUM': 'Lumpsum',
        'redemption': 'Redemption', 'Redemption': 'Redemption', 'REDEMPTION': 'Redemption'
    }
    df["transaction_type"] = df["transaction_type"].map(type_map).fillna("SIP")
    
    # 3. Validate amount > 0 (remove negative/zero amounts)
    df = df[df["amount"] > 0]
    
    # 4. Recalculate units based on the NAV of the fund on that transaction date
    # Build a lookup dictionary: (scheme_code, date_str) -> NAV
    nav_history["date_str"] = nav_history["date"].astype(str)
    nav_lookup = nav_history.set_index(["scheme_code", "date_str"])["nav"].to_dict()
    
    recalc_units = []
    for idx, row in df.iterrows():
        code = int(row["scheme_code"])
        d_str = row["transaction_date"].strftime("%Y-%m-%d")
        amt = float(row["amount"])
        
        # Look up NAV
        nav = nav_lookup.get((code, d_str))
        if nav is None:
            # Fallback to nearest date if exact date doesn't exist (e.g. dates out of fund range)
            # Find closest available date for this fund
            fund_navs = nav_history[nav_history["scheme_code"] == code]
            if not fund_navs.empty:
                closest_idx = (fund_navs["date"] - row["transaction_date"]).abs().idxmin()
                nav = fund_navs.loc[closest_idx, "nav"]
            else:
                nav = 50.0  # arbitrary default fallback
                
        recalc_units.append(round(amt / nav, 4))
        
    df["units"] = recalc_units
    
    # 5. Standardise KYC status
    def standardise_kyc(val):
        if pd.isnull(val):
            return "Pending"
        val = str(val).strip().lower()
        if val in ('y', 'yes', 'approved'):
            return "Approved"
        else:
            return "Pending"
            
    df["kyc_status"] = df["kyc_status"].apply(standardise_kyc)
    
    # Format date as string YYYY-MM-DD
    df["transaction_date"] = df["transaction_date"].dt.strftime("%Y-%m-%d")
    
    df.to_csv(proc_path, index=False)
    print(f"  Cleaned investor_transactions.csv -> {len(df)} of {initial_rows} valid records saved.")

def clean_scheme_performance():
    print("\n--- Cleaning scheme_performance.csv ---")
    raw_path = RAW_DIR / "scheme_performance.csv"
    proc_path = PROCESSED_DIR / "scheme_performance.csv"
    
    if not raw_path.exists():
        print("  [ERROR] raw/scheme_performance.csv not found!")
        return
        
    df = pd.read_csv(raw_path)
    
    def parse_pct_str(val):
        if pd.isnull(val):
            return np.nan
        val = str(val).strip()
        if val.upper() == 'N/A' or val == '':
            return np.nan
        if val.endswith('%'):
            val = val[:-1]
        try:
            return float(val)
        except ValueError:
            return np.nan
            
    df["returns_1y"] = df["returns_1y"].apply(parse_pct_str)
    df["returns_3y"] = df["returns_3y"].apply(parse_pct_str)
    df["returns_5y"] = df["returns_5y"].apply(parse_pct_str)
    df["expense_ratio"] = df["expense_ratio"].apply(parse_pct_str)
    
    # Check expense_ratio range (0.1% - 2.5%) and flag anomalies
    anomalies = []
    for idx, row in df.iterrows():
        er = row["expense_ratio"]
        if pd.notnull(er) and (er < 0.1 or er > 2.5):
            print(f"  [ANOMALY FLAG] Scheme {row['scheme_code']} ({row['scheme_name']}) has out-of-range expense ratio: {er}%")
            anomalies.append(True)
        else:
            anomalies.append(False)
            
    df["expense_ratio_anomaly"] = anomalies
    
    df.to_csv(proc_path, index=False)
    print(f"  Cleaned scheme_performance.csv -> {len(df)} rows saved to processed/")

def main():
    print("=" * 60)
    print("  Mutual Fund Analytics - Day 2 Data Cleaning Pipeline")
    print("=" * 60)
    
    clean_individual_nav_files()
    nav_history = clean_and_combine_nav_history()
    clean_fund_master()
    if nav_history is not None:
        clean_investor_transactions(nav_history)
    clean_scheme_performance()
    
    print("\n" + "=" * 60)
    print("  Data cleaning pipeline completed successfully.")
    print("=" * 60)

if __name__ == "__main__":
    main()
