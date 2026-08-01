from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from grizzl.config import CHARGERS
from grizzl.database import record_scan_results, set_service_state
from grizzl.wifi import WiFiError, scan_configured_chargers

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScanCycleResult:
    """Result from one approved-SSID scan pass."""

    status: str
    visible_count: int
    observations: list[dict[str, Any]]
    error: str | None = None


def scan_and_record() -> ScanCycleResult:
    """
    Scan wlan0 for configured SSIDs and persist visibility for every charger.

    If NetworkManager or wlan0 is unavailable, production chargers are still
    recorded as not visible so the dashboard/report can show offline state.
    """
    try:
        matches = scan_configured_chargers()
        rows = record_scan_results(matches)
        visible_count = sum(1 for row in rows if row["visible"])
        logger.info(
            "Approved charger scan complete; visible=%d configured=%d",
            visible_count,
            len(rows),
        )
        set_service_state("scanner_last_error", None)
        return ScanCycleResult(
            status="success",
            visible_count=visible_count,
            observations=rows,
        )
    except WiFiError as exc:
        logger.warning("Wi-Fi scan failed; logging configured APs offline: %s", exc)
        rows = record_scan_results([])
        set_service_state("scanner_last_error", str(exc))
        return ScanCycleResult(
            status="error",
            visible_count=0,
            observations=rows,
            error=str(exc),
        )


def visible_wifi_chargers_from_last_scan(
    observations: list[dict[str, Any]],
) -> set[int]:
    """Return visible Wi-Fi charger IDs from a scan result."""
    configured_wifi_ids = {
        int(charger.get("charger_id", 0))
        for charger in CHARGERS
        if charger.get("connect_mode", "wifi") == "wifi"
    }
    return {
        int(row["charger_id"])
        for row in observations
        if row.get("visible") and int(row["charger_id"]) in configured_wifi_ids
    }
