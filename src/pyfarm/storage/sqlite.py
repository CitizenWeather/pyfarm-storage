"""Async SQLite storage backend for pyfarm."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SQLiteBackend:
    """
    Async SQLite backend using aiosqlite.

    Tables:
    - snapshots:       grow_id, timestamp, data (JSON)
    - sensor_readings: timestamp, sensor_id, metric, value, unit, error
    - events:          timestamp, grow_id, event_type, event_kind, message, data (JSON)

    The database connection is opened lazily on first use; no ``await`` needed
    at construction time.
    """

    def __init__(self, db_path: str | Path = "pyfarm.db"):
        self.db_path = Path(db_path)
        self._db = None

    async def connect(self) -> None:
        """Open the database and create tables if they do not exist."""
        try:
            import aiosqlite
        except ImportError:
            raise ImportError(
                "aiosqlite is required for SQLiteBackend. "
                "Install with: pip install pyfarm-storage[sqlite]"
            )

        self._db = await aiosqlite.connect(str(self.db_path))
        await self._init_schema()

    async def _init_schema(self) -> None:
        if not self._db:
            return

        await self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS snapshots (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                grow_id   TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                data      TEXT NOT NULL,
                UNIQUE(grow_id, timestamp)
            )
            """
        )

        await self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                sensor_id TEXT NOT NULL,
                metric    TEXT NOT NULL,
                value     REAL NOT NULL,
                unit      TEXT,
                error     TEXT
            )
            """
        )
        await self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_readings_sensor_time "
            "ON sensor_readings(sensor_id, timestamp)"
        )

        await self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp  TEXT NOT NULL,
                grow_id    TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_kind TEXT NOT NULL,
                message    TEXT,
                data       TEXT
            )
            """
        )
        await self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_grow_time "
            "ON events(grow_id, timestamp)"
        )

        await self._db.commit()

    # ------------------------------------------------------------------ #
    # Snapshots
    # ------------------------------------------------------------------ #

    async def write_snapshot(self, ctx: Any) -> None:
        if not self._db:
            await self.connect()

        grow_id = getattr(ctx, "grow_id", "default")
        timestamp = datetime.now(timezone.utc).isoformat()
        if hasattr(ctx, "to_status_dict"):
            data = json.dumps(ctx.to_status_dict())
        else:
            data = json.dumps({"context": str(ctx)})

        try:
            await self._db.execute(
                "INSERT OR REPLACE INTO snapshots (grow_id, timestamp, data) "
                "VALUES (?, ?, ?)",
                (grow_id, timestamp, data),
            )
            await self._db.commit()
        except Exception as exc:
            logger.error("Failed to write snapshot: %s", exc)

    async def get_latest_snapshot(self, grow_id: str) -> dict | None:
        if not self._db:
            await self.connect()

        cursor = await self._db.execute(
            "SELECT data FROM snapshots WHERE grow_id = ? "
            "ORDER BY timestamp DESC LIMIT 1",
            (grow_id,),
        )
        row = await cursor.fetchone()
        return json.loads(row[0]) if row else None

    # ------------------------------------------------------------------ #
    # Sensor readings
    # ------------------------------------------------------------------ #

    async def insert_sensor_reading(self, reading: Any) -> None:
        if not self._db:
            await self.connect()

        ts = (
            reading.timestamp.isoformat()
            if hasattr(reading.timestamp, "isoformat")
            else str(reading.timestamp)
        )
        try:
            await self._db.execute(
                "INSERT INTO sensor_readings "
                "(timestamp, sensor_id, metric, value, unit, error) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (ts, reading.sensor_id, reading.metric, reading.value, reading.unit, reading.error),
            )
            await self._db.commit()
        except Exception as exc:
            logger.error("Failed to insert sensor reading: %s", exc)

    async def get_readings(
        self,
        sensor_id: str,
        start_time: datetime,
        end_time: datetime,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        if not self._db:
            await self.connect()

        start_iso = start_time.isoformat() if hasattr(start_time, "isoformat") else str(start_time)
        end_iso = end_time.isoformat() if hasattr(end_time, "isoformat") else str(end_time)

        query = (
            "SELECT timestamp, sensor_id, metric, value, unit, error "
            "FROM sensor_readings "
            "WHERE sensor_id = ? AND timestamp BETWEEN ? AND ? "
            "ORDER BY timestamp DESC"
        )
        params: list[Any] = [sensor_id, start_iso, end_iso]

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        cursor = await self._db.execute(query, params)
        rows = await cursor.fetchall()
        return [
            {
                "timestamp": r[0],
                "sensor_id": r[1],
                "metric": r[2],
                "value": r[3],
                "unit": r[4],
                "error": r[5],
            }
            for r in rows
        ]

    # ------------------------------------------------------------------ #
    # Events
    # ------------------------------------------------------------------ #

    async def insert_event(
        self,
        event_type: str,
        event_kind: str,
        message: str,
        timestamp: datetime,
        data: dict[str, Any] | None = None,
    ) -> None:
        if not self._db:
            await self.connect()

        grow_id = "default"
        ts = timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp)
        data_json = json.dumps(data or {})

        try:
            await self._db.execute(
                "INSERT INTO events "
                "(timestamp, grow_id, event_type, event_kind, message, data) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (ts, grow_id, event_type, event_kind, message, data_json),
            )
            await self._db.commit()
        except Exception as exc:
            logger.error("Failed to insert event: %s", exc)

    async def get_events(
        self,
        grow_id: str,
        start_time: datetime,
        end_time: datetime,
        event_kind: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        if not self._db:
            await self.connect()

        start_iso = start_time.isoformat() if hasattr(start_time, "isoformat") else str(start_time)
        end_iso = end_time.isoformat() if hasattr(end_time, "isoformat") else str(end_time)

        query = (
            "SELECT timestamp, grow_id, event_type, event_kind, message, data "
            "FROM events "
            "WHERE grow_id = ? AND timestamp BETWEEN ? AND ?"
        )
        params: list[Any] = [grow_id, start_iso, end_iso]

        if event_kind:
            query += " AND event_kind = ?"
            params.append(event_kind)

        query += " ORDER BY timestamp DESC"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        cursor = await self._db.execute(query, params)
        rows = await cursor.fetchall()
        return [
            {
                "timestamp": r[0],
                "grow_id": r[1],
                "event_type": r[2],
                "event_kind": r[3],
                "message": r[4],
                "data": json.loads(r[5]) if r[5] else {},
            }
            for r in rows
        ]

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None
