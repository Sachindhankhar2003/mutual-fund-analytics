"""find_scheme_codes.py - Search mfapi.in for correct scheme codes."""
from __future__ import annotations
import io, sys, requests

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SEARCHES = [
    "HDFC Top 100",
    "SBI Bluechip",
    "ICICI Pru Bluechip",
    "Nippon India Large Cap",
    "Axis Bluechip",
    "Kotak Bluechip",
]

BASE = "https://api.mfapi.in/mf/search?q="

print("=" * 70)
print("  MFAPI.IN SCHEME CODE LOOKUP")
print("=" * 70)

for term in SEARCHES:
    print(f"\n--- Searching: '{term}' ---")
    try:
        url = BASE + requests.utils.quote(term)
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        results = resp.json()
        if not results:
            print("  (no results)")
        else:
            for item in results[:10]:
                code = item.get("schemeCode", item.get("scheme_code", "?"))
                name = item.get("schemeName", item.get("scheme_name", "?"))
                print(f"  {code:>8}  {name}")
    except Exception as exc:
        print(f"  [ERROR] {exc}")

print()
print("=" * 70)
