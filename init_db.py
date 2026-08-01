from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path("data/grizzl.db")


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS charging_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                charger_id TEXT NOT NULL,
                session_start TEXT NOT NULL,
                duration_seconds INTEGER NOT NULL,
                energy_kwh REAL NOT NULL,
                cost REAL NOT NULL,
                collected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(charger_id, session_start)
            )
            """
        )

    print(f"Database initialized: {DB_PATH}")


if __name__ == "__main__":
    main()

