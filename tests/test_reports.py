from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import grizzl.database as database
from grizzl.config import CHARGERS
from grizzl.parser import DEFAULT_TIMEZONE, parse_charging_history
from grizzl.reports import ReportPeriod, report_summary


FIXTURES = Path(__file__).parent / "fixtures"


def test_report_summary_totals(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "grizzl.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)
    payload = (FIXTURES / "post_get_logResult.json").read_text(encoding="utf-8")
    tz = ZoneInfo(DEFAULT_TIMEZONE)
    reference = datetime(2026, 8, 1, 12, 0, tzinfo=tz)

    database.initialize_database()
    database.sync_chargers(CHARGERS)
    parsed = parse_charging_history(payload, charger_id=0, reference_dt=reference)
    database.save_parsed_sessions(0, parsed.sessions)

    summary = report_summary(
        ReportPeriod(
            start=datetime(2026, 7, 28, 0, 0, tzinfo=tz),
            end=datetime(2026, 8, 4, 0, 0, tzinfo=tz),
        )
    )

    assert summary["session_count"] == 4
    assert summary["total_energy_kwh"] == 63.017
    assert summary["by_charger"][0]["charger_id"] == 0
