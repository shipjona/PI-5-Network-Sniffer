from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from grizzl.logging_config import configure_logging
from grizzl.services.polling import poll_once, poll_single


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one collector cycle.")
    parser.add_argument("--charger-id", type=int, help="Poll one charger by numeric ID.")
    parser.add_argument(
        "--no-wifi-scan",
        action="store_true",
        help="Skip wlan0 scan in the full collector cycle.",
    )
    args = parser.parse_args()

    configure_logging()

    if args.charger_id is not None:
        result = poll_single(args.charger_id, include_wifi_scan=True)
    else:
        result = poll_once(include_wifi=not args.no_wifi_scan)

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
