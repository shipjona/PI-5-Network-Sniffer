from __future__ import annotations

import os
import shutil
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from grizzl.config import DB_PATH
from grizzl.database import (
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


def _read_float(path: Path, divisor: float = 1.0) -> float | None:
    try:
        return float(path.read_text(encoding="utf-8").strip()) / divisor
    except (FileNotFoundError, PermissionError, ValueError):
        return None


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
    except (FileNotFoundError, IndexError, PermissionError):
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
    except (FileNotFoundError, PermissionError):
        return {
            "memory_total_bytes": None,
            "memory_available_bytes": None,
            "memory_used_percent": None,
            "swap_total_bytes": None,
            "swap_free_bytes": None,
        }

    total = parsed.get("MemTotal")
    available = parsed.get("MemAvailable")
    swap_total = parsed.get("SwapTotal")
    swap_free = parsed.get("SwapFree")
    used_percent = None

    if total and available is not None:
        used_percent = round(((total - available) / total) * 100, 2)

    return {
        "memory_total_bytes": total,
        "memory_available_bytes": available,
        "memory_used_percent": used_percent,
        "swap_total_bytes": swap_total,
        "swap_free_bytes": swap_free,
    }


def _disk_usage(path: Path, prefix: str) -> dict[str, int | float | None]:
    try:
        usage = shutil.disk_usage(path)
    except (FileNotFoundError, PermissionError):
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
    except (FileNotFoundError, IndexError, PermissionError, ValueError):
        return None


def collect_system_vitals() -> dict[str, Any]:
    """Collect one system vitals sample for the Raspberry Pi dashboard."""
    load_1, load_5, load_15 = read_load_average()
    sample: dict[str, Any] = {
        "sampled_at": _utc_now().isoformat(),
        "temperature_c": read_temperature_c(),
        "cpu_percent": read_cpu_percent(),
        "cpu_frequency_mhz": read_cpu_frequency_mhz(),
        "load_1": load_1,
        "load_5": load_5,
        "load_15": load_15,
        "uptime_seconds": read_uptime_seconds(),
        "throttled_raw": read_throttled_raw(),
    }
    sample.update(read_memory())
    sample.update(_disk_usage(Path("/"), "root"))
    sample.update(_disk_usage(Path(DB_PATH).parent, "data"))
    return sample


def collect_and_store_system_vitals() -> dict[str, Any]:
    """Collect and persist one vitals sample."""
    sample = collect_system_vitals()
    sample["id"] = save_system_vitals(sample)
    return sample


def build_vitals_payload(range_key: str | None = None) -> dict[str, Any]:
    """Return current and historical vitals for the dashboard/API."""
    selected_range = normalize_vital_range(range_key)
    _label, delta = VITAL_RANGES[selected_range]
    since = (_utc_now() - delta).isoformat()
    current = collect_and_store_system_vitals()

    return {
        "current": current,
        "ranges": vital_range_options(),
        "selected_range": selected_range,
        "samples": list_system_vitals(since=since, limit=200),
        "trends": summarize_system_vitals(since=since),
    }
