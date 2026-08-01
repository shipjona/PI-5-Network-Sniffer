from __future__ import annotations

import os
import secrets
from typing import Any

from flask import (
    Flask,
    Response,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from grizzl.config import APP_NAME, CHARGERS, SITE_NAME
from grizzl.database import (
    count_sessions,
    get_chargers_with_status,
    get_sessions,
    get_summary_metrics,
    initialize_database,
    list_collection_runs,
    list_report_runs,
    sync_chargers,
    update_charger_settings,
)
from grizzl.export import export_filename, session_export_rows, sessions_csv_text
from grizzl.health import run_health_checks
from grizzl.reports import send_weekly_report
from grizzl.routes.api import api_blueprint
from grizzl.services.polling import poll_single
from grizzl.vitals import build_vitals_payload


def _bootstrap() -> None:
    initialize_database()
    sync_chargers(CHARGERS)


def _csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return str(token)


def _require_csrf() -> None:
    posted_token = request.form.get("csrf_token") or request.headers.get(
        "X-CSRF-Token"
    )
    if posted_token != session.get("csrf_token"):
        raise ValueError("Invalid form token")


def _filters() -> dict[str, Any]:
    charger_id = request.args.get("charger_id", type=int)
    return {
        "charger_id": charger_id,
        "start": request.args.get("start") or None,
        "end": request.args.get("end") or None,
        "keyword": request.args.get("keyword") or None,
    }


app = Flask(__name__)
app.secret_key = os.getenv("GRIZZL_FLASK_SECRET_KEY", secrets.token_urlsafe(32))
app.register_blueprint(api_blueprint)
app.jinja_env.globals["csrf_token"] = _csrf_token


@app.get("/")
def index():
    _bootstrap()
    return render_template(
        "dashboard.html",
        app_name=APP_NAME,
        site_name=SITE_NAME,
        chargers=get_chargers_with_status(),
        sessions=get_sessions(limit=10),
        metrics=get_summary_metrics(),
        runs=list_collection_runs(limit=8),
    )


@app.get("/chargers")
def chargers_page():
    _bootstrap()
    return render_template(
        "chargers.html",
        app_name=APP_NAME,
        site_name=SITE_NAME,
        chargers=get_chargers_with_status(),
        runs=list_collection_runs(limit=20),
    )


@app.get("/sessions")
def sessions_page():
    _bootstrap()
    filters = _filters()
    page = max(1, request.args.get("page", default=1, type=int) or 1)
    per_page = 50
    offset = (page - 1) * per_page
    sessions_data = get_sessions(
        limit=per_page,
        offset=offset,
        **filters,
    )
    total = count_sessions(**filters)
    return render_template(
        "sessions.html",
        app_name=APP_NAME,
        site_name=SITE_NAME,
        chargers=get_chargers_with_status(),
        sessions=sessions_data,
        filters=filters,
        page=page,
        total=total,
        per_page=per_page,
    )


@app.get("/settings")
def settings_page():
    _bootstrap()
    return render_template(
        "settings.html",
        app_name=APP_NAME,
        site_name=SITE_NAME,
        chargers=get_chargers_with_status(),
        reports=list_report_runs(),
    )


@app.get("/health")
def health_page():
    _bootstrap()
    return render_template(
        "health.html",
        app_name=APP_NAME,
        site_name=SITE_NAME,
        health=run_health_checks(),
    )


@app.get("/vitals")
def vitals_page():
    _bootstrap()
    return render_template(
        "vitals.html",
        app_name=APP_NAME,
        site_name=SITE_NAME,
        vitals=build_vitals_payload(request.args.get("range")),
    )


@app.get("/export.csv")
def export_csv():
    _bootstrap()
    filters = _filters()
    rows = session_export_rows(**filters)
    csv_text = sessions_csv_text(rows)
    filename = export_filename(filters["start"], filters["end"])
    return Response(
        csv_text,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )


@app.post("/chargers/<int:charger_id>/collect")
def collect_charger(charger_id: int):
    _bootstrap()
    try:
        _require_csrf()
        result = poll_single(charger_id, include_wifi_scan=True)
        status = result.get("status")
        if status == "success":
            flash(f"CHARGER_{charger_id} collected successfully.", "success")
        elif status == "offline":
            flash(f"CHARGER_{charger_id} is offline/not visible.", "warning")
        else:
            flash(str(result.get("error", "Collection failed.")), "error")
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(request.referrer or url_for("chargers_page"))


@app.post("/chargers/<int:charger_id>/settings")
def update_charger(charger_id: int):
    _bootstrap()
    try:
        _require_csrf()
        display_name = request.form.get("display_name", "").strip()
        target_url = request.form.get("target_url", "").strip()
        enabled = request.form.get("enabled") == "on"
        if not target_url.startswith(("http://", "https://")):
            raise ValueError("Target URL must start with http:// or https://")
        update_charger_settings(
            charger_id,
            display_name=display_name,
            enabled=enabled,
            target_url=target_url,
        )
        flash(f"CHARGER_{charger_id} settings updated.", "success")
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(url_for("settings_page"))


@app.post("/reports/test")
def test_report():
    _bootstrap()
    try:
        _require_csrf()
        result = send_weekly_report(dry_run=True, output_dir=None)
        flash(
            "Report dry run generated "
            f"{result['summary']['session_count']} session row(s).",
            "success",
        )
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(url_for("settings_page"))


@app.errorhandler(404)
def not_found(_error):
    return render_template(
        "errors.html",
        app_name=APP_NAME,
        site_name=SITE_NAME,
        title="Page Not Found",
        message="The requested page does not exist.",
    ), 404


@app.errorhandler(500)
def server_error(error):
    return render_template(
        "errors.html",
        app_name=APP_NAME,
        site_name=SITE_NAME,
        title="Server Error",
        message=str(error),
    ), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
    )
