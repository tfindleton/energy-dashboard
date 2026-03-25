from __future__ import annotations

import calendar
import csv
import datetime as dt
import json
import os
import sqlite3
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .common import (
    ARCHIVE_IMPORT_SCHEMA_VERSION,
    DAY_COMPARE_DAILY_TOTAL_COLUMNS,
    DAY_COMPARE_METRICS,
    DEFAULT_DOWNLOAD_ROOT,
    DEFAULT_HISTORY_DAYS,
    DEFAULT_POWER_BACKFILL_DAYS,
    DEFAULT_TESLAPY_TIMEOUT,
    detect_local_timezone_name,
    flatten_scalars,
    fieldnames_from_rows,
    flatten_history_row_for_csv,
    flatten_power_row_for_csv,
    format_csv_timestamp,
    import_teslapy,
    latest_scheduled_daily_sync_utc,
    normalize_code_verifier,
    normalize_history_row,
    parse_dateish,
    parse_datetime,
    parse_daily_sync_time,
    resolve_tzinfo,
    utc_now,
    utc_now_iso,
    aggregate_daily_history_rows,
    DEFAULT_DAILY_SYNC_TIME,
)
from .payloads import (
    build_comparison_payload,
    build_day_compare_payload,
    build_diagnostics_payload,
    build_insights_payload,
    build_trend_payload,
    build_weekday_pattern_payload,
)

def chunk_date_ranges(start_date: dt.date, end_date: dt.date, chunk_days: int = 90) -> List[Tuple[dt.date, dt.date]]:
    chunks = []
    cursor = start_date
    while cursor <= end_date:
        chunk_end = min(cursor + dt.timedelta(days=chunk_days - 1), end_date)
        chunks.append((cursor, chunk_end))
        cursor = chunk_end + dt.timedelta(days=1)
    return chunks


def json_request(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    form_data: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
) -> Any:
    request_headers = dict(headers or {})
    payload = None
    if form_data is not None:
        payload = urllib.parse.urlencode(form_data).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    request = urllib.request.Request(url, data=payload, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
            if isinstance(payload, dict):
                message = payload.get("error_description") or payload.get("error") or body
            else:
                message = body
        except json.JSONDecodeError:
            message = body
        raise RuntimeError(f"Tesla API error {error.code}: {message}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Request failed for {url}: {error.reason}") from error
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Non-JSON response from {url}") from error


def unwrap_response(payload: Any) -> Any:
    if isinstance(payload, dict) and "response" in payload:
        return payload["response"]
    return payload


def extract_energy_sites(products_payload: Any) -> List[Dict[str, Any]]:
    payload = unwrap_response(products_payload)
    items = payload if isinstance(payload, list) else []
    sites = []
    for item in items:
        if not isinstance(item, dict):
            continue
        site_id = item.get("energy_site_id")
        resource_type = str(item.get("resource_type", "")).lower()
        if site_id is None and not any(term in resource_type for term in ("solar", "battery", "powerwall", "energy")):
            continue
        site_id = str(site_id if site_id is not None else item.get("id", ""))
        if not site_id:
            continue
        sites.append(
            {
                "site_id": site_id,
                "site_name": item.get("site_name") or item.get("display_name") or f"Site {site_id}",
                "resource_type": item.get("resource_type", ""),
                "raw": item,
            }
        )
    deduped: Dict[str, Dict[str, Any]] = {site["site_id"]: site for site in sites}
    return list(deduped.values())


def extract_timezone(payload: Any, fallback: str) -> str:
    flat = flatten_scalars(unwrap_response(payload))
    for key, value in flat.items():
        if not isinstance(value, str):
            continue
        if ("time_zone" in key or "timezone" in key) and "/" in value:
            return value
    return fallback


def extract_site_name(payload: Any, fallback: str) -> str:
    flat = flatten_scalars(unwrap_response(payload))
    for candidate in ("site_name", "display_name", "name"):
        if candidate in flat and isinstance(flat[candidate], str):
            return flat[candidate]
    return fallback


def extract_installation_date(payload: Any) -> Optional[dt.date]:
    flat = flatten_scalars(unwrap_response(payload))
    for key, value in flat.items():
        if "installation_date" not in key:
            continue
        parsed = parse_dateish(value)
        if parsed is not None:
            return parsed
    return None


def extract_history_rows(payload: Any) -> List[Dict[str, Any]]:
    unwrapped = unwrap_response(payload)
    if isinstance(unwrapped, list):
        return [item for item in unwrapped if isinstance(item, dict)]
    if isinstance(unwrapped, dict):
        for key in ("time_series", "history", "series", "calendar_history", "records"):
            if key in unwrapped and unwrapped.get(key) in (None, "", []):
                return []
            rows = unwrapped.get(key)
            if isinstance(rows, list):
                return [item for item in rows if isinstance(item, dict)]
        for value in unwrapped.values():
            if isinstance(value, list) and all(isinstance(item, dict) for item in value):
                return [item for item in value if isinstance(item, dict)]
        if not unwrapped:
            return []
    raise RuntimeError("Unexpected Tesla history payload shape.")


class TeslaSolarDashboard:
    def __init__(self, db_path: str, config_path: str, download_root: Optional[str] = None) -> None:
        self.db_path = db_path
        self.config_path = config_path
        base_dir = os.path.dirname(os.path.abspath(db_path)) or os.getcwd()
        self.download_root = os.path.abspath(download_root or os.path.join(base_dir, DEFAULT_DOWNLOAD_ROOT))
        self.sync_lock = threading.Lock()
        self.sync_progress_lock = threading.Lock()
        self.archive_refresh_lock = threading.Lock()
        self.auto_sync_enabled = False
        self.auto_sync_interval_minutes = 0
        self.auto_sync_daily_time = ""
        self.auto_sync_description = ""
        self.auto_sync_next_run: Optional[str] = None
        self.auto_sync_site_id: Optional[str] = None
        self.config_warning = ""
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

    def load_config(self) -> Dict[str, Any]:
        config: Dict[str, Any] = {}
        self.config_warning = ""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
                    if isinstance(loaded, dict):
                        config.update(loaded)
            except json.JSONDecodeError:
                stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
                backup_path = f"{self.config_path}.invalid-{stamp}"
                os.replace(self.config_path, backup_path)
                self.config_warning = (
                    f"Saved an invalid auth config backup to {os.path.basename(backup_path)}. "
                    "Please start Tesla sign-in again."
                )
                print(f"[config] Backed up invalid config to {backup_path}", file=sys.stderr, flush=True)
        env_map = {
            "email": "TESLA_EMAIL",
            "energy_site_id": "TESLA_ENERGY_SITE_ID",
            "time_zone": "TESLA_TIME_ZONE",
        }
        for key, env_name in env_map.items():
            if os.environ.get(env_name):
                config[key] = os.environ[env_name]
        return config

    def save_config(self, config: Dict[str, Any]) -> None:
        config_dir = os.path.dirname(os.path.abspath(self.config_path)) or "."
        os.makedirs(config_dir, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=config_dir,
            prefix=".tesla-auth-",
            suffix=".tmp",
            delete=False,
        ) as handle:
            json.dump(config, handle, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = handle.name
        os.replace(temp_path, self.config_path)

    def teslapy_available(self) -> bool:
        try:
            import_teslapy()
            return True
        except RuntimeError:
            return False

    def config_public_payload(self) -> Dict[str, Any]:
        config = self.load_config()
        pending_auth = config.get("pending_auth") or {}
        return {
            "email": config.get("email", ""),
            "energy_site_id": config.get("energy_site_id", ""),
            "time_zone": config.get("time_zone", ""),
            "auth_pending": bool(pending_auth),
            "pending_auth_url": pending_auth.get("authorization_url", ""),
            "download_root": self.download_root,
        }

    def save_user_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        config = self.load_config()
        old_email = config.get("email")

        for key in ("email", "energy_site_id", "time_zone"):
            if key in updates:
                value = str(updates.get(key, "") or "").strip()
                if value:
                    config[key] = value
                else:
                    config.pop(key, None)

        if config.get("email") != old_email:
            for key in ("teslapy_cache", "pending_auth"):
                config.pop(key, None)

        self.save_config(config)
        return self.config_public_payload()

    def missing_login_fields(self, config: Optional[Dict[str, Any]] = None) -> List[str]:
        active = config or self.load_config()
        return ["Tesla account email"] if not active.get("email") else []

    def auth_login_ready(self) -> bool:
        return self.teslapy_available() and not self.missing_login_fields()

    def auth_configured(self) -> bool:
        if not self.auth_login_ready():
            return False
        try:
            with self._tesla_session() as tesla:
                return bool(tesla.authorized)
        except RuntimeError:
            return False

    def _teslapy_cache_loader(self) -> Dict[str, Any]:
        return dict(self.load_config().get("teslapy_cache", {}))

    def _teslapy_cache_dumper(self, cache: Dict[str, Any]) -> None:
        config = self.load_config()
        config["teslapy_cache"] = cache
        self.save_config(config)

    def _tesla_session(
        self,
        email: Optional[str] = None,
        state: Optional[str] = None,
        code_verifier: Optional[str] = None,
    ) -> Any:
        teslapy = import_teslapy()
        config = self.load_config()
        active_email = email or config.get("email")
        if not active_email:
            raise RuntimeError("Tesla account email is required.")
        return teslapy.Tesla(
            active_email,
            cache_loader=self._teslapy_cache_loader,
            cache_dumper=self._teslapy_cache_dumper,
            retry=2,
            timeout=DEFAULT_TESLAPY_TIMEOUT,
            state=state,
            code_verifier=code_verifier,
        )

    def start_web_login(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        self.save_user_config(updates)
        config = self.load_config()
        if not config.get("email"):
            raise RuntimeError("Tesla account email is required.")
        with self._tesla_session() as tesla:
            if tesla.authorized:
                return {"authorization_url": "", "already_authorized": True}
            state = tesla.new_state()
            code_verifier = tesla.new_code_verifier()
            authorization_url = tesla.authorization_url(state=state, code_verifier=code_verifier)
        config["pending_auth"] = {
            "email": config["email"],
            "state": state,
            "code_verifier": normalize_code_verifier(code_verifier),
            "authorization_url": authorization_url,
        }
        self.save_config(config)
        return {"authorization_url": authorization_url, "already_authorized": False}

    def finish_web_login(self, authorization_response: str) -> Dict[str, Any]:
        if not authorization_response:
            raise RuntimeError("Paste the full Tesla URL from the final page.")
        config = self.load_config()
        pending_auth = config.get("pending_auth") or {}
        email = pending_auth.get("email") or config.get("email")
        state = pending_auth.get("state")
        code_verifier = pending_auth.get("code_verifier")
        if not (email and state and code_verifier):
            raise RuntimeError("No Tesla sign-in is in progress. Start sign-in first.")
        with self._tesla_session(email=email, state=state, code_verifier=code_verifier) as tesla:
            tesla.fetch_token(authorization_response=authorization_response)
        config = self.load_config()
        config.pop("pending_auth", None)
        self.save_config(config)
        return {"authorized": True}

    def logout(self) -> Dict[str, Any]:
        config = self.load_config()
        config.pop("teslapy_cache", None)
        config.pop("pending_auth", None)
        self.save_config(config)
        return {"authorized": False}

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

    def sync_progress_payload(self) -> Dict[str, Any]:
        with self.sync_progress_lock:
            return dict(self.sync_progress)

    def sync(self, days_back: int, requested_site_id: Optional[str] = None) -> Dict[str, Any]:
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
            requested_start_date = end_date - dt.timedelta(days=max(days_back - 1, 0))
            synced_sites = []
            warning_messages: List[str] = []

            with self._tesla_session() as tesla:
                products_payload = tesla.api("PRODUCT_LIST")
                sites = extract_energy_sites(products_payload)
                configured_site_id = requested_site_id or config.get("energy_site_id")
                if configured_site_id:
                    sites = [site for site in sites if site["site_id"] == str(configured_site_id)] or [
                        {"site_id": str(configured_site_id), "site_name": f"Site {configured_site_id}", "resource_type": "energy", "raw": {}}
                    ]
                if not sites:
                    raise RuntimeError("No Tesla energy sites were found for this account.")

                site_plans = []
                total_download_steps = 0
                total_import_steps = 0

                for site in sites:
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

                    archive_start_date = dt.date(requested_start_date.year, requested_start_date.month, 1)
                    power_start_date = max(
                        requested_start_date,
                        end_date - dt.timedelta(days=DEFAULT_POWER_BACKFILL_DAYS - 1),
                    )
                    if installation_date is not None:
                        archive_start_date = max(archive_start_date, installation_date)
                        power_start_date = max(power_start_date, installation_date)
                    latest_power_date = self._latest_power_archive_date(site_id)
                    if latest_power_date is not None:
                        power_start_date = max(power_start_date, latest_power_date)

                    self._cleanup_partial_energy_csvs(site_id)
                    self._cleanup_partial_power_csvs(site_id)

                    month_windows = []
                    for month_start, month_end in self._iter_energy_month_windows(archive_start_date, end_date, time_zone):
                        month_date = month_start.date().replace(day=1)
                        partial_month = month_date.year == end_date.year and month_date.month == end_date.month
                        finalized_csv_path = self._energy_csv_path(site_id, month_date, partial_month=False)
                        needs_download = partial_month or not os.path.exists(finalized_csv_path)
                        month_windows.append(
                            {
                                "month_start": month_start,
                                "month_end": month_end,
                                "month_date": month_date,
                                "partial_month": partial_month,
                                "finalized_csv_path": finalized_csv_path,
                                "needs_download": needs_download,
                            }
                        )
                        total_import_steps += 1
                        if needs_download:
                            total_download_steps += 1

                    day_windows = []
                    for day_start, day_end in self._iter_power_day_windows(power_start_date, end_date, time_zone):
                        day_date = day_start.date()
                        partial_day = day_date == end_date
                        finalized_csv_path = self._power_csv_path(site_id, day_date, partial_day=False)
                        needs_download = partial_day or not os.path.exists(finalized_csv_path)
                        day_windows.append(
                            {
                                "day_start": day_start,
                                "day_end": day_end,
                                "day_date": day_date,
                                "partial_day": partial_day,
                                "finalized_csv_path": finalized_csv_path,
                                "needs_download": needs_download,
                            }
                        )
                        if needs_download:
                            total_download_steps += 1

                    site_plans.append(
                        {
                            "site_id": site_id,
                            "site_name": site_name,
                            "time_zone": time_zone,
                            "month_windows": month_windows,
                            "day_windows": day_windows,
                        }
                    )

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

                for site_plan in site_plans:
                    site_id = site_plan["site_id"]
                    site_name = site_plan["site_name"]
                    time_zone = site_plan["time_zone"]
                    imported_row_count = 0
                    for month_plan in site_plan["month_windows"]:
                        month_start = month_plan["month_start"]
                        month_end = month_plan["month_end"]
                        month_date = month_plan["month_date"]
                        partial_month = bool(month_plan["partial_month"])
                        csv_path = self._energy_csv_path(site_id, month_date, partial_month=partial_month)
                        finalized_csv_path = str(month_plan["finalized_csv_path"])
                        month_label = month_date.strftime("%Y-%m")

                        if month_plan["needs_download"]:
                            self._set_sync_progress(
                                stage="downloading",
                                label="Downloading Data",
                                message=f"{site_name} {month_label}: downloading monthly history from Tesla...",
                                active=True,
                                phase_current=downloaded_steps,
                                phase_total=total_download_steps,
                                step_current=downloaded_steps + imported_steps,
                                step_total=total_steps,
                                started_at=sync_started_at,
                            )
                            time_series: List[Dict[str, Any]] = []
                            last_error: Optional[Exception] = None
                            for attempt in range(2):
                                try:
                                    history_payload = tesla.api(
                                        "CALENDAR_HISTORY_DATA",
                                        path_vars={"site_id": site_id},
                                        kind="energy",
                                        period="month",
                                        start_date=month_start.isoformat(),
                                        end_date=month_end.isoformat(),
                                        time_zone=time_zone,
                                    )
                                    time_series = extract_history_rows(history_payload)
                                    csv_path = self._write_energy_csv(
                                        site_id,
                                        month_date,
                                        time_series,
                                        partial_month=partial_month,
                                    )
                                    last_error = None
                                    break
                                except Exception as error:  # pragma: no cover - network dependent
                                    last_error = error
                                    if attempt == 0:
                                        time.sleep(1)
                            if last_error is not None:
                                raise last_error
                            downloaded_steps += 1
                        else:
                            csv_path = finalized_csv_path

                        self._set_sync_progress(
                            stage="importing",
                            label="Importing Data",
                            message=f"{site_name} {month_label}: importing CSV into SQLite...",
                            active=True,
                            phase_current=imported_steps,
                            phase_total=total_import_steps,
                            step_current=downloaded_steps + imported_steps,
                            step_total=total_steps,
                            started_at=sync_started_at,
                        )
                        imported_row_count += self._import_energy_csv(site_id, csv_path)
                        imported_steps += 1

                    for day_plan in site_plan["day_windows"]:
                        if not day_plan["needs_download"]:
                            continue
                        day_start = day_plan["day_start"]
                        day_end = day_plan["day_end"]
                        day_date = day_plan["day_date"]
                        partial_day = bool(day_plan["partial_day"])
                        day_label = day_date.strftime("%Y-%m-%d")

                        self._set_sync_progress(
                            stage="downloading",
                            label="Downloading Data",
                            message=f"{site_name} {day_label}: downloading intraday power from Tesla...",
                            active=True,
                            phase_current=downloaded_steps,
                            phase_total=total_download_steps,
                            step_current=downloaded_steps + imported_steps,
                            step_total=total_steps,
                            started_at=sync_started_at,
                        )
                        time_series = []
                        last_error: Optional[Exception] = None
                        for attempt in range(2):
                            try:
                                history_payload = tesla.api(
                                    "CALENDAR_HISTORY_DATA",
                                    path_vars={"site_id": site_id},
                                    kind="power",
                                    period="day",
                                    start_date=day_start.isoformat(),
                                    end_date=day_end.isoformat(),
                                    time_zone=time_zone,
                                )
                                time_series = extract_history_rows(history_payload)
                                last_error = None
                                break
                            except Exception as error:  # pragma: no cover - network dependent
                                last_error = error
                                if attempt == 0:
                                    time.sleep(1)
                        if last_error is not None:
                            warning_messages.append(f"{site_name} {day_label}: intraday power download skipped ({last_error})")
                            downloaded_steps += 1
                            continue
                        if time_series:
                            self._write_power_csv(
                                site_id,
                                day_date,
                                time_series,
                                partial_day=partial_day,
                            )
                        downloaded_steps += 1

                    synced_sites.append(
                        {
                            "site_id": site_id,
                            "site_name": site_name,
                            "time_zone": time_zone,
                            "row_count": imported_row_count,
                            "download_root": os.path.join(self.download_root, str(site_id), "energy"),
                            "power_root": os.path.join(self.download_root, str(site_id), "power"),
                        }
                    )

            synced_at = utc_now_iso()
            self.set_sync_state("last_sync", synced_at)
            self.set_sync_state("last_sync_error", "")
            completion_message = f"Finished syncing {len(synced_sites)} site(s)."
            if warning_messages:
                completion_message = f"{completion_message} {len(warning_messages)} warning(s); intraday data may still be catching up."
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

    def query_site_rows(self, site_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
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
        missed_sync_at: Optional[dt.datetime] = None
        if self.auto_sync_enabled and self.auto_sync_interval_minutes == 0:
            last_due = latest_scheduled_daily_sync_utc(self.auto_sync_daily_time, now=utc_now())
            if last_due and not self.sync_lock.locked():
                if last_sync_at is None or last_sync_at < last_due:
                    missed_sync_at = last_due
        today = dt.date.today()
        default_anchor = today.isoformat()
        default_trend_start = (today - dt.timedelta(days=365)).isoformat()
        if sites and sites[0].get("data_end"):
            default_anchor = sites[0]["data_end"]
            if sites[0].get("data_start"):
                start_candidate = parse_dateish(sites[0]["data_end"]) - dt.timedelta(days=365)
                if start_candidate:
                    default_trend_start = max(parse_dateish(sites[0]["data_start"]), start_candidate).isoformat()
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
            "auto_sync_interval_minutes": self.auto_sync_interval_minutes,
            "auto_sync_daily_time": self.auto_sync_daily_time,
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
