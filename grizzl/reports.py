from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from grizzl.config import ENV_FILE, load_environment_file
from grizzl.database import (
    complete_report_run,
    connection,
    create_report_run,
    get_chargers_with_status,
)
from grizzl.export import session_export_rows, sessions_csv_text


REPORT_TIMEZONE = os.getenv("GRIZZL_REPORT_TIMEZONE", "America/Tijuana")


class ReportError(RuntimeError):
    """Raised when a report cannot be generated or sent."""


@dataclass(frozen=True)
class ReportPeriod:
    """Inclusive/exclusive reporting period."""

    start: datetime
    end: datetime

    @property
    def start_iso(self) -> str:
        return self.start.isoformat()

    @property
    def end_iso(self) -> str:
        return self.end.isoformat()


def previous_week_period(
    *,
    timezone_name: str = REPORT_TIMEZONE,
    reference: datetime | None = None,
) -> ReportPeriod:
    """Return Monday 00:00 to next Monday 00:00 for the previous week."""
    tz = ZoneInfo(timezone_name)
    now = reference.astimezone(tz) if reference else datetime.now(tz)
    this_monday = (now - timedelta(days=now.weekday())).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    last_monday = this_monday - timedelta(days=7)
    return ReportPeriod(start=last_monday, end=this_monday)


def period_from_args(
    *,
    start: str | None = None,
    end: str | None = None,
    timezone_name: str = REPORT_TIMEZONE,
) -> ReportPeriod:
    tz = ZoneInfo(timezone_name)
    if start and end:
        return ReportPeriod(
            start=datetime.fromisoformat(start).astimezone(tz),
            end=datetime.fromisoformat(end).astimezone(tz),
        )
    return previous_week_period(timezone_name=timezone_name)


def report_summary(period: ReportPeriod) -> dict[str, Any]:
    """Calculate report totals, charger rollups, failures, and unseen chargers."""
    rows = session_export_rows(start=period.start_iso, end=period.end_iso)
    total_energy = sum(float(row["energy_kwh"] or 0) for row in rows)
    by_charger: dict[int, dict[str, Any]] = {}

    for row in rows:
        charger_id = int(row["charger_id"])
        item = by_charger.setdefault(
            charger_id,
            {
                "charger_id": charger_id,
                "charger_name": row["charger_name"],
                "ssid": row["ssid"],
                "session_count": 0,
                "energy_kwh": 0.0,
            },
        )
        item["session_count"] += 1
        item["energy_kwh"] += float(row["energy_kwh"] or 0)

    with connection() as conn:
        failures = conn.execute(
            """
            SELECT
                r.charger_id,
                c.display_name,
                c.ssid,
                r.completed_at,
                r.error_type,
                r.error_message
            FROM collection_runs r
            JOIN chargers c ON c.id = r.charger_id
            WHERE r.status != 'success'
              AND r.started_at >= ?
              AND r.started_at < ?
            ORDER BY r.started_at DESC
            """,
            (period.start_iso, period.end_iso),
        ).fetchall()
        seen = conn.execute(
            """
            SELECT DISTINCT charger_id
            FROM charger_observations
            WHERE visible = 1
              AND observed_at >= ?
              AND observed_at < ?
            """,
            (period.start_iso, period.end_iso),
        ).fetchall()

    seen_ids = {int(row["charger_id"]) for row in seen}
    unseen = [
        charger for charger in get_chargers_with_status()
        if int(charger["numeric_charger_id"]) not in seen_ids
        and not bool(charger["test_charger"])
    ]

    return {
        "period_start": period.start_iso,
        "period_end": period.end_iso,
        "session_count": len(rows),
        "total_energy_kwh": round(total_energy, 3),
        "by_charger": [
            {
                **item,
                "energy_kwh": round(float(item["energy_kwh"]), 3),
            }
            for item in sorted(by_charger.values(), key=lambda value: value["charger_id"])
        ],
        "unseen_chargers": unseen,
        "failures": [dict(row) for row in failures],
        "csv_rows": rows,
    }


def render_plain_text(summary: dict[str, Any]) -> str:
    lines = [
        "Grizzl-E Charger Monitor Weekly Report",
        f"Period: {summary['period_start']} to {summary['period_end']}",
        f"Sessions: {summary['session_count']}",
        f"Energy: {summary['total_energy_kwh']:.3f} kWh",
        "",
        "By charger:",
    ]

    if summary["by_charger"]:
        for row in summary["by_charger"]:
            lines.append(
                f"- CHARGER_{row['charger_id']} {row['charger_name']}: "
                f"{row['session_count']} session(s), "
                f"{row['energy_kwh']:.3f} kWh"
            )
    else:
        lines.append("- No sessions collected.")

    lines.append("")
    lines.append("Chargers not seen:")
    if summary["unseen_chargers"]:
        for charger in summary["unseen_chargers"]:
            lines.append(
                f"- {charger['charger_id']} {charger['display_name']} "
                f"({charger['ssid']})"
            )
    else:
        lines.append("- None")

    lines.append("")
    lines.append("Collection failures:")
    if summary["failures"]:
        for failure in summary["failures"][:20]:
            lines.append(
                f"- CHARGER_{failure['charger_id']} "
                f"{failure['completed_at']}: {failure['error_message']}"
            )
    else:
        lines.append("- None")

    return "\n".join(lines) + "\n"


def render_html(summary: dict[str, Any]) -> str:
    charger_rows = "".join(
        "<tr>"
        f"<td>CHARGER_{row['charger_id']}</td>"
        f"<td>{row['charger_name']}</td>"
        f"<td>{row['session_count']}</td>"
        f"<td>{row['energy_kwh']:.3f}</td>"
        "</tr>"
        for row in summary["by_charger"]
    ) or "<tr><td colspan='4'>No sessions collected.</td></tr>"

    unseen_rows = "".join(
        "<li>"
        f"{charger['charger_id']} {charger['display_name']} "
        f"({charger['ssid']})"
        "</li>"
        for charger in summary["unseen_chargers"]
    ) or "<li>None</li>"

    failure_rows = "".join(
        "<li>"
        f"CHARGER_{failure['charger_id']} {failure['completed_at']}: "
        f"{failure['error_message']}"
        "</li>"
        for failure in summary["failures"][:20]
    ) or "<li>None</li>"

    return f"""
    <html>
      <body>
        <h1>Grizzl-E Charger Monitor Weekly Report</h1>
        <p><strong>Period:</strong> {summary['period_start']} to {summary['period_end']}</p>
        <p><strong>Sessions:</strong> {summary['session_count']}</p>
        <p><strong>Energy:</strong> {summary['total_energy_kwh']:.3f} kWh</p>
        <h2>By charger</h2>
        <table border="1" cellpadding="5" cellspacing="0">
          <tr><th>Charger</th><th>Name</th><th>Sessions</th><th>kWh</th></tr>
          {charger_rows}
        </table>
        <h2>Chargers not seen</h2>
        <ul>{unseen_rows}</ul>
        <h2>Collection failures</h2>
        <ul>{failure_rows}</ul>
      </body>
    </html>
    """.strip()


def smtp_config() -> dict[str, str | int]:
    load_environment_file()
    required = ["SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "REPORT_RECIPIENT"]
    missing = [name for name in required if not os.getenv(name)]

    if missing:
        raise ReportError(
            f"Missing required SMTP/report setting(s): {', '.join(missing)}. "
            f"Configure {ENV_FILE}."
        )

    return {
        "host": os.environ["SMTP_HOST"],
        "port": int(os.getenv("SMTP_PORT", "587")),
        "username": os.environ["SMTP_USERNAME"],
        "password": os.environ["SMTP_PASSWORD"],
        "recipient": os.environ["REPORT_RECIPIENT"],
        "sender": os.getenv("REPORT_SENDER", os.environ["SMTP_USERNAME"]),
    }


def build_email(summary: dict[str, Any], csv_text: str, recipient: str) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = (
        "Grizzl-E weekly report "
        f"{summary['period_start'][:10]} to {summary['period_end'][:10]}"
    )
    message["From"] = os.getenv("REPORT_SENDER", os.getenv("SMTP_USERNAME", ""))
    message["To"] = recipient
    message.set_content(render_plain_text(summary))
    message.add_alternative(render_html(summary), subtype="html")
    filename = (
        f"grizzl_sessions_{summary['period_start'][:10]}_to_"
        f"{summary['period_end'][:10]}.csv"
    )
    message.add_attachment(
        csv_text.encode("utf-8"),
        maintype="text",
        subtype="csv",
        filename=filename,
    )
    return message


def send_weekly_report(
    *,
    start: str | None = None,
    end: str | None = None,
    dry_run: bool = False,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    period = period_from_args(start=start, end=end)
    summary = report_summary(period)
    csv_text = sessions_csv_text(summary["csv_rows"])
    output_path: Path | None = None

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / (
            f"grizzl_sessions_{period.start.date()}_to_{period.end.date()}.csv"
        )
        output_path.write_text(csv_text, encoding="utf-8")

    recipient = os.getenv("REPORT_RECIPIENT")
    report_run_id = create_report_run(
        report_type="weekly",
        period_start=period.start_iso,
        period_end=period.end_iso,
        recipient=recipient,
        sessions_count=int(summary["session_count"]),
        total_energy_kwh=float(summary["total_energy_kwh"]),
        attachment_path=str(output_path) if output_path else None,
    )

    if dry_run:
        complete_report_run(report_run_id, status="dry-run")
        return {
            "status": "dry-run",
            "report_run_id": report_run_id,
            "summary": summary,
            "csv_path": str(output_path) if output_path else None,
        }

    try:
        config = smtp_config()
        message = build_email(summary, csv_text, str(config["recipient"]))

        with smtplib.SMTP(str(config["host"]), int(config["port"]), timeout=30) as smtp:
            smtp.starttls()
            smtp.login(str(config["username"]), str(config["password"]))
            smtp.send_message(message)

        complete_report_run(report_run_id, status="success")
        return {
            "status": "success",
            "report_run_id": report_run_id,
            "summary": summary,
            "csv_path": str(output_path) if output_path else None,
        }
    except Exception as exc:
        complete_report_run(
            report_run_id,
            status="error",
            error_message=str(exc),
        )
        raise
