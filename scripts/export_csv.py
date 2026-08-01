from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from grizzl.config import DB_PATH
from grizzl.database import initialize_database


CSV_FIELDS = [
    "session_id",
    "charger_id",
    "charger_name",
    "ssid",
    "session_start_local",
    "session_start_utc",
    "energy_kwh",
    "duration",
    "duration_seconds",
    "cost",
    "first_collected_at",
    "last_confirmed_at",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Export normalized sessions to CSV.")
    parser.add_argument("--charger-id", type=int)
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    initialize_database()
    query = """
        SELECT
            'CHARGER_' || s.charger_id || '-' ||
                strftime('%Y%m%dT%H%M%S', s.session_start_local) AS session_id,
            s.charger_id,
            c.display_name AS charger_name,
            c.ssid,
            s.session_start_local,
            s.session_start_utc,
            s.energy_kwh,
            s.duration_text AS duration,
            s.duration_seconds,
            s.cost,
            s.first_collected_at,
            s.last_confirmed_at
        FROM sessions s
        JOIN chargers c ON c.id = s.charger_id
        WHERE 1 = 1
    """
    params: list[object] = []

    if args.charger_id is not None:
        query += " AND s.charger_id = ?"
        params.append(args.charger_id)
    if args.start:
        query += " AND s.session_start_local >= ?"
        params.append(args.start)
    if args.end:
        query += " AND s.session_start_local <= ?"
        params.append(args.end)

    query += " ORDER BY s.session_start_utc"

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(dict(row) for row in rows)

    print(f"Exported {len(rows)} session(s) to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
