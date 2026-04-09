__version__ = "0.1.5"

from .common import (
    ARCHIVE_IMPORT_SCHEMA_VERSION,
    aggregate_daily_history_rows,
    normalize_history_row,
    resolve_tzinfo,
)
from .payloads import (
    build_comparison_payload,
    build_diagnostics_payload,
    build_insights_payload,
    build_trend_payload,
    build_weekday_pattern_payload,
    clamp_month_day,
)
from .scheduler import latest_scheduled_sync_utc
from .service import TeslaSolarDashboard, extract_history_rows
from .cli import main, normalize_cli_args

__all__ = [
    '__version__',
    'ARCHIVE_IMPORT_SCHEMA_VERSION',
    'TeslaSolarDashboard',
    'aggregate_daily_history_rows',
    'build_comparison_payload',
    'build_diagnostics_payload',
    'build_insights_payload',
    'build_trend_payload',
    'build_weekday_pattern_payload',
    'clamp_month_day',
    'extract_history_rows',
    'latest_scheduled_sync_utc',
    'main',
    'normalize_cli_args',
    'normalize_history_row',
    'resolve_tzinfo',
]
