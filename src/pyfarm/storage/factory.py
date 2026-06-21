"""Backend factory for pyfarm-storage."""
from __future__ import annotations

import os

from pyfarm.storage.backend import NullBackend, StorageBackend


def get_backend(
    backend: str | None = None,
    db_path: str | None = None,
) -> StorageBackend:
    """Return a configured :class:`StorageBackend` instance.

    Selection order (highest priority first):
    1. The explicit ``backend`` argument.
    2. The ``PYFARM_STORAGE_BACKEND`` environment variable.
    3. Default: ``"sqlite"``.

    Args:
        backend: ``"sqlite"`` or ``"null"``.
        db_path: SQLite database path (default: ``PYFARM_DB_PATH`` env var or
            ``"pyfarm.db"``). Ignored when backend is ``"null"``.
    """
    choice = (backend or os.environ.get("PYFARM_STORAGE_BACKEND") or "sqlite").lower()

    if choice == "null":
        return NullBackend()

    if choice == "sqlite":
        from pyfarm.storage.sqlite import SQLiteBackend

        path = db_path or os.environ.get("PYFARM_DB_PATH") or "pyfarm.db"
        return SQLiteBackend(path)

    raise ValueError(
        f"Unknown storage backend {choice!r}. Expected 'sqlite' or 'null'."
    )
