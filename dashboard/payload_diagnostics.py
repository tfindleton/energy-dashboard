from __future__ import annotations

import datetime as dt
import statistics
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .common import DEFAULT_DIAGNOSTIC_WINDOW_DAYS, parse_dateish
from .payload_helpers import clamp_month_day, normalize_query_rows, sum_metric_rows

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

