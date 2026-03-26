from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional, Sequence

from . import __version__
from .common import DAY_COMPARE_DAILY_TOTAL_COLUMNS, parse_dateish, parse_datetime, utc_now
from .payloads import (
    build_comparison_payload,
    build_day_compare_payload,
    build_diagnostics_payload,
    build_insights_payload,
    build_trend_payload,
    build_weekday_pattern_payload,
)
from .scheduler import latest_scheduled_sync_utc
from .service_base import DashboardServiceBase


class ServiceViewsMixin(DashboardServiceBase):
    def query_site_rows(
        self,
        site_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        sql = """
            SELECT bucket_date, solar_generation_wh, home_usage_wh, grid_import_wh, grid_export_wh
            FROM daily_energy
            WHERE site_id = ?
        """
        params: List[Any] = [site_id]
        if start_date:
            sql += " AND bucket_date >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND bucket_date <= ?"
            params.append(end_date)
        sql += " ORDER BY bucket_date"
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def list_sites(self) -> List[Dict[str, Any]]:
        self.refresh_archive_cache()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    m.site_id,
                    m.site_name,
                    m.time_zone,
                    MIN(d.bucket_date) AS data_start,
                    MAX(d.bucket_date) AS data_end,
                    COUNT(d.bucket_date) AS row_count
                FROM site_metadata m
                LEFT JOIN daily_energy d ON d.site_id = m.site_id
                GROUP BY m.site_id, m.site_name, m.time_zone
                ORDER BY m.site_name
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def default_site_id(self) -> str:
        configured = self.load_config().get("energy_site_id")
        if configured:
            return str(configured)
        sites = self.list_sites()
        return sites[0]["site_id"] if sites else ""

    def status_payload(self) -> Dict[str, Any]:
        sites = self.list_sites()
        config = self.load_config()
        missing_login_fields = self.missing_login_fields(config)
        last_sync = self.get_sync_state("last_sync")
        last_sync_at = parse_datetime(last_sync)
        sync_cron = self.effective_sync_cron()
        missed_sync_at: Optional[dt.datetime] = None
        if self.auto_sync_enabled and not self.sync_lock.locked():
            last_due = latest_scheduled_sync_utc(sync_cron, now=utc_now())
            if last_due and (last_sync_at is None or last_sync_at < last_due):
                missed_sync_at = last_due
        today = dt.date.today()
        default_anchor = today.isoformat()
        default_trend_start = (today - dt.timedelta(days=365)).isoformat()
        if sites and sites[0].get("data_end"):
            data_end_value = str(sites[0]["data_end"])
            default_anchor = data_end_value
            data_end = parse_dateish(data_end_value)
            data_start = parse_dateish(sites[0].get("data_start"))
            if data_end is not None:
                start_candidate = data_end - dt.timedelta(days=365)
                default_trend_start = (
                    max(data_start, start_candidate).isoformat()
                    if data_start is not None
                    else start_candidate.isoformat()
                )
        if not self.teslapy_available():
            message = "Install requirements first: `pip install -r requirements.txt`."
        elif sites:
            message = ""
        elif missing_login_fields:
            message = "Enter your Tesla account email, then start sign-in."
        elif not self.auth_configured():
            if config.get("pending_auth"):
                message = "Tesla login is in progress. Paste the final Tesla URL to finish sign-in."
            else:
                message = "Start Sign In, complete Tesla login, then paste the final Tesla URL here."
        else:
            message = "No cached data yet. Run sync to import history."
        if self.config_warning:
            message = f"{self.config_warning} {message}".strip()
        return {
            "version": __version__,
            "library_ready": self.teslapy_available(),
            "auth_configured": self.auth_configured(),
            "auth_login_ready": self.auth_login_ready(),
            "auth_pending": bool(config.get("pending_auth")),
            "config": self.config_public_payload(),
            "sync_in_progress": self.sync_lock.locked(),
            "sync_progress": self.sync_progress_payload(),
            "last_sync": last_sync,
            "last_sync_error": self.get_sync_state("last_sync_error"),
            "auto_sync_enabled": self.auto_sync_enabled,
            "auto_sync_cron": sync_cron,
            "auto_sync_description": self.auto_sync_description,
            "auto_sync_next_run": self.auto_sync_next_run,
            "auto_sync_missed": bool(missed_sync_at),
            "auto_sync_missed_since": (
                missed_sync_at.replace(microsecond=0).isoformat().replace("+00:00", "Z")
                if missed_sync_at is not None
                else None
            ),
            "auto_sync_site_id": self.auto_sync_site_id,
            "sites": sites,
            "selected_site_id": self.default_site_id(),
            "default_anchor_date": default_anchor,
            "default_trend_start": default_trend_start,
            "message": message,
        }

    def comparison_payload(self, site_id: str, mode: str, anchor: str, years: int) -> Dict[str, Any]:
        site = self.site_or_error(site_id)
        anchor_date = parse_dateish(anchor)
        if anchor_date is None:
            raise RuntimeError("Anchor date is required.")
        rows = self.query_site_rows(site_id)
        payload = build_comparison_payload(rows, mode, anchor_date, years)
        payload["site"] = {"site_id": site["site_id"], "site_name": site["site_name"]}
        return payload

    def trend_payload(
        self,
        site_id: str,
        start_date: str,
        end_date: str,
        granularity: str,
        metrics: Sequence[str],
    ) -> Dict[str, Any]:
        site = self.site_or_error(site_id)
        start = parse_dateish(start_date)
        end = parse_dateish(end_date)
        if start is None or end is None:
            raise RuntimeError("Start and end dates are required.")
        if end < start:
            raise RuntimeError("End date must be on or after start date.")
        rows = self.query_site_rows(site_id, start.isoformat(), end.isoformat())
        payload = build_trend_payload(rows, start, end, granularity, metrics)
        payload["site"] = {"site_id": site["site_id"], "site_name": site["site_name"]}
        payload["start_date"] = start.isoformat()
        payload["end_date"] = end.isoformat()
        payload["granularity"] = granularity
        return payload

    def weekday_pattern_payload(
        self,
        site_id: str,
        start_date: str,
        end_date: str,
        metrics: Sequence[str],
        value_mode: str,
    ) -> Dict[str, Any]:
        site = self.site_or_error(site_id)
        start = parse_dateish(start_date)
        end = parse_dateish(end_date)
        if start is None or end is None:
            raise RuntimeError("Start and end dates are required.")
        if end < start:
            raise RuntimeError("End date must be on or after start date.")
        rows = self.query_site_rows(site_id, start.isoformat(), end.isoformat())
        payload = build_weekday_pattern_payload(rows, start, end, metrics, value_mode=value_mode)
        payload["site"] = {"site_id": site["site_id"], "site_name": site["site_name"]}
        payload["start_date"] = start.isoformat()
        payload["end_date"] = end.isoformat()
        return payload

    def day_compare_payload(
        self,
        site_id: str,
        dates: Sequence[str],
        metric: str,
    ) -> Dict[str, Any]:
        site = self.site_or_error(site_id)
        selected_dates: List[dt.date] = []
        seen = set()
        for raw_value in dates:
            parsed = parse_dateish(raw_value)
            if parsed is None:
                continue
            if parsed.isoformat() in seen:
                continue
            selected_dates.append(parsed)
            seen.add(parsed.isoformat())
        if not selected_dates:
            raise RuntimeError("At least one day is required.")
        if len(selected_dates) > 10:
            raise RuntimeError("Pick up to 10 days for day compare.")

        metric_total_column = DAY_COMPARE_DAILY_TOTAL_COLUMNS.get(metric)
        daily_totals_by_date: Dict[str, float] = {}
        if metric_total_column and selected_dates:
            daily_rows = self.query_site_rows(
                site["site_id"],
                min(selected_dates).isoformat(),
                max(selected_dates).isoformat(),
            )
            daily_totals_by_date = {
                str(row["bucket_date"]): round(float(row.get(metric_total_column) or 0.0) / 1000.0, 2)
                for row in daily_rows
            }

        loaded_series = []
        missing_dates = []
        for day_date in selected_dates:
            try:
                series = self._read_power_day_csv(site["site_id"], day_date, metric)
                total_kwh = daily_totals_by_date.get(day_date.isoformat())
                if total_kwh is not None:
                    series["total_kwh"] = total_kwh
                    series["total_source"] = "energy"
                loaded_series.append(series)
            except FileNotFoundError:
                missing_dates.append(day_date.isoformat())
        if not loaded_series:
            raise RuntimeError("No intraday power CSVs were found for the selected days.")
        payload = build_day_compare_payload(loaded_series, metric)
        payload["site"] = {"site_id": site["site_id"], "site_name": site["site_name"]}
        payload["selected_dates"] = [day.isoformat() for day in selected_dates]
        payload["missing_dates"] = missing_dates
        return payload

    def insights_payload(self, site_id: str) -> Dict[str, Any]:
        site = self.site_or_error(site_id)
        rows = self.query_site_rows(site["site_id"])
        payload = build_insights_payload(rows)
        payload["site"] = {"site_id": site["site_id"], "site_name": site["site_name"]}
        return payload

    def diagnostics_payload(self, site_id: str) -> Dict[str, Any]:
        site = self.site_or_error(site_id)
        rows = self.query_site_rows(site["site_id"])
        payload = build_diagnostics_payload(rows)
        payload["site"] = {"site_id": site["site_id"], "site_name": site["site_name"]}
        return payload

    def site_or_error(self, site_id: str) -> Dict[str, Any]:
        selected_id = site_id or self.default_site_id()
        if not selected_id:
            raise RuntimeError("No Tesla energy site is available yet.")
        for site in self.list_sites():
            if site["site_id"] == selected_id:
                return site
        raise RuntimeError(f"Unknown site: {selected_id}")
