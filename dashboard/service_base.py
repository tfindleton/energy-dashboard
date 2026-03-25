from __future__ import annotations

import datetime as dt
import sqlite3
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple


class DashboardServiceBase:
    db_path: str
    config_path: str
    download_root: str
    sync_lock: Any
    sync_progress_lock: Any
    archive_refresh_lock: Any
    auto_sync_enabled: bool
    auto_sync_description: str
    auto_sync_next_run: Optional[str]
    auto_sync_site_id: Optional[str]
    sync_cron_default: str
    sync_schedule_refresh: Optional[Callable[[], None]]
    config_warning: str
    _last_sync_log_signature: str
    sync_progress: Dict[str, Any]

    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def load_config(self) -> Dict[str, Any]:
        raise NotImplementedError

    def save_config(self, config: Dict[str, Any]) -> None:
        raise NotImplementedError

    def effective_sync_cron(self, default_sync_cron: Optional[str] = None) -> str:
        raise NotImplementedError

    def _notify_sync_schedule_changed(self) -> None:
        raise NotImplementedError

    def teslapy_available(self) -> bool:
        raise NotImplementedError

    def config_public_payload(self) -> Dict[str, Any]:
        raise NotImplementedError

    def save_user_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def save_sync_settings(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def missing_login_fields(self, config: Optional[Dict[str, Any]] = None) -> List[str]:
        raise NotImplementedError

    def auth_login_ready(self) -> bool:
        raise NotImplementedError

    def auth_configured(self) -> bool:
        raise NotImplementedError

    def _tesla_session(
        self,
        email: Optional[str] = None,
        state: Optional[str] = None,
        code_verifier: Optional[str] = None,
    ) -> Any:
        raise NotImplementedError

    def _site_metadata_row(self, site_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def _site_time_zone(self, site_config: Dict[str, Any], fallback: str) -> str:
        raise NotImplementedError

    def _iter_energy_month_windows(
        self,
        start_date: dt.date,
        end_date: dt.date,
        time_zone: str,
    ) -> Iterable[Tuple[dt.datetime, dt.datetime]]:
        raise NotImplementedError

    def _iter_power_day_windows(
        self,
        start_date: dt.date,
        end_date: dt.date,
        time_zone: str,
    ) -> Iterable[Tuple[dt.datetime, dt.datetime]]:
        raise NotImplementedError

    def _energy_csv_path(self, site_id: str, month_date: dt.date, partial_month: bool = False) -> str:
        raise NotImplementedError

    def _power_csv_path(self, site_id: str, day_date: dt.date, partial_day: bool = False) -> str:
        raise NotImplementedError

    def _existing_power_csv_path(self, site_id: str, day_date: dt.date) -> Optional[str]:
        raise NotImplementedError

    def _latest_power_archive_date(self, site_id: str) -> Optional[dt.date]:
        raise NotImplementedError

    def _earliest_energy_archive_date(self, site_id: str) -> Optional[dt.date]:
        raise NotImplementedError

    def _read_power_day_csv(self, site_id: str, day_date: dt.date, metric: str) -> Dict[str, Any]:
        raise NotImplementedError

    def _cleanup_partial_energy_csvs(self, site_id: str) -> None:
        raise NotImplementedError

    def _cleanup_partial_power_csvs(self, site_id: str) -> None:
        raise NotImplementedError

    def refresh_archive_cache(self) -> int:
        raise NotImplementedError

    def _write_energy_csv(
        self,
        site_id: str,
        month_date: dt.date,
        time_series: Sequence[Dict[str, Any]],
        partial_month: bool = False,
    ) -> str:
        raise NotImplementedError

    def _write_power_csv(
        self,
        site_id: str,
        day_date: dt.date,
        time_series: Sequence[Dict[str, Any]],
        partial_day: bool = False,
    ) -> str:
        raise NotImplementedError

    def _import_energy_csv(self, site_id: str, csv_path: str) -> int:
        raise NotImplementedError

    def upsert_site_metadata(self, site_id: str, site_name: str, time_zone: str, raw_json: str) -> None:
        raise NotImplementedError

    def upsert_daily_rows(self, site_id: str, rows: Sequence[Dict[str, Any]]) -> None:
        raise NotImplementedError

    def set_sync_state(self, key: str, value: str) -> None:
        raise NotImplementedError

    def get_sync_state(self, key: str) -> Optional[str]:
        raise NotImplementedError

    def _set_sync_progress(
        self,
        *,
        stage: str,
        label: str,
        message: str,
        active: bool,
        phase_current: int = 0,
        phase_total: int = 0,
        step_current: int = 0,
        step_total: int = 0,
        started_at: Optional[str] = None,
        finished_at: Optional[str] = None,
        error: str = "",
    ) -> None:
        raise NotImplementedError

    def sync_progress_payload(self) -> Dict[str, Any]:
        raise NotImplementedError

    def query_site_rows(
        self,
        site_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def list_sites(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def default_site_id(self) -> str:
        raise NotImplementedError

    def site_or_error(self, site_id: str) -> Dict[str, Any]:
        raise NotImplementedError
