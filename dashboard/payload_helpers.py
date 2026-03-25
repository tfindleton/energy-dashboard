from __future__ import annotations

import calendar
import datetime as dt
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .common import METRIC_ORDER, parse_dateish

def clamp_month_day(year: int, month: int, day: int) -> dt.date:
    last_day = calendar.monthrange(year, month)[1]
    return dt.date(year, month, min(day, last_day))


def metric_to_slug(metric_key: str) -> str:
    return metric_key.replace("_wh", "")


def start_of_iso_week(date_value: dt.date) -> dt.date:
    return date_value - dt.timedelta(days=date_value.weekday())


def sum_metric_rows(rows: Iterable[Dict[str, Any]]) -> Dict[str, float]:
    totals = {metric: 0.0 for metric, _, _ in METRIC_ORDER}
    for row in rows:
        for metric in totals:
            totals[metric] += float(row.get(metric, 0.0) or 0.0)
    return totals


def normalize_query_rows(
    rows: Sequence[Dict[str, Any]],
    start_date: Optional[dt.date] = None,
    end_date: Optional[dt.date] = None,
) -> List[Dict[str, Any]]:
    parsed_rows = []
    for row in rows:
        bucket_date = parse_dateish(row["bucket_date"])
        if not bucket_date:
            continue
        if start_date and bucket_date < start_date:
            continue
        if end_date and bucket_date > end_date:
            continue
        parsed_rows.append(
            {
                "bucket_date": bucket_date,
                **{metric: float(row.get(metric, 0.0) or 0.0) for metric, _, _ in METRIC_ORDER},
            }
        )
    return parsed_rows


def aggregate_rows_for_period(
    rows: Sequence[Dict[str, Any]],
    granularity: str,
) -> List[Dict[str, Any]]:
    buckets: Dict[dt.date, Dict[str, Any]] = {}
    for row in rows:
        date_value = row["bucket_date"]
        if granularity == "day":
            bucket_start = date_value
        elif granularity == "week":
            bucket_start = start_of_iso_week(date_value)
        elif granularity == "month":
            bucket_start = dt.date(date_value.year, date_value.month, 1)
        elif granularity == "year":
            bucket_start = dt.date(date_value.year, 1, 1)
        else:
            raise ValueError(f"Unsupported granularity: {granularity}")
        bucket = buckets.setdefault(
            bucket_start,
            {"start_date": bucket_start, **{metric: 0.0 for metric, _, _ in METRIC_ORDER}},
        )
        for metric, _, _ in METRIC_ORDER:
            bucket[metric] += row[metric]
    return [buckets[key] for key in sorted(buckets)]


def format_period_label(start_date: dt.date, granularity: str) -> str:
    if granularity == "day":
        return start_date.strftime("%b %d, %Y")
    if granularity == "week":
        iso = start_date.isocalendar()
        return f"Week {iso.week:02d}, {iso.year}"
    if granularity == "month":
        return start_date.strftime("%B %Y")
    if granularity == "year":
        return start_date.strftime("%Y")
    raise ValueError(f"Unsupported granularity: {granularity}")


def find_peak_period(
    rows: Sequence[Dict[str, Any]],
    granularity: str,
    metric: str,
    start_date: Optional[dt.date] = None,
    end_date: Optional[dt.date] = None,
) -> Optional[Dict[str, Any]]:
    parsed_rows = normalize_query_rows(rows, start_date=start_date, end_date=end_date)
    if not parsed_rows:
        return None
    aggregated = aggregate_rows_for_period(parsed_rows, granularity)
    if not aggregated:
        return None
    peak = max(aggregated, key=lambda row: (row[metric], -row["start_date"].toordinal()))
    return {
        "label": format_period_label(peak["start_date"], granularity),
        "start_date": peak["start_date"].isoformat(),
        "value_kwh": round(peak[metric] / 1000.0, 2),
    }


def make_peak_item(
    rows: Sequence[Dict[str, Any]],
    label: str,
    granularity: str,
    metric: str,
    start_date: Optional[dt.date] = None,
    end_date: Optional[dt.date] = None,
) -> Dict[str, Any]:
    peak = find_peak_period(rows, granularity, metric, start_date=start_date, end_date=end_date)
    return {
        "label": label,
        "value": peak["value_kwh"] if peak else None,
        "kind": "energy",
        "hint": peak["label"] if peak else "No data",
    }


def classify_signal_tone(value: Optional[float], kind: str) -> str:
    if value is None:
        return ""
    if kind == "self_power":
        if value >= 80:
            return "good"
        if value < 55:
            return "bad"
    if kind == "solar_delta":
        if value >= 5:
            return "good"
        if value <= -10:
            return "bad"
    if kind == "export_share":
        if value >= 35:
            return "good"
    return ""

__all__ = [
    "aggregate_rows_for_period",
    "classify_signal_tone",
    "clamp_month_day",
    "find_peak_period",
    "format_period_label",
    "make_peak_item",
    "metric_to_slug",
    "normalize_query_rows",
    "start_of_iso_week",
    "sum_metric_rows",
]
