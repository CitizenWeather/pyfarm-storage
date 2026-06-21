"""Smoke tests for pyfarm-storage."""
from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

from pyfarm.storage import NullBackend, SQLiteBackend, StorageBackend, get_backend
from pyfarm.storage.backend import StorageBackend as BackendProtocol


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------

def test_null_backend_is_storage_backend():
    assert isinstance(NullBackend(), StorageBackend)


# ---------------------------------------------------------------------------
# NullBackend
# ---------------------------------------------------------------------------

async def test_null_backend_write_snapshot_no_error():
    nb = NullBackend()
    await nb.write_snapshot(object())


async def test_null_backend_get_latest_snapshot_returns_none():
    nb = NullBackend()
    assert await nb.get_latest_snapshot("grow-1") is None


async def test_null_backend_get_readings_returns_empty():
    nb = NullBackend()
    now = datetime.now(timezone.utc)
    result = await nb.get_readings("s1", now, now)
    assert result == []


async def test_null_backend_get_events_returns_empty():
    nb = NullBackend()
    now = datetime.now(timezone.utc)
    result = await nb.get_events("grow-1", now, now)
    assert result == []


async def test_null_backend_close_no_error():
    nb = NullBackend()
    await nb.close()


# ---------------------------------------------------------------------------
# get_backend factory
# ---------------------------------------------------------------------------

def test_get_backend_null():
    b = get_backend("null")
    assert isinstance(b, NullBackend)


def test_get_backend_unknown_raises():
    with pytest.raises(ValueError, match="Unknown storage backend"):
        get_backend("unknown")


def test_get_backend_env_null(monkeypatch):
    monkeypatch.setenv("PYFARM_STORAGE_BACKEND", "null")
    b = get_backend()
    assert isinstance(b, NullBackend)


def test_get_backend_sqlite_returns_sqlite_backend(tmp_path):
    b = get_backend("sqlite", db_path=str(tmp_path / "test.db"))
    assert isinstance(b, SQLiteBackend)


# ---------------------------------------------------------------------------
# SQLiteBackend
# ---------------------------------------------------------------------------

async def test_sqlite_backend_connect_and_close(tmp_path):
    b = SQLiteBackend(tmp_path / "test.db")
    await b.connect()
    await b.close()


async def test_sqlite_backend_snapshot_round_trip(tmp_path):
    b = SQLiteBackend(tmp_path / "test.db")

    class FakeCtx:
        grow_id = "grow-42"

        def to_status_dict(self):
            return {"stage": 1, "grow_id": self.grow_id}

    await b.write_snapshot(FakeCtx())
    snap = await b.get_latest_snapshot("grow-42")
    assert snap is not None
    assert snap["grow_id"] == "grow-42"
    await b.close()


async def test_sqlite_backend_events_round_trip(tmp_path):
    b = SQLiteBackend(tmp_path / "test.db")
    now = datetime.now(timezone.utc)

    await b.insert_event("control", "sensor_alert", "temp high", now, {"value": 35})

    events = await b.get_events("default", now, now)
    assert len(events) == 1
    assert events[0]["event_kind"] == "sensor_alert"
    assert events[0]["data"]["value"] == 35
    await b.close()


async def test_sqlite_backend_get_latest_snapshot_empty(tmp_path):
    b = SQLiteBackend(tmp_path / "test.db")
    result = await b.get_latest_snapshot("nonexistent")
    assert result is None
    await b.close()
