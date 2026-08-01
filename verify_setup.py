from pathlib import Path
import sqlite3

import flask
import requests
from bs4 import BeautifulSoup
import lxml


def main() -> None:
    database_path = Path("data/test.db")

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS setup_test (
                id INTEGER PRIMARY KEY,
                message TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT INTO setup_test (message) VALUES (?)",
            ("Grizzl monitor setup verified",),
        )
        connection.commit()

    print("Python imports: OK")
    print(f"SQLite write: OK ({database_path})")
    print("Project setup: READY")


if __name__ == "__main__":
    main()
