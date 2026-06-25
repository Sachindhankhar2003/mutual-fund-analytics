import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
from pathlib import Path

# Paths
RAW_DIR = Path(__file__).parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# Set seed for reproducibility
random.seed(42)
np.random.seed(42)

# Scheme codes and names
SCHEMES = {
    119018: "HDFC Large Cap Fund",
    119598: "SBI Large Cap Fund",
    120586: "ICICI Prudential Large Cap Fund",
    118632: "Nippon India Large Cap Fund",
    120465: "Axis Large Cap Fund",
    120152: "Kotak Large Cap Fund",
}

def generate_investor_transactions():
    n_records = 1000
    txn_types = ['SIP', 'sip', 'Sip', 'Lumpsum', 'lumpsum', 'Redemption', 'redemption', 'REDEMPTION', 'LUMP-SUM']
    kyc_statuses = ['Y', 'N', 'Yes', 'No', 'Approved', 'Pending', 'done', None]
    states = ['Maharashtra', 'Delhi', 'Karnataka', 'Tamil Nadu', 'Uttar Pradesh', 'Gujarat', 'West Bengal', 'Haryana', 'Telangana', 'Punjab']
    
    records = []
    
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2026, 6, 15)
    delta_days = (end_date - start_date).days
    
    for i in range(n_records):
        txn_id = f"TXN{10001 + i}"
        inv_id = f"INV{random.randint(20001, 20250)}"
        scheme_code = random.choice(list(SCHEMES.keys()))
        
        # messy dates
        rand_days = random.randint(0, delta_days)
        dt = start_date + timedelta(days=rand_days)
        date_format_choice = random.choice(['iso', 'dmy_dash', 'dmy_slash', 'mdy_slash'])
        if date_format_choice == 'iso':
            txn_date = dt.strftime('%Y-%m-%d')
        elif date_format_choice == 'dmy_dash':
            txn_date = dt.strftime('%d-%m-%Y')
        elif date_format_choice == 'dmy_slash':
            txn_date = dt.strftime('%d/%m/%Y')
        else:
            txn_date = dt.strftime('%m/%d/%Y')
            
        txn_type = random.choice(txn_types)
        
        # amounts: add some dirty amounts (negative or zero)
        amount_rand = random.random()
        if amount_rand < 0.02:
            amount = 0
        elif amount_rand < 0.04:
            amount = -random.randint(500, 10000)
        else:
            amount = random.randint(1000, 250000)
            
        # units: set to None or a placeholder, we will calculate them from NAV during cleaning
        units = round(amount / 50.0, 4) if amount > 0 else 0
        if random.random() < 0.2:
            units = None  # to show we can compute missing units
            
        kyc = random.choice(kyc_statuses)
        state = random.choice(states)
        
        records.append({
            "transaction_id": txn_id,
            "investor_id": inv_id,
            "scheme_code": scheme_code,
            "transaction_date": txn_date,
            "transaction_type": txn_type,
            "amount": amount,
            "units": units,
            "kyc_status": kyc,
            "state": state
        })
        
    df = pd.DataFrame(records)
    df.to_csv(RAW_DIR / "investor_transactions.csv", index=False)
    print(f"Generated {n_records} dirty transactions in {RAW_DIR / 'investor_transactions.csv'}")

def generate_scheme_performance():
    records = []
    
    # Let's create performance records with string percent formats and out-of-bounds expense ratios
    performance_data = [
        {
            "scheme_code": 119018,
            "scheme_name": SCHEMES[119018],
            "returns_1y": "15.4%",
            "returns_3y": "14.2",
            "returns_5y": "13.5%",
            "expense_ratio": "0.75%",
            "aum": 45600.5
        },
        {
            "scheme_code": 119598,
            "scheme_name": SCHEMES[119598],
            "returns_1y": "12.8",
            "returns_3y": "16.1%",
            "returns_5y": "15.0",
            "expense_ratio": "1.2%",
            "aum": 38400.2
        },
        {
            "scheme_code": 120586,
            "scheme_name": SCHEMES[120586],
            "returns_1y": "N/A",
            "returns_3y": "15.8%",
            "returns_5y": "12.9%",
            "expense_ratio": "2.8%",  # Anomaly! Out of range [0.1% - 2.5%]
            "aum": 28900.8
        },
        {
            "scheme_code": 118632,
            "scheme_name": SCHEMES[118632],
            "returns_1y": "18.2%",
            "returns_3y": "N/A",
            "returns_5y": "14.6%",
            "expense_ratio": "0.05%", # Anomaly! Out of range [0.1% - 2.5%]
            "aum": 21500.1
        },
        {
            "scheme_code": 120465,
            "scheme_name": SCHEMES[120465],
            "returns_1y": "20.1",
            "returns_3y": "17.5%",
            "returns_5y": "N/A",
            "expense_ratio": "1.5%",
            "aum": 31200.4
        },
        {
            "scheme_code": 120152,
            "scheme_name": SCHEMES[120152],
            "returns_1y": "14.8%",
            "returns_3y": "13.9",
            "returns_5y": "11.8%",
            "expense_ratio": "0.9%",
            "aum": 16400.6
        }
    ]
    
    df = pd.DataFrame(performance_data)
    df.to_csv(RAW_DIR / "scheme_performance.csv", index=False)
    print(f"Generated scheme performance records in {RAW_DIR / 'scheme_performance.csv'}")

if __name__ == "__main__":
    generate_investor_transactions()
    generate_scheme_performance()
