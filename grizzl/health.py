from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from grizzl.config import CHARGERS, CHARGER_URL, DB_PATH, REQUEST_TIMEOUT_SECONDS
from grizzl.database import connection, get_service_state, initialize_database


@dataclass(frozen=True)
class HealthCheck:
    """One health check result."""

    name: str
    status: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
        }


def _run(args: list[str], timeout: int = 5) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def check_database() -> HealthCheck:
    try:
        initialize_database()
        with connection() as conn:
            conn.execute("SELECT 1").fetchone()
        return HealthCheck("database", "ok", f"SQLite reachable at {DB_PATH}")
    except Exception as exc:
        return HealthCheck("database", "error", str(exc))


def check_disk(path: Path = Path(".")) -> HealthCheck:
    usage = shutil.disk_usage(path)
    free_gb = usage.free / (1024 ** 3)
    total_gb = usage.total / (1024 ** 3)
    status = "ok" if free_gb >= 1 else "warning"
    return HealthCheck(
        "disk",
        status,
        f"{free_gb:.1f} GB free of {total_gb:.1f} GB",
    )


def check_nmcli() -> HealthCheck:
    if platform.system() != "Linux":
        return HealthCheck(
            "NetworkManager",
            "ok",
            f"Linux-only check skipped on {platform.system()}",
        )

    try:
        result = _run(["nmcli", "--version"])
    except FileNotFoundError:
        return HealthCheck("NetworkManager", "warning", "nmcli not installed")
    except Exception as exc:
        return HealthCheck("NetworkManager", "error", str(exc))

    if result.returncode != 0:
        return HealthCheck("NetworkManager", "error", result.stderr.strip())
    return HealthCheck("NetworkManager", "ok", result.stdout.strip())


def check_interface(interface: str) -> HealthCheck:
    if platform.system() != "Linux":
        return HealthCheck(
            interface,
            "ok",
            f"Linux-only check skipped on {platform.system()}",
        )

    try:
        result = _run(
            ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device", "status"]
        )
    except FileNotFoundError:
        return HealthCheck(interface, "warning", "nmcli not installed")
    except Exception as exc:
        return HealthCheck(interface, "error", str(exc))

    for line in result.stdout.splitlines():
        fields = line.split(":")
        if len(fields) >= 3 and fields[0] == interface:
            state = fields[2]
            if interface == "wlan0" and state == "disconnected":
                return HealthCheck(interface, "ok", "disconnected; idle")
            status = "ok" if state == "connected" else "warning"
            return HealthCheck(interface, status, state)

    return HealthCheck(interface, "warning", "interface not found")


def _has_default_route() -> bool:
    try:
        result = _run(["ip", "route", "show", "default"])
    except Exception:
        return True

    return result.returncode == 0 and bool(result.stdout.strip())


def check_system_time() -> HealthCheck:
    if platform.system() != "Linux":
        return HealthCheck(
            "time",
            "ok",
            f"Linux-only check skipped on {platform.system()}",
        )

    try:
        result = _run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"])
    except FileNotFoundError:
        return HealthCheck("time", "warning", "timedatectl not installed")
    except Exception as exc:
        return HealthCheck("time", "error", str(exc))

    value = result.stdout.strip()
    if value == "yes":
        return HealthCheck("time", "ok", "NTP synchronized")
    if not _has_default_route():
        return HealthCheck(
            "time",
            "ok",
            f"NTP synchronized: {value or 'unknown'}; offline mode",
        )
    return HealthCheck("time", "warning", f"NTP synchronized: {value or 'unknown'}")


def check_test_charger(url: str = CHARGER_URL) -> HealthCheck:
    test_charger = next(
        (charger for charger in CHARGERS if charger.get("test_charger")),
        None,
    )
    if test_charger is not None and not test_charger.get("enabled", True):
        return HealthCheck("test_charger", "ok", "disabled")

    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        detail = f"HTTP {response.status_code} at {url}"
        status = "ok" if response.ok else "warning"
        return HealthCheck("test_charger", status, detail)
    except requests.RequestException as exc:
        return HealthCheck("test_charger", "warning", str(exc))


def run_health_checks(*, include_test_charger: bool = True) -> dict[str, Any]:
    checks = [
        check_database(),
        check_disk(),
        check_nmcli(),
        check_interface("eth0"),
        check_interface("wlan0"),
        check_system_time(),
    ]

    if include_test_charger:
        checks.append(check_test_charger())

    statuses = {check.status for check in checks}
    overall = "error" if "error" in statuses else "warning" if "warning" in statuses else "ok"

    return {
        "overall": overall,
        "checks": [check.as_dict() for check in checks],
        "service_state": get_service_state(),
    }
