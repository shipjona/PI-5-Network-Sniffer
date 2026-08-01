from __future__ import annotations

import logging
import sys

from grizzl.api import ChargerAPIError, ChargerClient
from grizzl.config import CHARGERS
from grizzl.database import (
    get_session_count,
    initialize_database,
    save_charger_status,
    save_sessions,
    sync_chargers,
)
from grizzl.discovery import discover_chargers
from grizzl.wifi import WiFiError, connect_to_charger, disconnect


def print_step(message: str) -> None:
    print(f"\n{message}")


def print_success(message: str) -> None:
    print(f"✓ {message}")


def print_failure(message: str) -> None:
    print(f"✗ {message}")


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    print_step("Initializing fleet database...")
    initialize_database()
    sync_chargers(CHARGERS)
    print_success(f"{len(CHARGERS)} configured chargers synchronized")

    print_step("Scanning Wi-Fi for configured chargers...")

    try:
        chargers = discover_chargers()
    except WiFiError as exc:
        print_failure(f"Wi-Fi scan failed: {exc}")
        return 1

    if not chargers:
        print_failure("No configured charger SSIDs were found")
        return 1

    print_success(
        "Found: " + ", ".join(str(charger["ssid"]) for charger in chargers)
    )

    overall_success = True

    for charger in chargers:
        charger_id = str(charger["id"])
        ssid = str(charger["ssid"])

        print_step(f"Testing {charger_id} ({ssid})...")

        try:
            print("Connecting...")
            connect_to_charger(charger)
            print_success(f"Connected to {ssid}")

            with ChargerClient(charger) as client:
                print("Querying charger...")
                status = client.status()
                save_charger_status(
                    charger_id,
                    online=True,
                    active_ssid=ssid,
                    http_status=status["http_status"],
                )
                print_success(
                    f"Charger responded with HTTP {status['http_status']}"
                )

                before_count = get_session_count(charger_id)

                print("Downloading sessions...")
                payload = client.sessions()
                inserted = save_sessions(charger_id, payload)
                after_count = get_session_count(charger_id)

                print_success(
                    f"{inserted} new session record(s) saved "
                    f"({before_count} before, {after_count} total)"
                )

        except (WiFiError, ChargerAPIError) as exc:
            overall_success = False
            print_failure(f"{charger_id} failed: {exc}")
            save_charger_status(
                charger_id,
                online=False,
                last_error=str(exc),
            )

        finally:
            print("Disconnecting...")
            try:
                disconnect()
                print_success("Wi-Fi disconnected")
            except WiFiError as exc:
                overall_success = False
                print_failure(f"Disconnect failed: {exc}")

    print_step("Fleet test complete.")

    if overall_success:
        print_success("All discovered chargers completed successfully")
        return 0

    print_failure("One or more charger tests failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
