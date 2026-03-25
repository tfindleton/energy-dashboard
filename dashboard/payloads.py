from __future__ import annotations

import calendar
import datetime as dt
import statistics
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .common import (
    DAY_COMPARE_METRICS,
    DAY_COMPARE_PALETTE,
    DEFAULT_DIAGNOSTIC_WINDOW_DAYS,
    METRIC_ORDER,
    WEEKDAY_LABELS,
    palette_color,
    parse_dateish,
    slugify,
)

def clamp_month_day(year: int, month: int, day: int) -> dt.date:
    last_day = calendar.monthrange(year, month)[1]
    return dt.date(year, month, min(day, last_day))


def metric_to_slug(metric_key: str) -> str:
    return metric_key.replace("_wh", "")


def metric_series_definition() -> List[Dict[str, str]]:
    return [
        {"metric": metric_to_slug(key), "label": label, "color": color}
        for key, label, color in METRIC_ORDER
    ]


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


def build_insights_payload(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    parsed_rows = normalize_query_rows(rows)
    if not parsed_rows:
        return {"sections": [], "summary": ""}

    data_start = min(row["bucket_date"] for row in parsed_rows)
    data_end = max(row["bucket_date"] for row in parsed_rows)
    current_year_start = dt.date(data_end.year, 1, 1)
    previous_year_start = dt.date(data_end.year - 1, 1, 1)
    previous_year_end = clamp_month_day(data_end.year - 1, data_end.month, data_end.day)
    current_year_rows = [row for row in parsed_rows if current_year_start <= row["bucket_date"] <= data_end]
    previous_year_rows = [row for row in parsed_rows if previous_year_start <= row["bucket_date"] <= previous_year_end]
    current_year_totals = sum_metric_rows(current_year_rows)
    previous_year_totals = sum_metric_rows(previous_year_rows)

    self_power_pct = None
    if current_year_totals["home_usage_wh"] > 0:
        self_power_pct = max(
            0.0,
            min(
                100.0,
                (1.0 - (current_year_totals["grid_import_wh"] / current_year_totals["home_usage_wh"])) * 100.0,
            ),
        )

    export_share_pct = None
    if current_year_totals["solar_generation_wh"] > 0:
        export_share_pct = max(
            0.0,
            min(
                100.0,
                (current_year_totals["grid_export_wh"] / current_year_totals["solar_generation_wh"]) * 100.0,
            ),
        )

    solar_delta_pct = None
    if previous_year_totals["solar_generation_wh"] > 0:
        solar_delta_pct = (
            (current_year_totals["solar_generation_wh"] - previous_year_totals["solar_generation_wh"])
            / previous_year_totals["solar_generation_wh"]
        ) * 100.0

    current_year_label = str(data_end.year)
    sections = [
        {
            "title": "Lifetime Solar Peaks",
            "accent": "solar",
            "items": [
                make_peak_item(parsed_rows, "Best Day", "day", "solar_generation_wh"),
                make_peak_item(parsed_rows, "Best Week", "week", "solar_generation_wh"),
                make_peak_item(parsed_rows, "Best Month", "month", "solar_generation_wh"),
                make_peak_item(parsed_rows, "Best Year", "year", "solar_generation_wh"),
            ],
        },
        {
            "title": "Lifetime Load Peaks",
            "accent": "load",
            "items": [
                make_peak_item(parsed_rows, "Highest Day", "day", "home_usage_wh"),
                make_peak_item(parsed_rows, "Highest Week", "week", "home_usage_wh"),
                make_peak_item(parsed_rows, "Highest Month", "month", "home_usage_wh"),
                make_peak_item(parsed_rows, "Highest Year", "year", "home_usage_wh"),
            ],
        },
        {
            "title": f"{current_year_label} Solar Peaks",
            "accent": "solar",
            "items": [
                make_peak_item(
                    parsed_rows,
                    "Best Day This Year",
                    "day",
                    "solar_generation_wh",
                    start_date=current_year_start,
                    end_date=data_end,
                ),
                make_peak_item(
                    parsed_rows,
                    "Best Week This Year",
                    "week",
                    "solar_generation_wh",
                    start_date=current_year_start,
                    end_date=data_end,
                ),
                make_peak_item(
                    parsed_rows,
                    "Best Month This Year",
                    "month",
                    "solar_generation_wh",
                    start_date=current_year_start,
                    end_date=data_end,
                ),
                {
                    "label": "Solar YTD",
                    "value": round(current_year_totals["solar_generation_wh"] / 1000.0, 2),
                    "kind": "energy",
                    "hint": f"Through {data_end.isoformat()}",
                },
            ],
        },
        {
            "title": f"{current_year_label} Load Peaks",
            "accent": "load",
            "items": [
                make_peak_item(
                    parsed_rows,
                    "Highest Day This Year",
                    "day",
                    "home_usage_wh",
                    start_date=current_year_start,
                    end_date=data_end,
                ),
                make_peak_item(
                    parsed_rows,
                    "Highest Week This Year",
                    "week",
                    "home_usage_wh",
                    start_date=current_year_start,
                    end_date=data_end,
                ),
                make_peak_item(
                    parsed_rows,
                    "Highest Month This Year",
                    "month",
                    "home_usage_wh",
                    start_date=current_year_start,
                    end_date=data_end,
                ),
                {
                    "label": "Usage YTD",
                    "value": round(current_year_totals["home_usage_wh"] / 1000.0, 2),
                    "kind": "energy",
                    "hint": f"Through {data_end.isoformat()}",
                },
            ],
        },
        {
            "title": "Action Signals",
            "accent": "signal",
            "items": [
                {
                    "label": "Self-Powered YTD",
                    "value": None if self_power_pct is None else round(self_power_pct, 1),
                    "kind": "percent",
                    "hint": f"Through {data_end.isoformat()}",
                    "tone": classify_signal_tone(self_power_pct, "self_power"),
                },
                {
                    "label": "Solar YTD vs Last Year",
                    "value": None if solar_delta_pct is None else round(solar_delta_pct, 1),
                    "kind": "delta_percent",
                    "hint": f"Compared through {previous_year_end.isoformat()}",
                    "tone": classify_signal_tone(solar_delta_pct, "solar_delta"),
                },
                {
                    "label": "Export Share YTD",
                    "value": None if export_share_pct is None else round(export_share_pct, 1),
                    "kind": "percent",
                    "hint": "Share of generated solar exported to grid",
                    "tone": classify_signal_tone(export_share_pct, "export_share"),
                },
            ],
        },
    ]

    return {
        "summary": f"Lifetime peaks and current-year signals through {data_end.isoformat()}",
        "sections": sections,
        "data_start": data_start.isoformat(),
        "data_end": data_end.isoformat(),
    }


def iter_date_range(start_date: dt.date, end_date: dt.date) -> Iterable[dt.date]:
    cursor = start_date
    while cursor <= end_date:
        yield cursor
        cursor += dt.timedelta(days=1)


def seasonal_window_year_medians(
    rows_by_date: Dict[dt.date, Dict[str, Any]],
    current_date: dt.date,
    metric: str,
    prior_years: Sequence[int],
    window_days: int = DEFAULT_DIAGNOSTIC_WINDOW_DAYS,
) -> List[Dict[str, Any]]:
    rows = []
    for year in prior_years:
        values = []
        for offset in range(-window_days, window_days + 1):
            peer_date = clamp_month_day(year, current_date.month, current_date.day) + dt.timedelta(days=offset)
            peer_row = rows_by_date.get(peer_date)
            if peer_row is None:
                continue
            values.append(float(peer_row.get(metric, 0.0) or 0.0))
        if not values:
            continue
        rows.append(
            {
                "year": year,
                "median_wh": statistics.median(values),
                "min_wh": min(values),
                "max_wh": max(values),
                "samples": len(values),
            }
        )
    return rows


def format_year_history_summary(year_rows: Sequence[Dict[str, Any]]) -> str:
    return " | ".join(
        f"{int(row['year'])}: {round(float(row['median_wh']) / 1000.0, 1)}"
        for row in year_rows
    )


def format_history_range_hint(year_rows: Sequence[Dict[str, Any]]) -> str:
    if not year_rows:
        return "No prior-year window data"
    values = [float(row["median_wh"]) / 1000.0 for row in year_rows]
    return f"{round(min(values), 1)} to {round(max(values), 1)} kWh across {len(year_rows)} prior years"


def group_consecutive_rows(rows: Sequence[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    ordered = sorted(
        [dict(row) for row in rows],
        key=lambda item: parse_dateish(item.get("date")) or dt.date.min,
    )
    groups: List[List[Dict[str, Any]]] = []
    current_group: List[Dict[str, Any]] = []
    previous_date: Optional[dt.date] = None
    for row in ordered:
        row_date = parse_dateish(row.get("date"))
        if row_date is None:
            continue
        if previous_date is None or row_date == previous_date + dt.timedelta(days=1):
            current_group.append(row)
        else:
            if current_group:
                groups.append(current_group)
            current_group = [row]
        previous_date = row_date
    if current_group:
        groups.append(current_group)
    return groups


def solar_streak_threshold(date_value: dt.date) -> int:
    if date_value.month in (6, 7, 8):
        return 2
    if date_value.month in (3, 4, 5, 9, 10):
        return 3
    return 4


def annotate_streak_rows(
    streaks: Sequence[Sequence[Dict[str, Any]]],
    metric_kind: str,
) -> Tuple[List[Dict[str, Any]], int]:
    annotated_rows: List[Dict[str, Any]] = []
    for streak in streaks:
        if not streak:
            continue
        start_date = streak[0]["date"]
        end_date = streak[-1]["date"]
        run_days = len(streak)
        if run_days == 1:
            run_label = start_date
        else:
            run_label = f"{start_date} to {end_date} ({run_days} days)"
        for row in streak:
            annotated = dict(row)
            annotated["run_label"] = run_label
            annotated["run_days"] = run_days
            annotated_rows.append(annotated)
    if metric_kind == "solar":
        annotated_rows.sort(key=lambda row: (float(row["delta_kwh"]), row["date"]))
    else:
        annotated_rows.sort(key=lambda row: (-float(row["delta_kwh"]), row["date"]))
    return annotated_rows, len(streaks)


def seasonal_window_history_values(
    rows_by_date: Dict[dt.date, Dict[str, Any]],
    current_date: dt.date,
    metric: str,
    prior_years: Sequence[int],
    window_days: int = DEFAULT_DIAGNOSTIC_WINDOW_DAYS,
) -> List[float]:
    values = []
    for row in seasonal_window_year_medians(rows_by_date, current_date, metric, prior_years, window_days=window_days):
        values.append(float(row["median_wh"]))
    return values


def historical_baseline_total(
    rows_by_date: Dict[dt.date, Dict[str, Any]],
    dates: Sequence[dt.date],
    metric: str,
    prior_years: Sequence[int],
    window_days: int = DEFAULT_DIAGNOSTIC_WINDOW_DAYS,
) -> Tuple[float, int]:
    total = 0.0
    comparable_days = 0
    for current_date in dates:
        values = seasonal_window_history_values(rows_by_date, current_date, metric, prior_years, window_days=window_days)
        if not values:
            continue
        total += statistics.median(values)
        comparable_days += 1
    return total, comparable_days


def classify_diagnostic_delta_tone(value: Optional[float], low_is_bad: bool) -> str:
    if value is None:
        return ""
    if low_is_bad:
        if value <= -15:
            return "bad"
        if value <= -7:
            return "warning"
        if value >= 5:
            return "good"
    else:
        if value >= 15:
            return "bad"
        if value >= 7:
            return "warning"
        if value <= -5:
            return "good"
    return ""


def make_diagnostic_delta_item(
    label: str,
    current_total_wh: float,
    baseline_total_wh: float,
    comparable_days: int,
    low_is_bad: bool,
) -> Dict[str, Any]:
    if baseline_total_wh <= 0 or comparable_days == 0:
        return {
            "label": label,
            "value": None,
            "kind": "delta_percent",
            "hint": "Not enough prior-year history for this window.",
            "tone": "",
        }
    delta_percent = ((current_total_wh - baseline_total_wh) / baseline_total_wh) * 100.0
    return {
        "label": label,
        "value": round(delta_percent, 1),
        "kind": "delta_percent",
        "hint": f"{round(current_total_wh / 1000.0, 1)} kWh vs {round(baseline_total_wh / 1000.0, 1)} kWh prior-year median",
        "tone": classify_diagnostic_delta_tone(delta_percent, low_is_bad),
    }


def build_diagnostics_payload(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    parsed_rows = normalize_query_rows(rows)
    if not parsed_rows:
        return {"summary": "", "sections": [], "alerts": [], "tables": []}

    today = dt.date.today()
    if any(row["bucket_date"] == today for row in parsed_rows):
        complete_rows = [row for row in parsed_rows if row["bucket_date"] < today]
        if complete_rows:
            parsed_rows = complete_rows

    rows_by_date = {row["bucket_date"]: row for row in parsed_rows}
    data_start = min(row["bucket_date"] for row in parsed_rows)
    data_end = max(row["bucket_date"] for row in parsed_rows)
    current_year = data_end.year
    prior_years = sorted({row["bucket_date"].year for row in parsed_rows if row["bucket_date"].year < current_year})
    current_year_rows = [row for row in parsed_rows if row["bucket_date"].year == current_year]

    trailing_30_start = max(data_start, data_end - dt.timedelta(days=29))
    month_start = dt.date(data_end.year, data_end.month, 1)

    current_trailing_30_rows = normalize_query_rows(rows, start_date=trailing_30_start, end_date=data_end)
    current_month_rows = normalize_query_rows(rows, start_date=month_start, end_date=data_end)
    trailing_30_dates = [row["bucket_date"] for row in current_trailing_30_rows]
    current_month_dates = [row["bucket_date"] for row in current_month_rows]
    trailing_30_totals = sum_metric_rows(current_trailing_30_rows)
    month_totals = sum_metric_rows(current_month_rows)

    solar_baseline_30, solar_days_30 = historical_baseline_total(
        rows_by_date, trailing_30_dates, "solar_generation_wh", prior_years
    )
    usage_baseline_30, usage_days_30 = historical_baseline_total(
        rows_by_date, trailing_30_dates, "home_usage_wh", prior_years
    )
    grid_import_baseline_30, grid_import_days_30 = historical_baseline_total(
        rows_by_date, trailing_30_dates, "grid_import_wh", prior_years
    )
    solar_baseline_month, solar_days_month = historical_baseline_total(
        rows_by_date, current_month_dates, "solar_generation_wh", prior_years
    )
    usage_baseline_month, usage_days_month = historical_baseline_total(
        rows_by_date, current_month_dates, "home_usage_wh", prior_years
    )

    self_power_pct = None
    if trailing_30_totals["home_usage_wh"] > 0:
        self_power_pct = max(
            0.0,
            min(
                100.0,
                (1.0 - (trailing_30_totals["grid_import_wh"] / trailing_30_totals["home_usage_wh"])) * 100.0,
            ),
        )

    low_solar_days = []
    high_usage_days = []
    for row in current_year_rows:
        current_date = row["bucket_date"]
        solar_year_rows = seasonal_window_year_medians(
            rows_by_date,
            current_date,
            "solar_generation_wh",
            prior_years,
        )
        solar_baseline_values = [float(item["median_wh"]) for item in solar_year_rows]
        if solar_baseline_values:
            solar_baseline = statistics.median(solar_baseline_values)
            solar_delta = row["solar_generation_wh"] - solar_baseline
            if solar_baseline >= 4000 and row["solar_generation_wh"] < solar_baseline * 0.75 and solar_delta <= -4000:
                low_solar_days.append(
                    {
                        "date": current_date.isoformat(),
                        "actual_kwh": round(row["solar_generation_wh"] / 1000.0, 2),
                        "expected_kwh": round(solar_baseline / 1000.0, 2),
                        "delta_kwh": round(solar_delta / 1000.0, 2),
                        "history_summary": format_year_history_summary(solar_year_rows),
                        "history_hint": format_history_range_hint(solar_year_rows),
                        "usage_kwh": round(row["home_usage_wh"] / 1000.0, 2),
                        "inspect_metric": "solar_power",
                    }
                )

        usage_year_rows = seasonal_window_year_medians(
            rows_by_date,
            current_date,
            "home_usage_wh",
            prior_years,
        )
        usage_baseline_values = [float(item["median_wh"]) for item in usage_year_rows]
        if usage_baseline_values:
            usage_baseline = statistics.median(usage_baseline_values)
            usage_delta = row["home_usage_wh"] - usage_baseline
            if usage_baseline >= 6000 and row["home_usage_wh"] > usage_baseline * 1.25 and usage_delta >= 5000:
                high_usage_days.append(
                    {
                        "date": current_date.isoformat(),
                        "actual_kwh": round(row["home_usage_wh"] / 1000.0, 2),
                        "expected_kwh": round(usage_baseline / 1000.0, 2),
                        "delta_kwh": round(usage_delta / 1000.0, 2),
                        "history_summary": format_year_history_summary(usage_year_rows),
                        "history_hint": format_history_range_hint(usage_year_rows),
                        "solar_kwh": round(row["solar_generation_wh"] / 1000.0, 2),
                        "inspect_metric": "load_power",
                    }
                )

    low_solar_streaks = [
        streak
        for streak in group_consecutive_rows(low_solar_days)
        if streak and len(streak) >= solar_streak_threshold(parse_dateish(streak[0]["date"]) or data_end)
    ]
    high_usage_streaks = [
        streak
        for streak in group_consecutive_rows(high_usage_days)
        if len(streak) >= 2
    ]
    persistent_low_solar_days, low_solar_run_count = annotate_streak_rows(low_solar_streaks, "solar")
    persistent_high_usage_days, high_usage_run_count = annotate_streak_rows(high_usage_streaks, "usage")

    solar_30_item = make_diagnostic_delta_item(
        "Last 30 Days vs Prior Years",
        trailing_30_totals["solar_generation_wh"],
        solar_baseline_30,
        solar_days_30,
        low_is_bad=True,
    )
    solar_month_item = make_diagnostic_delta_item(
        "Current Month vs Prior Years",
        month_totals["solar_generation_wh"],
        solar_baseline_month,
        solar_days_month,
        low_is_bad=True,
    )
    usage_30_item = make_diagnostic_delta_item(
        "Last 30 Days vs Prior Years",
        trailing_30_totals["home_usage_wh"],
        usage_baseline_30,
        usage_days_30,
        low_is_bad=False,
    )
    usage_month_item = make_diagnostic_delta_item(
        "Current Month vs Prior Years",
        month_totals["home_usage_wh"],
        usage_baseline_month,
        usage_days_month,
        low_is_bad=False,
    )
    grid_30_item = make_diagnostic_delta_item(
        "Grid Import Last 30 Days",
        trailing_30_totals["grid_import_wh"],
        grid_import_baseline_30,
        grid_import_days_30,
        low_is_bad=False,
    )

    sections = [
        {
            "title": "Solar Watch",
            "accent": "solar",
            "items": [
                solar_30_item,
                solar_month_item,
                {
                    "label": "Persistent Low Solar Runs",
                    "value": low_solar_run_count,
                    "kind": "runs",
                    "hint": (
                        f"Only consecutive low-output runs are surfaced "
                        f"({len(persistent_low_solar_days)} affected days)"
                    ),
                    "tone": "bad" if low_solar_run_count >= 2 else "warning" if low_solar_run_count == 1 else "good",
                },
            ],
        },
        {
            "title": "Load Watch",
            "accent": "load",
            "items": [
                usage_30_item,
                usage_month_item,
                {
                    "label": "Persistent High Usage Runs",
                    "value": high_usage_run_count,
                    "kind": "runs",
                    "hint": (
                        f"Only consecutive high-usage runs are surfaced "
                        f"({len(persistent_high_usage_days)} affected days)"
                    ),
                    "tone": "bad" if high_usage_run_count >= 2 else "warning" if high_usage_run_count == 1 else "good",
                },
            ],
        },
        {
            "title": "Grid Dependence",
            "accent": "signal",
            "items": [
                grid_30_item,
                {
                    "label": "Self-Powered Last 30 Days",
                    "value": None if self_power_pct is None else round(self_power_pct, 1),
                    "kind": "percent",
                    "hint": f"Through {data_end.isoformat()}",
                    "tone": "good" if self_power_pct is not None and self_power_pct >= 80 else "warning" if self_power_pct is not None and self_power_pct < 60 else "",
                },
                {
                    "label": "Recent Grid Import",
                    "value": round(trailing_30_totals["grid_import_wh"] / 1000.0, 2),
                    "kind": "energy",
                    "hint": f"Trailing 30 days ending {data_end.isoformat()}",
                    "tone": grid_30_item["tone"],
                },
            ],
        },
    ]

    alerts = []
    if low_solar_run_count > 0 or (solar_30_item["tone"] == "bad" and solar_month_item["tone"] == "bad"):
        alerts.append(
            {
                "tone": "bad" if low_solar_run_count > 0 or "bad" in (solar_30_item["tone"], solar_month_item["tone"]) else "warning",
                "title": "Solar output is below seasonal baseline",
                "body": (
                    "Check panel cleanliness, new shade, inverter alerts, or whether export has fallen while usage stayed flat. "
                    "Isolated storm days are suppressed unless they develop into a seasonally suspicious run."
                ),
            }
        )
    if low_solar_run_count > 0:
        alerts.append(
            {
                "tone": "warning",
                "title": "Low-solar streaks were flagged this year",
                "body": "Review the suspect-day list for consecutive weak-production runs compared with prior-year seasonal windows.",
            }
        )
    if high_usage_run_count > 0 or (usage_30_item["tone"] == "bad" and usage_month_item["tone"] == "bad"):
        alerts.append(
            {
                "tone": "bad" if high_usage_run_count > 0 or "bad" in (usage_30_item["tone"], usage_month_item["tone"]) else "warning",
                "title": "Home usage is elevated versus prior years",
                "body": (
                    "Check HVAC runtime, EV charging, water heating, pool pumps, or backup heat loads before assuming solar is the only issue. "
                    "Single recurring spike days are suppressed unless they turn into a sustained run."
                ),
            }
        )
    if grid_30_item["tone"] in ("bad", "warning"):
        alerts.append(
            {
                "tone": grid_30_item["tone"],
                "title": "Grid dependence is trending up",
                "body": "Higher recent grid import can reinforce either a production drop, a usage spike, or both. Compare the solar and load watch cards together.",
            }
        )

    tables = [
        {
            "title": "Potential Low Solar Days",
            "description": (
                f"Actual solar is compared against prior-year seasonal medians using a ±{DEFAULT_DIAGNOSTIC_WINDOW_DAYS} day window. "
                "Only days inside seasonally suspicious consecutive runs are shown. Home usage is context for the same day."
            ),
            "rows": persistent_low_solar_days[:8],
            "columns": [
                {"key": "run_label", "label": "Run"},
                {"key": "date", "label": "Date"},
                {"key": "actual_kwh", "label": "Actual Solar", "unit": "kWh"},
                {"key": "expected_kwh", "label": "Expected Solar", "unit": "kWh"},
                {"key": "delta_kwh", "label": "Solar Delta", "unit": "kWh"},
                {"key": "history_summary", "label": "Prior-Year Solar", "type": "history"},
                {"key": "usage_kwh", "label": "Home Usage", "unit": "kWh"},
                {"key": "inspect_metric", "label": "Inspect", "type": "action"},
            ],
        },
        {
            "title": "Potential High Usage Days",
            "description": (
                f"Actual home usage is compared against prior-year seasonal medians using a ±{DEFAULT_DIAGNOSTIC_WINDOW_DAYS} day window. "
                "Only days inside sustained consecutive runs are shown. Solar generation is context for the same day."
            ),
            "rows": persistent_high_usage_days[:8],
            "columns": [
                {"key": "run_label", "label": "Run"},
                {"key": "date", "label": "Date"},
                {"key": "actual_kwh", "label": "Actual Usage", "unit": "kWh"},
                {"key": "expected_kwh", "label": "Expected Usage", "unit": "kWh"},
                {"key": "delta_kwh", "label": "Usage Delta", "unit": "kWh"},
                {"key": "history_summary", "label": "Prior-Year Usage", "type": "history"},
                {"key": "solar_kwh", "label": "Solar Generation", "unit": "kWh"},
                {"key": "inspect_metric", "label": "Inspect", "type": "action"},
            ],
        },
    ]

    return {
        "summary": (
            f"Seasonal baselines use all prior years within ±{DEFAULT_DIAGNOSTIC_WINDOW_DAYS} day windows "
            f"through {data_end.isoformat()} to smooth one-off weather swings."
        ),
        "sections": sections,
        "alerts": alerts,
        "tables": tables,
        "data_start": data_start.isoformat(),
        "data_end": data_end.isoformat(),
    }


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
        row_payload = {"label": label}
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

