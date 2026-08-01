from flask import Blueprint, jsonify, request

from grizzl.config import CHARGERS
from grizzl.database import (
    get_summary_metrics,
    get_chargers_with_status,
    get_sessions,
    initialize_database,
    list_collection_runs,
    sync_chargers,
)
from grizzl.health import run_health_checks
from grizzl.scanner import scan_and_record
from grizzl.services.polling import poll_once


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
    sessions = get_sessions(limit=100)

    return jsonify(
        {
            "chargers": chargers,
            "runs": list_collection_runs(limit=8),
            "sessions": sessions,
            "statistics": get_summary_metrics(),
        }
    )


@api_blueprint.get("/chargers")
def chargers():
    _bootstrap()
    return jsonify(get_chargers_with_status())


@api_blueprint.get("/sessions")
def sessions():
    _bootstrap()

    charger_id = request.args.get("charger_id", type=int)
    limit = request.args.get("limit", default=100, type=int)

    return jsonify(
        get_sessions(
            limit=limit or 100,
            charger_id=charger_id,
            start=request.args.get("start") or None,
            end=request.args.get("end") or None,
            keyword=request.args.get("keyword") or None,
        )
    )


@api_blueprint.get("/statistics")
def statistics():
    _bootstrap()
    return jsonify(get_summary_metrics())


@api_blueprint.get("/scan")
def scan():
    result = scan_and_record()
    return jsonify(result.__dict__)


@api_blueprint.post("/poll")
def poll():
    try:
        result = poll_once()
    except Exception as exc:
        return jsonify(
            {
                "status": "error",
                "error": str(exc),
            }
        ), 503

    return jsonify(
        result
    ), 200


@api_blueprint.get("/health")
def health():
    _bootstrap()
    return jsonify(run_health_checks())
