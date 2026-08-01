from __future__ import annotations

import csv
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import grizzl.database as database
from grizzl.config import CHARGERS
from grizzl.parser import DEFAULT_TIMEZONE, parse_charging_history


FIXTURES = Path(__file__).parent / "fixtures"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_csv_export(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "grizzl.db"
    csv_path = tmp_path / "sessions.csv"
    monkeypatch.setattr(database, "DB_PATH", db_path)
    monkeypatch.setenv("GRIZZL_DB_PATH", str(db_path))
    payload = (FIXTURES / "post_get_logResult.json").read_text(encoding="utf-8")
    reference = datetime(2026, 8, 1, 12, 0, tzinfo=ZoneInfo(DEFAULT_TIMEZONE))

    database.initialize_database()
    database.sync_chargers(CHARGERS)
    parsed = parse_charging_history(payload, charger_id=0, reference_dt=reference)
    database.save_parsed_sessions(0, parsed.sessions)

    subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "export_csv.py"),
            "--output",
            str(csv_path),
        ],
        cwd=PROJECT_ROOT,
        check=True,
    )

    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 4
    assert rows[0]["charger_id"] == "0"
    assert rows[0]["ssid"] == "Shipman-GRU"
