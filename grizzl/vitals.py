from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from grizzl.config import DB_PATH, PROJECT_ROOT
from grizzl.database import (
    get_service_state,
    get_vitals_operational_summary,
    list_system_vitals,
    save_system_vitals,
    summarize_system_vitals,
)

VITAL_RANGES: dict[str, tuple[str, timedelta]] = {
    "1h": ("Last hour", timedelta(hours=1)),
    "6h": ("Last 6 hours", timedelta(hours=6)),
    "24h": ("Last 24 hours", timedelta(hours=24)),
    "7d": ("Last 7 days", timedelta(days=7)),
    "30d": ("Last 30 days", timedelta(days=30)),
}
DEFAULT_VITAL_RANGE = "24h"

SYSTEMD_UNITS: dict[str, str] = {
    "web_service": "grizzl-monitor-web.service",
    "collector_service": "grizzl-monitor-collector.service",
    "report_timer": "grizzl-monitor-report.timer",
}

THROTTLED_BITS: tuple[tuple[int, str, str], ...] = (
    (0, "under_voltage_now", "Under-voltage now"),
    (1, "frequency_capped_now", "Frequency capped now"),
    (2, "throttled_now", "Throttled now"),
    (3, "soft_temp_limit_now", "Soft temperature limit now"),
    (16, "under_voltage_ever", "Under-voltage since boot"),
    (17, "frequency_capped_ever", "Frequency capped since boot"),
    (18, "throttled_ever", "Throttled since boot"),
    (19, "soft_temp_limit_ever", "Soft temperature limit since boot"),
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_vital_range(range_key: str | None) -> str:
    """Return a supported range key for vitals trend queries."""
    if range_key in VITAL_RANGES:
        return str(range_key)
    return DEFAULT_VITAL_RANGE


def vital_range_options() -> list[dict[str, str]]:
    """Return selectable vitals ranges for the dashboard."""
    return [
        {"key": key, "label": label}
        for key, (label, _delta) in VITAL_RANGES.items()
    ]


def _run(args: list[str], timeout: int = 5) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError, PermissionError):
        return None


def _read_int(path: Path) -> int | None:
    text = _read_text(path)
    if text is None:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _read_float(path: Path, divisor: float = 1.0) -> float | None:
    text = _read_text(path)
    if text is None:
        return None
    try:
        return float(text) / divisor
    except ValueError:
        return None


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _bool_int(value: bool | None) -> int | None:
    if value is None:
        return None
    return 1 if value else 0


def read_temperature_c() -> float | None:
    """Return CPU temperature in Celsius when available."""
    try:
        result = _run(["vcgencmd", "measure_temp"])
        if result.returncode == 0:
            raw = result.stdout.strip()
            marker = "temp="
            if raw.startswith(marker) and raw.endswith("'C"):
                return float(raw[len(marker):-2])
    except (FileNotFoundError, ValueError, subprocess.SubprocessError):
        pass

    return _read_float(Path("/sys/class/thermal/thermal_zone0/temp"), 1000)


def read_throttled_raw() -> str | None:
    """Return raw Raspberry Pi throttling flags from vcgencmd."""
    try:
        result = _run(["vcgencmd", "get_throttled"])
    except (FileNotFoundError, subprocess.SubprocessError):
        return None

    if result.returncode != 0:
        return None

    value = result.stdout.strip()
    return value or None


def parse_throttled_value(raw: str | None) -> int | None:
    """Parse vcgencmd get_throttled output into an integer bit field."""
    if not raw:
        return None
    value = raw.strip()
    if "=" in value:
        value = value.split("=", 1)[1].strip()
    try:
        return int(value, 16 if value.lower().startswith("0x") else 10)
    except ValueError:
        return None


def decode_throttled_flags(raw: str | None) -> dict[str, Any]:
    """Decode Raspberry Pi power/throttle flags into named booleans."""
    value = parse_throttled_value(raw)
    decoded: dict[str, Any] = {
        "raw": raw,
        "value": value,
        "status": "unavailable" if value is None else "ok",
        "messages": [],
    }

    for bit, key, label in THROTTLED_BITS:
        active = bool(value & (1 << bit)) if value is not None else None
        decoded[key] = active
        if active:
            decoded["messages"].append(label)

    current_issue = any(
        decoded.get(key)
        for key in (
            "under_voltage_now",
            "frequency_capped_now",
            "throttled_now",
            "soft_temp_limit_now",
        )
    )
    previous_issue = any(
        decoded.get(key)
        for key in (
            "under_voltage_ever",
            "frequency_capped_ever",
            "throttled_ever",
            "soft_temp_limit_ever",
        )
    )
    if current_issue:
        decoded["status"] = "warning"
    elif previous_issue:
        decoded["status"] = "history"

    return decoded


def read_cpu_frequency_mhz() -> float | None:
    """Return current CPU frequency in MHz when Linux cpufreq is available."""
    khz = _read_float(
        Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq")
    )
    if khz is None:
        return None
    return khz / 1000


def read_proc_stat(path: Path = Path("/proc/stat")) -> tuple[int, int] | None:
    """Return total and idle CPU counters from /proc/stat."""
    try:
        first_line = path.read_text(encoding="utf-8").splitlines()[0]
    except (FileNotFoundError, IndexError, OSError, PermissionError):
        return None

    parts = first_line.split()
    if not parts or parts[0] != "cpu":
        return None

    try:
        values = [int(value) for value in parts[1:]]
    except ValueError:
        return None

    idle = values[3] + (values[4] if len(values) > 4 else 0)
    return sum(values), idle


def calculate_cpu_percent(
    before: tuple[int, int] | None,
    after: tuple[int, int] | None,
) -> float | None:
    """Calculate CPU busy percentage from two /proc/stat snapshots."""
    if before is None or after is None:
        return None

    total_delta = after[0] - before[0]
    idle_delta = after[1] - before[1]
    if total_delta <= 0:
        return None

    busy = max(0, total_delta - idle_delta)
    return round((busy / total_delta) * 100, 2)


def read_cpu_percent(interval_seconds: float = 0.1) -> float | None:
    """Return short-window CPU busy percentage."""
    before = read_proc_stat()
    if before is None:
        return None

    time.sleep(interval_seconds)
    return calculate_cpu_percent(before, read_proc_stat())


def parse_meminfo(text: str) -> dict[str, int]:
    """Parse Linux /proc/meminfo content into byte values."""
    values: dict[str, int] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue

        key, raw_value = line.split(":", 1)
        parts = raw_value.strip().split()
        if not parts:
            continue

        try:
            value = int(parts[0])
        except ValueError:
            continue

        multiplier = 1024 if len(parts) > 1 and parts[1].lower() == "kb" else 1
        values[key] = value * multiplier

    return values


def read_memory() -> dict[str, int | float | None]:
    """Return memory and swap counters from /proc/meminfo."""
    try:
        parsed = parse_meminfo(Path("/proc/meminfo").read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, PermissionError):
        return {
            "memory_total_bytes": None,
            "memory_available_bytes": None,
            "memory_used_percent": None,
            "swap_total_bytes": None,
            "swap_free_bytes": None,
            "swap_used_percent": None,
        }

    total = parsed.get("MemTotal")
    available = parsed.get("MemAvailable")
    swap_total = parsed.get("SwapTotal")
    swap_free = parsed.get("SwapFree")
    used_percent = None
    swap_used_percent = None

    if total and available is not None:
        used_percent = round(((total - available) / total) * 100, 2)
    if swap_total and swap_free is not None:
        swap_used_percent = round(((swap_total - swap_free) / swap_total) * 100, 2)

    return {
        "memory_total_bytes": total,
        "memory_available_bytes": available,
        "memory_used_percent": used_percent,
        "swap_total_bytes": swap_total,
        "swap_free_bytes": swap_free,
        "swap_used_percent": swap_used_percent,
    }


def _disk_usage(path: Path, prefix: str) -> dict[str, int | float | None]:
    try:
        usage = shutil.disk_usage(path)
    except (FileNotFoundError, OSError, PermissionError):
        return {
            f"{prefix}_total_bytes": None,
            f"{prefix}_free_bytes": None,
            f"{prefix}_used_percent": None,
        }

    used = usage.total - usage.free
    return {
        f"{prefix}_total_bytes": usage.total,
        f"{prefix}_free_bytes": usage.free,
        f"{prefix}_used_percent": round((used / usage.total) * 100, 2)
        if usage.total
        else None,
    }


def read_load_average() -> tuple[float | None, float | None, float | None]:
    """Return 1, 5, and 15 minute load averages where available."""
    try:
        return os.getloadavg()
    except (AttributeError, OSError):
        return None, None, None


def read_uptime_seconds() -> int | None:
    """Return uptime seconds from /proc/uptime."""
    try:
        return int(float(Path("/proc/uptime").read_text(encoding="utf-8").split()[0]))
    except (FileNotFoundError, IndexError, OSError, PermissionError, ValueError):
        return None


def _path_size_bytes(path: Path) -> int | None:
    if not path.exists():
        return 0
    if path.is_file():
        try:
            return path.stat().st_size
        except OSError:
            return None

    total = 0
    try:
        for child in path.rglob("*"):
            if child.is_file():
                total += child.stat().st_size
    except (OSError, PermissionError):
        return None
    return total


def _sqlite_size_bytes(path: Path) -> int | None:
    total = 0
    found = False
    for candidate in (path, path.with_name(path.name + "-wal"), path.with_name(path.name + "-shm")):
        size = _path_size_bytes(candidate)
        if size is None:
            continue
        total += size
        found = True
    return total if found else None


def read_storage_sizes() -> dict[str, int | None]:
    """Return project storage component sizes."""
    return {
        "database_size_bytes": _sqlite_size_bytes(Path(DB_PATH)),
        "logs_size_bytes": _path_size_bytes(PROJECT_ROOT / "logs"),
        "backups_size_bytes": _path_size_bytes(PROJECT_ROOT / "backups"),
    }


def _temperature_to_c(value: Any) -> float | None:
    numeric = _to_float(value)
    if numeric is None:
        return None
    if numeric > 200:
        return round(numeric - 273.15, 1)
    return numeric


def parse_nvme_smart_json(
    data: dict[str, Any],
    *,
    device: str,
    tool: str,
) -> dict[str, Any]:
    """Normalize smartctl/nvme-cli NVMe SMART JSON into dashboard fields."""
    log = data.get("nvme_smart_health_information_log")
    if not isinstance(log, dict):
        log = data

    smart_status = data.get("smart_status")
    status_passed = (
        smart_status.get("passed") if isinstance(smart_status, dict) else None
    )
    critical_warning = _to_int(log.get("critical_warning"))
    temperature = (
        _temperature_to_c(data.get("temperature", {}).get("current"))
        if isinstance(data.get("temperature"), dict)
        else None
    )
    if temperature is None:
        temperature = _temperature_to_c(log.get("temperature"))

    data_units_written = _to_int(log.get("data_units_written"))
    data_written_bytes = (
        data_units_written * 512000 if data_units_written is not None else None
    )

    if isinstance(status_passed, bool):
        health_status = "passed" if status_passed else "failed"
    elif critical_warning is not None:
        health_status = "passed" if critical_warning == 0 else "warning"
    else:
        health_status = "unknown"

    return {
        "nvme_smart_available": 1,
        "nvme_smart_tool": tool,
        "nvme_device": device,
        "nvme_smart_status": health_status,
        "nvme_temperature_c": temperature,
        "nvme_percentage_used": _to_float(log.get("percentage_used")),
        "nvme_power_on_hours": _to_int(log.get("power_on_hours")),
        "nvme_unsafe_shutdowns": _to_int(log.get("unsafe_shutdowns")),
        "nvme_data_written_bytes": data_written_bytes,
        "nvme_media_errors": _to_int(log.get("media_errors")),
        "nvme_error_log_entries": _to_int(log.get("num_err_log_entries")),
        "nvme_critical_warning": critical_warning,
        "nvme_smart_error": None,
    }


def read_nvme_smart() -> dict[str, Any]:
    """Return NVMe SMART health when smartctl or nvme-cli is available."""
    fallback = {
        "nvme_smart_available": 0,
        "nvme_smart_tool": None,
        "nvme_device": None,
        "nvme_smart_status": None,
        "nvme_temperature_c": None,
        "nvme_percentage_used": None,
        "nvme_power_on_hours": None,
        "nvme_unsafe_shutdowns": None,
        "nvme_data_written_bytes": None,
        "nvme_media_errors": None,
        "nvme_error_log_entries": None,
        "nvme_critical_warning": None,
        "nvme_smart_error": "smartctl/nvme unavailable",
    }
    devices = ("/dev/nvme0", "/dev/nvme0n1")
    last_error = fallback["nvme_smart_error"]

    for device in devices:
        try:
            result = _run(["smartctl", "-a", "-j", device], timeout=8)
        except (FileNotFoundError, subprocess.SubprocessError):
            break

        if result.stdout.strip():
            try:
                return parse_nvme_smart_json(
                    json.loads(result.stdout),
                    device=device,
                    tool="smartctl",
                )
            except json.JSONDecodeError:
                last_error = result.stderr.strip() or "invalid smartctl JSON"
        elif result.stderr.strip():
            last_error = result.stderr.strip()

    for device in devices:
        try:
            result = _run(
                ["nvme", "smart-log", device, "--output-format=json"],
                timeout=8,
            )
        except (FileNotFoundError, subprocess.SubprocessError):
            break

        if result.returncode == 0 and result.stdout.strip():
            try:
                return parse_nvme_smart_json(
                    json.loads(result.stdout),
                    device=device,
                    tool="nvme",
                )
            except json.JSONDecodeError:
                last_error = result.stderr.strip() or "invalid nvme JSON"
        elif result.stderr.strip():
            last_error = result.stderr.strip()

    fallback["nvme_smart_error"] = last_error
    return fallback


def read_interface_stats(interface: str) -> dict[str, Any]:
    """Read link state and counters from /sys/class/net."""
    base = Path("/sys/class/net") / interface
    prefix = interface.replace("-", "_")
    stats = base / "statistics"
    return {
        f"{prefix}_operstate": _read_text(base / "operstate"),
        f"{prefix}_carrier": _read_int(base / "carrier"),
        f"{prefix}_speed_mbps": _read_int(base / "speed"),
        f"{prefix}_rx_bytes": _read_int(stats / "rx_bytes"),
        f"{prefix}_tx_bytes": _read_int(stats / "tx_bytes"),
        f"{prefix}_rx_errors": _read_int(stats / "rx_errors"),
        f"{prefix}_tx_errors": _read_int(stats / "tx_errors"),
        f"{prefix}_rx_dropped": _read_int(stats / "rx_dropped"),
        f"{prefix}_tx_dropped": _read_int(stats / "tx_dropped"),
    }


def _signal_percent_from_dbm(dbm: int | None) -> int | None:
    if dbm is None:
        return None
    return max(0, min(100, int(round((dbm + 100) * 2))))


def parse_iw_link(text: str) -> dict[str, Any]:
    """Parse `iw dev wlan0 link` output."""
    parsed: dict[str, Any] = {
        "wlan0_connected_ssid": None,
        "wlan0_signal_dbm": None,
        "wlan0_signal_percent": None,
    }
    if "Not connected" in text:
        return parsed

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("SSID:"):
            parsed["wlan0_connected_ssid"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("signal:"):
            signal = _to_float(stripped.split(":", 1)[1])
            dbm = int(signal) if signal is not None else None
            parsed["wlan0_signal_dbm"] = dbm
            parsed["wlan0_signal_percent"] = _signal_percent_from_dbm(dbm)

    return parsed


def read_wlan_link(interface: str = "wlan0") -> dict[str, Any]:
    try:
        result = _run(["iw", "dev", interface, "link"], timeout=5)
    except (FileNotFoundError, subprocess.SubprocessError):
        return {
            "wlan0_connected_ssid": None,
            "wlan0_signal_dbm": None,
            "wlan0_signal_percent": None,
        }
    if result.returncode != 0:
        return {
            "wlan0_connected_ssid": None,
            "wlan0_signal_dbm": None,
            "wlan0_signal_percent": None,
        }
    return parse_iw_link(result.stdout)


def read_approved_visible_count() -> int | None:
    try:
        state = get_service_state()
    except Exception:
        return None
    value = state.get("scanner_visible_count", {}).get("value")
    return _to_int(value)


def read_network() -> dict[str, Any]:
    """Return Ethernet/wlan state without initiating a Wi-Fi scan."""
    sample = read_interface_stats("eth0")
    sample.update(read_interface_stats("wlan0"))
    sample.update(read_wlan_link("wlan0"))
    sample["approved_chargers_visible"] = read_approved_visible_count()
    return sample


def parse_systemctl_show(text: str) -> dict[str, str]:
    """Parse key=value output from systemctl show."""
    parsed: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key] = value
    return parsed


def read_systemd_unit(prefix: str, unit: str) -> dict[str, Any]:
    try:
        result = _run(
            [
                "systemctl",
                "show",
                unit,
                "--no-pager",
                "-p",
                "ActiveState",
                "-p",
                "SubState",
                "-p",
                "NRestarts",
                "-p",
                "ExecMainPID",
                "-p",
                "MemoryCurrent",
                "-p",
                "CPUUsageNSec",
            ],
            timeout=5,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        result = None

    if result is None or result.returncode != 0:
        return {
            f"{prefix}_active_state": None,
            f"{prefix}_sub_state": None,
            f"{prefix}_restart_count": None,
            f"{prefix}_pid": None,
            f"{prefix}_memory_bytes": None,
            f"{prefix}_cpu_seconds": None,
        }

    parsed = parse_systemctl_show(result.stdout)
    cpu_ns = _to_int(parsed.get("CPUUsageNSec"))
    return {
        f"{prefix}_active_state": parsed.get("ActiveState") or None,
        f"{prefix}_sub_state": parsed.get("SubState") or None,
        f"{prefix}_restart_count": _to_int(parsed.get("NRestarts")),
        f"{prefix}_pid": _to_int(parsed.get("ExecMainPID")),
        f"{prefix}_memory_bytes": _to_int(parsed.get("MemoryCurrent")),
        f"{prefix}_cpu_seconds": round(cpu_ns / 1_000_000_000, 2)
        if cpu_ns is not None
        else None,
    }


def read_systemd_units() -> dict[str, Any]:
    sample: dict[str, Any] = {}
    for prefix, unit in SYSTEMD_UNITS.items():
        sample.update(read_systemd_unit(prefix, unit))
    return sample


def parse_timedatectl_show(text: str) -> dict[str, str]:
    return parse_systemctl_show(text)


def read_time_sync() -> dict[str, Any]:
    try:
        result = _run(
            [
                "timedatectl",
                "show",
                "--property=NTPSynchronized",
                "--property=SystemClockSynchronized",
                "--property=Timezone",
            ],
            timeout=5,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        result = None

    if result is None or result.returncode != 0:
        return {
            "ntp_synchronized": None,
            "clock_synchronized": None,
            "system_timezone": None,
        }

    parsed = parse_timedatectl_show(result.stdout)
    return {
        "ntp_synchronized": _bool_int(parsed.get("NTPSynchronized") == "yes"),
        "clock_synchronized": _bool_int(
            parsed.get("SystemClockSynchronized") == "yes"
        ),
        "system_timezone": parsed.get("Timezone") or None,
    }


def read_boot_time() -> str | None:
    try:
        result = _run(["uptime", "-s"], timeout=5)
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def read_reboot_count() -> int | None:
    try:
        result = _run(["journalctl", "--list-boots", "--no-pager", "--quiet"], timeout=8)
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return len([line for line in result.stdout.splitlines() if line.strip()])


def read_mount_readonly(path: Path) -> int | None:
    try:
        result = _run(["findmnt", "-no", "OPTIONS", "--target", str(path)], timeout=5)
    except (FileNotFoundError, subprocess.SubprocessError):
        result = None

    if result is not None and result.returncode == 0:
        options = result.stdout.strip().split(",")
        return 1 if "ro" in options else 0

    try:
        target = path.resolve()
        rows = Path("/proc/mounts").read_text(encoding="utf-8").splitlines()
    except (FileNotFoundError, OSError, PermissionError):
        return None

    best_match: tuple[int, str] | None = None
    for row in rows:
        parts = row.split()
        if len(parts) < 4:
            continue
        mountpoint = Path(parts[1])
        try:
            if target == mountpoint or mountpoint in target.parents:
                length = len(str(mountpoint))
                if best_match is None or length > best_match[0]:
                    best_match = (length, parts[3])
        except RuntimeError:
            continue

    if best_match is None:
        return None
    return 1 if "ro" in best_match[1].split(",") else 0


def read_filesystem_error_count() -> int | None:
    try:
        result = _run(["dmesg", "--level=err,crit,alert,emerg"], timeout=8)
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None

    patterns = ("i/o error", "ext4-fs error", "filesystem error", "buffer i/o")
    return sum(
        1
        for line in result.stdout.splitlines()
        if any(pattern in line.lower() for pattern in patterns)
    )


def read_reliability() -> dict[str, Any]:
    sample = {
        "boot_time": read_boot_time(),
        "reboot_count": read_reboot_count(),
        "root_filesystem_readonly": read_mount_readonly(Path("/")),
        "data_filesystem_readonly": read_mount_readonly(Path(DB_PATH).parent),
        "filesystem_error_count": read_filesystem_error_count(),
    }
    sample.update(read_time_sync())
    return sample


def collect_system_vitals() -> dict[str, Any]:
    """Collect one system vitals sample for the Raspberry Pi dashboard."""
    load_1, load_5, load_15 = read_load_average()
    throttled_raw = read_throttled_raw()
    throttle = decode_throttled_flags(throttled_raw)
    sample: dict[str, Any] = {
        "sampled_at": _utc_now().isoformat(),
        "temperature_c": read_temperature_c(),
        "cpu_percent": read_cpu_percent(),
        "cpu_frequency_mhz": read_cpu_frequency_mhz(),
        "load_1": load_1,
        "load_5": load_5,
        "load_15": load_15,
        "uptime_seconds": read_uptime_seconds(),
        "throttled_raw": throttled_raw,
    }
    for _bit, key, _label in THROTTLED_BITS:
        sample[key] = _bool_int(throttle.get(key))

    sample.update(read_memory())
    sample.update(_disk_usage(Path("/"), "root"))
    sample.update(_disk_usage(Path(DB_PATH).parent, "data"))
    sample.update(read_storage_sizes())
    sample.update(read_nvme_smart())
    sample.update(read_network())
    sample.update(read_systemd_units())
    sample.update(read_reliability())
    return sample


def collect_and_store_system_vitals() -> dict[str, Any]:
    """Collect and persist one vitals sample."""
    sample = collect_system_vitals()
    sample["id"] = save_system_vitals(sample)
    return sample


def format_bytes(value: Any) -> str:
    numeric = _to_float(value)
    if numeric is None:
        return "-"
    units = ("B", "KB", "MB", "GB", "TB", "PB")
    index = 0
    while abs(numeric) >= 1024 and index < len(units) - 1:
        numeric /= 1024
        index += 1
    digits = 0 if index == 0 else 1
    return f"{numeric:.{digits}f} {units[index]}"


def format_number(value: Any, digits: int = 1, unit: str = "") -> str:
    numeric = _to_float(value)
    if numeric is None:
        return "-"
    suffix = f" {unit}" if unit else ""
    return f"{numeric:.{digits}f}{suffix}"


def format_percent(value: Any) -> str:
    return format_number(value, 1, "%")


def format_count(value: Any) -> str:
    numeric = _to_int(value)
    return "-" if numeric is None else str(numeric)


def format_bool(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on", "active"}:
            return "Yes"
        if normalized in {"0", "false", "no", "off", "inactive"}:
            return "No"
    return "Yes" if bool(value) else "No"


def format_seconds(value: Any) -> str:
    seconds = _to_int(value)
    if seconds is None or seconds <= 0:
        return "-"
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def row(
    label: str,
    value: str,
    *,
    detail: str | None = None,
    status: str | None = None,
) -> dict[str, str | None]:
    return {"label": label, "value": value, "detail": detail, "status": status}


def _state_status(active_state: Any) -> str:
    if active_state == "active":
        return "ok"
    if active_state in (None, ""):
        return "muted"
    return "warning"


def build_vitals_sections(
    current: dict[str, Any],
    summary: dict[str, Any],
) -> dict[str, list[dict[str, str | None]]]:
    """Build display-ready Vitals page sections."""
    throttle = decode_throttled_flags(current.get("throttled_raw"))
    storage_growth = summary.get("storage_growth", {})
    polling = summary.get("polling", {})
    sessions = summary.get("sessions", {})

    power_status = "Stable"
    power_row_status = "ok"
    if throttle["status"] == "warning":
        power_status = "Current issue"
        power_row_status = "warning"
    elif throttle["status"] == "history":
        power_status = "Past issue"
        power_row_status = "warning"
    elif throttle["status"] == "unavailable":
        power_status = "Unavailable"
        power_row_status = "muted"

    nvme_status = current.get("nvme_smart_status")
    nvme_error = current.get("nvme_smart_error")
    nvme_row_status = (
        "ok"
        if nvme_status == "passed"
        else "warning"
        if nvme_status
        else "muted"
    )

    error_type_text = ", ".join(
        f"{item['error_type']} ({item['count']})"
        for item in polling.get("error_types", [])
    )

    return {
        "power": [
            row("Power state", power_status, status=power_row_status),
            row("Under-voltage now", format_bool(throttle.get("under_voltage_now"))),
            row("Under-voltage since boot", format_bool(throttle.get("under_voltage_ever"))),
            row("Throttled now", format_bool(throttle.get("throttled_now"))),
            row("Throttled since boot", format_bool(throttle.get("throttled_ever"))),
            row("Frequency capped now", format_bool(throttle.get("frequency_capped_now"))),
            row("Frequency capped since boot", format_bool(throttle.get("frequency_capped_ever"))),
            row("Soft temp limit now", format_bool(throttle.get("soft_temp_limit_now"))),
            row("Soft temp limit since boot", format_bool(throttle.get("soft_temp_limit_ever"))),
            row("Raw flags", str(current.get("throttled_raw") or "-")),
        ],
        "storage": [
            row("Data disk used", format_percent(current.get("data_used_percent"))),
            row("Data disk free", format_bytes(current.get("data_free_bytes"))),
            row("Database size", format_bytes(current.get("database_size_bytes"))),
            row("Log folder size", format_bytes(current.get("logs_size_bytes"))),
            row("Pi backup folder size", format_bytes(current.get("backups_size_bytes"))),
            row("Monitored growth", format_bytes(storage_growth.get("growth_bytes"))),
            row("Growth per day", format_bytes(storage_growth.get("growth_bytes_per_day"))),
            row(
                "Estimated full date",
                str(storage_growth.get("estimated_full_at") or "-"),
                detail=(
                    f"{storage_growth['estimated_days_until_full']:.1f} days"
                    if storage_growth.get("estimated_days_until_full") is not None
                    else None
                ),
            ),
            row("Oldest charge session", str(sessions.get("oldest_session_start_local") or "-")),
            row("Newest charge session", str(sessions.get("newest_session_start_local") or "-")),
        ],
        "nvme": [
            row(
                "SMART status",
                str(nvme_status or "Unavailable"),
                detail=str(nvme_error or current.get("nvme_smart_tool") or ""),
                status=nvme_row_status,
            ),
            row("Device", str(current.get("nvme_device") or "-")),
            row("Temperature", format_number(current.get("nvme_temperature_c"), 1, "C")),
            row("Wear used", format_percent(current.get("nvme_percentage_used"))),
            row("Power-on hours", format_count(current.get("nvme_power_on_hours"))),
            row("Unsafe shutdowns", format_count(current.get("nvme_unsafe_shutdowns"))),
            row("Data written", format_bytes(current.get("nvme_data_written_bytes"))),
            row("Media errors", format_count(current.get("nvme_media_errors"))),
            row("Error log entries", format_count(current.get("nvme_error_log_entries"))),
            row("Critical warning", format_count(current.get("nvme_critical_warning"))),
        ],
        "network": [
            row("eth0 state", str(current.get("eth0_operstate") or "-")),
            row("eth0 carrier", format_bool(current.get("eth0_carrier"))),
            row("eth0 speed", format_number(current.get("eth0_speed_mbps"), 0, "Mb/s")),
            row("eth0 RX/TX", f"{format_bytes(current.get('eth0_rx_bytes'))} / {format_bytes(current.get('eth0_tx_bytes'))}"),
            row("eth0 errors", f"RX {format_count(current.get('eth0_rx_errors'))} / TX {format_count(current.get('eth0_tx_errors'))}"),
            row("eth0 dropped", f"RX {format_count(current.get('eth0_rx_dropped'))} / TX {format_count(current.get('eth0_tx_dropped'))}"),
            row("wlan0 state", str(current.get("wlan0_operstate") or "-")),
            row("wlan0 SSID", str(current.get("wlan0_connected_ssid") or "-")),
            row("wlan0 signal", format_percent(current.get("wlan0_signal_percent")), detail=format_number(current.get("wlan0_signal_dbm"), 0, "dBm")),
            row("wlan0 errors", f"RX {format_count(current.get('wlan0_rx_errors'))} / TX {format_count(current.get('wlan0_tx_errors'))}"),
            row("wlan0 dropped", f"RX {format_count(current.get('wlan0_rx_dropped'))} / TX {format_count(current.get('wlan0_tx_dropped'))}"),
            row("Approved chargers visible", format_count(current.get("approved_chargers_visible"))),
        ],
        "services": [
            row(
                "Web dashboard",
                str(current.get("web_service_active_state") or "-"),
                detail=f"restarts {format_count(current.get('web_service_restart_count'))}, memory {format_bytes(current.get('web_service_memory_bytes'))}",
                status=_state_status(current.get("web_service_active_state")),
            ),
            row(
                "Collector",
                str(current.get("collector_service_active_state") or "-"),
                detail=f"restarts {format_count(current.get('collector_service_restart_count'))}, memory {format_bytes(current.get('collector_service_memory_bytes'))}",
                status=_state_status(current.get("collector_service_active_state")),
            ),
            row(
                "Report timer",
                str(current.get("report_timer_active_state") or "-"),
                detail=f"restarts {format_count(current.get('report_timer_restart_count'))}",
                status=_state_status(current.get("report_timer_active_state")),
            ),
        ],
        "reliability": [
            row("Uptime", format_seconds(current.get("uptime_seconds"))),
            row("Boot time", str(current.get("boot_time") or "-")),
            row("Known boot records", format_count(current.get("reboot_count"))),
            row("NTP synchronized", format_bool(current.get("ntp_synchronized"))),
            row("Clock synchronized", format_bool(current.get("clock_synchronized"))),
            row("System timezone", str(current.get("system_timezone") or "-")),
            row("Root filesystem read-only", format_bool(current.get("root_filesystem_readonly"))),
            row("Data filesystem read-only", format_bool(current.get("data_filesystem_readonly"))),
            row("Kernel FS/I/O errors", format_count(current.get("filesystem_error_count"))),
        ],
        "polling": [
            row("Scans in range", format_count(polling.get("scan_count"))),
            row("Chargers seen in range", format_count(polling.get("chargers_seen"))),
            row("Approved visible now", format_count(polling.get("approved_visible_now"))),
            row("Collection runs", format_count(polling.get("total_runs"))),
            row("Successful collections", format_count(polling.get("successful_runs"))),
            row("Failed collections", format_count(polling.get("failed_runs"))),
            row("New records inserted", format_count(polling.get("records_inserted"))),
            row("Duplicates ignored", format_count(polling.get("records_duplicate"))),
            row("Malformed rows rejected", format_count(polling.get("records_rejected"))),
            row("Average HTTP time", format_number(polling.get("average_response_time_ms"), 0, "ms")),
            row("Last success", str((polling.get("last_success") or {}).get("completed_at") or "-")),
            row("Last failure", str((polling.get("last_failure") or {}).get("completed_at") or "-")),
            row("Failure types", error_type_text or "-"),
        ],
    }


def build_vitals_payload(range_key: str | None = None) -> dict[str, Any]:
    """Return current and historical vitals for the dashboard/API."""
    selected_range = normalize_vital_range(range_key)
    _label, delta = VITAL_RANGES[selected_range]
    since = (_utc_now() - delta).isoformat()
    current = collect_and_store_system_vitals()
    summary = get_vitals_operational_summary(since=since)

    return {
        "current": current,
        "ranges": vital_range_options(),
        "selected_range": selected_range,
        "samples": list_system_vitals(since=since, limit=200),
        "trends": summarize_system_vitals(since=since),
        "summary": summary,
        "sections": build_vitals_sections(current, summary),
    }
