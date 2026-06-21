"""pyfarm-storage — persistence layer for pyfarm.

Provides:
  StorageBackend  — @runtime_checkable Protocol all backends implement
  NullBackend     — no-op backend (testing / dry-run)
  SQLiteBackend   — async SQLite backend via aiosqlite
  get_backend     — factory that reads env vars and returns the right backend
"""
from __future__ import annotations

from pyfarm.storage.backend import NullBackend, StorageBackend
from pyfarm.storage.factory import get_backend
from pyfarm.storage.sqlite import SQLiteBackend

__all__ = ["StorageBackend", "NullBackend", "SQLiteBackend", "get_backend"]
__version__ = "0.1.0"
