from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Final

APP_NAME: Final = "Grizzl-E Fleet Monitor"
SITE_NAME: Final = "Shipman Residence"

PROJECT_ROOT: Final = Path(__file__).resolve().parents[1]
CONFIG_DIR: Final = Path(os.getenv("GRIZZL_CONFIG_DIR", "/etc/grizzl-monitor"))
ENV_FILE: Final = Path(
    os.getenv("GRIZZL_ENV_FILE", str(CONFIG_DIR / "grizzl-monitor.env"))
)

# Legacy single-charger compatibility
CHARGER_ID: Final = "Shipman-GRU"
CHARGER_URL: Final = "http://192.168.68.166"
LOG_ENDPOINT: Final = "/get_logResult"

# Wi-Fi configuration
WIFI_INTERFACE: Final = "wlan0"
WORK_CHARGER_URL: Final = "http://192.168.4.1"
PRODUCTION_WIFI_PASSWORD_ENV: Final = "GRIZZL_PRODUCTION_WIFI_PASSWORD"
TEST_WIFI_PASSWORD_ENV: Final = "GRIZZL_TEST_WIFI_PASSWORD"


class ConfigurationError(RuntimeError):
    """Raised when required runtime configuration is missing or invalid."""


def load_environment_file(path: Path = ENV_FILE) -> None:
    """
    Load KEY=VALUE lines from the protected environment file if it exists.

    Existing process environment variables win. Values are not logged or
    returned to callers.
    """
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


def required_secret(name: str) -> str:
    """Return a required secret without ever supplying a default value."""
    load_environment_file()
    value = os.getenv(name)

    if not value:
        raise ConfigurationError(
            f"Required secret {name} is missing. Configure {ENV_FILE} "
            "with root:grizzl-monitor ownership and 0640 permissions."
        )

    return value


def charger_password(charger: dict[str, Any]) -> str:
    """Resolve the Wi-Fi password for a charger from its environment key."""
    password_env = charger.get("password_env")

    if not password_env:
        raise ConfigurationError(
            f"Charger {charger.get('id', '<unknown>')} has no password_env"
        )

    return required_secret(str(password_env))

# Fleet inventory
CHARGERS: Final = (
    {
        "id": "CHARGER_0",
        "charger_id": 0,
        "display_name": "Home Test Charger",
        "ssid": "Shipman-GRU",
        "password_env": TEST_WIFI_PASSWORD_ENV,
        "url": CHARGER_URL,
        "target_url": CHARGER_URL,
        "enabled": True,
        "environment": "development",
        "test_charger": True,
        "connect_mode": "direct",
    },
    {
        "id": "CHARGER_2",
        "charger_id": 2,
        "display_name": "Charger 2",
        "ssid": "CHARGER_2",
        "password_env": PRODUCTION_WIFI_PASSWORD_ENV,
        "url": WORK_CHARGER_URL,
        "target_url": WORK_CHARGER_URL,
        "enabled": True,
        "environment": "production",
        "test_charger": False,
        "connect_mode": "wifi",
    },
    {
        "id": "CHARGER_3",
        "charger_id": 3,
        "display_name": "Charger 3",
        "ssid": "CHARGER_3",
        "password_env": PRODUCTION_WIFI_PASSWORD_ENV,
        "url": WORK_CHARGER_URL,
        "target_url": WORK_CHARGER_URL,
        "enabled": True,
        "environment": "production",
        "test_charger": False,
        "connect_mode": "wifi",
    },
    {
        "id": "CHARGER_10",
        "charger_id": 10,
        "display_name": "Charger 10",
        "ssid": "CHARGER_10",
        "password_env": PRODUCTION_WIFI_PASSWORD_ENV,
        "url": WORK_CHARGER_URL,
        "target_url": WORK_CHARGER_URL,
        "enabled": True,
        "environment": "production",
        "test_charger": False,
        "connect_mode": "wifi",
    },
    {
        "id": "CHARGER_11",
        "charger_id": 11,
        "display_name": "Charger 11",
        "ssid": "CHARGER_11",
        "password_env": PRODUCTION_WIFI_PASSWORD_ENV,
        "url": WORK_CHARGER_URL,
        "target_url": WORK_CHARGER_URL,
        "enabled": True,
        "environment": "production",
        "test_charger": False,
        "connect_mode": "wifi",
    },
    {
        "id": "CHARGER_12",
        "charger_id": 12,
        "display_name": "Charger 12",
        "ssid": "CHARGER_12",
        "password_env": PRODUCTION_WIFI_PASSWORD_ENV,
        "url": WORK_CHARGER_URL,
        "target_url": WORK_CHARGER_URL,
        "enabled": True,
        "environment": "production",
        "test_charger": False,
        "connect_mode": "wifi",
    },
    {
        "id": "CHARGER_13",
        "charger_id": 13,
        "display_name": "Charger 13",
        "ssid": "CHARGER_13",
        "password_env": PRODUCTION_WIFI_PASSWORD_ENV,
        "url": WORK_CHARGER_URL,
        "target_url": WORK_CHARGER_URL,
        "enabled": True,
        "environment": "production",
        "test_charger": False,
        "connect_mode": "wifi",
    },
    {
        "id": "CHARGER_14",
        "charger_id": 14,
        "display_name": "Charger 14",
        "ssid": "CHARGER_14",
        "password_env": PRODUCTION_WIFI_PASSWORD_ENV,
        "url": WORK_CHARGER_URL,
        "target_url": WORK_CHARGER_URL,
        "enabled": True,
        "environment": "production",
        "test_charger": False,
        "connect_mode": "wifi",
    },
    {
        "id": "CHARGER_15",
        "charger_id": 15,
        "display_name": "Charger 15",
        "ssid": "CHARGER_15",
        "password_env": PRODUCTION_WIFI_PASSWORD_ENV,
        "url": WORK_CHARGER_URL,
        "target_url": WORK_CHARGER_URL,
        "enabled": True,
        "environment": "production",
        "test_charger": False,
        "connect_mode": "wifi",
    },
    {
        "id": "CHARGER_16",
        "charger_id": 16,
        "display_name": "Charger 16",
        "ssid": "CHARGER_16",
        "password_env": PRODUCTION_WIFI_PASSWORD_ENV,
        "url": WORK_CHARGER_URL,
        "target_url": WORK_CHARGER_URL,
        "enabled": True,
        "environment": "production",
        "test_charger": False,
        "connect_mode": "wifi",
    },
    {
        "id": "CHARGER_17",
        "charger_id": 17,
        "display_name": "Charger 17",
        "ssid": "CHARGER_17",
        "password_env": PRODUCTION_WIFI_PASSWORD_ENV,
        "url": WORK_CHARGER_URL,
        "target_url": WORK_CHARGER_URL,
        "enabled": True,
        "environment": "production",
        "test_charger": False,
        "connect_mode": "wifi",
    },
    {
        "id": "CHARGER_18",
        "charger_id": 18,
        "display_name": "Charger 18",
        "ssid": "CHARGER_18",
        "password_env": PRODUCTION_WIFI_PASSWORD_ENV,
        "url": WORK_CHARGER_URL,
        "target_url": WORK_CHARGER_URL,
        "enabled": True,
        "environment": "production",
        "test_charger": False,
        "connect_mode": "wifi",
    },
    {
        "id": "CHARGER_19",
        "charger_id": 19,
        "display_name": "Charger 19",
        "ssid": "CHARGER_19",
        "password_env": PRODUCTION_WIFI_PASSWORD_ENV,
        "url": WORK_CHARGER_URL,
        "target_url": WORK_CHARGER_URL,
        "enabled": True,
        "environment": "production",
        "test_charger": False,
        "connect_mode": "wifi",
    },
    {
        "id": "CHARGER_20",
        "charger_id": 20,
        "display_name": "Charger 20",
        "ssid": "CHARGER_20",
        "password_env": PRODUCTION_WIFI_PASSWORD_ENV,
        "url": WORK_CHARGER_URL,
        "target_url": WORK_CHARGER_URL,
        "enabled": True,
        "environment": "production",
        "test_charger": False,
        "connect_mode": "wifi",
    },
    {
        "id": "CHARGER_21",
        "charger_id": 21,
        "display_name": "Charger 21",
        "ssid": "CHARGER_21",
        "password_env": PRODUCTION_WIFI_PASSWORD_ENV,
        "url": WORK_CHARGER_URL,
        "target_url": WORK_CHARGER_URL,
        "enabled": True,
        "environment": "production",
        "test_charger": False,
        "connect_mode": "wifi",
    },
)

APPROVED_SSIDS: Final = frozenset(str(charger["ssid"]) for charger in CHARGERS)

DB_PATH: Final = Path(os.getenv("GRIZZL_DB_PATH", "data/grizzl.db"))

REQUEST_TIMEOUT_SECONDS: Final = 10
POLL_INTERVAL_SECONDS: Final = 300
ONLINE_TIMEOUT_SECONDS: Final = 600
WIFI_CONNECT_TIMEOUT_SECONDS: Final = 30
WIFI_SCAN_INTERVAL_SECONDS: Final = 15
WIFI_SCAN_SETTLE_SECONDS: Final = 2


def validate_configuration(chargers: tuple[dict[str, Any], ...] = CHARGERS) -> None:
    """Validate non-secret charger configuration at startup/test time."""
    seen_ssids: set[str] = set()
    seen_ids: set[str] = set()

    for charger in chargers:
        charger_id = str(charger.get("id", ""))
        ssid = str(charger.get("ssid", ""))
        target_url = str(charger.get("target_url") or charger.get("url") or "")
        connect_mode = str(charger.get("connect_mode", "wifi"))

        if not charger_id:
            raise ConfigurationError("A charger is missing id")
        if charger_id in seen_ids:
            raise ConfigurationError(f"Duplicate charger id: {charger_id}")
        seen_ids.add(charger_id)

        if not ssid:
            raise ConfigurationError(f"{charger_id} is missing ssid")
        if ssid in seen_ssids:
            raise ConfigurationError(f"Duplicate charger ssid: {ssid}")
        seen_ssids.add(ssid)

        if not target_url.startswith(("http://", "https://")):
            raise ConfigurationError(f"{charger_id} has invalid target_url")

        if connect_mode not in {"wifi", "direct"}:
            raise ConfigurationError(
                f"{charger_id} has invalid connect_mode {connect_mode!r}"
            )

        if connect_mode == "wifi" and not charger.get("password_env"):
            raise ConfigurationError(f"{charger_id} is missing password_env")


validate_configuration()
