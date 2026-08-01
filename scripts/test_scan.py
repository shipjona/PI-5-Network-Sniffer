from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from grizzl.config import APPROVED_SSIDS, WIFI_INTERFACE
from grizzl.logging_config import configure_logging
from grizzl.wifi import scan_observations


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan wlan0 and print approved Grizzl-E charger APs."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Show all visible SSIDs instead of only approved charger SSIDs.",
    )
    parser.add_argument(
        "--no-rescan",
        action="store_true",
        help="Use NetworkManager's current Wi-Fi list without requesting a rescan.",
    )
    args = parser.parse_args()

    configure_logging()
    observations = scan_observations(rescan=not args.no_rescan)

    if not args.all:
        observations = [
            observation
            for observation in observations
            if observation.ssid in APPROVED_SSIDS
        ]

    payload = {
        "interface": WIFI_INTERFACE,
        "approved_only": not args.all,
        "visible_count": len(observations),
        "observations": [asdict(observation) for observation in observations],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
