from __future__ import annotations

import calendar
import csv
import datetime as dt
import os
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .common import (
    ARCHIVE_IMPORT_SCHEMA_VERSION,
    DAY_COMPARE_METRICS,
    aggregate_daily_history_rows,
    detect_local_timezone_name,
    fieldnames_from_rows,
    flatten_history_row_for_csv,
    flatten_power_row_for_csv,
    normalize_history_row,
    parse_dateish,
    resolve_tzinfo,
    utc_now_iso,
)
from .service_base import DashboardServiceBase


class ServiceArchiveMixin(DashboardServiceBase):
    def _site_time_zone(self, site_config: Dict[str, Any], fallback: str) -> str:
        if isinstance(site_config.get("installation_time_zone"), str):
            return site_config["installation_time_zone"]
        return fallback

    def _iter_energy_month_windows(
        self,
        start_date: dt.date,
        end_date: dt.date,
        time_zone: str,
    ) -> Iterable[Tuple[dt.datetime, dt.datetime]]:
        tzinfo = resolve_tzinfo(time_zone)
        cursor = dt.date(start_date.year, start_date.month, 1)
        final_month = dt.date(end_date.year, end_date.month, 1)
        while cursor <= final_month:
            month_start_date = max(cursor, start_date)
            month_end_date = min(
                dt.date(cursor.year, cursor.month, calendar.monthrange(cursor.year, cursor.month)[1]),
                end_date,
            )
            yield (
                dt.datetime.combine(month_start_date, dt.time.min, tzinfo=tzinfo),
                dt.datetime.combine(month_end_date, dt.time(23, 59, 59), tzinfo=tzinfo),
            )
            if cursor.month == 12:
                cursor = dt.date(cursor.year + 1, 1, 1)
            else:
                cursor = dt.date(cursor.year, cursor.month + 1, 1)

    def _iter_power_day_windows(
        self,
        start_date: dt.date,
        end_date: dt.date,
        time_zone: str,
    ) -> Iterable[Tuple[dt.datetime, dt.datetime]]:
        tzinfo = resolve_tzinfo(time_zone)
        cursor = start_date
        while cursor <= end_date:
            yield (
                dt.datetime.combine(cursor, dt.time.min, tzinfo=tzinfo),
                dt.datetime.combine(cursor, dt.time(23, 59, 59), tzinfo=tzinfo),
            )
            cursor += dt.timedelta(days=1)

    def _energy_csv_path(self, site_id: str, month_date: dt.date, partial_month: bool = False) -> str:
        filename = month_date.strftime("%Y-%m")
        suffix = ".partial.csv" if partial_month else ".csv"
        return os.path.join(self.download_root, str(site_id), "energy", f"{filename}{suffix}")

    def _power_csv_path(self, site_id: str, day_date: dt.date, partial_day: bool = False) -> str:
        filename = day_date.strftime("%Y-%m-%d")
        suffix = ".partial.csv" if partial_day else ".csv"
        return os.path.join(self.download_root, str(site_id), "power", f"{filename}{suffix}")

    def _existing_power_csv_path(self, site_id: str, day_date: dt.date) -> Optional[str]:
        exact = self._power_csv_path(site_id, day_date, partial_day=False)
        if os.path.exists(exact):
            return exact
        partial = self._power_csv_path(site_id, day_date, partial_day=True)
        if os.path.exists(partial):
            return partial
        return None

    def _latest_power_archive_date(self, site_id: str) -> Optional[dt.date]:
        power_dir = os.path.join(self.download_root, str(site_id), "power")
        if not os.path.isdir(power_dir):
            return None
        latest_date: Optional[dt.date] = None
        for filename in os.listdir(power_dir):
            if not filename.endswith(".csv"):
                continue
            parsed = parse_dateish(filename[:10])
            if parsed is None:
                continue
            if latest_date is None or parsed > latest_date:
                latest_date = parsed
        return latest_date

    def _earliest_energy_archive_date(self, site_id: str) -> Optional[dt.date]:
        energy_dir = os.path.join(self.download_root, str(site_id), "energy")
        if not os.path.isdir(energy_dir):
            return None
        earliest_date: Optional[dt.date] = None
        for filename in os.listdir(energy_dir):
            if not filename.endswith(".csv") or len(filename) < 7:
                continue
            parsed = parse_dateish(f"{filename[:7]}-01")
            if parsed is None:
                continue
            if earliest_date is None or parsed < earliest_date:
                earliest_date = parsed
        return earliest_date

    def _site_metadata_row(self, site_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT site_id, site_name, time_zone, raw_json, updated_at
                FROM site_metadata
                WHERE site_id = ?
                """,
                (site_id,),
            ).fetchone()
        return dict(row) if row else None

    def _read_power_day_csv(self, site_id: str, day_date: dt.date, metric: str) -> Dict[str, Any]:
        if metric not in DAY_COMPARE_METRICS:
            raise RuntimeError("Unsupported day-compare metric.")
        csv_path = self._existing_power_csv_path(site_id, day_date)
        if csv_path is None:
            raise FileNotFoundError(day_date.isoformat())
        values_by_time: Dict[str, float] = {}
        sample_count = 0
        total_kwh = 0.0
        peak_kw = 0.0
        peak_time = ""
        with open(csv_path, "r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if not row or not any((value or "").strip() for value in row.values() if isinstance(value, str)):
                    continue
                timestamp_text = str(row.get("timestamp", "") or "").strip()
                if not timestamp_text:
                    continue
                try:
                    timestamp = dt.datetime.fromisoformat(timestamp_text.replace("T", " "))
                except ValueError:
                    continue
                grid_power = float(str(row.get("grid_power", "0") or "0").strip() or "0")
                if metric == "grid_import_power":
                    metric_value = max(grid_power, 0.0)
                elif metric == "grid_export_power":
                    metric_value = max(-grid_power, 0.0)
                else:
                    metric_value = float(str(row.get(metric, "0") or "0").strip() or "0")
                label = timestamp.strftime("%H:%M")
                value_kw = metric_value / 1000.0
                values_by_time[label] = round(value_kw, 3)
                sample_count += 1
                total_kwh += metric_value * (5.0 / 60.0) / 1000.0
                if value_kw > peak_kw:
                    peak_kw = value_kw
                    peak_time = label
        return {
            "date": day_date.isoformat(),
            "label": f"{day_date.strftime('%b %d, %Y')}{' (partial)' if csv_path.endswith('.partial.csv') else ''}",
            "values_by_time": values_by_time,
            "sample_count": sample_count,
            "total_kwh": round(total_kwh, 2),
            "estimated_total_kwh": round(total_kwh, 2),
            "total_source": "estimated",
            "peak_kw": round(peak_kw, 2),
            "peak_time": peak_time,
            "partial": csv_path.endswith(".partial.csv"),
        }

    def _archive_csv_files(self) -> List[Tuple[str, str]]:
        if not os.path.isdir(self.download_root):
            return []
        matches: List[Tuple[str, str]] = []
        for site_id in sorted(os.listdir(self.download_root)):
            energy_dir = os.path.join(self.download_root, site_id, "energy")
            if not os.path.isdir(energy_dir):
                continue
            for filename in sorted(os.listdir(energy_dir)):
                if not filename.endswith(".csv"):
                    continue
                matches.append((site_id, os.path.join(energy_dir, filename)))
        return matches

    def _cleanup_partial_energy_csvs(self, site_id: str) -> None:
        energy_dir = os.path.join(self.download_root, str(site_id), "energy")
        if not os.path.isdir(energy_dir):
            return
        for filename in os.listdir(energy_dir):
            if filename.endswith(".partial.csv"):
                os.remove(os.path.join(energy_dir, filename))

    def _cleanup_partial_power_csvs(self, site_id: str) -> None:
        power_dir = os.path.join(self.download_root, str(site_id), "power")
        if not os.path.isdir(power_dir):
            return
        for filename in os.listdir(power_dir):
            if filename.endswith(".partial.csv"):
                os.remove(os.path.join(power_dir, filename))

    def _archive_file_needs_import(self, site_id: str, csv_path: str) -> bool:
        stat = os.stat(csv_path)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT mtime_ns, size_bytes
                FROM archive_import_state
                WHERE site_id = ? AND csv_path = ?
                """,
                (site_id, csv_path),
            ).fetchone()
        if row is None:
            return True
        return int(row["mtime_ns"]) != int(stat.st_mtime_ns) or int(row["size_bytes"]) != int(stat.st_size)

    def _record_archive_import(self, site_id: str, csv_path: str) -> None:
        stat = os.stat(csv_path)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO archive_import_state (site_id, csv_path, mtime_ns, size_bytes, imported_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(site_id, csv_path) DO UPDATE SET
                    mtime_ns = excluded.mtime_ns,
                    size_bytes = excluded.size_bytes,
                    imported_at = excluded.imported_at
                """,
                (site_id, csv_path, int(stat.st_mtime_ns), int(stat.st_size), utc_now_iso()),
            )

    def _ensure_archive_import_schema(self) -> None:
        current_version = self.get_sync_state("archive_import_version")
        if current_version == ARCHIVE_IMPORT_SCHEMA_VERSION:
            return
        with self._connect() as connection:
            connection.execute("DELETE FROM archive_import_state")
        self.set_sync_state("archive_import_version", ARCHIVE_IMPORT_SCHEMA_VERSION)

    def _ensure_archive_site_metadata(self, site_id: str) -> None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT site_id FROM site_metadata WHERE site_id = ?",
                (site_id,),
            ).fetchone()
        if row is not None:
            return
        fallback_zone = self.load_config().get("time_zone") or detect_local_timezone_name() or "UTC"
        self.upsert_site_metadata(site_id, f"Site {site_id}", fallback_zone, "{}")

    def refresh_archive_cache(self) -> int:
        if not self.archive_refresh_lock.acquire(blocking=False):
            return 0
        try:
            self._ensure_archive_import_schema()
            imported_rows = 0
            for site_id, csv_path in self._archive_csv_files():
                if not self._archive_file_needs_import(site_id, csv_path):
                    continue
                self._ensure_archive_site_metadata(site_id)
                imported_rows += self._import_energy_csv(site_id, csv_path)
            return imported_rows
        finally:
            self.archive_refresh_lock.release()

    def _write_energy_csv(
        self,
        site_id: str,
        month_date: dt.date,
        time_series: Sequence[Dict[str, Any]],
        partial_month: bool = False,
    ) -> str:
        if not time_series:
            raise RuntimeError(f"No timeseries returned for {month_date:%Y-%m}.")
        flattened_rows = [flatten_history_row_for_csv(row) for row in time_series]
        csv_path = self._energy_csv_path(site_id, month_date, partial_month=partial_month)
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        fieldnames = fieldnames_from_rows(flattened_rows)
        with open(csv_path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in flattened_rows:
                writer.writerow(row)
        return csv_path

    def _write_power_csv(
        self,
        site_id: str,
        day_date: dt.date,
        time_series: Sequence[Dict[str, Any]],
        partial_day: bool = False,
    ) -> str:
        if not time_series:
            raise RuntimeError(f"No intraday power returned for {day_date.isoformat()}.")
        flattened_rows = [flatten_power_row_for_csv(row) for row in time_series]
        csv_path = self._power_csv_path(site_id, day_date, partial_day=partial_day)
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        fieldnames = fieldnames_from_rows(flattened_rows)
        with open(csv_path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in flattened_rows:
                writer.writerow(row)
        return csv_path

    def _import_energy_csv(self, site_id: str, csv_path: str) -> int:
        if not os.path.exists(csv_path):
            return 0
        normalized_rows: List[Dict[str, Any]] = []
        with open(csv_path, "r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                clean_row = {
                    str(key): (value.strip() if isinstance(value, str) else value)
                    for key, value in row.items()
                    if key
                }
                normalized_rows.append(normalize_history_row(clean_row))
        aggregated_rows = aggregate_daily_history_rows(normalized_rows, csv_path=csv_path)
        self.upsert_daily_rows(site_id, aggregated_rows)
        self._record_archive_import(site_id, csv_path)
        return len(aggregated_rows)

    def upsert_site_metadata(self, site_id: str, site_name: str, time_zone: str, raw_json: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO site_metadata (site_id, site_name, time_zone, raw_json, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(site_id) DO UPDATE SET
                    site_name = excluded.site_name,
                    time_zone = excluded.time_zone,
                    raw_json = excluded.raw_json,
                    updated_at = excluded.updated_at
                """,
                (site_id, site_name, time_zone, raw_json, utc_now_iso()),
            )

    def upsert_daily_rows(self, site_id: str, rows: Sequence[Dict[str, Any]]) -> None:
        if not rows:
            return
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO daily_energy (
                    site_id, bucket_date, solar_generation_wh, home_usage_wh,
                    grid_import_wh, grid_export_wh, raw_json, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(site_id, bucket_date) DO UPDATE SET
                    solar_generation_wh = excluded.solar_generation_wh,
                    home_usage_wh = excluded.home_usage_wh,
                    grid_import_wh = excluded.grid_import_wh,
                    grid_export_wh = excluded.grid_export_wh,
                    raw_json = excluded.raw_json,
                    updated_at = excluded.updated_at
                """,
                [
                    (
                        site_id,
                        row["bucket_date"],
                        row["solar_generation_wh"],
                        row["home_usage_wh"],
                        row["grid_import_wh"],
                        row["grid_export_wh"],
                        row["raw_json"],
                        utc_now_iso(),
                    )
                    for row in rows
                ],
            )

    def set_sync_state(self, key: str, value: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sync_state (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    def get_sync_state(self, key: str) -> Optional[str]:
        with self._connect() as connection:
            row = connection.execute("SELECT value FROM sync_state WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None
