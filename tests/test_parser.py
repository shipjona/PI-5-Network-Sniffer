from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from grizzl.parser import (
    DEFAULT_TIMEZONE,
    ParseError,
    duration_to_seconds,
    parse_charging_history,
    parse_date_text,
)


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_real_get_log_result_fixture() -> None:
    payload = (FIXTURES / "post_get_logResult.json").read_text(encoding="utf-8")
    reference = datetime(2026, 8, 1, 12, 0, tzinfo=ZoneInfo(DEFAULT_TIMEZONE))

    result = parse_charging_history(
        payload,
        charger_id=0,
        reference_dt=reference,
    )

    assert len(result.sessions) == 4
    assert result.rejected == []
    assert result.sessions[0].session_start_local.startswith("2026-08-01T02:23:13")
    assert result.sessions[1].energy_kwh == pytest.approx(56.995)
    assert result.sessions[1].duration_seconds == 33935


def test_parse_rendered_html_rows_with_whitespace() -> None:
    html = (FIXTURES / "rendered_history_sample.html").read_text(encoding="utf-8")
    reference = datetime(2026, 7, 31, 12, 0, tzinfo=ZoneInfo(DEFAULT_TIMEZONE))

    result = parse_charging_history(
        html,
        charger_id=12,
        reference_dt=reference,
    )

    assert len(result.sessions) == 2
    assert result.sessions[0].source_date_text == "18/07 15:11:20"
    assert result.sessions[0].energy_kwh == pytest.approx(6.1)
    assert result.sessions[0].duration_seconds == 2481
    assert result.sessions[0].cost == pytest.approx(6.12)


def test_year_rollover_uses_previous_year_for_future_december() -> None:
    reference = datetime(2026, 1, 1, 1, 0, tzinfo=ZoneInfo(DEFAULT_TIMEZONE))

    parsed = parse_date_text(
        "31/12 23:59:00",
        reference_dt=reference,
    )

    assert parsed.year == 2025


def test_duration_validation() -> None:
    assert duration_to_seconds("12:50:00") == 46200

    with pytest.raises(ParseError):
        duration_to_seconds("00:99:00")
