from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from grizzl.database import initialize_database
from grizzl.export import session_export_rows, write_sessions_csv
from grizzl.parser import DEFAULT_TIMEZONE


def _week_bounds(current: bool) -> tuple[str, str]:
    tz = ZoneInfo(DEFAULT_TIMEZONE)
    now = datetime.now(tz)
    this_monday = (now - timedelta(days=now.weekday())).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    start = this_monday if current else this_monday - timedelta(days=7)
    end = this_monday + timedelta(days=7) if current else this_monday
    return start.isoformat(), end.isoformat()


def _month_bounds(month: str) -> tuple[str, str]:
    tz = ZoneInfo(DEFAULT_TIMEZONE)
    start = datetime.strptime(month, "%Y-%m").replace(tzinfo=tz)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start.isoformat(), end.isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description="Export normalized sessions to CSV.")
    parser.add_argument("--charger-id", type=int)
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--current-week", action="store_true")
    parser.add_argument("--previous-week", action="store_true")
    parser.add_argument("--month", help="Export one month in YYYY-MM format.")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    selected_periods = [
        bool(args.current_week),
        bool(args.previous_week),
        bool(args.month),
    ]
    if sum(selected_periods) > 1:
        raise SystemExit("Choose only one of --current-week, --previous-week, --month")

    start = args.start
    end = args.end
    if args.current_week:
        start, end = _week_bounds(current=True)
    elif args.previous_week:
        start, end = _week_bounds(current=False)
    elif args.month:
        start, end = _month_bounds(args.month)

    initialize_database()
    output_path = Path(args.output)
    rows = session_export_rows(
        charger_id=args.charger_id,
        start=start,
        end=end,
    )
    write_sessions_csv(rows, output_path)

    print(f"Exported {len(rows)} session(s) to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
