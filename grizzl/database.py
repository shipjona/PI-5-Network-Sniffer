from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from grizzl.config import CHARGERS, DB_PATH
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
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            );

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

            CREATE INDEX IF NOT EXISTS idx_collection_runs_charger_started
                ON collection_runs(charger_id, started_at);

            CREATE TABLE IF NOT EXISTS service_state (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS report_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_type TEXT NOT NULL,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                status TEXT NOT NULL,
                recipient TEXT,
                sessions_count INTEGER NOT NULL DEFAULT 0,
                total_energy_kwh REAL NOT NULL DEFAULT 0,
                attachment_path TEXT,
                error_message TEXT
            );

            CREATE TABLE IF NOT EXISTS system_vitals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sampled_at TEXT NOT NULL,
                temperature_c REAL,
                cpu_percent REAL,
                cpu_frequency_mhz REAL,
                load_1 REAL,
                load_5 REAL,
                load_15 REAL,
                memory_total_bytes INTEGER,
                memory_available_bytes INTEGER,
                memory_used_percent REAL,
                swap_total_bytes INTEGER,
                swap_free_bytes INTEGER,
                root_total_bytes INTEGER,
                root_free_bytes INTEGER,
                root_used_percent REAL,
                data_total_bytes INTEGER,
                data_free_bytes INTEGER,
                data_used_percent REAL,
                uptime_seconds INTEGER,
                throttled_raw TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_system_vitals_sampled_at
                ON system_vitals(sampled_at);
            """
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO schema_migrations (version, applied_at)
            VALUES (?, ?)
            """,
            (1, utc_now_iso()),
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
                environment = excluded.environment,
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


def get_runtime_chargers(
    chargers: tuple[dict, ...] | list[dict] = CHARGERS,
    *,
    enabled_only: bool = False,
) -> list[dict[str, Any]]:
    """
    Return charger config merged with dashboard-editable database settings.

    Static config remains the source for immutable fields and secret env names.
    The database is authoritative for display_name, enabled, and target_url so
    settings changed from the dashboard are not overwritten by config sync.
    """
    sync_chargers(chargers)
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT id, display_name, enabled, target_url
            FROM chargers
            """
        ).fetchall()

    saved_by_id = {int(row["id"]): row for row in rows}
    merged_chargers: list[dict[str, Any]] = []

    for charger in chargers:
        numeric_id = int(charger.get("charger_id", 0))
        merged = dict(charger)
        saved = saved_by_id.get(numeric_id)

        if saved is not None:
            merged["display_name"] = saved["display_name"]
            merged["enabled"] = bool(saved["enabled"])
            merged["target_url"] = saved["target_url"]

        if enabled_only and not merged.get("enabled", True):
            continue

        merged_chargers.append(merged)

    return merged_chargers


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

        numeric_id = _numeric_charger_id(charger_id)
        if numeric_id is not None:
            conn.execute(
                """
                UPDATE chargers
                SET last_error = ?,
                    last_scrape_success_at = CASE
                        WHEN ? = 1 THEN ?
                        ELSE last_scrape_success_at
                    END,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    last_error,
                    int(online),
                    now,
                    now,
                    numeric_id,
                ),
            )


def _numeric_charger_id(charger_id: str | int) -> int | None:
    if isinstance(charger_id, int):
        return charger_id

    value = str(charger_id).strip()
    if value.startswith("CHARGER_"):
        value = value.removeprefix("CHARGER_")

    try:
        return int(value)
    except ValueError:
        return None


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


def record_charger_observation(
    charger_id: int,
    *,
    visible: bool,
    bssid: str | None = None,
    signal: int | None = None,
    channel: int | None = None,
    frequency: str | None = None,
    activation_id: str | None = None,
    observed_at: str | None = None,
) -> None:
    """Persist one visibility sample and update charger visibility fields."""
    initialize_database()
    timestamp = observed_at or utc_now_iso()

    with connection() as conn:
        conn.execute(
            """
            INSERT INTO charger_observations (
                charger_id, observed_at, bssid, signal, channel,
                frequency, visible, activation_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                charger_id,
                timestamp,
                bssid,
                signal,
                channel,
                frequency,
                int(visible),
                activation_id,
            ),
        )

        if visible:
            conn.execute(
                """
                UPDATE chargers
                SET first_seen_at = COALESCE(first_seen_at, ?),
                    last_seen_at = ?,
                    last_signal = ?,
                    last_error = NULL,
                    updated_at = ?
                WHERE id = ?
                """,
                (timestamp, timestamp, signal, timestamp, charger_id),
            )
            save_key_value(f"charger:{charger_id}:visible", "1", conn=conn)
        else:
            save_key_value(f"charger:{charger_id}:visible", "0", conn=conn)


def record_scan_results(
    matches: list[tuple[dict[str, Any], Any]],
    *,
    all_chargers: tuple[dict[str, Any], ...] | list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    Record one scan pass, including offline rows for configured APs not visible.
    """
    initialize_database()
    runtime_chargers = (
        get_runtime_chargers()
        if all_chargers is None
        else get_runtime_chargers(all_chargers)
    )
    observed_at = utc_now_iso()
    visible_by_id: dict[int, Any] = {
        int(charger.get("charger_id", 0)): observation
        for charger, observation in matches
    }
    rows: list[dict[str, Any]] = []

    for charger in runtime_chargers:
        if not charger.get("enabled", True):
            continue

        numeric_id = int(charger.get("charger_id", 0))
        observation = visible_by_id.get(numeric_id)
        visible = observation is not None

        record_charger_observation(
            numeric_id,
            visible=visible,
            bssid=getattr(observation, "bssid", None) if observation else None,
            signal=getattr(observation, "signal", None) if observation else None,
            channel=getattr(observation, "channel", None) if observation else None,
            frequency=getattr(observation, "frequency", None) if observation else None,
            observed_at=observed_at,
        )

        if not visible and charger.get("connect_mode") == "wifi":
            save_charger_status(
                str(charger["id"]),
                online=False,
                last_error="SSID not visible",
            )

        rows.append(
            {
                "charger_id": numeric_id,
                "ssid": charger["ssid"],
                "visible": visible,
                "signal": getattr(observation, "signal", None)
                if observation
                else None,
            }
        )

    set_service_state(
        "scanner_last_run_at",
        observed_at,
    )
    set_service_state(
        "scanner_visible_count",
        str(sum(1 for row in rows if row["visible"])),
    )
    return rows


def start_collection_run(charger_id: int) -> int:
    """Create a collection run row and return its ID."""
    initialize_database()
    started_at = utc_now_iso()

    with connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO collection_runs (charger_id, started_at, status)
            VALUES (?, ?, ?)
            """,
            (charger_id, started_at, "running"),
        )
        run_id = int(cursor.lastrowid)

        conn.execute(
            """
            UPDATE chargers
            SET last_scrape_attempt_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (started_at, started_at, charger_id),
        )

    return run_id


def complete_collection_run(
    run_id: int,
    *,
    status: str,
    http_status: int | None = None,
    records_found: int = 0,
    records_inserted: int = 0,
    records_duplicate: int = 0,
    records_rejected: int = 0,
    error_type: str | None = None,
    error_message: str | None = None,
    response_time_ms: int | None = None,
) -> None:
    """Finish a collection run and update charger summary fields."""
    completed_at = utc_now_iso()

    with connection() as conn:
        row = conn.execute(
            "SELECT charger_id FROM collection_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        charger_id = int(row["charger_id"]) if row else None

        conn.execute(
            """
            UPDATE collection_runs
            SET completed_at = ?,
                status = ?,
                http_status = ?,
                records_found = ?,
                records_inserted = ?,
                records_duplicate = ?,
                records_rejected = ?,
                error_type = ?,
                error_message = ?,
                response_time_ms = ?
            WHERE id = ?
            """,
            (
                completed_at,
                status,
                http_status,
                records_found,
                records_inserted,
                records_duplicate,
                records_rejected,
                error_type,
                error_message,
                response_time_ms,
                run_id,
            ),
        )

        if charger_id is not None:
            conn.execute(
                """
                UPDATE chargers
                SET last_scrape_success_at = CASE
                        WHEN ? = 'success' THEN ?
                        ELSE last_scrape_success_at
                    END,
                    last_error = CASE
                        WHEN ? = 'success' THEN NULL
                        ELSE ?
                    END,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    completed_at,
                    status,
                    error_message,
                    completed_at,
                    charger_id,
                ),
            )


def save_key_value(
    key: str,
    value: str | None,
    *,
    conn: sqlite3.Connection | None = None,
) -> None:
    """Persist service state, optionally reusing an open transaction."""
    now = utc_now_iso()
    parameters = (key, value, now)
    query = """
        INSERT INTO service_state (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = excluded.updated_at
    """

    if conn is not None:
        conn.execute(query, parameters)
        return

    initialize_database()
    with connection() as own_conn:
        own_conn.execute(query, parameters)


def set_service_state(key: str, value: str | None) -> None:
    save_key_value(key, value)


def get_service_state() -> dict[str, dict[str, str | None]]:
    initialize_database()
    with connection() as conn:
        rows = conn.execute(
            "SELECT key, value, updated_at FROM service_state ORDER BY key"
        ).fetchall()
    return {row["key"]: {"value": row["value"], "updated_at": row["updated_at"]} for row in rows}


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
                CASE
                    WHEN c.id = 0 THEN 'CHARGER_0'
                    ELSE 'CHARGER_' || c.id
                END AS charger_id,
                c.id AS numeric_charger_id,
                c.display_name,
                c.ssid,
                c.target_url AS url,
                c.environment,
                c.enabled,
                CASE WHEN c.environment = 'development' THEN 1 ELSE 0 END
                    AS test_charger,
                COALESCE(s.online, 0) AS online,
                s.active_ssid,
                s.http_status,
                s.last_seen_at,
                COALESCE(c.last_error, s.last_error) AS last_error,
                s.updated_at AS status_updated_at,
                c.first_seen_at,
                c.last_seen_at AS ssid_last_seen_at,
                c.last_signal,
                c.last_scrape_attempt_at,
                c.last_scrape_success_at,
                latest_session.session_start_local AS most_recent_session,
                COALESCE(last_observation.visible, 0) AS visible,
                last_observation.observed_at AS last_observed_at,
                (
                    SELECT COUNT(*)
                    FROM sessions session_count
                    WHERE session_count.charger_id = c.id
                ) AS session_count
            FROM chargers c
            LEFT JOIN fleet_charger_status s
                ON s.charger_id = CASE
                    WHEN c.id = 0 THEN 'CHARGER_0'
                    ELSE 'CHARGER_' || c.id
                END
            LEFT JOIN sessions latest_session
                ON latest_session.id = (
                    SELECT latest.id
                    FROM sessions latest
                    WHERE latest.charger_id = c.id
                    ORDER BY latest.session_start_utc DESC
                    LIMIT 1
                )
            LEFT JOIN charger_observations last_observation
                ON last_observation.id = (
                    SELECT observation.id
                    FROM charger_observations observation
                    WHERE observation.charger_id = c.id
                    ORDER BY observation.observed_at DESC, observation.id DESC
                    LIMIT 1
                )
            ORDER BY c.environment = 'development' DESC, c.id
            """
        ).fetchall()

    chargers: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        for key in ("enabled", "test_charger", "online", "visible"):
            item[key] = bool(item[key])
        chargers.append(item)

    return chargers


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


def get_sessions(
    *,
    limit: int = 100,
    offset: int = 0,
    charger_id: int | None = None,
    start: str | None = None,
    end: str | None = None,
    min_energy: float | None = None,
    max_energy: float | None = None,
    keyword: str | None = None,
) -> list[dict[str, Any]]:
    """Return normalized sessions with optional dashboard/export filters."""
    initialize_database()
    query = """
        SELECT
            s.id,
            'CHARGER_' || s.charger_id || '-' ||
                strftime('%Y%m%dT%H%M%S', s.session_start_local)
                AS session_id,
            s.charger_id,
            c.display_name AS charger_name,
            c.ssid,
            s.session_start_local,
            s.session_start_utc,
            s.source_date_text,
            s.source_timezone,
            s.energy_kwh,
            s.duration_text AS duration,
            s.duration_seconds,
            s.cost,
            s.first_collected_at,
            s.last_confirmed_at,
            s.collected_at,
            s.raw_row_json
        FROM sessions s
        JOIN chargers c ON c.id = s.charger_id
        WHERE 1 = 1
    """
    params: list[Any] = []

    if charger_id is not None:
        query += " AND s.charger_id = ?"
        params.append(charger_id)
    if start:
        query += " AND s.session_start_local >= ?"
        params.append(start)
    if end:
        query += " AND s.session_start_local <= ?"
        params.append(end)
    if min_energy is not None:
        query += " AND s.energy_kwh >= ?"
        params.append(min_energy)
    if max_energy is not None:
        query += " AND s.energy_kwh <= ?"
        params.append(max_energy)
    if keyword:
        like = f"%{keyword}%"
        query += """
            AND (
                c.display_name LIKE ?
                OR c.ssid LIKE ?
                OR s.source_date_text LIKE ?
                OR s.raw_row_json LIKE ?
            )
        """
        params.extend([like, like, like, like])

    query += " ORDER BY s.session_start_utc DESC, s.id DESC LIMIT ? OFFSET ?"
    params.extend([max(1, min(int(limit), 1000)), max(0, int(offset))])

    with connection() as conn:
        rows = conn.execute(query, params).fetchall()

    return [dict(row) for row in rows]


def count_sessions(
    *,
    charger_id: int | None = None,
    start: str | None = None,
    end: str | None = None,
    keyword: str | None = None,
) -> int:
    initialize_database()
    query = """
        SELECT COUNT(*) AS count
        FROM sessions s
        JOIN chargers c ON c.id = s.charger_id
        WHERE 1 = 1
    """
    params: list[Any] = []

    if charger_id is not None:
        query += " AND s.charger_id = ?"
        params.append(charger_id)
    if start:
        query += " AND s.session_start_local >= ?"
        params.append(start)
    if end:
        query += " AND s.session_start_local <= ?"
        params.append(end)
    if keyword:
        like = f"%{keyword}%"
        query += """
            AND (
                c.display_name LIKE ?
                OR c.ssid LIKE ?
                OR s.source_date_text LIKE ?
                OR s.raw_row_json LIKE ?
            )
        """
        params.extend([like, like, like, like])

    with connection() as conn:
        row = conn.execute(query, params).fetchone()
    return int(row["count"])


def get_summary_metrics() -> dict[str, Any]:
    initialize_database()
    with connection() as conn:
        totals = conn.execute(
            """
            SELECT
                COUNT(*) AS session_count,
                COALESCE(SUM(energy_kwh), 0) AS total_energy_kwh,
                COALESCE(AVG(energy_kwh), 0) AS average_energy_kwh,
                COALESCE(AVG(duration_seconds), 0) AS average_duration_seconds
            FROM sessions
            """
        ).fetchone()
        today = conn.execute(
            """
            SELECT COALESCE(SUM(energy_kwh), 0) AS energy
            FROM sessions
            WHERE date(session_start_local) = date('now', 'localtime')
            """
        ).fetchone()
        month = conn.execute(
            """
            SELECT COALESCE(SUM(energy_kwh), 0) AS energy
            FROM sessions
            WHERE strftime('%Y-%m', session_start_local)
                = strftime('%Y-%m', 'now', 'localtime')
            """
        ).fetchone()
        by_charger = conn.execute(
            """
            SELECT
                c.id AS charger_id,
                c.display_name,
                c.ssid,
                COUNT(s.id) AS session_count,
                COALESCE(SUM(s.energy_kwh), 0) AS energy_kwh
            FROM chargers c
            LEFT JOIN sessions s ON s.charger_id = c.id
            GROUP BY c.id, c.display_name, c.ssid
            ORDER BY c.id
            """
        ).fetchall()
        daily = conn.execute(
            """
            SELECT
                date(session_start_local) AS day,
                COUNT(*) AS session_count,
                COALESCE(SUM(energy_kwh), 0) AS energy_kwh
            FROM sessions
            GROUP BY date(session_start_local)
            ORDER BY day DESC
            LIMIT 30
            """
        ).fetchall()
        last_success = conn.execute(
            """
            SELECT completed_at
            FROM collection_runs
            WHERE status = 'success'
            ORDER BY completed_at DESC
            LIMIT 1
            """
        ).fetchone()
        last_error = conn.execute(
            """
            SELECT completed_at, error_message
            FROM collection_runs
            WHERE status != 'success'
            ORDER BY completed_at DESC
            LIMIT 1
            """
        ).fetchone()

    return {
        "session_count": int(totals["session_count"]),
        "total_energy_kwh": round(float(totals["total_energy_kwh"]), 3),
        "average_energy_kwh": round(float(totals["average_energy_kwh"]), 3),
        "average_duration_seconds": int(totals["average_duration_seconds"] or 0),
        "today_energy_kwh": round(float(today["energy"]), 3),
        "month_energy_kwh": round(float(month["energy"]), 3),
        "by_charger": [dict(row) for row in by_charger],
        "daily": [dict(row) for row in daily],
        "last_successful_collection": last_success["completed_at"] if last_success else None,
        "last_service_error": dict(last_error) if last_error else None,
    }


def list_collection_runs(limit: int = 50) -> list[dict[str, Any]]:
    initialize_database()
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT
                r.*,
                c.display_name,
                c.ssid
            FROM collection_runs r
            JOIN chargers c ON c.id = r.charger_id
            ORDER BY r.started_at DESC, r.id DESC
            LIMIT ?
            """,
            (max(1, min(int(limit), 500)),),
        ).fetchall()
    return [dict(row) for row in rows]


def update_charger_settings(
    charger_id: int,
    *,
    display_name: str,
    enabled: bool,
    target_url: str,
) -> None:
    initialize_database()
    now = utc_now_iso()
    with connection() as conn:
        cursor = conn.execute(
            """
            UPDATE chargers
            SET display_name = ?,
                enabled = ?,
                target_url = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                display_name.strip(),
                int(enabled),
                target_url.strip(),
                now,
                charger_id,
            ),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"Unknown charger_id {charger_id}")
        conn.execute(
            """
            UPDATE fleet_chargers
            SET enabled = ?,
                url = ?,
                updated_at = ?
            WHERE charger_id = ?
            """,
            (
                int(enabled),
                target_url.strip(),
                now,
                f"CHARGER_{charger_id}",
            ),
        )


def create_report_run(
    *,
    report_type: str,
    period_start: str,
    period_end: str,
    recipient: str | None,
    sessions_count: int,
    total_energy_kwh: float,
    attachment_path: str | None,
    status: str = "running",
) -> int:
    initialize_database()
    created_at = utc_now_iso()
    with connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO report_runs (
                report_type, period_start, period_end, created_at, status,
                recipient, sessions_count, total_energy_kwh, attachment_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report_type,
                period_start,
                period_end,
                created_at,
                status,
                recipient,
                sessions_count,
                total_energy_kwh,
                attachment_path,
            ),
        )
        return int(cursor.lastrowid)


def complete_report_run(
    report_run_id: int,
    *,
    status: str,
    error_message: str | None = None,
) -> None:
    with connection() as conn:
        conn.execute(
            """
            UPDATE report_runs
            SET status = ?,
                completed_at = ?,
                error_message = ?
            WHERE id = ?
            """,
            (status, utc_now_iso(), error_message, report_run_id),
        )


SYSTEM_VITAL_COLUMNS = (
    "sampled_at",
    "temperature_c",
    "cpu_percent",
    "cpu_frequency_mhz",
    "load_1",
    "load_5",
    "load_15",
    "memory_total_bytes",
    "memory_available_bytes",
    "memory_used_percent",
    "swap_total_bytes",
    "swap_free_bytes",
    "root_total_bytes",
    "root_free_bytes",
    "root_used_percent",
    "data_total_bytes",
    "data_free_bytes",
    "data_used_percent",
    "uptime_seconds",
    "throttled_raw",
)


SYSTEM_VITAL_TREND_COLUMNS = (
    ("temperature_c", "Temperature", "C"),
    ("cpu_percent", "CPU Used", "%"),
    ("cpu_frequency_mhz", "CPU Frequency", "MHz"),
    ("load_1", "Load 1m", ""),
    ("memory_used_percent", "Memory Used", "%"),
    ("root_used_percent", "System Disk Used", "%"),
    ("data_used_percent", "Data Disk Used", "%"),
)


def save_system_vitals(sample: dict[str, Any]) -> int:
    """Persist one Pi vitals sample and return its row ID."""
    initialize_database()
    values = [sample.get(column) for column in SYSTEM_VITAL_COLUMNS]
    placeholders = ", ".join("?" for _column in SYSTEM_VITAL_COLUMNS)
    columns = ", ".join(SYSTEM_VITAL_COLUMNS)

    with connection() as conn:
        cursor = conn.execute(
            f"INSERT INTO system_vitals ({columns}) VALUES ({placeholders})",
            values,
        )
        return int(cursor.lastrowid)


def list_system_vitals(
    *,
    since: str,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Return recent vitals samples within a UTC ISO time window."""
    initialize_database()

    with connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM system_vitals
            WHERE sampled_at >= ?
            ORDER BY sampled_at DESC, id DESC
            LIMIT ?
            """,
            (since, max(1, min(int(limit), 1000))),
        ).fetchall()

    return [dict(row) for row in rows]


def summarize_system_vitals(*, since: str) -> list[dict[str, Any]]:
    """Return latest/average/min/max trend rows for selected vitals."""
    initialize_database()
    trends: list[dict[str, Any]] = []

    with connection() as conn:
        for column, label, unit in SYSTEM_VITAL_TREND_COLUMNS:
            summary = conn.execute(
                f"""
                SELECT
                    COUNT({column}) AS count,
                    AVG({column}) AS average,
                    MIN({column}) AS minimum,
                    MAX({column}) AS maximum
                FROM system_vitals
                WHERE sampled_at >= ?
                  AND {column} IS NOT NULL
                """,
                (since,),
            ).fetchone()
            latest = conn.execute(
                f"""
                SELECT {column} AS value
                FROM system_vitals
                WHERE sampled_at >= ?
                  AND {column} IS NOT NULL
                ORDER BY sampled_at DESC, id DESC
                LIMIT 1
                """,
                (since,),
            ).fetchone()

            trends.append(
                {
                    "metric": column,
                    "label": label,
                    "unit": unit,
                    "count": int(summary["count"]),
                    "latest": latest["value"] if latest is not None else None,
                    "average": summary["average"],
                    "minimum": summary["minimum"],
                    "maximum": summary["maximum"],
                }
            )

    return trends


def list_report_runs(limit: int = 20) -> list[dict[str, Any]]:
    initialize_database()
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM report_runs
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (max(1, min(int(limit), 100)),),
        ).fetchall()
    return [dict(row) for row in rows]
