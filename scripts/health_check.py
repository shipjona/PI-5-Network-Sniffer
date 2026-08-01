from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from grizzl.health import run_health_checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Grizzl-E monitor health checks.")
    parser.add_argument(
        "--skip-test-charger",
        action="store_true",
        help="Do not attempt to reach the development charger URL.",
    )
    args = parser.parse_args()

    result = run_health_checks(include_test_charger=not args.skip_test_charger)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["overall"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
