from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Sequence

from .common import DAY_COMPARE_METRICS, DAY_COMPARE_PALETTE, METRIC_ORDER, WEEKDAY_LABELS, palette_color
from .payload_helpers import clamp_month_day, metric_to_slug, normalize_query_rows, start_of_iso_week, sum_metric_rows

def build_comparison_payload(
    rows: Sequence[Dict[str, Any]],
    mode: str,
    anchor_date: dt.date,
    years_back: int,
) -> Dict[str, Any]:
    parsed_rows = normalize_query_rows(rows)
    if not parsed_rows:
        return {
            "labels": [],
            "series": [
                {"metric": metric_to_slug(metric), "label": label, "color": color, "values": []}
                for metric, label, color in METRIC_ORDER
            ],
            "rows": [],
            "period_label": "",
        }

    latest_year = anchor_date.year
    earliest_year = latest_year - max(years_back - 1, 0)
    labels: List[str] = []
    table_rows: List[Dict[str, float | str]] = []
    values_by_metric = {metric: [] for metric, _, _ in METRIC_ORDER}

    for year in range(earliest_year, latest_year + 1):
        if mode == "day":
            target = clamp_month_day(year, anchor_date.month, anchor_date.day)
            period_rows = [row for row in parsed_rows if row["bucket_date"] == target]
            label = str(year)
        elif mode == "week":
            iso_week = anchor_date.isocalendar().week
            try:
                week_start = dt.date.fromisocalendar(year, iso_week, 1)
            except ValueError:
                week_start = None
            week_end = week_start + dt.timedelta(days=6) if week_start else None
            period_rows = [
                row for row in parsed_rows
                if week_start and week_end and week_start <= row["bucket_date"] <= week_end
            ]
            label = f"{year} W{iso_week:02d}"
        elif mode == "month":
            period_rows = [
                row for row in parsed_rows
                if row["bucket_date"].year == year and row["bucket_date"].month == anchor_date.month
            ]
            label = str(year)
        elif mode == "ytd":
            end_date = clamp_month_day(year, anchor_date.month, anchor_date.day)
            start_date = dt.date(year, 1, 1)
            period_rows = [
                row for row in parsed_rows
                if start_date <= row["bucket_date"] <= end_date
            ]
            label = str(year)
        else:
            raise ValueError(f"Unsupported comparison mode: {mode}")

        totals = sum_metric_rows(period_rows)
        labels.append(label)
        row_payload: Dict[str, str | float] = {"label": label}
        for metric, _, _ in METRIC_ORDER:
            metric_value = round(totals[metric] / 1000.0, 2)
            row_payload[metric_to_slug(metric)] = metric_value
            values_by_metric[metric].append(metric_value)
        table_rows.append(row_payload)

    if mode == "day":
        period_label = anchor_date.strftime("Same day each year: %b %d")
    elif mode == "week":
        period_label = f"Same ISO week each year: W{anchor_date.isocalendar().week:02d}"
    elif mode == "month":
        period_label = anchor_date.strftime("Same month each year: %B")
    else:
        period_label = anchor_date.strftime("Year to date through %b %d")

    series = []
    for metric, label, color in METRIC_ORDER:
        series.append(
            {
                "metric": metric_to_slug(metric),
                "label": label,
                "color": color,
                "values": values_by_metric[metric],
            }
        )

    return {
        "labels": labels,
        "series": series,
        "rows": table_rows,
        "period_label": period_label,
    }


def build_trend_payload(
    rows: Sequence[Dict[str, Any]],
    start_date: dt.date,
    end_date: dt.date,
    granularity: str,
    metrics: Sequence[str],
) -> Dict[str, Any]:
    parsed_rows = normalize_query_rows(rows, start_date=start_date, end_date=end_date)

    buckets: Dict[str, Dict[str, float]] = {}
    for row in parsed_rows:
        date_value = row["bucket_date"]
        if granularity == "day":
            bucket_label = date_value.isoformat()
        elif granularity == "week":
            bucket_label = start_of_iso_week(date_value).isoformat()
        elif granularity == "month":
            bucket_label = f"{date_value.year:04d}-{date_value.month:02d}"
        elif granularity == "year":
            bucket_label = f"{date_value.year:04d}"
        else:
            raise ValueError(f"Unsupported granularity: {granularity}")
        buckets.setdefault(bucket_label, {metric: 0.0 for metric, _, _ in METRIC_ORDER})
        for metric, _, _ in METRIC_ORDER:
            buckets[bucket_label][metric] += row[metric]

    labels = sorted(buckets)
    selected_metric_keys = {
        f"{metric}_wh" if not metric.endswith("_wh") else metric
        for metric in metrics
    }
    if not selected_metric_keys:
        selected_metric_keys = {"home_usage_wh"}

    series = []
    for metric, label, color in METRIC_ORDER:
        if metric not in selected_metric_keys:
            continue
        series.append(
            {
                "metric": metric_to_slug(metric),
                "label": label,
                "color": color,
                "values": [round(buckets[label_key][metric] / 1000.0, 2) for label_key in labels],
            }
        )

    table_rows = []
    for label in labels:
        table_rows.append(
            {
                "label": label,
                "solar_generation": round(buckets[label]["solar_generation_wh"] / 1000.0, 2),
                "home_usage": round(buckets[label]["home_usage_wh"] / 1000.0, 2),
                "grid_export": round(buckets[label]["grid_export_wh"] / 1000.0, 2),
                "grid_import": round(buckets[label]["grid_import_wh"] / 1000.0, 2),
            }
        )

    return {
        "labels": labels,
        "series": series,
        "rows": table_rows,
    }


def build_weekday_pattern_payload(
    rows: Sequence[Dict[str, Any]],
    start_date: dt.date,
    end_date: dt.date,
    metrics: Sequence[str],
    value_mode: str = "average",
) -> Dict[str, Any]:
    parsed_rows = normalize_query_rows(rows, start_date=start_date, end_date=end_date)
    if value_mode not in ("average", "total"):
        raise ValueError("Weekday pattern mode must be 'average' or 'total'.")
    selected_metric_keys = {
        f"{metric}_wh" if not metric.endswith("_wh") else metric
        for metric in metrics
    }
    if not selected_metric_keys:
        selected_metric_keys = {"solar_generation_wh", "home_usage_wh"}

    buckets: Dict[int, Dict[str, float]] = {
        index: {metric: 0.0 for metric, _, _ in METRIC_ORDER}
        for index in range(7)
    }
    counts = {index: 0 for index in range(7)}
    for row in parsed_rows:
        weekday = row["bucket_date"].weekday()
        counts[weekday] += 1
        for metric, _, _ in METRIC_ORDER:
            buckets[weekday][metric] += row[metric]

    labels = [label[:3] for label in WEEKDAY_LABELS]
    series = []
    for metric, label, color in METRIC_ORDER:
        if metric not in selected_metric_keys:
            continue
        values: List[float] = []
        for weekday in range(7):
            total_value = buckets[weekday][metric]
            if value_mode == "average" and counts[weekday] > 0:
                total_value /= counts[weekday]
            values.append(round(total_value / 1000.0, 2))
        series.append(
            {
                "metric": metric_to_slug(metric),
                "label": label,
                "color": color,
                "values": values,
            }
        )

    table_rows = []
    for weekday, label in enumerate(WEEKDAY_LABELS):
        row_payload = {"label": label, "samples": counts[weekday]}
        for metric, _, _ in METRIC_ORDER:
            total_value = buckets[weekday][metric]
            if value_mode == "average" and counts[weekday] > 0:
                total_value /= counts[weekday]
            row_payload[metric_to_slug(metric)] = round(total_value / 1000.0, 2)
        table_rows.append(row_payload)

    return {
        "labels": labels,
        "series": series,
        "rows": table_rows,
        "value_mode": value_mode,
        "sample_count": len(parsed_rows),
    }


def build_day_compare_payload(
    day_series: Sequence[Dict[str, Any]],
    metric: str,
) -> Dict[str, Any]:
    metric_info = DAY_COMPARE_METRICS.get(metric)
    if metric_info is None:
        raise RuntimeError("Unsupported day-compare metric.")
    all_labels = sorted(
        {label for series in day_series for label in series["values_by_time"].keys()},
        key=lambda value: dt.time.fromisoformat(value),
    )
    chart_series = []
    summary_rows = []
    series_count = len(day_series)
    for index, series in enumerate(day_series):
        chart_series.append(
            {
                "metric": series["date"],
                "label": series["label"],
                "color": palette_color(index, series_count, DAY_COMPARE_PALETTE),
                "values": [series["values_by_time"].get(label, 0.0) for label in all_labels],
            }
        )
        summary_rows.append(
            {
                "date": series["date"],
                "label": series["label"],
                "total_kwh": series["total_kwh"],
                "estimated_total_kwh": series["estimated_total_kwh"],
                "total_source": series["total_source"],
                "peak_kw": series["peak_kw"],
                "peak_time": series["peak_time"],
                "samples": series["sample_count"],
                "partial": series["partial"],
            }
        )
    return {
        "labels": all_labels,
        "series": chart_series,
        "rows": summary_rows,
        "metric": metric,
        "metric_label": metric_info["label"],
        "unit": metric_info["unit"],
        "axis_label": metric_info["unit"],
    }

