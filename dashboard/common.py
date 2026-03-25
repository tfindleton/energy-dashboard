#!/usr/bin/env python3
"""Tesla energy dashboard with local sync and comparison charts."""

from __future__ import annotations

import argparse
import calendar
import csv
import datetime as dt
import json
import mimetypes
import os
import sqlite3
import statistics
import sys
import tempfile
import time
import threading
import urllib.error
import urllib.parse
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore[assignment]
    ZoneInfoNotFoundError = Exception  # type: ignore[assignment]


DEFAULT_DATA_DIR = "data"
DEFAULT_DB_FILENAME = "dashboard.sqlite3"
DEFAULT_CONFIG_FILENAME = "tesla_auth.json"
DEFAULT_DOWNLOAD_DIRNAME = "download"
DEFAULT_DB_PATH = os.path.join(DEFAULT_DATA_DIR, DEFAULT_DB_FILENAME)
DEFAULT_CONFIG_PATH = os.path.join(DEFAULT_DATA_DIR, DEFAULT_CONFIG_FILENAME)
DEFAULT_DOWNLOAD_ROOT = os.path.join(DEFAULT_DATA_DIR, DEFAULT_DOWNLOAD_DIRNAME)
DEFAULT_HISTORY_DAYS = 365 * 5
DEFAULT_POWER_BACKFILL_DAYS = 45
DEFAULT_DIAGNOSTIC_WINDOW_DAYS = 2
DEFAULT_SYNC_INTERVAL_MINUTES = 0
DEFAULT_DAILY_SYNC_TIME = "01:00"
DEFAULT_SERVE_HOST = "0.0.0.0"
DEFAULT_TESLAPY_TIMEOUT = 15
ARCHIVE_IMPORT_SCHEMA_VERSION = "2"
EXCLUDED_HISTORY_COLUMNS = (
    "grid_services_power",
    "generator_power",
    "generator_energy_exported",
    "grid_services_energy_imported",
    "grid_services_energy_exported",
    "grid_energy_exported_from_generator",
    "battery_energy_imported_from_generator",
    "consumer_energy_imported_from_generator",
)
METRIC_ORDER = [
    ("solar_generation_wh", "Solar generation", "#d97706"),
    ("home_usage_wh", "Home usage", "#1d4ed8"),
    ("grid_export_wh", "Grid export", "#059669"),
    ("grid_import_wh", "Grid import", "#dc2626"),
]
WEEKDAY_LABELS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]
DAY_COMPARE_METRICS = {
    "load_power": {"label": "Home usage", "unit": "kW"},
    "solar_power": {"label": "Solar generation", "unit": "kW"},
    "grid_import_power": {"label": "Grid import", "unit": "kW"},
    "grid_export_power": {"label": "Grid export", "unit": "kW"},
}
DAY_COMPARE_DAILY_TOTAL_COLUMNS = {
    "load_power": "home_usage_wh",
    "solar_power": "solar_generation_wh",
    "grid_import_power": "grid_import_wh",
    "grid_export_power": "grid_export_wh",
}
DAY_COMPARE_PALETTE = [
    "#312e81",
    "#4338ca",
    "#1d4ed8",
    "#2563eb",
    "#0284c7",
    "#06b6d4",
    "#0f766e",
    "#10b981",
    "#22c55e",
    "#65a30d",
    "#a3e635",
    "#eab308",
    "#f59e0b",
    "#f97316",
    "#ef4444",
    "#e11d48",
]


def palette_color(index: int, total: int, palette: Sequence[str]) -> str:
    if not palette:
        return "#d97706"
    if total <= 1:
        return palette[len(palette) // 2]
    position = round(index * (len(palette) - 1) / max(total - 1, 1))
    return palette[max(0, min(position, len(palette) - 1))]


def import_teslapy() -> Any:
    try:
        import teslapy  # type: ignore
    except ModuleNotFoundError as error:
        raise RuntimeError("TeslaPy is not installed. Run `pip install -r requirements.txt`.") from error
    return teslapy


PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(PACKAGE_DIR, "templates")
STATIC_DIR = os.path.join(PACKAGE_DIR, "static")
INDEX_TEMPLATE_PATH = os.path.join(TEMPLATE_DIR, "index.html")


def sibling_path_for_db_path(db_path: str, name: str) -> str:
    db_dir = os.path.dirname(os.path.normpath(db_path))
    return os.path.join(db_dir, name) if db_dir else name


def default_config_path_for_db_path(db_path: str) -> str:
    return sibling_path_for_db_path(db_path, DEFAULT_CONFIG_FILENAME)


def default_download_root_for_db_path(db_path: str) -> str:
    return sibling_path_for_db_path(db_path, DEFAULT_DOWNLOAD_DIRNAME)


def read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def resolve_static_path(relative_path: str) -> str:
    normalized = os.path.normpath(relative_path).lstrip("/\\")
    candidate = os.path.abspath(os.path.join(STATIC_DIR, normalized))
    if os.path.commonpath([STATIC_DIR, candidate]) != STATIC_DIR:
        raise RuntimeError("Invalid static asset path.")
    if not os.path.exists(candidate):
        raise FileNotFoundError(candidate)
    return candidate


def guess_content_type(path: str) -> str:
    content_type, _ = mimetypes.guess_type(path)
    return content_type or "application/octet-stream"


def normalize_code_verifier(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("ascii")
    return str(value)


def resolve_tzinfo(time_zone: str) -> dt.tzinfo:
    if ZoneInfo is not None and time_zone:
        try:
            return ZoneInfo(time_zone)
        except Exception:
            pass
    local_tz = dt.datetime.now().astimezone().tzinfo
    return local_tz if local_tz is not None else dt.timezone.utc


def slugify(value: str) -> str:
    pieces = []
    previous_underscore = False
    for char in value.lower():
        if char.isalnum():
            pieces.append(char)
            previous_underscore = False
        elif not previous_underscore:
            pieces.append("_")
            previous_underscore = True
    return "".join(pieces).strip("_")


def flatten_scalars(value: Any, prefix: str = "") -> Dict[str, Any]:
    items: Dict[str, Any] = {}
    if isinstance(value, dict):
        for key, nested in value.items():
            clean_key = slugify(str(key))
            new_prefix = f"{prefix}_{clean_key}" if prefix and clean_key else clean_key or prefix
            if isinstance(nested, (dict, list)):
                items.update(flatten_scalars(nested, new_prefix))
            elif nested is not None and not isinstance(nested, bool):
                items[new_prefix] = nested
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            new_prefix = f"{prefix}_{index}" if prefix else str(index)
            if isinstance(nested, (dict, list)):
                items.update(flatten_scalars(nested, new_prefix))
            elif nested is not None and not isinstance(nested, bool):
                items[new_prefix] = nested
    return items


def flatten_numbers(value: Any) -> Dict[str, float]:
    numbers: Dict[str, float] = {}
    for key, item in flatten_scalars(value).items():
        if isinstance(item, (int, float)) and not isinstance(item, bool):
            numbers[key] = float(item)
        elif isinstance(item, str):
            raw = item.strip()
            if not raw:
                continue
            try:
                numbers[key] = float(raw)
            except ValueError:
                continue
    return numbers


def fieldnames_from_rows(rows: Sequence[Dict[str, Any]]) -> List[str]:
    fieldnames: Dict[str, bool] = {}
    for row in rows:
        for key in row:
            fieldnames[key] = True
    return [key for key in fieldnames if key not in EXCLUDED_HISTORY_COLUMNS]


def flatten_history_row_for_csv(row: Dict[str, Any]) -> Dict[str, Any]:
    flattened = flatten_scalars(row)
    if "timestamp" in flattened:
        flattened["timestamp"] = format_csv_timestamp(flattened["timestamp"])
    return {
        key: value
        for key, value in flattened.items()
        if key not in EXCLUDED_HISTORY_COLUMNS
    }


def flatten_power_row_for_csv(row: Dict[str, Any]) -> Dict[str, Any]:
    flattened = flatten_scalars(row)
    if "timestamp" in flattened:
        flattened["timestamp"] = format_csv_timestamp(flattened["timestamp"])

    def read_number(key: str) -> float:
        raw_value = flattened.get(key, 0)
        try:
            return float(raw_value)
        except (TypeError, ValueError):
            return 0.0

    if "load_power" not in flattened:
        flattened["load_power"] = (
            read_number("solar_power")
            + read_number("battery_power")
            + read_number("grid_power")
            + read_number("generator_power")
        )

    return {
        key: value
        for key, value in flattened.items()
        if key not in EXCLUDED_HISTORY_COLUMNS
    }


def parse_dateish(value: Any) -> Optional[dt.date]:
    if value in (None, ""):
        return None
    if isinstance(value, dt.date) and not isinstance(value, dt.datetime):
        return value
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp /= 1000.0
        try:
            return dt.datetime.utcfromtimestamp(timestamp).date()
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            return dt.date.fromisoformat(raw[:10])
        except ValueError:
            pass
        try:
            normalized = raw.replace("Z", "+00:00")
            return dt.datetime.fromisoformat(normalized).date()
        except ValueError:
            return None
    return None


def extract_bucket_date(row: Dict[str, Any]) -> Optional[dt.date]:
    flat = flatten_scalars(row)
    priority = [
        "timestamp",
        "time",
        "start_date",
        "start_at",
        "date",
        "end_date",
    ]
    for needle in priority:
        for key, value in flat.items():
            if needle in key:
                parsed = parse_dateish(value)
                if parsed:
                    return parsed
    for value in flat.values():
        parsed = parse_dateish(value)
        if parsed:
            return parsed
    return None


def key_tokens(key: str) -> set[str]:
    return {piece for piece in key.split("_") if piece}


def sum_with_tokens(
    numbers: Dict[str, float],
    required_groups: Sequence[Sequence[str]],
    forbidden: Sequence[str] = (),
    require_token: Optional[str] = None,
    exclude_token: Optional[str] = None,
) -> Optional[float]:
    total = 0.0
    matched = False
    for key, value in numbers.items():
        tokens = key_tokens(key)
        if require_token and require_token not in tokens:
            continue
        if exclude_token and exclude_token in tokens:
            continue
        if any(term in tokens for term in forbidden):
            continue
        if all(any(alias in tokens for alias in group) for group in required_groups):
            total += value
            matched = True
    return total if matched else None


def first_direct_total(
    numbers: Dict[str, float],
    required_groups: Sequence[Sequence[str]],
    forbidden: Sequence[str] = (),
) -> Optional[float]:
    for key, value in numbers.items():
        tokens = key_tokens(key)
        if "from" in tokens or "to" in tokens:
            continue
        if any(term in tokens for term in forbidden):
            continue
        if all(any(alias in tokens for alias in group) for group in required_groups):
            return value
    return None


def extract_solar_generation_wh(numbers: Dict[str, float]) -> float:
    direct = first_direct_total(
        numbers,
        [["solar", "pv"], ["energy"], ["exported", "generated", "generation", "produced"]],
        forbidden=["grid", "consumer", "home", "load", "battery"],
    )
    if direct is not None:
        return direct
    fallback = sum_with_tokens(
        numbers,
        [["from"], ["solar", "pv"]],
    )
    return fallback or 0.0


def extract_home_usage_wh(numbers: Dict[str, float]) -> float:
    direct = first_direct_total(
        numbers,
        [["consumer", "home", "load", "house"], ["energy"], ["imported", "consumed", "usage", "used"]],
        forbidden=["grid", "solar", "battery"],
    )
    if direct is not None:
        return direct
    fallback = sum_with_tokens(
        numbers,
        [["consumer", "home", "load", "house"], ["energy"], ["imported", "consumed"]],
    )
    return fallback or 0.0


def extract_grid_import_wh(numbers: Dict[str, float]) -> float:
    direct = first_direct_total(
        numbers,
        [["grid", "utility"], ["energy"], ["imported", "purchased", "consumed"]],
        forbidden=["solar", "battery", "consumer", "home", "load"],
    )
    if direct is not None:
        return direct
    fallback = sum_with_tokens(
        numbers,
        [["from"], ["grid", "utility"]],
    )
    return fallback or 0.0


def extract_grid_export_wh(numbers: Dict[str, float]) -> float:
    direct = first_direct_total(
        numbers,
        [["grid", "utility"], ["energy"], ["exported", "sold", "sent"]],
        forbidden=["consumer", "home", "load"],
    )
    if direct is not None:
        return direct
    fallback = sum_with_tokens(
        numbers,
        [["grid", "utility"], ["energy"], ["exported", "sold", "sent"]],
        require_token="from",
    )
    return fallback or 0.0


def normalize_history_row(row: Dict[str, Any]) -> Dict[str, Any]:
    bucket_date = extract_bucket_date(row)
    if bucket_date is None:
        raise ValueError("Unable to determine row date from Tesla history payload.")
    numbers = flatten_numbers(row)
    return {
        "bucket_date": bucket_date.isoformat(),
        "solar_generation_wh": extract_solar_generation_wh(numbers),
        "home_usage_wh": extract_home_usage_wh(numbers),
        "grid_import_wh": extract_grid_import_wh(numbers),
        "grid_export_wh": extract_grid_export_wh(numbers),
        "raw_json": json.dumps(row, sort_keys=True),
    }


def aggregate_daily_history_rows(rows: Sequence[Dict[str, Any]], csv_path: str = "") -> List[Dict[str, Any]]:
    aggregated: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        bucket_date = str(row["bucket_date"])
        bucket = aggregated.setdefault(
            bucket_date,
            {
                "bucket_date": bucket_date,
                "solar_generation_wh": 0.0,
                "home_usage_wh": 0.0,
                "grid_import_wh": 0.0,
                "grid_export_wh": 0.0,
                "_interval_count": 0,
            },
        )
        for metric, _, _ in METRIC_ORDER:
            bucket[metric] += float(row.get(metric, 0.0) or 0.0)
        bucket["_interval_count"] += 1

    summarized_rows: List[Dict[str, Any]] = []
    for bucket_date in sorted(aggregated):
        bucket = aggregated[bucket_date]
        interval_count = int(bucket.pop("_interval_count", 0))
        bucket["raw_json"] = json.dumps(
            {
                "source": "energy_csv",
                "csv_name": os.path.basename(csv_path) if csv_path else "",
                "interval_count": interval_count,
            },
            sort_keys=True,
        )
        summarized_rows.append(bucket)
    return summarized_rows




def parse_datetime(value: Any) -> Optional[dt.datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, dt.datetime):
        if value.tzinfo is not None:
            return value.astimezone(dt.timezone.utc)
        return value.replace(tzinfo=dt.timezone.utc)
    if isinstance(value, str):
        raw = value.strip().replace("Z", "+00:00")
        try:
            parsed = dt.datetime.fromisoformat(raw)
        except ValueError:
            return None
        if parsed.tzinfo is not None:
            return parsed.astimezone(dt.timezone.utc)
        return parsed.replace(tzinfo=dt.timezone.utc)
    return None


def format_csv_timestamp(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, dt.datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    raw = str(value).strip()
    if not raw:
        return ""
    try:
        return dt.datetime.fromisoformat(raw.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        if "T" in raw and len(raw) >= 19:
            return raw[:19].replace("T", " ")
        return raw


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def utc_now_iso() -> str:
    return utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def detect_local_timezone_name() -> Optional[str]:
    if ZoneInfo is None:
        return None
    tz_name = os.environ.get("TZ")
    if tz_name:
        try:
            ZoneInfo(tz_name)
            return tz_name
        except Exception:
            pass
    local_tz = dt.datetime.now().astimezone().tzinfo
    key = getattr(local_tz, "key", None)
    return key if isinstance(key, str) else None


def parse_daily_sync_time(value: str) -> Optional[Tuple[int, int]]:
    raw = (value or "").strip().lower()
    if raw in ("", "off", "none", "disabled", "manual", "0"):
        return None
    try:
        hour_text, minute_text = raw.split(":", 1)
        hour = int(hour_text)
        minute = int(minute_text)
    except (ValueError, AttributeError):
        raise RuntimeError("Daily sync time must look like HH:MM, for example 01:00.")
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise RuntimeError("Daily sync time must be between 00:00 and 23:59.")
    return hour, minute


def describe_daily_sync_time(value: str) -> str:
    parsed = parse_daily_sync_time(value)
    if parsed is None:
        return "Disabled"
    hour, minute = parsed
    label = dt.time(hour=hour, minute=minute).strftime("%I:%M %p")
    return f"Daily at {label.lstrip('0')}"


def latest_scheduled_daily_sync_utc(
    daily_sync_time: str,
    now: Optional[dt.datetime] = None,
) -> Optional[dt.datetime]:
    parsed = parse_daily_sync_time(daily_sync_time)
    if parsed is None:
        return None
    hour, minute = parsed
    local_now = now.astimezone() if now is not None else dt.datetime.now().astimezone()
    scheduled_local = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if scheduled_local > local_now:
        scheduled_local -= dt.timedelta(days=1)
    return scheduled_local.astimezone(dt.timezone.utc)
