from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from grizzl.config import CHARGERS, LOG_ENDPOINT, REQUEST_TIMEOUT_SECONDS
from grizzl.database import (
    get_normalized_session_count,
    initialize_database,
    save_parsed_sessions,
    sync_chargers,
)
from grizzl.parser import parse_charging_history


def _charger_by_numeric_id(charger_id: int) -> dict:
    for charger in CHARGERS:
        if int(charger.get("charger_id", -1)) == charger_id:
            return charger
    raise SystemExit(f"Unknown configured numeric charger_id: {charger_id}")


def _load_payload(args: argparse.Namespace, charger: dict) -> str:
    if args.fixture:
        return Path(args.fixture).read_text(encoding="utf-8")

    target_url = str(charger.get("target_url") or charger["url"]).rstrip("/")
    url = f"{target_url}/{LOG_ENDPOINT.lstrip('/')}"
    response = requests.post(url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    if args.save_fixture:
        fixture_path = Path(args.save_fixture)
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(response.text, encoding="utf-8")

    return response.text


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch or import Grizzl-E charging history safely."
    )
    parser.add_argument("--charger-id", type=int, default=0)
    parser.add_argument(
        "--fixture",
        help="Parse an existing saved payload instead of calling the charger.",
    )
    parser.add_argument(
        "--save-fixture",
        help="Write the fetched raw response to this path.",
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Parse and print counts without inserting into SQLite.",
    )
    args = parser.parse_args()

    charger = _charger_by_numeric_id(args.charger_id)
    payload = _load_payload(args, charger)
    parse_result = parse_charging_history(
        payload,
        charger_id=args.charger_id,
    )

    result = {
        "charger_id": args.charger_id,
        "records_parsed": len(parse_result.sessions),
        "records_rejected": len(parse_result.rejected),
        "records_inserted": 0,
        "records_duplicate": 0,
        "total_sessions": None,
    }

    if not args.no_db:
        initialize_database()
        sync_chargers(CHARGERS)
        insert_result = save_parsed_sessions(
            args.charger_id,
            parse_result.sessions,
            rejected_count=len(parse_result.rejected),
        )
        result["records_inserted"] = insert_result.inserted
        result["records_duplicate"] = insert_result.duplicates
        result["total_sessions"] = get_normalized_session_count(args.charger_id)

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not parse_result.rejected else 2


if __name__ == "__main__":
    raise SystemExit(main())
