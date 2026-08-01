from __future__ import annotations

import pytest

from grizzl.config import CHARGERS, ConfigurationError, validate_configuration


def test_configured_chargers_do_not_contain_password_literals() -> None:
    for charger in CHARGERS:
        assert "password" not in charger
        assert "password_env" in charger


def test_validate_configuration_rejects_duplicate_ssids() -> None:
    charger = {
        "id": "CHARGER_X",
        "ssid": "DUPLICATE",
        "target_url": "http://192.168.4.1",
        "password_env": "SECRET",
        "connect_mode": "wifi",
    }

    with pytest.raises(ConfigurationError, match="Duplicate charger ssid"):
        validate_configuration((charger, {**charger, "id": "CHARGER_Y"}))
