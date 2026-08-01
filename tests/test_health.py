from __future__ import annotations

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
