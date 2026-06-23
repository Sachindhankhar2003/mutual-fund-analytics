# data_ingestion.py - Day 1: load and profile NAV CSV files
# reads every CSV from data/raw/, checks quality, prints a summary

import io
import sys
from pathlib import Path

# fix console encoding issue on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import pandas as pd

# expected keywords in scheme_name for each file
# used to catch cases where mfapi returned the wrong fund
EXPECTED_FUNDS = {
    "hdfc_top100_nav.csv":   ["HDFC", "Large Cap"],
    "sbi_bluechip_nav.csv":  ["SBI",  "Large Cap"],
    "icici_bluechip_nav.csv":["ICICI","Large Cap"],
    "nippon_largecap_nav.csv":["Nippon","Large Cap"],
    "axis_bluechip_nav.csv": ["Axis", "Large Cap"],
    "kotak_bluechip_nav.csv":["Kotak","Large Cap"],
}

# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────
RAW_DIR: Path = Path(__file__).parent / "data" / "raw"
SEPARATOR: str = "=" * 70
SUBSEP: str = "-" * 70


# ─────────────────────────────────────────────────────────────
# Helper utilities
# ─────────────────────────────────────────────────────────────
def print_section(title: str) -> None:
    """Print a visually distinct section header."""
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)


def print_subsection(title: str) -> None:
    """Print a lighter sub-section divider."""
    print(f"\n{SUBSEP}")
    print(f"  {title}")
    print(SUBSEP)


# ─────────────────────────────────────────────────────────────
# Core profiling logic
# ─────────────────────────────────────────────────────────────

def load_csv(filepath):
    """Load a CSV file, return DataFrame or None if it fails."""
    try:
        return pd.read_csv(filepath)
    except pd.errors.EmptyDataError:
        print(f"  [WARNING] File is empty: {filepath.name}")
    except pd.errors.ParserError as exc:
        print(f"  [ERROR] CSV parse error in '{filepath.name}': {exc}")
    except PermissionError:
        print(f"  [ERROR] Permission denied: '{filepath.name}'")
    except Exception as exc:
        print(f"  [ERROR] Could not load '{filepath.name}': {exc}")
    return None


def check_scheme_name(df, filename):
    """
    Check that the scheme_name column matches the expected fund.
    Flags cases where mfapi returned a different fund for our scheme code.
    """
    if "scheme_name" not in df.columns:
        return True  # can't check, skip
    keywords = EXPECTED_FUNDS.get(filename, [])
    if not keywords:
        return True  # no expectation defined for this file
    actual = str(df["scheme_name"].iloc[0])
    match = all(kw.lower() in actual.lower() for kw in keywords)
    if match:
        print(f"  [OK] scheme_name matches expected fund ({keywords})")
    else:
        print(f"  [WARN] scheme_name MISMATCH!")
        print(f"         Expected keywords : {keywords}")
        print(f"         Actual name       : {actual}")
        print(f"         --> The scheme code may be wrong. Re-run live_nav_fetch.py")
    return match


def report_missing_values(df: pd.DataFrame) -> None:
    """Print per-column missing-value counts and percentage."""
    missing = df.isnull().sum()
    missing_pct = (missing / len(df) * 100).round(2)
    missing_df = pd.DataFrame(
        {"Missing Count": missing, "Missing %": missing_pct}
    )
    missing_df = missing_df[missing_df["Missing Count"] > 0]

    if missing_df.empty:
        print("  [OK]  No missing values detected.")
    else:
        print("  [WARNING] Columns with missing values:\n")
        print(missing_df.to_string(index=True))


def report_duplicates(df: pd.DataFrame) -> int:
    """Print duplicate-row statistics and return duplicate count."""
    dup_count = df.duplicated().sum()
    if dup_count == 0:
        print("  [OK]  No duplicate rows detected.")
    else:
        print(f"  [WARNING] Duplicate rows : {dup_count:,} ({dup_count / len(df) * 100:.2f}%)")
    return int(dup_count)


def profile_dataframe(filepath):
    """Profile a single CSV file and return a summary dict."""
    print_section(f"FILE: {filepath.name}")

    df = load_csv(filepath)
    if df is None:
        return {"file": filepath.name, "status": "LOAD_FAILED",
                "rows": 0, "cols": 0, "missing_cells": 0,
                "duplicate_rows": 0, "name_ok": False}

    print(f"  Path: {filepath}")

    # shape
    print_subsection("Shape")
    rows, cols = df.shape
    print(f"  Rows    : {rows:,}")
    print(f"  Columns : {cols}")

    # column types
    print_subsection("Column Data Types")
    print(df.dtypes.to_string())

    # first 5 rows
    print_subsection("First 5 Rows")
    print(df.head(5).to_string(index=True))

    # scheme name validation (did we get the right fund?)
    print_subsection("Scheme Name Check")
    name_ok = check_scheme_name(df, filepath.name)

    # missing values
    print_subsection("Missing Values")
    missing_cells = int(df.isnull().sum().sum())
    report_missing_values(df)

    # duplicate rows
    print_subsection("Duplicate Rows")
    duplicate_rows = report_duplicates(df)

    # basic stats for numeric columns
    print_subsection("Descriptive Statistics")
    numeric_cols = df.select_dtypes(include="number")
    if numeric_cols.empty:
        print("  No numeric columns.")
    else:
        print(numeric_cols.describe().round(4).to_string())

    return {
        "file":           filepath.name,
        "status":         "OK",
        "rows":           rows,
        "cols":           cols,
        "missing_cells":  missing_cells,
        "duplicate_rows": duplicate_rows,
        "name_ok":        name_ok,
    }


# ─────────────────────────────────────────────────────────────
# Data Quality Summary
# ─────────────────────────────────────────────────────────────

def generate_quality_report(summaries):
    """Print a summary table of all files processed."""
    print_section("DAY-1 DATA QUALITY SUMMARY")

    if not summaries:
        print("  No files processed.")
        return

    report_df = pd.DataFrame(summaries)
    report_df["quality_score"] = report_df.apply(_compute_quality_score, axis=1)

    print(report_df[["file", "status", "name_ok", "rows",
                      "missing_cells", "duplicate_rows",
                      "quality_score"]].to_string(index=False))

    total_files   = len(report_df)
    loaded_ok     = (report_df["status"] == "OK").sum()
    total_rows    = report_df["rows"].sum()
    total_missing = report_df["missing_cells"].sum()
    total_dups    = report_df["duplicate_rows"].sum()
    avg_quality   = report_df["quality_score"].mean()
    name_issues   = (~report_df["name_ok"]).sum()

    print(f"""
+---------------------------------------------+
|  Day-1 Summary                              |
+---------------------------------------------+
|  Files loaded OK   : {loaded_ok}/{total_files}                      |
|  Total rows        : {total_rows:<10,}           |
|  Total missing     : {total_missing:<10,}           |
|  Total duplicates  : {total_dups:<10,}           |
|  Avg quality score : {avg_quality:<5.1f}% / 100          |
|  Scheme name issues: {name_issues:<4}                   |
+---------------------------------------------+
""")
    if name_issues > 0:
        print("  [ACTION NEEDED] Some files have wrong fund data.")
        print("  Re-run live_nav_fetch.py to download correct NAV files.")


def _compute_quality_score(row: pd.Series) -> float:
    """
    Simple composite quality score (0-100).

    Penalises missing cells and duplicate rows proportionally.
    """
    if row["status"] != "OK" or row["rows"] == 0:
        return 0.0
    total_cells = row["rows"] * row["cols"]
    missing_penalty = (row["missing_cells"] / total_cells) * 50 if total_cells else 0
    dup_penalty     = (row["duplicate_rows"] / row["rows"]) * 50
    score = 100 - missing_penalty - dup_penalty
    return round(max(score, 0), 1)


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────

def main() -> None:
    """Discover and profile all CSV files in data/raw/."""
    print_section("MUTUAL FUND ANALYTICS – DATA INGESTION PIPELINE")
    print(f"  Scanning directory: {RAW_DIR.resolve()}\n")

    if not RAW_DIR.exists():
        print(f"  [ERROR] Directory not found: {RAW_DIR}")
        sys.exit(1)

    csv_files = sorted(RAW_DIR.glob("*.csv"))

    if not csv_files:
        print("  [INFO] No CSV files found in data/raw/. Fetch NAV data first.")
        print("         Run: python live_nav_fetch.py")
        sys.exit(0)

    print(f"  Found {len(csv_files)} CSV file(s):\n")
    for f in csv_files:
        print(f"    * {f.name}")

    summaries: list[dict] = []
    for filepath in csv_files:
        summary = profile_dataframe(filepath)
        summaries.append(summary)

    generate_quality_report(summaries)
    print(f"\n{'=' * 70}")
    print("  Ingestion pipeline complete.")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
