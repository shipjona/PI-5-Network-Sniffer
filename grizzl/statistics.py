from __future__ import annotations

from typing import Any


def _first_number(payload: Any, keys: tuple[str, ...]) -> float:
    if not isinstance(payload, dict):
        return 0.0

    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue

    return 0.0


def calculate_fleet_statistics(
    chargers: list[dict[str, Any]],
    sessions: list[dict[str, Any]],
) -> dict[str, int | float | str]:
    enabled_chargers = [
        charger for charger in chargers if bool(charger["enabled"])
    ]
    online_chargers = [
        charger for charger in enabled_chargers if bool(charger["online"])
    ]

    total_energy = 0.0

    for session in sessions:
        if session.get("energy_kwh") is not None:
            total_energy += float(session["energy_kwh"])
            continue

        total_energy += _first_number(
            session.get("payload"),
            (
                "energy_kwh",
                "energy",
                "kwh",
                "total_energy",
                "energyDelivered",
                "s_enrg",
            ),
        )

    return {
        "charger_count": len(enabled_chargers),
        "online_count": len(online_chargers),
        "offline_count": len(enabled_chargers) - len(online_chargers),
        "session_count": len(sessions),
        "total_energy_kwh": round(total_energy, 3),
        "total_energy": f"{total_energy:,.3f} kWh",
    }
