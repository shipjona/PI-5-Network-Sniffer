from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import grizzl.database as database
from grizzl import vitals


def sample_vitals() -> dict:
    return {
        "sampled_at": "2026-08-01T18:00:00+00:00",
        "temperature_c": 40.5,
        "cpu_percent": 12.5,
        "cpu_frequency_mhz": 2400.0,
        "load_1": 0.14,
        "load_5": 0.09,
        "load_15": 0.04,
        "memory_total_bytes": 8_000_000_000,
        "memory_available_bytes": 6_000_000_000,
        "memory_used_percent": 25.0,
        "swap_total_bytes": 2_000_000_000,
        "swap_free_bytes": 1_900_000_000,
        "root_total_bytes": 120_000_000_000,
        "root_free_bytes": 108_000_000_000,
        "root_used_percent": 10.0,
        "data_total_bytes": 240_000_000_000,
        "data_free_bytes": 230_000_000_000,
        "data_used_percent": 4.17,
        "uptime_seconds": 3600,
        "throttled_raw": "throttled=0x0",
    }


def test_parse_meminfo_converts_kb_to_bytes() -> None:
    parsed = vitals.parse_meminfo(
        "\n".join(
            [
                "MemTotal:        1000 kB",
                "MemAvailable:     750 kB",
                "SwapTotal:        500 kB",
            ]
        )
    )

    assert parsed["MemTotal"] == 1_024_000
    assert parsed["MemAvailable"] == 768_000
    assert parsed["SwapTotal"] == 512_000


def test_calculate_cpu_percent_from_proc_stat_snapshots() -> None:
    assert vitals.calculate_cpu_percent((100, 40), (200, 70)) == 70.0


def test_save_and_summarize_system_vitals(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "grizzl.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)
    database.initialize_database()
    row_id = database.save_system_vitals(sample_vitals())

    samples = database.list_system_vitals(
        since="2026-08-01T00:00:00+00:00",
    )
    trends = database.summarize_system_vitals(
        since="2026-08-01T00:00:00+00:00",
    )

    assert row_id == 1
    assert samples[0]["temperature_c"] == 40.5
    temperature = next(trend for trend in trends if trend["metric"] == "temperature_c")
    assert temperature["latest"] == 40.5
    assert temperature["average"] == 40.5


def test_build_vitals_payload_records_current_sample(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "grizzl.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)
    monkeypatch.setattr(vitals, "collect_system_vitals", sample_vitals)
    monkeypatch.setattr(
        vitals,
        "_utc_now",
        lambda: datetime(2026, 8, 1, 18, 30, tzinfo=timezone.utc),
    )

    payload = vitals.build_vitals_payload("1h")

    assert payload["selected_range"] == "1h"
    assert payload["current"]["id"] == 1
    assert payload["samples"][0]["temperature_c"] == 40.5
