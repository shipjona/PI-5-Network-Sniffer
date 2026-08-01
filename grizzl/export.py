from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

from grizzl.database import get_sessions


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


def session_export_rows(
    *,
    charger_id: int | None = None,
    start: str | None = None,
    end: str | None = None,
    keyword: str | None = None,
    limit: int = 100_000,
) -> list[dict[str, Any]]:
    """Return rows ready for standards-compliant CSV export."""
    rows = get_sessions(
        charger_id=charger_id,
        start=start,
        end=end,
        keyword=keyword,
        limit=limit,
    )
    return [
        {
            "session_id": row["session_id"],
            "charger_id": row["charger_id"],
            "charger_name": row["charger_name"],
            "ssid": row["ssid"],
            "session_start_local": row["session_start_local"],
            "session_start_utc": row["session_start_utc"],
            "energy_kwh": row["energy_kwh"],
            "duration": row["duration"],
            "duration_seconds": row["duration_seconds"],
            "cost": row["cost"],
            "first_collected_at": row["first_collected_at"],
            "last_confirmed_at": row["last_confirmed_at"],
        }
        for row in rows
    ]


def write_sessions_csv(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def sessions_csv_text(rows: list[dict[str, Any]]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def export_filename(start: str | None, end: str | None) -> str:
    safe_start = (start or "all").split("T", 1)[0]
    safe_end = (end or "latest").split("T", 1)[0]
    return f"grizzl_sessions_{safe_start}_to_{safe_end}.csv"
