from __future__ import annotations

from grizzl.wifi import _split_nmcli_terse, parse_wifi_observations


def test_split_nmcli_terse_handles_escaped_colons() -> None:
    assert _split_nmcli_terse(r"Shipman\:GRU:aa\:bb:6:2437 MHz:87") == [
        "Shipman:GRU",
        "aa:bb",
        "6",
        "2437 MHz",
        "87",
    ]


def test_parse_wifi_observations_returns_structured_rows() -> None:
    output = "\n".join(
        [
            r"CHARGER_12:AA\:BB\:CC\:DD\:EE\:FF:11:2462 MHz:74",
            r"Shipman-GRU:11\:22\:33\:44\:55\:66:6:2437 MHz:91",
        ]
    )

    rows = parse_wifi_observations(output)

    assert len(rows) == 2
    assert rows[0].ssid == "CHARGER_12"
    assert rows[0].bssid == "AA:BB:CC:DD:EE:FF"
    assert rows[0].channel == 11
    assert rows[0].frequency == "2462 MHz"
    assert rows[0].signal == 74
