"""
==============================================================
 data_ingestion.py  –  Mutual Fund Analytics  |  Day 1
==============================================================
Purpose:
    Load every CSV file from data/raw/, profile its content,
    and generate a concise data-quality summary report.

Author : Mutual Fund Analytics Team
Version: 1.0.0
==============================================================
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional
import textwrap

import pandas as pd

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

def load_csv(filepath: Path) -> Optional[pd.DataFrame]:
    """
    Safely load a CSV file into a DataFrame.

    Parameters
    ----------
    filepath : Path
        Absolute path to the CSV file.

    Returns
    -------
    pd.DataFrame | None
        Loaded DataFrame or None if loading fails.
    """
    try:
        df = pd.read_csv(filepath)
        return df
    except pd.errors.EmptyDataError:
        print(f"  [WARNING] File is empty: {filepath.name}")
    except pd.errors.ParserError as exc:
        print(f"  [ERROR] CSV parse error in '{filepath.name}': {exc}")
    except PermissionError:
        print(f"  [ERROR] Permission denied reading '{filepath.name}'")
    except Exception as exc:  # noqa: BLE001
        print(f"  [ERROR] Unexpected error loading '{filepath.name}': {exc}")
    return None


def report_missing_values(df: pd.DataFrame) -> None:
    """Print per-column missing-value counts and percentage."""
    missing = df.isnull().sum()
    missing_pct = (missing / len(df) * 100).round(2)
    missing_df = pd.DataFrame(
        {"Missing Count": missing, "Missing %": missing_pct}
    )
    missing_df = missing_df[missing_df["Missing Count"] > 0]

    if missing_df.empty:
        print("  ✅  No missing values detected.")
    else:
        print(f"  ⚠️  Columns with missing values:\n")
        print(missing_df.to_string(index=True))


def report_duplicates(df: pd.DataFrame) -> int:
    """Print duplicate-row statistics and return duplicate count."""
    dup_count = df.duplicated().sum()
    if dup_count == 0:
        print("  ✅  No duplicate rows detected.")
    else:
        print(f"  ⚠️  Duplicate rows : {dup_count:,} ({dup_count / len(df) * 100:.2f}%)")
    return int(dup_count)


def profile_dataframe(filepath: Path) -> dict:
    """
    Full profiling pipeline for a single CSV file.

    Returns a summary dict for the aggregated quality report.
    """
    print_section(f"FILE: {filepath.name}")

    # ── 1. Load ────────────────────────────────────────────────
    df = load_csv(filepath)
    if df is None:
        return {
            "file": filepath.name,
            "status": "LOAD_FAILED",
            "rows": 0,
            "cols": 0,
            "missing_cells": 0,
            "duplicate_rows": 0,
        }

    # ── 2. Filename ────────────────────────────────────────────
    print(f"\n📄  Filename : {filepath.name}")
    print(f"    Full path: {filepath}")

    # ── 3. Shape ───────────────────────────────────────────────
    print_subsection("Shape")
    rows, cols = df.shape
    print(f"  Rows    : {rows:,}")
    print(f"  Columns : {cols}")

    # ── 4. Data types ──────────────────────────────────────────
    print_subsection("Column Data Types")
    dtype_df = pd.DataFrame(
        {"Column": df.columns, "Dtype": df.dtypes.values}
    ).reset_index(drop=True)
    print(dtype_df.to_string(index=False))

    # ── 5. First 5 rows ────────────────────────────────────────
    print_subsection("First 5 Rows")
    print(df.head(5).to_string(index=True))

    # ── 6. Missing values ──────────────────────────────────────
    print_subsection("Missing Value Report")
    missing_cells = int(df.isnull().sum().sum())
    report_missing_values(df)

    # ── 7. Duplicate rows ──────────────────────────────────────
    print_subsection("Duplicate Row Report")
    duplicate_rows = report_duplicates(df)

    # ── 8. Basic descriptive stats ─────────────────────────────
    print_subsection("Descriptive Statistics (Numeric Columns)")
    numeric_cols = df.select_dtypes(include="number")
    if numeric_cols.empty:
        print("  No numeric columns found.")
    else:
        print(numeric_cols.describe().round(4).to_string())

    return {
        "file": filepath.name,
        "status": "OK",
        "rows": rows,
        "cols": cols,
        "missing_cells": missing_cells,
        "duplicate_rows": duplicate_rows,
    }


# ─────────────────────────────────────────────────────────────
# Data Quality Summary
# ─────────────────────────────────────────────────────────────

def generate_quality_report(summaries: list[dict]) -> None:
    """
    Aggregate all per-file summaries into one data-quality report.
    """
    print_section("DATA QUALITY SUMMARY REPORT")

    if not summaries:
        print("  No files were processed.")
        return

    report_df = pd.DataFrame(summaries)
    report_df["quality_score"] = report_df.apply(_compute_quality_score, axis=1)

    print(
        report_df[
            ["file", "status", "rows", "cols", "missing_cells", "duplicate_rows", "quality_score"]
        ].to_string(index=False)
    )

    # Overall stats
    total_files    = len(report_df)
    loaded_ok      = (report_df["status"] == "OK").sum()
    total_rows     = report_df["rows"].sum()
    total_missing  = report_df["missing_cells"].sum()
    total_dups     = report_df["duplicate_rows"].sum()
    avg_quality    = report_df["quality_score"].mean()

    print(f"""
┌─────────────────────────────────────────────┐
│           OVERALL QUALITY METRICS           │
├─────────────────────────────────────────────┤
│  Files processed   : {total_files:<4}                   │
│  Files loaded OK   : {loaded_ok:<4}                   │
│  Total rows        : {total_rows:<10,}           │
│  Total missing     : {total_missing:<10,}           │
│  Total duplicates  : {total_dups:<10,}           │
│  Avg quality score : {avg_quality:<6.1f}% / 100         │
└─────────────────────────────────────────────┘
""")


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
        print(f"    • {f.name}")

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
