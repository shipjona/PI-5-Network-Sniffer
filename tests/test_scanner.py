from __future__ import annotations

from pathlib import Path

import grizzl.database as database
import grizzl.scanner as scanner
from grizzl.config import CHARGERS
from grizzl.wifi import WiFiError


def test_scan_failure_records_work_chargers_offline(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "grizzl.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)

    def fail_scan():
        raise WiFiError("nmcli unavailable")

    monkeypatch.setattr(scanner, "scan_configured_chargers", fail_scan)
    database.initialize_database()
    database.sync_chargers(CHARGERS)

    result = scanner.scan_and_record()
    chargers = database.get_chargers_with_status()
    work_chargers = [charger for charger in chargers if not charger["test_charger"]]

    assert result.status == "error"
    assert result.visible_count == 0
    assert len(work_chargers) == 14
    assert all(charger["last_error"] == "SSID not visible" for charger in work_chargers)


def test_successful_scan_clears_previous_scanner_error(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "grizzl.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)
    monkeypatch.setattr(scanner, "scan_configured_chargers", lambda: [])
    database.initialize_database()
    database.sync_chargers(CHARGERS)
    database.set_service_state("scanner_last_error", "old scan failure")

    result = scanner.scan_and_record()
    state = database.get_service_state()

    assert result.status == "success"
    assert state["scanner_last_error"]["value"] is None
