from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .common import DEFAULT_POWER_BACKFILL_DAYS, FULL_SYNC_FALLBACK_DAYS, detect_local_timezone_name, utc_now_iso
from .service_base import DashboardServiceBase
from .tesla_api import (
    extract_energy_sites,
    extract_history_rows,
    extract_installation_date,
    extract_site_name,
    unwrap_response,
)


@dataclass
class MonthSyncPlan:
    month_start: dt.datetime
    month_end: dt.datetime
    month_date: dt.date
    partial_month: bool
    finalized_csv_path: str
    needs_download: bool


@dataclass
class DaySyncPlan:
    day_start: dt.datetime
    day_end: dt.datetime
    day_date: dt.date
    partial_day: bool
    finalized_csv_path: str
    needs_download: bool


@dataclass
class SiteSyncPlan:
    site_id: str
    site_name: str
    time_zone: str
    month_windows: List[MonthSyncPlan]
    day_windows: List[DaySyncPlan]


class ServiceSyncMixin(DashboardServiceBase):
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
        total_steps = max(int(step_total or 0), 0)
        current_steps = max(int(step_current or 0), 0)
        if total_steps:
            current_steps = min(current_steps, total_steps)
        percent = round((current_steps / total_steps) * 100.0, 1) if total_steps else 0.0
        signature = "|".join([stage, label, message, str(current_steps), str(total_steps), str(bool(active)), error])
        should_log = False
        with self.sync_progress_lock:
            carry_started_at = self.sync_progress.get("started_at", "")
            self.sync_progress = {
                "active": bool(active),
                "stage": stage,
                "label": label,
                "message": message,
                "phase_current": max(int(phase_current or 0), 0),
                "phase_total": max(int(phase_total or 0), 0),
                "step_current": current_steps,
                "step_total": total_steps,
                "percent": percent,
                "started_at": started_at or carry_started_at,
                "updated_at": utc_now_iso(),
                "finished_at": finished_at or "",
                "error": error,
            }
            if signature != self._last_sync_log_signature:
                self._last_sync_log_signature = signature
                should_log = True
        if should_log:
            progress_suffix = f" [{current_steps}/{total_steps}, {percent:.1f}%]" if total_steps else ""
            line = f"[sync:{stage}] {label}{progress_suffix} {message}".strip()
            if stage == "error" or error:
                print(line, file=sys.stderr, flush=True)
            else:
                print(line, flush=True)

    def sync_progress_payload(self) -> Dict[str, Any]:
        with self.sync_progress_lock:
            return dict(self.sync_progress)

    def _cleanup_partial_energy_csvs(self, site_id: str) -> None:
        super()._cleanup_partial_energy_csvs(site_id)

    def _cleanup_partial_power_csvs(self, site_id: str) -> None:
        super()._cleanup_partial_power_csvs(site_id)

    def _build_site_sync_plan(
        self,
        tesla: Any,
        site: Dict[str, Any],
        config: Dict[str, Any],
        end_date: dt.date,
        fallback_start_date: dt.date,
        warning_messages: List[str],
    ) -> SiteSyncPlan:
        site_id = site["site_id"]
        fallback_zone = config.get("time_zone") or detect_local_timezone_name() or "UTC"
        cached_site = self._site_metadata_row(site_id)
        try:
            site_info = tesla.api("SITE_CONFIG", path_vars={"site_id": site_id})
            site_name = extract_site_name(site_info, site["site_name"])
            unwrapped_site_info = unwrap_response(site_info)
            time_zone = self._site_time_zone(unwrapped_site_info, fallback_zone)
            installation_date = extract_installation_date(unwrapped_site_info)
            self.upsert_site_metadata(site_id, site_name, time_zone, json.dumps(unwrapped_site_info, sort_keys=True))
        except Exception as error:
            raw_cached = {}
            if cached_site and cached_site.get("raw_json"):
                try:
                    raw_cached = json.loads(cached_site["raw_json"])
                except (TypeError, ValueError):
                    raw_cached = {}
            site_name = str((cached_site or {}).get("site_name") or site["site_name"])
            time_zone = str((cached_site or {}).get("time_zone") or fallback_zone)
            installation_date = extract_installation_date(raw_cached)
            warning_messages.append(f"Using cached site info for {site_name}: {error}")

        existing_archive_start = self._earliest_energy_archive_date(site_id)
        archive_start_date = installation_date or existing_archive_start or fallback_start_date
        archive_start_date = dt.date(archive_start_date.year, archive_start_date.month, 1)
        power_start_date = max(
            archive_start_date,
            end_date - dt.timedelta(days=DEFAULT_POWER_BACKFILL_DAYS - 1),
        )
        if installation_date is not None:
            power_start_date = max(power_start_date, installation_date)
        latest_power_date = self._latest_power_archive_date(site_id)
        if latest_power_date is not None:
            power_start_date = max(power_start_date, latest_power_date)

        self._cleanup_partial_energy_csvs(site_id)
        self._cleanup_partial_power_csvs(site_id)

        month_windows: List[MonthSyncPlan] = []
        for month_start, month_end in self._iter_energy_month_windows(archive_start_date, end_date, time_zone):
            month_date = month_start.date().replace(day=1)
            partial_month = month_date.year == end_date.year and month_date.month == end_date.month
            finalized_csv_path = self._energy_csv_path(site_id, month_date, partial_month=False)
            month_windows.append(
                MonthSyncPlan(
                    month_start=month_start,
                    month_end=month_end,
                    month_date=month_date,
                    partial_month=partial_month,
                    finalized_csv_path=finalized_csv_path,
                    needs_download=partial_month or not os.path.exists(finalized_csv_path),
                )
            )

        day_windows: List[DaySyncPlan] = []
        for day_start, day_end in self._iter_power_day_windows(power_start_date, end_date, time_zone):
            day_date = day_start.date()
            partial_day = day_date == end_date
            finalized_csv_path = self._power_csv_path(site_id, day_date, partial_day=False)
            day_windows.append(
                DaySyncPlan(
                    day_start=day_start,
                    day_end=day_end,
                    day_date=day_date,
                    partial_day=partial_day,
                    finalized_csv_path=finalized_csv_path,
                    needs_download=partial_day or not os.path.exists(finalized_csv_path),
                )
            )

        return SiteSyncPlan(
            site_id=site_id,
            site_name=site_name,
            time_zone=time_zone,
            month_windows=month_windows,
            day_windows=day_windows,
        )

    def _download_energy_month_csv(self, tesla: Any, site_plan: SiteSyncPlan, month_plan: MonthSyncPlan) -> str:
        time_series: List[Dict[str, Any]] = []
        last_error: Optional[Exception] = None
        for attempt in range(2):
            try:
                history_payload = tesla.api(
                    "CALENDAR_HISTORY_DATA",
                    path_vars={"site_id": site_plan.site_id},
                    kind="energy",
                    period="month",
                    start_date=month_plan.month_start.isoformat(),
                    end_date=month_plan.month_end.isoformat(),
                    time_zone=site_plan.time_zone,
                )
                time_series = extract_history_rows(history_payload)
                return self._write_energy_csv(
                    site_plan.site_id,
                    month_plan.month_date,
                    time_series,
                    partial_month=month_plan.partial_month,
                )
            except Exception as error:
                last_error = error
                if attempt == 0:
                    time.sleep(1)
        raise last_error if last_error is not None else RuntimeError("Monthly energy download failed.")

    def _download_power_day_csv(self, tesla: Any, site_plan: SiteSyncPlan, day_plan: DaySyncPlan) -> None:
        time_series: List[Dict[str, Any]] = []
        last_error: Optional[Exception] = None
        for attempt in range(2):
            try:
                history_payload = tesla.api(
                    "CALENDAR_HISTORY_DATA",
                    path_vars={"site_id": site_plan.site_id},
                    kind="power",
                    period="day",
                    start_date=day_plan.day_start.isoformat(),
                    end_date=day_plan.day_end.isoformat(),
                    time_zone=site_plan.time_zone,
                )
                time_series = extract_history_rows(history_payload)
                last_error = None
                break
            except Exception as error:
                last_error = error
                if attempt == 0:
                    time.sleep(1)
        if last_error is not None:
            raise last_error
        if time_series:
            self._write_power_csv(
                site_plan.site_id,
                day_plan.day_date,
                time_series,
                partial_day=day_plan.partial_day,
            )

    def sync(self, requested_site_id: Optional[str] = None) -> Dict[str, Any]:
        if not self.sync_lock.acquire(blocking=False):
            raise RuntimeError("A sync is already in progress.")
        sync_started_at = utc_now_iso()
        self.set_sync_state("last_sync_error", "")
        self._set_sync_progress(
            stage="preparing",
            label="Preparing Sync",
            message="Checking Tesla sign-in and local archive state...",
            active=True,
            started_at=sync_started_at,
        )
        try:
            if not self.auth_configured():
                raise RuntimeError("Sign in with Tesla before syncing.")

            config = self.load_config()
            end_date = dt.date.today()
            fallback_start_date = end_date - dt.timedelta(days=FULL_SYNC_FALLBACK_DAYS - 1)
            warning_messages: List[str] = []

            with self._tesla_session() as tesla:
                products_payload = tesla.api("PRODUCT_LIST")
                sites = extract_energy_sites(products_payload)
                configured_site_id = requested_site_id or config.get("energy_site_id")
                if configured_site_id:
                    sites = [site for site in sites if site["site_id"] == str(configured_site_id)] or [
                        {
                            "site_id": str(configured_site_id),
                            "site_name": f"Site {configured_site_id}",
                            "resource_type": "energy",
                            "raw": {},
                        }
                    ]
                if not sites:
                    raise RuntimeError("No Tesla energy sites were found for this account.")

                site_plans = [
                    self._build_site_sync_plan(tesla, site, config, end_date, fallback_start_date, warning_messages)
                    for site in sites
                ]
                total_download_steps = sum(
                    1
                    for site_plan in site_plans
                    for month_plan in site_plan.month_windows
                    if month_plan.needs_download
                ) + sum(
                    1
                    for site_plan in site_plans
                    for day_plan in site_plan.day_windows
                    if day_plan.needs_download
                )
                total_import_steps = sum(len(site_plan.month_windows) for site_plan in site_plans)
                total_steps = total_download_steps + total_import_steps
                downloaded_steps = 0
                imported_steps = 0

                if total_download_steps > 0:
                    self._set_sync_progress(
                        stage="downloading",
                        label="Downloading Data",
                        message=f"Downloading Tesla history for {total_download_steps} month(s)...",
                        active=True,
                        phase_current=0,
                        phase_total=total_download_steps,
                        step_current=0,
                        step_total=total_steps,
                        started_at=sync_started_at,
                    )
                else:
                    self._set_sync_progress(
                        stage="importing",
                        label="Importing Data",
                        message="No Tesla download needed. Using the local CSV archive.",
                        active=True,
                        phase_current=0,
                        phase_total=total_import_steps,
                        step_current=0,
                        step_total=total_steps,
                        started_at=sync_started_at,
                    )

                synced_sites = []
                for site_plan in site_plans:
                    imported_row_count = 0
                    for month_plan in site_plan.month_windows:
                        month_label = month_plan.month_date.strftime("%Y-%m")
                        if month_plan.needs_download:
                            self._set_sync_progress(
                                stage="downloading",
                                label="Downloading Data",
                                message=f"{site_plan.site_name} {month_label}: downloading monthly history from Tesla...",
                                active=True,
                                phase_current=downloaded_steps,
                                phase_total=total_download_steps,
                                step_current=downloaded_steps + imported_steps,
                                step_total=total_steps,
                                started_at=sync_started_at,
                            )
                            csv_path = self._download_energy_month_csv(tesla, site_plan, month_plan)
                            downloaded_steps += 1
                        else:
                            csv_path = month_plan.finalized_csv_path

                        self._set_sync_progress(
                            stage="importing",
                            label="Importing Data",
                            message=f"{site_plan.site_name} {month_label}: importing CSV into SQLite...",
                            active=True,
                            phase_current=imported_steps,
                            phase_total=total_import_steps,
                            step_current=downloaded_steps + imported_steps,
                            step_total=total_steps,
                            started_at=sync_started_at,
                        )
                        imported_row_count += self._import_energy_csv(site_plan.site_id, csv_path)
                        imported_steps += 1

                    for day_plan in site_plan.day_windows:
                        if not day_plan.needs_download:
                            continue
                        day_label = day_plan.day_date.strftime("%Y-%m-%d")
                        self._set_sync_progress(
                            stage="downloading",
                            label="Downloading Data",
                            message=f"{site_plan.site_name} {day_label}: downloading intraday power from Tesla...",
                            active=True,
                            phase_current=downloaded_steps,
                            phase_total=total_download_steps,
                            step_current=downloaded_steps + imported_steps,
                            step_total=total_steps,
                            started_at=sync_started_at,
                        )
                        try:
                            self._download_power_day_csv(tesla, site_plan, day_plan)
                        except Exception as error:
                            warning_messages.append(
                                f"{site_plan.site_name} {day_label}: intraday power download skipped ({error})"
                            )
                        downloaded_steps += 1

                    synced_sites.append(
                        {
                            "site_id": site_plan.site_id,
                            "site_name": site_plan.site_name,
                            "time_zone": site_plan.time_zone,
                            "row_count": imported_row_count,
                            "download_root": os.path.join(self.download_root, str(site_plan.site_id), "energy"),
                            "power_root": os.path.join(self.download_root, str(site_plan.site_id), "power"),
                        }
                    )

            synced_at = utc_now_iso()
            self.set_sync_state("last_sync", synced_at)
            self.set_sync_state("last_sync_error", "")
            completion_message = f"Finished syncing {len(synced_sites)} site(s)."
            if warning_messages:
                completion_message = (
                    f"{completion_message} {len(warning_messages)} warning(s); intraday data may still be catching up."
                )
            self._set_sync_progress(
                stage="complete",
                label="Sync Complete",
                message=completion_message,
                active=False,
                phase_current=total_steps,
                phase_total=total_steps,
                step_current=total_steps,
                step_total=total_steps,
                started_at=sync_started_at,
                finished_at=synced_at,
            )
            return {"synced_at": synced_at, "sites": synced_sites}
        except Exception as error:
            self.set_sync_state("last_sync_error", str(error))
            self._set_sync_progress(
                stage="error",
                label="Sync Failed",
                message=str(error),
                active=False,
                started_at=sync_started_at,
                finished_at=utc_now_iso(),
                error=str(error),
            )
            raise
        finally:
            self.sync_lock.release()
