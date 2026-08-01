from __future__ import annotations

from dataclasses import dataclass
import subprocess
import time
from typing import Final

from grizzl.config import (
    CHARGERS,
    WIFI_SCAN_SETTLE_SECONDS,
    WIFI_CONNECT_TIMEOUT_SECONDS,
    WIFI_INTERFACE,
    charger_password,
)
from grizzl.database import get_runtime_chargers

NMCLI: Final = "nmcli"


class WiFiError(RuntimeError):
    """Raised when a Wi-Fi operation fails."""


@dataclass(frozen=True)
class WiFiObservation:
    """Machine-readable NetworkManager Wi-Fi scan observation."""

    ssid: str
    bssid: str | None
    signal: int | None
    channel: int | None
    frequency: str | None


def _run_nmcli(
    *args: str,
    timeout: int = 30,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    command = [NMCLI, *args]

    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=check,
        )
    except FileNotFoundError as exc:
        raise WiFiError("nmcli is not installed or not available in PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise WiFiError(
            f"nmcli command timed out after {timeout} seconds"
        ) from exc
    except subprocess.CalledProcessError as exc:
        error_message = exc.stderr.strip() or exc.stdout.strip()
        raise WiFiError(
            f"nmcli command failed: {error_message or 'unknown error'}"
        ) from exc


def _split_nmcli_terse(line: str) -> list[str]:
    """
    Split nmcli terse output while preserving escaped separator characters.

    NetworkManager escapes literal ':' and '\\' characters with a backslash in
    terse mode. SSIDs may contain those characters, so plain str.split(':') is
    not safe enough for scanner output.
    """
    fields: list[str] = []
    current: list[str] = []
    escaped = False

    for char in line:
        if escaped:
            current.append(char)
            escaped = False
            continue

        if char == "\\":
            escaped = True
            continue

        if char == ":":
            fields.append("".join(current))
            current = []
            continue

        current.append(char)

    if escaped:
        current.append("\\")

    fields.append("".join(current))
    return fields


def _parse_int(value: str) -> int | None:
    value = value.strip()

    if not value:
        return None

    try:
        return int(value)
    except ValueError:
        return None


def parse_wifi_observations(output: str) -> list[WiFiObservation]:
    """Parse nmcli terse Wi-Fi list output into structured observations."""
    observations: list[WiFiObservation] = []

    for line in output.splitlines():
        if not line.strip():
            continue

        fields = _split_nmcli_terse(line)

        if len(fields) < 5:
            continue

        ssid, bssid, channel, frequency, signal = fields[:5]
        ssid = ssid.strip()

        if not ssid:
            continue

        observations.append(
            WiFiObservation(
                ssid=ssid,
                bssid=bssid.strip() or None,
                signal=_parse_int(signal),
                channel=_parse_int(channel),
                frequency=frequency.strip() or None,
            )
        )

    return observations


def wifi_enabled() -> bool:
    result = _run_nmcli(
        "-t",
        "-f",
        "WIFI",
        "radio",
        check=False,
    )
    return result.stdout.strip().lower() == "enabled"


def enable_wifi() -> None:
    _run_nmcli("radio", "wifi", "on")


def current_ssid() -> str | None:
    result = _run_nmcli(
        "-t",
        "-f",
        "ACTIVE,SSID",
        "device",
        "wifi",
        "list",
        "ifname",
        WIFI_INTERFACE,
        check=False,
    )

    for line in result.stdout.splitlines():
        parts = _split_nmcli_terse(line)
        if len(parts) >= 2 and parts[0].lower() == "yes" and parts[1]:
            return parts[1]

    return None


def scan_observations(*, rescan: bool = True) -> list[WiFiObservation]:
    """Return structured Wi-Fi observations from wlan0."""
    if not wifi_enabled():
        enable_wifi()

    if rescan:
        _run_nmcli(
            "device",
            "wifi",
            "rescan",
            "ifname",
            WIFI_INTERFACE,
            check=False,
        )

        time.sleep(WIFI_SCAN_SETTLE_SECONDS)

    result = _run_nmcli(
        "-t",
        "-f",
        "SSID,BSSID,CHAN,FREQ,SIGNAL",
        "device",
        "wifi",
        "list",
        "ifname",
        WIFI_INTERFACE,
        "--rescan",
        "yes" if rescan else "no",
        check=False,
    )

    return parse_wifi_observations(result.stdout)


def scan_ssids() -> list[str]:
    """Return visible SSIDs on wlan0, preserving first-seen order."""
    visible_ssids: list[str] = []

    for observation in scan_observations():
        ssid = observation.ssid

        if ssid and ssid not in visible_ssids:
            visible_ssids.append(ssid)

    return visible_ssids


def scan_configured_chargers() -> list[tuple[dict, WiFiObservation]]:
    """Return enabled configured chargers currently visible on wlan0."""
    observations = scan_observations()
    observations_by_ssid: dict[str, WiFiObservation] = {}

    for observation in observations:
        existing = observations_by_ssid.get(observation.ssid)

        if existing is None:
            observations_by_ssid[observation.ssid] = observation
            continue

        existing_signal = existing.signal if existing.signal is not None else -1
        new_signal = observation.signal if observation.signal is not None else -1

        if new_signal > existing_signal:
            observations_by_ssid[observation.ssid] = observation

    matches: list[tuple[dict, WiFiObservation]] = []

    for charger in get_runtime_chargers(enabled_only=True):
        observation = observations_by_ssid.get(str(charger["ssid"]))

        if observation is not None:
            matches.append((charger, observation))

    return matches


def visible_configured_chargers() -> list[dict]:
    return [charger for charger, _observation in scan_configured_chargers()]


def _profile_name(ssid: str) -> str:
    safe_ssid = "".join(
        char if char.isalnum() or char in {"-", "_"} else "-"
        for char in ssid
    )
    return f"grizzl-monitor-{safe_ssid}"


def _connection_exists(profile_name: str) -> bool:
    result = _run_nmcli(
        "-t",
        "-f",
        "NAME",
        "connection",
        "show",
        profile_name,
        check=False,
    )
    return result.returncode == 0


def _ensure_charger_profile(charger: dict) -> str:
    """
    Create or update a charger Wi-Fi profile that cannot replace eth0 routing.
    """
    ssid = str(charger["ssid"])
    password = charger_password(charger)
    profile_name = _profile_name(ssid)

    if not _connection_exists(profile_name):
        result = _run_nmcli(
            "connection",
            "add",
            "type",
            "wifi",
            "ifname",
            WIFI_INTERFACE,
            "con-name",
            profile_name,
            "ssid",
            ssid,
            check=False,
        )

        if result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip()
            raise WiFiError(
                f"Unable to create NetworkManager profile for {ssid}: "
                f"{message or 'unknown error'}"
            )

    result = _run_nmcli(
        "connection",
        "modify",
        profile_name,
        "connection.autoconnect",
        "no",
        "connection.interface-name",
        WIFI_INTERFACE,
        "wifi-sec.key-mgmt",
        "wpa-psk",
        "wifi-sec.psk",
        password,
        "ipv4.method",
        "auto",
        "ipv4.never-default",
        "yes",
        "ipv4.route-metric",
        "900",
        "ipv6.method",
        "auto",
        "ipv6.never-default",
        "yes",
        "ipv6.route-metric",
        "900",
        check=False,
    )

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise WiFiError(
            f"Unable to configure NetworkManager profile for {ssid}: "
            f"{message or 'unknown error'}"
        )

    return profile_name


def connect_to_charger(charger: dict) -> None:
    ssid = str(charger["ssid"])

    if current_ssid() == ssid:
        return

    profile_name = _ensure_charger_profile(charger)

    result = _run_nmcli(
        "connection",
        "up",
        profile_name,
        "ifname",
        WIFI_INTERFACE,
        timeout=WIFI_CONNECT_TIMEOUT_SECONDS,
        check=False,
    )

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise WiFiError(
            f"Unable to connect to {ssid}: {message or 'unknown error'}"
        )

    deadline = time.monotonic() + WIFI_CONNECT_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        if current_ssid() == ssid:
            return
        time.sleep(1)

    raise WiFiError(
        f"Connection to {ssid} did not become active within "
        f"{WIFI_CONNECT_TIMEOUT_SECONDS} seconds"
    )


def disconnect() -> None:
    result = _run_nmcli(
        "device",
        "disconnect",
        WIFI_INTERFACE,
        check=False,
    )

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()

        if "not active" not in message.lower():
            raise WiFiError(
                f"Unable to disconnect {WIFI_INTERFACE}: "
                f"{message or 'unknown error'}"
            )


def get_charger_by_id(charger_id: str) -> dict | None:
    for charger in CHARGERS:
        if charger["id"] == charger_id:
            return charger

    return None


def get_charger_by_ssid(ssid: str) -> dict | None:
    for charger in CHARGERS:
        if charger["ssid"] == ssid:
            return charger

    return None
