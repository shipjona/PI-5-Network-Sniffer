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
        "swap_used_percent": 5.0,
        "root_total_bytes": 120_000_000_000,
        "root_free_bytes": 108_000_000_000,
        "root_used_percent": 10.0,
        "data_total_bytes": 240_000_000_000,
        "data_free_bytes": 230_000_000_000,
        "data_used_percent": 4.17,
        "uptime_seconds": 3600,
        "throttled_raw": "throttled=0x0",
        "under_voltage_now": 0,
        "under_voltage_ever": 0,
        "frequency_capped_now": 0,
        "frequency_capped_ever": 0,
        "throttled_now": 0,
        "throttled_ever": 0,
        "soft_temp_limit_now": 0,
        "soft_temp_limit_ever": 0,
        "database_size_bytes": 100_000,
        "logs_size_bytes": 20_000,
        "backups_size_bytes": 0,
        "nvme_smart_available": 1,
        "nvme_temperature_c": 35.0,
        "nvme_percentage_used": 1.0,
        "nvme_power_on_hours": 12,
        "nvme_unsafe_shutdowns": 0,
        "nvme_data_written_bytes": 512_000,
        "nvme_media_errors": 0,
        "nvme_error_log_entries": 0,
        "nvme_critical_warning": 0,
        "nvme_smart_status": "passed",
        "nvme_device": "/dev/nvme0",
        "eth0_speed_mbps": 1000,
        "eth0_operstate": "up",
        "eth0_carrier": 1,
        "eth0_rx_bytes": 1000,
        "eth0_tx_bytes": 2000,
        "eth0_rx_errors": 0,
        "eth0_tx_errors": 0,
        "eth0_rx_dropped": 0,
        "eth0_tx_dropped": 0,
        "wlan0_operstate": "up",
        "wlan0_connected_ssid": "Shipman-GRU",
        "wlan0_signal_dbm": -42,
        "wlan0_signal_percent": 100,
        "wlan0_rx_bytes": 3000,
        "wlan0_tx_bytes": 4000,
        "wlan0_rx_errors": 0,
        "wlan0_tx_errors": 0,
        "wlan0_rx_dropped": 0,
        "wlan0_tx_dropped": 0,
        "approved_chargers_visible": 1,
        "web_service_active_state": "active",
        "web_service_restart_count": 0,
        "collector_service_active_state": "active",
        "collector_service_restart_count": 0,
        "report_timer_active_state": "active",
        "report_timer_restart_count": 0,
        "boot_time": "2026-08-01 10:00:00",
        "reboot_count": 1,
        "ntp_synchronized": 1,
        "clock_synchronized": 1,
        "root_filesystem_readonly": 0,
        "data_filesystem_readonly": 0,
        "filesystem_error_count": 0,
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


def test_decode_throttled_flags() -> None:
    decoded = vitals.decode_throttled_flags("throttled=0x50005")

    assert decoded["under_voltage_now"] is True
    assert decoded["throttled_now"] is True
    assert decoded["under_voltage_ever"] is True
    assert decoded["throttled_ever"] is True
    assert decoded["status"] == "warning"


def test_parse_iw_link() -> None:
    parsed = vitals.parse_iw_link(
        "\n".join(
            [
                "Connected to 00:11:22:33:44:55 (on wlan0)",
                "\tSSID: Shipman-GRU",
                "\tsignal: -42 dBm",
            ]
        )
    )

    assert parsed["wlan0_connected_ssid"] == "Shipman-GRU"
    assert parsed["wlan0_signal_dbm"] == -42
    assert parsed["wlan0_signal_percent"] == 100


def test_parse_nvme_smart_json() -> None:
    parsed = vitals.parse_nvme_smart_json(
        {
            "smart_status": {"passed": True},
            "nvme_smart_health_information_log": {
                "temperature": 309,
                "percentage_used": 2,
                "power_on_hours": 123,
                "unsafe_shutdowns": 1,
                "data_units_written": 10,
                "media_errors": 0,
                "num_err_log_entries": 0,
                "critical_warning": 0,
            },
        },
        device="/dev/nvme0",
        tool="smartctl",
    )

    assert parsed["nvme_smart_status"] == "passed"
    assert parsed["nvme_temperature_c"] == 35.9
    assert parsed["nvme_data_written_bytes"] == 5_120_000


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
    assert samples[0]["eth0_speed_mbps"] == 1000
    assert samples[0]["nvme_smart_status"] == "passed"
    temperature = next(trend for trend in trends if trend["metric"] == "temperature_c")
    assert temperature["latest"] == 40.5
    assert temperature["average"] == 40.5
    db_size = next(trend for trend in trends if trend["metric"] == "database_size_bytes")
    assert db_size["latest"] == 100_000


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
    assert payload["sections"]["power"][0]["label"] == "Power state"
