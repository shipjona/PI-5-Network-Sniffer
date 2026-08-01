from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import grizzl.database as database
from app import app
from grizzl.config import CHARGERS
from grizzl.parser import DEFAULT_TIMEZONE, parse_charging_history


FIXTURES = Path(__file__).parent / "fixtures"


def seed_sessions(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "grizzl.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)
    payload = (FIXTURES / "post_get_logResult.json").read_text(encoding="utf-8")
    reference = datetime(2026, 8, 1, 12, 0, tzinfo=ZoneInfo(DEFAULT_TIMEZONE))

    database.initialize_database()
    database.sync_chargers(CHARGERS)
    parsed = parse_charging_history(payload, charger_id=0, reference_dt=reference)
    database.save_parsed_sessions(0, parsed.sessions)


def test_dashboard_and_sessions_routes(tmp_path: Path, monkeypatch) -> None:
    seed_sessions(tmp_path, monkeypatch)
    app.config.update(TESTING=True)

    with app.test_client() as client:
        overview = client.get("/")
        sessions = client.get("/sessions")

    assert overview.status_code == 200
    assert b"Total Sessions" in overview.data
    assert sessions.status_code == 200
    assert b"CHARGER_0" in sessions.data


def test_csv_export_route(tmp_path: Path, monkeypatch) -> None:
    seed_sessions(tmp_path, monkeypatch)
    app.config.update(TESTING=True)

    with app.test_client() as client:
        response = client.get("/export.csv?charger_id=0")

    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert b"session_id,charger_id,charger_name" in response.data
