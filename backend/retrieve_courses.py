#!/usr/bin/env python3
"""
Simple script to fetch courses from Supabase REST API and keep only courses whose
course code contains a 3-digit number. Matches the request/headers style used in
the rest of the backend (see `schedule.py`).

Assumptions:
- Table name: `amherst_courses_all` by default (can override using SUPABASE_COURSES_TABLE env var)
- Columns present: `id`, `semester`, `course_code`, `course_name`. If different,
  change the SELECT string or set the SUPABASE_COURSES_TABLE to a table with those columns.

Output: writes filtered JSON to ./data/retrieved_supabase_courses_filtered.json
"""
from dotenv import load_dotenv
import os
import requests
import json
import re
from typing import List, Dict, Any


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TABLE_NAME = os.getenv("SUPABASE_COURSES_TABLE", "amherst_courses_all")

OUT_PATH = os.path.join(os.path.dirname(__file__), "data", "retrieved_supabase_courses_filtered.json")


def _build_headers() -> Dict[str, str]:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def fetch_courses(select_cols: str = "id,semester,course_code,course_name", limit: int = 10000) -> List[Dict[str, Any]]:
    """Fetch rows from Supabase REST API.

    select_cols: columns to request (Supabase `select=` syntax)
    limit: maximum number of rows to fetch in a single call (increase if needed)
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in the environment")

    headers = _build_headers()
    # include limit to try to avoid default paging; adjust as needed
    url = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}?select={select_cols}&limit={limit}"

    resp = requests.get(url, headers=headers)
    try:
        resp.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"Supabase request failed: {resp.status_code} {resp.text}") from e

    rows = resp.json()
    if not isinstance(rows, list):
        raise RuntimeError("Unexpected response format from Supabase: expected a JSON list")

    return rows


def filter_three_digit_codes(rows: List[Dict[str, Any]], code_field: str = "course_code") -> List[Dict[str, Any]]:
    """Return only rows where the course code contains a sequence of three digits.

    This matches codes like 'COSC-111', 'MATH 201', or 'HIST-123A' (because it contains '123').
    If you want stricter matching (digits-only portion equals 3 digits), change the regex.
    """
    pattern = re.compile(r"\d{3}")
    kept = []

    for r in rows:
        code = r.get(code_field)
        if not code:
            # Try some common alternative keys
            code = r.get("course_codes") or r.get("code") or r.get("course_number")

        if not code:
            continue

        # Normalize to string
        code_str = str(code)

        if pattern.search(code_str):
            # Keep only requested output fields for clarity
            filtered = {
                "id": r.get("id"),
                "semester": r.get("semester"),
                "course_code": code_str,
                "course_name": r.get("course_name") or r.get("course_title")
            }
            kept.append(filtered)

    return kept


def main():
    # Fetch records
    print(f"Fetching courses from Supabase table '{TABLE_NAME}'...")
    try:
        rows = fetch_courses()
    except Exception as e:
        print("Error fetching courses:", e)
        return

    print(f"Fetched {len(rows)} rows from Supabase")

    filtered = filter_three_digit_codes(rows)
    print(f"Filtered down to {len(filtered)} rows where course code contains 3 digits")

    # Ensure output directory exists
    out_dir = os.path.dirname(OUT_PATH)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    # Write JSON
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(filtered, f, indent=2, ensure_ascii=False)

    print(f"Wrote filtered results to {OUT_PATH}")


if __name__ == "__main__":
    main()
