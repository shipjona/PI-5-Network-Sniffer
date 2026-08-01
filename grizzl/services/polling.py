from __future__ import annotations

import logging
import subprocess
import time
from typing import Any

from grizzl.api import ChargerAPIError, ChargerClient
from grizzl.config import CHARGERS, POLL_INTERVAL_SECONDS
from grizzl.database import (
    save_parsed_sessions,
    save_charger_status,
    sync_chargers,
)
from grizzl.discovery import discover_chargers
from grizzl.parser import parse_charging_history
from grizzl.wifi import WiFiError, connect_to_charger, disconnect

logger = logging.getLogger(__name__)


class EthernetRequiredError(RuntimeError):
    """Raised when Wi-Fi switching is requested without wired connectivity."""


def _run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=False,
        capture_output=True,
        text=True,
    )


def ethernet_is_connected() -> bool:
    """
    Return True when NetworkManager reports an active non-loopback,
    non-Wi-Fi Ethernet device.
    """
    result = _run_command(
        [
            "nmcli",
            "-t",
            "-f",
            "DEVICE,TYPE,STATE",
            "device",
            "status",
        ]
    )

    if result.returncode != 0:
        logger.error(
            "Unable to inspect network devices: %s",
            result.stderr.strip(),
        )
        return False

    for line in result.stdout.splitlines():
        parts = line.split(":")
        if len(parts) < 3:
            continue

        device, device_type, state = parts[0], parts[1], parts[2]

        if (
            device
            and device != "lo"
            and device_type == "ethernet"
            and state == "connected"
        ):
            return True

    return False


def require_ethernet() -> None:
    """
    Refuse to manipulate Wi-Fi unless a wired connection is active.

    This protects the SSH session from being lost when wlan0 disconnects
    from the normal mesh network.
    """
    if not ethernet_is_connected():
        raise EthernetRequiredError(
            "Fleet Wi-Fi switching is disabled because no active Ethernet "
            "connection was detected."
        )


def _poll_charger(charger: dict[str, Any]) -> dict[str, Any]:
    charger_id = str(charger["id"])
    uses_wifi = charger.get("connect_mode", "wifi") == "wifi"

    try:
        if uses_wifi:
            logger.info(
                "Connecting wlan0 to charger=%s ssid=%s",
                charger_id,
                charger["ssid"],
            )
            connect_to_charger(charger)
        else:
            logger.info(
                "Polling charger=%s directly at %s",
                charger_id,
                charger.get("target_url") or charger.get("url"),
            )

        with ChargerClient(charger) as client:
            status = client.status()

            save_charger_status(
                charger_id,
                online=True,
                active_ssid=str(charger["ssid"]),
                http_status=status.get("http_status"),
                last_error=None,
            )

            payload = client.sessions()
            parse_result = parse_charging_history(
                payload,
                charger_id=int(charger.get("charger_id", 0)),
            )
            insert_result = save_parsed_sessions(
                int(charger.get("charger_id", 0)),
                parse_result.sessions,
                rejected_count=len(parse_result.rejected),
            )

        logger.info(
            "%s: poll succeeded; parsed=%d inserted=%d duplicates=%d rejected=%d",
            charger_id,
            insert_result.parsed,
            insert_result.inserted,
            insert_result.duplicates,
            insert_result.rejected,
        )

        return {
            "charger_id": charger_id,
            "status": "success",
            "parsed": insert_result.parsed,
            "inserted": insert_result.inserted,
            "duplicates": insert_result.duplicates,
            "rejected": insert_result.rejected,
        }

    except (WiFiError, ChargerAPIError) as exc:
        logger.exception("%s failed: %s", charger_id, exc)

        save_charger_status(
            charger_id,
            online=False,
            active_ssid=None,
            last_error=str(exc),
        )

        return {
            "charger_id": charger_id,
            "status": "error",
            "error": str(exc),
        }

    except Exception as exc:
        logger.exception("%s unexpected failure: %s", charger_id, exc)

        save_charger_status(
            charger_id,
            online=False,
            active_ssid=None,
            last_error=str(exc),
        )

        return {
            "charger_id": charger_id,
            "status": "error",
            "error": str(exc),
        }

    finally:
        if uses_wifi:
            try:
                disconnect()
            except Exception:
                logger.exception(
                    "Failed to disconnect wlan0 after charger=%s",
                    charger_id,
                )


def poll_once() -> dict[str, Any]:
    """
    Discover and poll all visible configured chargers.

    An active Ethernet connection is mandatory because this cycle may
    disconnect wlan0 from the normal mesh network.
    """
    sync_chargers(CHARGERS)

    chargers = discover_chargers()
    wifi_chargers = [
        charger for charger in chargers
        if charger.get("connect_mode", "wifi") == "wifi"
    ]

    if wifi_chargers:
        require_ethernet()

    if not chargers:
        logger.info("No configured charger SSIDs are currently visible.")
        return {
            "status": "success",
            "mode": "ethernet-guarded-wifi-switching",
            "polled": 0,
            "results": [],
        }

    results = [_poll_charger(charger) for charger in chargers]

    return {
        "status": "success",
        "mode": "ethernet-guarded-wifi-switching",
        "polled": len(results),
        "results": results,
    }


def run_forever() -> None:
    logger.info(
        "Ethernet-guarded fleet poller started; interval=%s seconds",
        POLL_INTERVAL_SECONDS,
    )

    while True:
        try:
            poll_once()
        except EthernetRequiredError as exc:
            logger.warning("%s", exc)
        except Exception:
            logger.exception("Fleet polling cycle failed")

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    run_forever()
