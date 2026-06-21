"""StorageBackend protocol and NullBackend."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class StorageBackend(Protocol):
    """
    Async persistence interface for pyfarm.

    Three orthogonal concerns:
    - Snapshots: full control context for crash recovery
    - Readings: time-series sensor data for analytics
    - Events: audit trail of control/analytics/commerce events
    """

    async def write_snapshot(self, ctx: Any) -> None:
        """Persist a control context snapshot from the runner."""
        ...

    async def get_latest_snapshot(self, grow_id: str) -> dict | None:
        """Retrieve the most recent control context snapshot for a grow."""
        ...

    async def insert_sensor_reading(self, reading: Any) -> None:
        """Record a sensor reading (temperature, pH, EC, PPFD, etc.)."""
        ...

    async def get_readings(
        self,
        sensor_id: str,
        start_time: datetime,
        end_time: datetime,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Query sensor readings in a time range."""
        ...

    async def insert_event(
        self,
        event_type: str,
        event_kind: str,
        message: str,
        timestamp: datetime,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Log a control/analytics/commerce event."""
        ...

    async def get_events(
        self,
        grow_id: str,
        start_time: datetime,
        end_time: datetime,
        event_kind: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Query events for a grow in a time range."""
        ...

    async def close(self) -> None:
        """Release connections/resources."""
        ...


class NullBackend:
    """No-op storage — does nothing, returns empty results. Useful for tests."""

    async def write_snapshot(self, ctx: Any) -> None:
        pass

    async def get_latest_snapshot(self, grow_id: str) -> dict | None:
        return None

    async def insert_sensor_reading(self, reading: Any) -> None:
        pass

    async def get_readings(
        self,
        sensor_id: str,
        start_time: datetime,
        end_time: datetime,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        return []

    async def insert_event(
        self,
        event_type: str,
        event_kind: str,
        message: str,
        timestamp: datetime,
        data: dict[str, Any] | None = None,
    ) -> None:
        pass

    async def get_events(
        self,
        grow_id: str,
        start_time: datetime,
        end_time: datetime,
        event_kind: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        return []

    async def close(self) -> None:
        pass
