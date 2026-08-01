from __future__ import annotations

from datetime import datetime


def format_duration(total_seconds: int) -> str:
    hours, remainder = divmod(int(total_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def format_datetime(value: str) -> str:
    parsed = datetime.fromisoformat(value)
    return parsed.strftime("%b %d, %Y at %I:%M %p")


def format_energy(value: float) -> str:
    return f"{float(value):,.3f} kWh"


def format_currency(value: float) -> str:
    return f"${float(value):,.2f}"
