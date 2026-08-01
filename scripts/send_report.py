from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from grizzl.reports import send_weekly_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate or send a weekly report.")
    parser.add_argument("--start", help="Inclusive ISO start datetime.")
    parser.add_argument("--end", help="Exclusive ISO end datetime.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "reports",
        help="Directory for generated CSV attachments.",
    )
    args = parser.parse_args()

    result = send_weekly_report(
        start=args.start,
        end=args.end,
        dry_run=args.dry_run,
        output_dir=args.output_dir,
    )
    printable = {
        "status": result["status"],
        "report_run_id": result["report_run_id"],
        "csv_path": result["csv_path"],
        "session_count": result["summary"]["session_count"],
        "total_energy_kwh": result["summary"]["total_energy_kwh"],
    }
    print(json.dumps(printable, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
