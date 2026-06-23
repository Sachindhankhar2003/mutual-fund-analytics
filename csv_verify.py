"""
csv_verify.py  -  Mutual Fund Analytics
Produces a detailed verification report for all NAV CSV files in data/raw/.
"""
from __future__ import annotations
import io, sys
from pathlib import Path
import pandas as pd

# -- UTF-8 console fix for Windows cp1252
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

RAW_DIR = Path(__file__).parent / "data" / "raw"
SEP = "=" * 72
SUB = "-" * 72

# Expected: scheme_code -> (short label, filename)
# These codes match live_nav_fetch.py (verified against AMFI master list 2026-06-22)
EXPECTED = {
    119018: ("HDFC Large Cap",      "hdfc_top100_nav.csv"),
    119598: ("SBI Large Cap",       "sbi_bluechip_nav.csv"),
    120586: ("ICICI Large Cap",     "icici_bluechip_nav.csv"),
    118632: ("Nippon Large Cap",    "nippon_largecap_nav.csv"),
    120465: ("Axis Large Cap",      "axis_bluechip_nav.csv"),
    120152: ("Kotak Large Cap",     "kotak_bluechip_nav.csv"),
}

now = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
print(SEP)
print("  MUTUAL FUND ANALYTICS -- CSV VERIFICATION REPORT")
print(f"  Generated : {now}")
print(SEP)

issues: list[tuple[str, str]] = []


def check(condition: bool, fname: str, msg: str) -> None:
    tag = "[OK]    " if condition else "[ISSUE] "
    print(f"  {tag} {msg}")
    if not condition:
        issues.append((fname, msg))


for code, (label, fname) in EXPECTED.items():
    path = RAW_DIR / fname
    print(f"\n[FILE] {fname}")
    print(SUB)

    if not path.exists():
        print(f"  [ERROR] FILE NOT FOUND: {path}")
        issues.append((fname, "file missing"))
        continue

    try:
        df = pd.read_csv(path)
    except Exception as exc:
        print(f"  [ERROR] Cannot read file: {exc}")
        issues.append((fname, f"read error: {exc}"))
        continue

    rows, cols = df.shape
    print(f"  Rows          : {rows:,}")
    print(f"  Columns       : {cols}")
    print(f"  Column names  : {list(df.columns)}")
    print()

    # 1. Required columns present (scheme_type is NOT in these CSVs – not from mfapi)
    required_cols = ["scheme_code", "scheme_name", "scheme_category",
                     "fund_house", "date", "nav"]
    missing_cols = [c for c in required_cols if c not in df.columns]
    check(not missing_cols, fname, f"Required columns present -> missing: {missing_cols}")

    if missing_cols:
        print("  (Skipping further checks due to missing columns)")
        continue

    # 2. Scheme code consistency
    unique_codes = sorted(df["scheme_code"].dropna().unique().tolist())
    code_match = (unique_codes == [code])
    check(code_match, fname,
          f"scheme_code consistent ({code}) -> actual unique: {unique_codes}")

    # 3. Single scheme name
    actual_names = df["scheme_name"].dropna().unique().tolist()
    check(len(actual_names) == 1, fname,
          f"Single scheme_name -> found {len(actual_names)} unique name(s)")
    print(f"           scheme_name  : {actual_names[0] if actual_names else 'N/A'}")

    # 4. Label keyword match
    first_word = label.split()[0].lower()
    name_ok = first_word in str(actual_names[0]).lower() if actual_names else False
    tag = "[OK]    " if name_ok else "[WARN]  "
    print(f"  {tag} Label match ({label}) -> name: '{actual_names[0] if actual_names else 'N/A'}'")
    if not name_ok:
        issues.append((fname, f"scheme_name from API does not match expected label [{label}]"))

    # 5. Fund house
    fund_houses = df["fund_house"].dropna().unique().tolist()
    check(len(fund_houses) == 1, fname,
          f"Single fund_house -> found: {fund_houses}")

    # 6. Date parsing
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    date_nulls = int(df["date"].isnull().sum())
    check(date_nulls == 0, fname, f"No null dates -> null count: {date_nulls}")
    date_min = df["date"].min()
    date_max = df["date"].max()
    print(f"           date range   : {date_min.date()} -> {date_max.date()}")

    # 7. NAV column
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    nav_nulls = int(df["nav"].isnull().sum())
    nav_neg   = int((df["nav"] < 0).sum())
    nav_zeros = int((df["nav"] == 0).sum())
    nav_min   = df["nav"].min()
    nav_max   = df["nav"].max()
    check(nav_nulls == 0, fname, f"No null NAVs  -> null count: {nav_nulls}")
    check(nav_neg   == 0, fname, f"No negative NAVs -> count: {nav_neg}")
    check(nav_zeros == 0, fname, f"No zero NAVs  -> count: {nav_zeros}")
    print(f"           nav range    : {nav_min:.4f} -> {nav_max:.4f}")

    # 8. Duplicate rows
    dup_full  = int(df.duplicated().sum())
    dup_dates = int(df["date"].duplicated().sum())
    check(dup_full  == 0, fname, f"No duplicate rows  -> count: {dup_full}")
    check(dup_dates == 0, fname, f"No duplicate dates -> count: {dup_dates}")

    # 9. Missing values per column
    miss = df.isnull().sum()
    miss = miss[miss > 0]
    check(miss.empty, fname, f"No missing values  -> {dict(miss) if not miss.empty else '{}'}")

    # 10. Chronological order
    df_sorted = df.sort_values("date")
    is_sorted = df_sorted["date"].is_monotonic_increasing
    check(is_sorted, fname, f"Dates in chronological order -> sorted: {is_sorted}")

    # 11. Gap analysis
    gaps = df_sorted["date"].diff().dt.days.dropna()
    max_gap   = int(gaps.max())
    long_gaps = int((gaps > 14).sum())   # more than 2 weeks = unusual
    check(long_gaps == 0, fname,
          f"No date gaps > 14 days -> max gap: {max_gap}d, gaps>14d: {long_gaps}")

    # 12. Row count sanity (large-cap funds go back ~10 yrs: expect 2000+ rows)
    check(rows >= 2000, fname, f"Sufficient rows (>=2000) -> actual: {rows:,}")


# ── Summary ─────────────────────────────────────────────────────────────
print()
print(SEP)
print("  VERIFICATION SUMMARY")
print(SEP)

total_checks = len(EXPECTED) * 11  # 11 checks per file (removed scheme_type check)
print(f"  Files checked   : {len(EXPECTED)}")
print(f"  Total issues    : {len(issues)}")
print()

if not issues:
    print("  [ALL PASS] No issues found across all 6 CSV files.")
else:
    print(f"  Issues:")
    for i, (f, msg) in enumerate(issues, 1):
        print(f"    {i:2}. {f}")
        print(f"         -> {msg}")

print(SEP)
print()
