from flask import Flask, render_template

from grizzl.config import APP_NAME, CHARGERS, SITE_NAME
from grizzl.database import (
    get_chargers_with_status,
    get_recent_sessions,
    initialize_database,
    sync_chargers,
)
from grizzl.routes.api import api_blueprint
from grizzl.statistics import calculate_fleet_statistics


app = Flask(__name__)
app.register_blueprint(api_blueprint)


@app.get("/")
def index():
    initialize_database()
    sync_chargers(CHARGERS)

    chargers = get_chargers_with_status()
    sessions = get_recent_sessions(limit=100)
    statistics = calculate_fleet_statistics(chargers, sessions)

    return render_template(
        "index.html",
        app_name=APP_NAME,
        site_name=SITE_NAME,
        chargers=chargers,
        sessions=sessions,
        statistics=statistics,
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
    )
