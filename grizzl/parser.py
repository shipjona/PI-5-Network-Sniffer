from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup


DEFAULT_TIMEZONE = "America/Tijuana"
DATE_TEXT_RE = re.compile(
    r"(?P<day>\d{1,2})/(?P<month>\d{1,2})\s+"
    r"(?P<hour>\d{1,2}):(?P<minute>\d{1,2}):(?P<second>\d{1,2})"
)
DURATION_RE = re.compile(
    r"(?P<hours>\d{1,3}):(?P<minutes>\d{1,2}):(?P<seconds>\d{1,2})"
)


class ParseError(ValueError):
    """Raised when a charging-history row cannot be parsed."""


@dataclass(frozen=True)
class ParsedSession:
    """Normalized charging-history record."""

    charger_id: int
    session_id: str
    session_start_utc: str
    session_start_local: str
    source_date_text: str
    source_timezone: str
    energy_kwh: float
    duration_seconds: int
    duration_text: str
    cost: float | None
    raw_row: dict[str, Any]


@dataclass(frozen=True)
class RejectedRow:
    """Charging-history row rejected during parsing."""

    raw_row: Any
    error: str


@dataclass(frozen=True)
class ParseResult:
    """Parser result with accepted and rejected rows."""

    sessions: list[ParsedSession]
    rejected: list[RejectedRow]


def duration_to_seconds(duration_text: str) -> int:
    """Convert HH:MM:SS duration text to seconds."""
    match = DURATION_RE.fullmatch(duration_text.strip())

    if match is None:
        raise ParseError(f"Invalid duration {duration_text!r}")

    hours = int(match.group("hours"))
    minutes = int(match.group("minutes"))
    seconds = int(match.group("seconds"))

    if minutes > 59 or seconds > 59:
        raise ParseError(f"Invalid duration {duration_text!r}")

    return hours * 3600 + minutes * 60 + seconds


def parse_decimal(value: Any, field_name: str) -> float:
    """Parse a decimal numeric value as float for SQLite storage."""
    try:
        return float(Decimal(str(value).strip()))
    except (InvalidOperation, ValueError) as exc:
        raise ParseError(f"Invalid {field_name}: {value!r}") from exc


def resolve_year(
    *,
    month: int,
    day: int,
    hour: int,
    minute: int,
    second: int,
    timezone_name: str = DEFAULT_TIMEZONE,
    reference_dt: datetime | None = None,
) -> datetime:
    """
    Resolve a charger date without a year to a timezone-aware datetime.

    The chosen year is the most recent plausible timestamp that is not more
    than one day in the future relative to the reference clock. This handles
    New Year rollover without assigning impossible future sessions.
    """
    tz = ZoneInfo(timezone_name)
    now = reference_dt.astimezone(tz) if reference_dt else datetime.now(tz)
    candidates: list[datetime] = []

    for year in (now.year - 1, now.year, now.year + 1):
        try:
            candidates.append(
                datetime(year, month, day, hour, minute, second, tzinfo=tz)
            )
        except ValueError:
            continue

    if not candidates:
        raise ParseError(
            f"Invalid date components: {day:02d}/{month:02d} "
            f"{hour:02d}:{minute:02d}:{second:02d}"
        )

    future_limit = now + timedelta(days=1)
    plausible = [candidate for candidate in candidates if candidate <= future_limit]

    if not plausible:
        raise ParseError("All candidate years are implausibly in the future")

    return max(plausible)


def parse_date_text(
    value: str,
    *,
    timezone_name: str = DEFAULT_TIMEZONE,
    reference_dt: datetime | None = None,
) -> datetime:
    """Parse charger-rendered DD/MM HH:MM:SS date text."""
    normalized = " ".join(value.split())
    match = DATE_TEXT_RE.fullmatch(normalized)

    if match is None:
        raise ParseError(f"Invalid charger date text: {value!r}")

    return resolve_year(
        month=int(match.group("month")),
        day=int(match.group("day")),
        hour=int(match.group("hour")),
        minute=int(match.group("minute")),
        second=int(match.group("second")),
        timezone_name=timezone_name,
        reference_dt=reference_dt,
    )


def _session_id(charger_id: int, local_dt: datetime) -> str:
    return f"CHARGER_{charger_id}-{local_dt.strftime('%Y%m%dT%H%M%S')}"


def _build_session(
    *,
    charger_id: int,
    local_dt: datetime,
    source_date_text: str,
    energy_kwh: float,
    duration_text: str,
    cost: float | None,
    raw_row: dict[str, Any],
    timezone_name: str,
) -> ParsedSession:
    utc_dt = local_dt.astimezone(ZoneInfo("UTC"))

    return ParsedSession(
        charger_id=charger_id,
        session_id=_session_id(charger_id, local_dt),
        session_start_utc=utc_dt.isoformat(),
        session_start_local=local_dt.isoformat(),
        source_date_text=source_date_text,
        source_timezone=timezone_name,
        energy_kwh=energy_kwh,
        duration_seconds=duration_to_seconds(duration_text),
        duration_text=duration_text,
        cost=cost,
        raw_row=raw_row,
    )


def parse_json_row(
    row: dict[str, Any],
    *,
    charger_id: int,
    timezone_name: str = DEFAULT_TIMEZONE,
    reference_dt: datetime | None = None,
) -> ParsedSession:
    """Parse one `/get_logResult` JSON row."""
    required = (
        "log_mnth",
        "log_dd",
        "log_hh",
        "log_mm",
        "log_sec",
        "s_hh",
        "s_mm",
        "s_sec",
        "s_enrg",
    )
    missing = [key for key in required if key not in row]

    if missing:
        raise ParseError(f"Missing required fields: {', '.join(missing)}")

    month = int(row["log_mnth"])
    day = int(row["log_dd"])
    hour = int(row["log_hh"])
    minute = int(row["log_mm"])
    second = int(row["log_sec"])
    source_date_text = f"{day:02d}/{month:02d} {hour:02d}:{minute:02d}:{second:02d}"
    local_dt = resolve_year(
        month=month,
        day=day,
        hour=hour,
        minute=minute,
        second=second,
        timezone_name=timezone_name,
        reference_dt=reference_dt,
    )
    duration_text = (
        f"{int(row['s_hh']):02d}:"
        f"{int(row['s_mm']):02d}:"
        f"{int(row['s_sec']):02d}"
    )
    cost = parse_decimal(row["s_cost"], "cost") if "s_cost" in row else None

    return _build_session(
        charger_id=charger_id,
        local_dt=local_dt,
        source_date_text=source_date_text,
        energy_kwh=parse_decimal(row["s_enrg"], "energy"),
        duration_text=duration_text,
        cost=cost,
        raw_row=row,
        timezone_name=timezone_name,
    )


def parse_html_row(
    values: list[str],
    *,
    charger_id: int,
    timezone_name: str = DEFAULT_TIMEZONE,
    reference_dt: datetime | None = None,
) -> ParsedSession:
    """Parse one rendered HTML `statisticRow` with four values."""
    if len(values) != 4:
        raise ParseError(f"Expected 4 history values, got {len(values)}")

    date_text, energy_text, duration_text, cost_text = [
        " ".join(value.split()) for value in values
    ]
    local_dt = parse_date_text(
        date_text,
        timezone_name=timezone_name,
        reference_dt=reference_dt,
    )
    raw_row = {
        "date": date_text,
        "energy": energy_text,
        "duration": duration_text,
        "cost": cost_text,
    }

    return _build_session(
        charger_id=charger_id,
        local_dt=local_dt,
        source_date_text=date_text,
        energy_kwh=parse_decimal(energy_text, "energy"),
        duration_text=duration_text,
        cost=parse_decimal(cost_text, "cost"),
        raw_row=raw_row,
        timezone_name=timezone_name,
    )


def _parse_json_payload(
    payload: Any,
    *,
    charger_id: int,
    timezone_name: str,
    reference_dt: datetime | None,
) -> ParseResult:
    rows = payload if isinstance(payload, list) else [payload]
    sessions: list[ParsedSession] = []
    rejected: list[RejectedRow] = []

    for row in rows:
        if not isinstance(row, dict):
            rejected.append(RejectedRow(row, "JSON row is not an object"))
            continue

        try:
            sessions.append(
                parse_json_row(
                    row,
                    charger_id=charger_id,
                    timezone_name=timezone_name,
                    reference_dt=reference_dt,
                )
            )
        except Exception as exc:
            rejected.append(RejectedRow(row, str(exc)))

    return ParseResult(sessions=sessions, rejected=rejected)


def _parse_html_payload(
    html: str,
    *,
    charger_id: int,
    timezone_name: str,
    reference_dt: datetime | None,
) -> ParseResult:
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select("#textLogs .statisticRow")
    sessions: list[ParsedSession] = []
    rejected: list[RejectedRow] = []

    for row in rows:
        values = [
            cell.get_text(" ", strip=True)
            for cell in row.find_all("div", recursive=False)
        ]

        try:
            sessions.append(
                parse_html_row(
                    values,
                    charger_id=charger_id,
                    timezone_name=timezone_name,
                    reference_dt=reference_dt,
                )
            )
        except Exception as exc:
            rejected.append(RejectedRow(values, str(exc)))

    return ParseResult(sessions=sessions, rejected=rejected)


def parse_charging_history(
    payload: Any,
    *,
    charger_id: int,
    timezone_name: str = DEFAULT_TIMEZONE,
    reference_dt: datetime | None = None,
) -> ParseResult:
    """Parse charger history JSON or rendered HTML into normalized sessions."""
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8", errors="replace")

    if isinstance(payload, str):
        stripped = payload.lstrip("\ufeff").strip()

        if not stripped:
            return ParseResult(sessions=[], rejected=[])

        if stripped.startswith(("[", "{")):
            try:
                return _parse_json_payload(
                    json.loads(stripped),
                    charger_id=charger_id,
                    timezone_name=timezone_name,
                    reference_dt=reference_dt,
                )
            except json.JSONDecodeError:
                pass

        return _parse_html_payload(
            stripped,
            charger_id=charger_id,
            timezone_name=timezone_name,
            reference_dt=reference_dt,
        )

    if isinstance(payload, (list, dict)):
        return _parse_json_payload(
            payload,
            charger_id=charger_id,
            timezone_name=timezone_name,
            reference_dt=reference_dt,
        )

    return ParseResult(
        sessions=[],
        rejected=[RejectedRow(payload, f"Unsupported payload type {type(payload)}")],
    )
