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
    assert state["collector_last_polled_count"]["value"] == "0"
