from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from grizzl.config import DB_PATH
from grizzl.parser import ParsedSession


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _database_path() -> Path:
    path = Path(DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@dataclass(frozen=True)
class SessionInsertResult:
    """Counts returned from duplicate-safe normalized session insertion."""

    parsed: int
    inserted: int
    duplicates: int
    rejected: int = 0


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(_database_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_database() -> None:
    with connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS fleet_chargers (
                charger_id TEXT PRIMARY KEY,
                ssid TEXT NOT NULL,
                url TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                test_charger INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS fleet_charger_status (
                charger_id TEXT PRIMARY KEY,
                online INTEGER NOT NULL DEFAULT 0,
                active_ssid TEXT,
                http_status INTEGER,
                last_seen_at TEXT,
                last_error TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (charger_id)
                    REFERENCES fleet_chargers(charger_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS fleet_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                charger_id TEXT NOT NULL,
                session_key TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                collected_at TEXT NOT NULL,
                UNIQUE (charger_id, session_key),
                FOREIGN KEY (charger_id)
                    REFERENCES fleet_chargers(charger_id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_fleet_sessions_charger
                ON fleet_sessions(charger_id);

            CREATE INDEX IF NOT EXISTS idx_fleet_sessions_collected
                ON fleet_sessions(collected_at);

            CREATE TABLE IF NOT EXISTS chargers (
                id INTEGER PRIMARY KEY,
                ssid TEXT UNIQUE NOT NULL,
                display_name TEXT,
                enabled INTEGER NOT NULL DEFAULT 1,
                environment TEXT NOT NULL,
                target_url TEXT NOT NULL,
                expected_bssid TEXT,
                first_seen_at TEXT,
                last_seen_at TEXT,
                last_signal INTEGER,
                last_scrape_attempt_at TEXT,
                last_scrape_success_at TEXT,
                last_error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                charger_id INTEGER NOT NULL,
                session_start_utc TEXT NOT NULL,
                session_start_local TEXT NOT NULL,
                source_date_text TEXT,
                source_timezone TEXT,
                energy_kwh REAL,
                duration_seconds INTEGER,
                duration_text TEXT,
                cost REAL,
                raw_row_json TEXT,
                collected_at TEXT NOT NULL,
                first_collected_at TEXT NOT NULL,
                last_confirmed_at TEXT,
                FOREIGN KEY(charger_id) REFERENCES chargers(id),
                UNIQUE(charger_id, session_start_utc)
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_start_utc
                ON sessions(session_start_utc);

            CREATE INDEX IF NOT EXISTS idx_sessions_charger_start
                ON sessions(charger_id, session_start_utc);

            CREATE TABLE IF NOT EXISTS charger_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                charger_id INTEGER NOT NULL,
                observed_at TEXT NOT NULL,
                bssid TEXT,
                signal INTEGER,
                channel INTEGER,
                frequency TEXT,
                visible INTEGER NOT NULL,
                activation_id TEXT,
                FOREIGN KEY(charger_id) REFERENCES chargers(id)
            );

            CREATE INDEX IF NOT EXISTS idx_charger_observations_charger
                ON charger_observations(charger_id, observed_at);

            CREATE TABLE IF NOT EXISTS collection_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                charger_id INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                status TEXT NOT NULL,
                http_status INTEGER,
                records_found INTEGER NOT NULL DEFAULT 0,
                records_inserted INTEGER NOT NULL DEFAULT 0,
                records_duplicate INTEGER NOT NULL DEFAULT 0,
                records_rejected INTEGER NOT NULL DEFAULT 0,
                error_type TEXT,
                error_message TEXT,
                response_time_ms INTEGER,
                FOREIGN KEY(charger_id) REFERENCES chargers(id)
            );
            """
        )


def upsert_charger(charger: dict[str, Any]) -> None:
    now = utc_now_iso()
    numeric_id = int(charger.get("charger_id", 0))

    with connection() as conn:
        conn.execute(
            """
            INSERT INTO fleet_chargers (
                charger_id, ssid, url, enabled, test_charger,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(charger_id) DO UPDATE SET
                ssid = excluded.ssid,
                url = excluded.url,
                enabled = excluded.enabled,
                test_charger = excluded.test_charger,
                updated_at = excluded.updated_at
            """,
            (
                str(charger["id"]),
                str(charger["ssid"]),
                str(charger.get("target_url") or charger["url"]),
                int(bool(charger.get("enabled", True))),
                int(bool(charger.get("test_charger", False))),
                now,
                now,
            ),
        )
        conn.execute(
            """
            INSERT INTO chargers (
                id, ssid, display_name, enabled, environment, target_url,
                expected_bssid, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                ssid = excluded.ssid,
                display_name = excluded.display_name,
                enabled = excluded.enabled,
                environment = excluded.environment,
                target_url = excluded.target_url,
                expected_bssid = excluded.expected_bssid,
                updated_at = excluded.updated_at
            """,
            (
                numeric_id,
                str(charger["ssid"]),
                charger.get("display_name"),
                int(bool(charger.get("enabled", True))),
                str(charger.get("environment", "production")),
                str(charger.get("target_url") or charger["url"]),
                charger.get("expected_bssid"),
                now,
                now,
            ),
        )


def sync_chargers(chargers: tuple[dict, ...] | list[dict]) -> None:
    initialize_database()
    for charger in chargers:
        upsert_charger(charger)


def save_charger_status(
    charger_id: str,
    *,
    online: bool,
    active_ssid: str | None = None,
    http_status: int | None = None,
    last_error: str | None = None,
) -> None:
    now = utc_now_iso()
    last_seen_at = now if online else None

    with connection() as conn:
        conn.execute(
            """
            INSERT INTO fleet_charger_status (
                charger_id, online, active_ssid, http_status,
                last_seen_at, last_error, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(charger_id) DO UPDATE SET
                online = excluded.online,
                active_ssid = excluded.active_ssid,
                http_status = excluded.http_status,
                last_seen_at = CASE
                    WHEN excluded.online = 1
                    THEN excluded.last_seen_at
                    ELSE fleet_charger_status.last_seen_at
                END,
                last_error = excluded.last_error,
                updated_at = excluded.updated_at
            """,
            (
                charger_id,
                int(online),
                active_ssid,
                http_status,
                last_seen_at,
                last_error,
                now,
            ),
        )


def _session_key(payload: Any) -> str:
    normalized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _normalize_sessions(payload: Any) -> list[Any]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("sessions", "records", "logs", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return [payload]


def save_sessions(charger_id: str, payload: Any) -> int:
    sessions = _normalize_sessions(payload)
    inserted = 0
    collected_at = utc_now_iso()

    with connection() as conn:
        for session in sessions:
            payload_json = json.dumps(
                session,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            )
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO fleet_sessions (
                    charger_id, session_key, payload_json, collected_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    charger_id,
                    _session_key(session),
                    payload_json,
                    collected_at,
                ),
            )
            inserted += cursor.rowcount

    return inserted


def save_parsed_sessions(
    charger_id: int,
    sessions: list[ParsedSession],
    *,
    rejected_count: int = 0,
) -> SessionInsertResult:
    """Insert normalized sessions using charger_id + session_start_utc."""
    inserted = 0
    collected_at = utc_now_iso()

    with connection() as conn:
        for session in sessions:
            raw_row_json = json.dumps(
                session.raw_row,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            )
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO sessions (
                    charger_id,
                    session_start_utc,
                    session_start_local,
                    source_date_text,
                    source_timezone,
                    energy_kwh,
                    duration_seconds,
                    duration_text,
                    cost,
                    raw_row_json,
                    collected_at,
                    first_collected_at,
                    last_confirmed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    charger_id,
                    session.session_start_utc,
                    session.session_start_local,
                    session.source_date_text,
                    session.source_timezone,
                    session.energy_kwh,
                    session.duration_seconds,
                    session.duration_text,
                    session.cost,
                    raw_row_json,
                    collected_at,
                    collected_at,
                    collected_at,
                ),
            )

            if cursor.rowcount == 1:
                inserted += 1
                continue

            conn.execute(
                """
                UPDATE sessions
                SET last_confirmed_at = ?,
                    collected_at = ?,
                    raw_row_json = ?
                WHERE charger_id = ?
                  AND session_start_utc = ?
                """,
                (
                    collected_at,
                    collected_at,
                    raw_row_json,
                    charger_id,
                    session.session_start_utc,
                ),
            )

    parsed_count = len(sessions)

    return SessionInsertResult(
        parsed=parsed_count,
        inserted=inserted,
        duplicates=max(0, parsed_count - inserted),
        rejected=rejected_count,
    )


def get_normalized_session_count(charger_id: int | None = None) -> int:
    initialize_database()

    with connection() as conn:
        if charger_id is None:
            row = conn.execute("SELECT COUNT(*) AS count FROM sessions").fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) AS count FROM sessions WHERE charger_id = ?",
                (charger_id,),
            ).fetchone()

    return int(row["count"])


def get_latest_status(charger_id: str) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM fleet_charger_status WHERE charger_id = ?",
            (charger_id,),
        ).fetchone()
    return dict(row) if row is not None else None


def get_session_count(charger_id: str | None = None) -> int:
    with connection() as conn:
        if charger_id is None:
            row = conn.execute(
                "SELECT COUNT(*) AS count FROM fleet_sessions"
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) AS count FROM fleet_sessions "
                "WHERE charger_id = ?",
                (charger_id,),
            ).fetchone()
    return int(row["count"])


def get_chargers_with_status() -> list[dict[str, Any]]:
    initialize_database()

    with connection() as conn:
        rows = conn.execute(
            """
            SELECT
                c.charger_id,
                c.ssid,
                c.url,
                c.enabled,
                c.test_charger,
                COALESCE(s.online, 0) AS online,
                s.active_ssid,
                s.http_status,
                s.last_seen_at,
                s.last_error,
                s.updated_at AS status_updated_at,
                (
                    SELECT COUNT(*)
                    FROM sessions fs
                    WHERE fs.charger_id = CAST(
                        REPLACE(c.charger_id, 'CHARGER_', '') AS INTEGER
                    )
                ) AS session_count
            FROM fleet_chargers c
            LEFT JOIN fleet_charger_status s
                ON s.charger_id = c.charger_id
            ORDER BY c.test_charger DESC, c.charger_id
            """
        ).fetchall()

    return [dict(row) for row in rows]


def get_recent_sessions(
    limit: int = 100,
    charger_id: str | None = None,
) -> list[dict[str, Any]]:
    initialize_database()
    safe_limit = max(1, min(int(limit), 1000))

    query = """
        SELECT
            s.id,
            'CHARGER_' || s.charger_id AS charger_id,
            s.raw_row_json AS payload_json,
            s.collected_at,
            s.session_start_local,
            s.energy_kwh,
            s.duration_text,
            s.cost
        FROM sessions s
    """
    parameters: list[Any] = []

    if charger_id:
        query += " WHERE s.charger_id = CAST(REPLACE(?, 'CHARGER_', '') AS INTEGER)"
        parameters.append(charger_id)

    query += " ORDER BY s.session_start_utc DESC, s.id DESC LIMIT ?"
    parameters.append(safe_limit)

    with connection() as conn:
        rows = conn.execute(query, parameters).fetchall()

    result: list[dict[str, Any]] = []

    for row in rows:
        try:
            payload = json.loads(row["payload_json"])
        except (TypeError, json.JSONDecodeError):
            payload = row["payload_json"]

        result.append(
            {
                "id": row["id"],
                "charger_id": row["charger_id"],
                "payload": payload,
                "session_start_local": row["session_start_local"],
                "energy_kwh": row["energy_kwh"],
                "duration_text": row["duration_text"],
                "cost": row["cost"],
                "payload_preview": json.dumps(
                    payload,
                    indent=2,
                    sort_keys=True,
                    default=str,
                ),
                "collected_at": row["collected_at"],
            }
        )

    return result
