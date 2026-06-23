"""
live_nav_fetch.py - Day 1 NAV fetch for Mutual Fund Analytics project
Fetches NAV data from mfapi.in and saves to data/raw/

Note: Scheme codes verified against AMFI master list on 2026-06-22.
      Several funds were renamed (e.g. "HDFC Top 100" -> "HDFC Large Cap"),
      so the codes below reflect the current live scheme on AMFI.
"""

import io
import sys
import time
import requests
import pandas as pd
from pathlib import Path

# fix console encoding on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

RAW_DIR = Path(__file__).parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# Correct scheme codes pulled from AMFI master list (amfiindia.com/spages/NAVAll.txt)
# Original codes were wrong - funds were renamed/recoded since our reference list
SCHEMES = {
    119018: ("HDFC Large Cap Fund",                "hdfc_top100_nav.csv"),
    119598: ("SBI Large Cap Fund",                 "sbi_bluechip_nav.csv"),
    120586: ("ICICI Prudential Large Cap Fund",    "icici_bluechip_nav.csv"),
    118632: ("Nippon India Large Cap Fund",        "nippon_largecap_nav.csv"),
    120465: ("Axis Large Cap Fund",                "axis_bluechip_nav.csv"),
    120152: ("Kotak Large Cap Fund",               "kotak_bluechip_nav.csv"),
}

# what we expect the API's scheme_name field to contain (for validation)
# using partial strings so minor naming differences still pass
EXPECTED_NAME_KEYWORDS = {
    119018: ["HDFC", "Large Cap"],
    119598: ["SBI", "Large Cap"],
    120586: ["ICICI", "Large Cap"],
    118632: ["Nippon", "Large Cap"],
    120465: ["Axis", "Large Cap"],
    120152: ["Kotak", "Large Cap"],
}


def fetch_nav(scheme_code):
    """Fetch NAV data from mfapi.in with basic retry logic."""
    url = f"https://api.mfapi.in/mf/{scheme_code}"
    for attempt in range(1, 4):
        try:
            print(f"  Fetching scheme {scheme_code} (attempt {attempt}/3)...")
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            print(f"  [ERROR] {e}")
            if attempt < 3:
                time.sleep(2)
    return None


def validate_scheme_name(data, scheme_code, label):
    """
    Quick check: does the API-returned scheme name actually match
    what we expect? Catches cases where mfapi reassigned a code.
    """
    api_name = data.get("meta", {}).get("scheme_name", "")
    keywords = EXPECTED_NAME_KEYWORDS.get(scheme_code, [])
    match = all(kw.lower() in api_name.lower() for kw in keywords)
    if not match:
        print(f"  [WARN] Name mismatch for {label}!")
        print(f"         Expected keywords: {keywords}")
        print(f"         Got from API    : {api_name}")
    else:
        print(f"  [OK] Name matches: {api_name}")
    return match, api_name


def save_nav_csv(data, scheme_code, filename):
    """Parse the JSON response and save NAV history as CSV."""
    records = data.get("data", [])
    if not records:
        print(f"  [ERROR] No data records in response for scheme {scheme_code}")
        return None

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", dayfirst=True)
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    df["scheme_code"] = scheme_code

    # add metadata from the meta block
    meta = data.get("meta", {})
    df["scheme_name"]     = meta.get("scheme_name", "")
    df["scheme_category"] = meta.get("scheme_category", "")
    df["fund_house"]      = meta.get("fund_house", "")

    # sort oldest first
    df = df.sort_values("date").reset_index(drop=True)

    # clean bad zero-NAV records from the API (interpolate linearly)
    zero_nav_count = int((df["nav"] == 0).sum())
    if zero_nav_count:
        print(f"  [WARN] {zero_nav_count} zero-NAV row(s) detected – interpolating.")
        df.loc[df["nav"] == 0, "nav"] = float("nan")
        df["nav"] = df["nav"].interpolate(method="linear").round(4)

    # reorder columns
    df = df[["scheme_code", "scheme_name", "scheme_category", "fund_house", "date", "nav"]]

    filepath = RAW_DIR / filename
    df.to_csv(filepath, index=False)
    print(f"  Saved {len(df)} rows -> {filepath.name}")
    return df


def main():
    print("=" * 60)
    print("  Mutual Fund NAV Fetch")
    print("=" * 60)

    results = []

    for code, (label, filename) in SCHEMES.items():
        print(f"\n[{label}]")

        data = fetch_nav(code)
        if data is None:
            results.append({"fund": label, "status": "FETCH_FAILED", "rows": 0, "name_ok": False})
            continue

        name_ok, api_name = validate_scheme_name(data, code, label)
        df = save_nav_csv(data, code, filename)

        if df is not None:
            results.append({
                "fund":    label,
                "code":    code,
                "file":    filename,
                "rows":    len(df),
                "date_from": str(df["date"].min().date()),
                "date_to":   str(df["date"].max().date()),
                "name_ok": name_ok,
                "api_name": api_name,
                "status":  "OK",
            })
        else:
            results.append({"fund": label, "status": "PARSE_FAILED", "rows": 0, "name_ok": False})

    # print a simple summary table
    print("\n" + "=" * 60)
    print("  FETCH SUMMARY")
    print("=" * 60)
    summary = pd.DataFrame(results)
    print(summary[["fund", "code", "rows", "name_ok", "status"]].to_string(index=False))

    name_mismatches = [r for r in results if not r.get("name_ok")]
    if name_mismatches:
        print(f"\n[WARN] {len(name_mismatches)} scheme(s) had name mismatches - check above.")
    else:
        print("\n[OK] All scheme names validated.")


if __name__ == "__main__":
    main()
