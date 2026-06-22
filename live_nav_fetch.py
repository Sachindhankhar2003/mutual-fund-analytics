"""
==============================================================
 live_nav_fetch.py  –  Mutual Fund Analytics  |  Day 1
==============================================================
Purpose:
    Fetch live NAV (Net Asset Value) history for selected
    Indian mutual fund schemes from the mfapi.in public API
    and persist the results as CSV files in data/raw/.

Schemes covered:
    • HDFC Top 100      – 125497
    • SBI Bluechip      – 119551
    • ICICI Bluechip    – 120503
    • Nippon Large Cap  – 118632
    • Axis Bluechip     – 119092
    • Kotak Bluechip    – 120841

Author : Mutual Fund Analytics Team
Version: 1.0.0
==============================================================
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────
RAW_DIR: Path = Path(__file__).parent / "data" / "raw"
BASE_URL: str = "https://api.mfapi.in/mf"
REQUEST_TIMEOUT: int = 30          # seconds
RETRY_LIMIT: int = 3               # max retries per scheme
RETRY_DELAY: float = 2.0           # seconds between retries

# Schemes: {scheme_code: (fund_house, scheme_name, output_filename)}
SCHEMES: dict[int, tuple[str, str, str]] = {
    125497: ("HDFC Mutual Fund",   "HDFC Top 100 Fund",           "hdfc_top100_nav.csv"),
    119551: ("SBI Mutual Fund",    "SBI Bluechip Fund",           "sbi_bluechip_nav.csv"),
    120503: ("ICICI Prudential",   "ICICI Pru Bluechip Fund",     "icici_bluechip_nav.csv"),
    118632: ("Nippon India MF",    "Nippon India Large Cap Fund",  "nippon_largecap_nav.csv"),
    119092: ("Axis Mutual Fund",   "Axis Bluechip Fund",          "axis_bluechip_nav.csv"),
    120841: ("Kotak Mahindra MF",  "Kotak Bluechip Fund",         "kotak_bluechip_nav.csv"),
}

SEPARATOR: str = "=" * 70


# ─────────────────────────────────────────────────────────────
# Helper utilities
# ─────────────────────────────────────────────────────────────

def print_section(title: str) -> None:
    """Print a visually distinct section header."""
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)


def fetch_with_retry(url: str) -> Optional[dict]:
    """
    Perform an HTTP GET with automatic retries.

    Parameters
    ----------
    url : str
        Fully qualified API endpoint.

    Returns
    -------
    dict | None
        Parsed JSON body, or None on permanent failure.
    """
    for attempt in range(1, RETRY_LIMIT + 1):
        try:
            print(f"    Attempt {attempt}/{RETRY_LIMIT} → {url}")
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as exc:
            print(f"    [HTTP ERROR] {exc}")
        except requests.exceptions.ConnectionError:
            print("    [CONNECTION ERROR] Could not reach the server.")
        except requests.exceptions.Timeout:
            print(f"    [TIMEOUT] Request exceeded {REQUEST_TIMEOUT}s.")
        except requests.exceptions.JSONDecodeError:
            print("    [JSON ERROR] Response is not valid JSON.")
        except Exception as exc:  # noqa: BLE001
            print(f"    [ERROR] Unexpected: {exc}")

        if attempt < RETRY_LIMIT:
            print(f"    Retrying in {RETRY_DELAY}s…")
            time.sleep(RETRY_DELAY)

    return None


# ─────────────────────────────────────────────────────────────
# NAV parsing
# ─────────────────────────────────────────────────────────────

def parse_nav_response(payload: dict, scheme_code: int) -> Optional[pd.DataFrame]:
    """
    Extract NAV history from the mfapi.in JSON payload and
    return a clean, typed DataFrame.

    Expected payload structure:
        {
          "meta": { "scheme_code": ..., "scheme_name": ..., ... },
          "data": [ {"date": "DD-MM-YYYY", "nav": "123.456"}, ... ]
        }
    """
    try:
        meta: dict = payload.get("meta", {})
        nav_records: list[dict] = payload.get("data", [])

        if not nav_records:
            print(f"    [WARNING] No NAV records returned for scheme {scheme_code}.")
            return None

        df = pd.DataFrame(nav_records)

        # ── Type coercion ──────────────────────────────────────
        df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", dayfirst=True)
        df["nav"]  = pd.to_numeric(df["nav"], errors="coerce")

        # ── Enrich with metadata ───────────────────────────────
        df.insert(0, "scheme_code",      scheme_code)
        df.insert(1, "scheme_name",      meta.get("scheme_name", ""))
        df.insert(2, "scheme_category",  meta.get("scheme_category", ""))
        df.insert(3, "scheme_type",      meta.get("scheme_type", ""))
        df.insert(4, "fund_house",       meta.get("fund_house", ""))

        # ── Sort chronologically ───────────────────────────────
        df = df.sort_values("date").reset_index(drop=True)

        return df

    except KeyError as exc:
        print(f"    [PARSE ERROR] Missing key: {exc}")
    except Exception as exc:  # noqa: BLE001
        print(f"    [PARSE ERROR] {exc}")

    return None


# ─────────────────────────────────────────────────────────────
# Save to CSV
# ─────────────────────────────────────────────────────────────

def save_to_csv(df: pd.DataFrame, filepath: Path) -> bool:
    """
    Persist a DataFrame to disk as a UTF-8 CSV.

    Returns
    -------
    bool
        True if save succeeded, False otherwise.
    """
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(filepath, index=False, encoding="utf-8")
        return True
    except PermissionError:
        print(f"    [ERROR] Permission denied writing to {filepath}")
    except OSError as exc:
        print(f"    [OS ERROR] {exc}")
    return False


# ─────────────────────────────────────────────────────────────
# Per-scheme orchestration
# ─────────────────────────────────────────────────────────────

def fetch_and_save_scheme(
    scheme_code: int,
    fund_house: str,
    scheme_name: str,
    filename: str,
) -> dict:
    """
    End-to-end fetch → parse → save pipeline for one scheme.

    Returns a status dict for the summary report.
    """
    url      = f"{BASE_URL}/{scheme_code}"
    filepath = RAW_DIR / filename

    print(f"\n  ┌─ Scheme : {scheme_code} │ {scheme_name} ({fund_house})")
    print(f"  │  URL    : {url}")
    print(f"  │  Output : {filepath.name}")

    # 1. Fetch
    payload = fetch_with_retry(url)
    if payload is None:
        print(f"  └─ ❌  FAILED to fetch data.\n")
        return {"scheme_code": scheme_code, "scheme_name": scheme_name,
                "status": "FETCH_FAILED", "rows": 0, "file": filename}

    # 2. Parse
    df = parse_nav_response(payload, scheme_code)
    if df is None:
        print(f"  └─ ❌  FAILED to parse response.\n")
        return {"scheme_code": scheme_code, "scheme_name": scheme_name,
                "status": "PARSE_FAILED", "rows": 0, "file": filename}

    # 3. Save
    success = save_to_csv(df, filepath)
    if not success:
        print(f"  └─ ❌  FAILED to save CSV.\n")
        return {"scheme_code": scheme_code, "scheme_name": scheme_name,
                "status": "SAVE_FAILED", "rows": len(df), "file": filename}

    date_range = f"{df['date'].min().date()} → {df['date'].max().date()}"
    print(f"  │  Rows   : {len(df):,}  |  Date range: {date_range}")
    print(f"  └─ ✅  Saved → {filepath}\n")

    return {"scheme_code": scheme_code, "scheme_name": scheme_name,
            "status": "OK", "rows": len(df), "file": filename}


# ─────────────────────────────────────────────────────────────
# Fund master & exploration helpers (requirement 7)
# ─────────────────────────────────────────────────────────────

def explore_fund_master(master_csv: Path) -> None:
    """
    Load fund_master.csv and print:
        • Unique fund houses
        • Categories
        • Sub-categories
        • Risk grades
    Silently skips if the file does not exist.
    """
    if not master_csv.exists():
        print(f"\n  [INFO] fund_master.csv not found at {master_csv}. Skipping exploration.")
        return

    print_section("FUND MASTER DATA EXPLORATION")
    try:
        df = pd.read_csv(master_csv)
        print(f"  Rows: {len(df):,}  |  Columns: {list(df.columns)}\n")

        for col_label, col_candidates in {
            "Fund Houses":     ["fund_house", "amc", "AMCName"],
            "Categories":      ["scheme_category", "category", "Category"],
            "Sub-categories":  ["sub_category", "sub-category", "SubCategory"],
            "Risk Grades":     ["risk_grade", "risk", "Risk"],
        }.items():
            matched = next((c for c in col_candidates if c in df.columns), None)
            if matched:
                vals = df[matched].dropna().unique().tolist()
                print(f"  {col_label} ({len(vals)}):")
                for v in sorted(vals):
                    print(f"    • {v}")
            else:
                print(f"  {col_label}: column not found in fund_master.csv")
            print()

    except Exception as exc:  # noqa: BLE001
        print(f"  [ERROR] Could not explore fund_master.csv: {exc}")


# ─────────────────────────────────────────────────────────────
# AMFI validation logic (requirement 8)
# ─────────────────────────────────────────────────────────────

def validate_amfi_scheme_codes(master_csv: Path, nav_csv: Path) -> None:
    """
    Compare scheme_code values between fund_master.csv and
    the combined NAV history, then produce a data quality report.
    """
    print_section("AMFI SCHEME CODE VALIDATION")

    # Load master
    if not master_csv.exists():
        print(f"  [SKIP] fund_master.csv not found: {master_csv}")
        return

    # Collect all NAV CSV files present in data/raw/
    nav_files = sorted(RAW_DIR.glob("*_nav.csv"))
    if not nav_files:
        print(f"  [SKIP] No *_nav.csv files found in {RAW_DIR}")
        return

    try:
        master_df = pd.read_csv(master_csv)
    except Exception as exc:
        print(f"  [ERROR] Could not load fund_master.csv: {exc}")
        return

    # Determine master scheme-code column
    code_col = next(
        (c for c in ["scheme_code", "SchemeCode", "code"] if c in master_df.columns),
        None,
    )
    if code_col is None:
        print("  [ERROR] 'scheme_code' column not found in fund_master.csv")
        return

    master_codes: set[int] = set(master_df[code_col].dropna().astype(int))

    # Collect fetched codes from NAV CSVs
    fetched_codes: set[int] = set()
    for nav_file in nav_files:
        try:
            ndf = pd.read_csv(nav_file, usecols=["scheme_code"])
            fetched_codes.update(ndf["scheme_code"].dropna().astype(int).unique())
        except Exception as exc:
            print(f"  [WARNING] Could not read {nav_file.name}: {exc}")

    # Analysis
    in_master_not_fetched = master_codes - fetched_codes
    fetched_not_in_master = fetched_codes - master_codes
    matched               = master_codes & fetched_codes

    print(f"""
  Master codes          : {len(master_codes):>6,}
  Fetched NAV codes     : {len(fetched_codes):>6,}
  ─────────────────────────────────────
  Matched codes         : {len(matched):>6,}
  In master, NOT fetched: {len(in_master_not_fetched):>6,}
  Fetched, NOT in master: {len(fetched_not_in_master):>6,}
""")

    if in_master_not_fetched:
        print("  ⚠️  Scheme codes in master but missing from NAV data:")
        for code in sorted(in_master_not_fetched):
            print(f"       – {code}")

    if fetched_not_in_master:
        print("\n  ⚠️  Scheme codes in NAV data but NOT in master:")
        for code in sorted(fetched_not_in_master):
            print(f"       – {code}")

    if not in_master_not_fetched and not fetched_not_in_master:
        print("  ✅  All scheme codes are consistent between master and NAV data.")

    # Save quality report
    report_path = RAW_DIR.parent.parent / "reports" / "amfi_validation_report.txt"
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write("AMFI Scheme Code Validation Report\n")
            fh.write(SEPARATOR + "\n")
            fh.write(f"Master codes           : {len(master_codes)}\n")
            fh.write(f"Fetched NAV codes      : {len(fetched_codes)}\n")
            fh.write(f"Matched codes          : {len(matched)}\n")
            fh.write(f"Missing from NAV data  : {len(in_master_not_fetched)}\n")
            fh.write(f"Extra in NAV, not master: {len(fetched_not_in_master)}\n")
            if in_master_not_fetched:
                fh.write("\nMissing codes:\n")
                for code in sorted(in_master_not_fetched):
                    fh.write(f"  {code}\n")
        print(f"\n  📄  Validation report saved → {report_path}")
    except Exception as exc:
        print(f"  [WARNING] Could not save validation report: {exc}")


# ─────────────────────────────────────────────────────────────
# Summary printer
# ─────────────────────────────────────────────────────────────

def print_fetch_summary(results: list[dict]) -> None:
    """Display a tabular fetch summary."""
    print_section("FETCH SUMMARY")
    summary_df = pd.DataFrame(results)[
        ["scheme_code", "scheme_name", "status", "rows", "file"]
    ]
    print(summary_df.to_string(index=False))

    ok_count = sum(1 for r in results if r["status"] == "OK")
    print(f"\n  Schemes fetched successfully : {ok_count} / {len(results)}")


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────

def main() -> None:
    """Orchestrate fetching for all configured schemes."""
    print_section("MUTUAL FUND ANALYTICS – LIVE NAV FETCH")
    print(f"  API Base URL : {BASE_URL}")
    print(f"  Output Dir   : {RAW_DIR.resolve()}")
    print(f"  Schemes      : {len(SCHEMES)}")

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    for scheme_code, (fund_house, scheme_name, filename) in SCHEMES.items():
        result = fetch_and_save_scheme(scheme_code, fund_house, scheme_name, filename)
        results.append(result)

    print_fetch_summary(results)

    # ── Optional: Explore fund master if present ──────────────
    master_csv = RAW_DIR / "fund_master.csv"
    explore_fund_master(master_csv)

    # ── Optional: AMFI validation if master present ───────────
    nav_csv = RAW_DIR / "hdfc_top100_nav.csv"
    validate_amfi_scheme_codes(master_csv, nav_csv)

    print(f"\n{'=' * 70}")
    print("  NAV fetch pipeline complete.")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
