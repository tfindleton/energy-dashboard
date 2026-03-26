from __future__ import annotations

import os
import sqlite3
import threading
from typing import Any, Callable, Dict, Optional

from .common import default_download_root_for_db_path
from .scheduler import DEFAULT_SYNC_CRON, normalize_sync_cron
from .service_archive import ServiceArchiveMixin
from .service_auth import ServiceAuthMixin
from .service_sync import ServiceSyncMixin
from .service_views import ServiceViewsMixin
from .tesla_api import extract_history_rows, extract_installation_date, extract_site_name, extract_timezone

__all__ = ["TeslaSolarDashboard", "extract_history_rows", "extract_installation_date", "extract_site_name", "extract_timezone"]


class TeslaSolarDashboard(ServiceSyncMixin, ServiceViewsMixin, ServiceArchiveMixin, ServiceAuthMixin):
    def __init__(self, db_path: str, config_path: str, download_root: Optional[str] = None) -> None:
        self.db_path = db_path
        self.config_path = config_path
        self.download_root = os.path.abspath(download_root or default_download_root_for_db_path(db_path))
        self.sync_lock = threading.Lock()
        self.sync_progress_lock = threading.Lock()
        self.archive_refresh_lock = threading.Lock()
        self.auto_sync_enabled = False
        self.auto_sync_description = ""
        self.auto_sync_next_run: Optional[str] = None
        self.auto_sync_site_id: Optional[str] = None
        self.sync_cron_default = normalize_sync_cron(DEFAULT_SYNC_CRON)
        self.sync_schedule_refresh: Optional[Callable[[], None]] = None
        self.config_warning = ""
        self._last_sync_log_signature = ""
        self.sync_progress: Dict[str, Any] = {
            "active": False,
            "stage": "idle",
            "label": "",
            "message": "",
            "phase_current": 0,
            "phase_total": 0,
            "step_current": 0,
            "step_total": 0,
            "percent": 0.0,
            "started_at": "",
            "updated_at": "",
            "finished_at": "",
            "error": "",
        }
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS site_metadata (
                    site_id TEXT PRIMARY KEY,
                    site_name TEXT NOT NULL,
                    time_zone TEXT,
                    raw_json TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS daily_energy (
                    site_id TEXT NOT NULL,
                    bucket_date TEXT NOT NULL,
                    solar_generation_wh REAL NOT NULL DEFAULT 0,
                    home_usage_wh REAL NOT NULL DEFAULT 0,
                    grid_import_wh REAL NOT NULL DEFAULT 0,
                    grid_export_wh REAL NOT NULL DEFAULT 0,
                    raw_json TEXT,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (site_id, bucket_date)
                );

                CREATE TABLE IF NOT EXISTS sync_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS archive_import_state (
                    site_id TEXT NOT NULL,
                    csv_path TEXT NOT NULL,
                    mtime_ns INTEGER NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    imported_at TEXT NOT NULL,
                    PRIMARY KEY (site_id, csv_path)
                );
                """
            )
