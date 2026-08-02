from __future__ import annotations

from pathlib import Path

import grizzl.database as database
from grizzl.services import polling


def test_poll_once_records_zero_when_no_chargers_are_visible(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "grizzl.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)
    monkeypatch.setattr(polling, "configured_chargers", lambda: [])
    database.initialize_database()
    database.set_service_state("collector_last_polled_count", "5")

    result = polling.poll_once(include_wifi=False)
    state = database.get_service_state()

    assert result["polled"] == 0
    assert result["mode"] == "ethernet-guarded-wifi-switching"
    assert state["collector_last_polled_count"]["value"] == "0"


def test_require_ethernet_can_be_disabled_for_offline_appliance(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "grizzl.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)
    monkeypatch.setattr(polling, "REQUIRE_ETHERNET_FOR_WIFI", False)
    monkeypatch.setattr(polling, "ethernet_is_connected", lambda: False)
    database.initialize_database()

    polling.require_ethernet()
    state = database.get_service_state()

    assert state["ethernet_guard_required"]["value"] == "0"


def test_poll_once_reports_offline_mode_when_ethernet_guard_disabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "grizzl.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)
    monkeypatch.setattr(polling, "REQUIRE_ETHERNET_FOR_WIFI", False)
    monkeypatch.setattr(polling, "configured_chargers", lambda: [])
    database.initialize_database()

    result = polling.poll_once(include_wifi=False)

    assert result["mode"] == "offline-wifi-switching"


def test_require_ethernet_raises_when_guard_enabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "grizzl.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)
    monkeypatch.setattr(polling, "REQUIRE_ETHERNET_FOR_WIFI", True)
    monkeypatch.setattr(polling, "ethernet_is_connected", lambda: False)
    database.initialize_database()

    try:
        polling.require_ethernet()
    except polling.EthernetRequiredError:
        pass
    else:
        raise AssertionError("Expected EthernetRequiredError")
