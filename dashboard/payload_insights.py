from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Sequence

from .payload_helpers import (
    classify_signal_tone,
    clamp_month_day,
    make_peak_item,
    normalize_query_rows,
    sum_metric_rows,
)

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

