from __future__ import annotations

from grizzl.config import CHARGERS
from grizzl.wifi import current_ssid, scan_configured_chargers, scan_ssids


def configured_chargers() -> list[dict]:
    """Return all enabled chargers from the fleet configuration."""
    return [
        charger
        for charger in CHARGERS
        if charger.get("enabled", True)
    ]


def discover_chargers() -> list[dict]:
    """Return configured chargers whose SSIDs are currently visible."""
    discovered: list[dict] = []

    for charger, observation in scan_configured_chargers():
        discovered_charger = dict(charger)
        discovered_charger["bssid"] = observation.bssid
        discovered_charger["signal"] = observation.signal
        discovered_charger["channel"] = observation.channel
        discovered_charger["frequency"] = observation.frequency
        discovered.append(discovered_charger)

    return sorted(
        discovered,
        key=lambda charger: (
            not charger.get("test_charger", False),
            -(charger.get("signal") or -1),
            str(charger["id"]),
        ),
    )


def active_charger() -> dict | None:
    """Return the configured charger currently connected on Wi-Fi."""
    active_ssid = current_ssid()

    if active_ssid is None:
        return None

    for charger in configured_chargers():
        if charger["ssid"] == active_ssid:
            return charger

    return None


def charger_is_visible(charger: dict) -> bool:
    """Return True when a charger's SSID is visible."""
    return str(charger["ssid"]) in set(scan_ssids())
