from flask import Blueprint, jsonify, request

from grizzl.config import CHARGERS
from grizzl.database import (
    get_chargers_with_status,
    get_recent_sessions,
    initialize_database,
    sync_chargers,
)
from grizzl.services.polling import poll_once
from grizzl.statistics import calculate_fleet_statistics
from grizzl.wifi import scan_configured_chargers


api_blueprint = Blueprint(
    "api",
    __name__,
    url_prefix="/api",
)


def _bootstrap() -> None:
    initialize_database()
    sync_chargers(CHARGERS)


@api_blueprint.get("/fleet")
def fleet():
    _bootstrap()
    chargers = get_chargers_with_status()
    sessions = get_recent_sessions(limit=100)

    return jsonify(
        {
            "chargers": chargers,
            "sessions": sessions,
            "statistics": calculate_fleet_statistics(chargers, sessions),
        }
    )


@api_blueprint.get("/chargers")
def chargers():
    _bootstrap()
    return jsonify(get_chargers_with_status())


@api_blueprint.get("/sessions")
def sessions():
    _bootstrap()

    charger_id = request.args.get("charger_id") or None
    limit = request.args.get("limit", default=100, type=int)

    return jsonify(
        get_recent_sessions(
            limit=limit or 100,
            charger_id=charger_id,
        )
    )


@api_blueprint.get("/statistics")
def statistics():
    _bootstrap()
    chargers_data = get_chargers_with_status()
    sessions_data = get_recent_sessions(limit=1000)

    return jsonify(
        calculate_fleet_statistics(chargers_data, sessions_data)
    )


@api_blueprint.get("/scan")
def scan():
    matches = []

    for charger, observation in scan_configured_chargers():
        matches.append(
            {
                "charger_id": charger["id"],
                "numeric_charger_id": charger.get("charger_id"),
                "display_name": charger.get("display_name"),
                "ssid": charger["ssid"],
                "environment": charger.get("environment"),
                "test_charger": bool(charger.get("test_charger", False)),
                "bssid": observation.bssid,
                "signal": observation.signal,
                "channel": observation.channel,
                "frequency": observation.frequency,
            }
        )

    return jsonify(
        {
            "status": "success",
            "matches": matches,
            "visible_count": len(matches),
        }
    )


@api_blueprint.post("/poll")
def poll():
    try:
        poll_once()
    except Exception as exc:
        return jsonify(
            {
                "status": "error",
                "error": str(exc),
            }
        ), 503

    return jsonify(
        {
            "status": "success",
            "message": "Fleet polling cycle completed.",
        }
    ), 200
