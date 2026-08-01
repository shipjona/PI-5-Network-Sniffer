from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import grizzl.database as database
from grizzl.config import CHARGERS
from grizzl.parser import DEFAULT_TIMEZONE, parse_charging_history


FIXTURES = Path(__file__).parent / "fixtures"


def test_duplicate_prevention_and_same_timestamp_by_charger(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "grizzl.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)
    payload = (FIXTURES / "post_get_logResult.json").read_text(encoding="utf-8")
    reference = datetime(2026, 8, 1, 12, 0, tzinfo=ZoneInfo(DEFAULT_TIMEZONE))

    database.initialize_database()
    database.sync_chargers(CHARGERS)

    result = parse_charging_history(payload, charger_id=0, reference_dt=reference)
    first = database.save_parsed_sessions(0, result.sessions)
    second = database.save_parsed_sessions(0, result.sessions)

    assert first.inserted == 4
    assert first.duplicates == 0
    assert second.inserted == 0
    assert second.duplicates == 4
    assert database.get_normalized_session_count(0) == 4

    other = parse_charging_history(payload, charger_id=2, reference_dt=reference)
    third = database.save_parsed_sessions(2, other.sessions)

    assert third.inserted == 4
    assert database.get_normalized_session_count() == 8
