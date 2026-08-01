from __future__ import annotations

import subprocess

import pytest

from grizzl import health


def test_linux_missing_nmcli_is_warning(monkeypatch) -> None:
    monkeypatch.setattr(health.platform, "system", lambda: "Linux")

    def missing_nmcli(*_args, **_kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(health, "_run", missing_nmcli)

    result = health.check_nmcli()

    assert result.status == "warning"
    assert result.detail == "nmcli not installed"


@pytest.mark.parametrize(
    ("check", "name"),
    [
        (health.check_nmcli, "NetworkManager"),
        (lambda: health.check_interface("eth0"), "eth0"),
        (health.check_system_time, "time"),
    ],
)
def test_non_linux_system_checks_are_skipped(monkeypatch, check, name) -> None:
    monkeypatch.setattr(health.platform, "system", lambda: "Windows")

    result = check()

    assert result.name == name
    assert result.status == "ok"
    assert result.detail == "Linux-only check skipped on Windows"


def test_wlan0_disconnected_is_ok_for_idle_collector(monkeypatch) -> None:
    monkeypatch.setattr(health.platform, "system", lambda: "Linux")

    def nmcli_status(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="eth0:ethernet:connected\nwlan0:wifi:disconnected\n",
            stderr="",
        )

    monkeypatch.setattr(health, "_run", nmcli_status)

    result = health.check_interface("wlan0")

    assert result.status == "ok"
    assert result.detail == "disconnected; idle"


def test_unsynchronized_time_is_ok_without_default_route(monkeypatch) -> None:
    monkeypatch.setattr(health.platform, "system", lambda: "Linux")

    def command_result(args, *_positional, **_kwargs):
        if args[0] == "timedatectl":
            return subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout="no\n",
                stderr="",
            )
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(health, "_run", command_result)

    result = health.check_system_time()

    assert result.status == "ok"
    assert result.detail == "NTP synchronized: no; offline mode"


def test_disabled_test_charger_health_check_is_ok(monkeypatch) -> None:
    monkeypatch.setattr(
        health,
        "CHARGERS",
        ({"test_charger": True, "enabled": False},),
    )

    result = health.check_test_charger()

    assert result.status == "ok"
    assert result.detail == "disabled"
