from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import FrozenSet, Optional

DEFAULT_SYNC_CRON = "0 1 * * *"
_DISABLED_SYNC_VALUES = {"", "0", "off", "none", "disabled", "manual"}
_MAX_SCHEDULE_SCAN_MINUTES = 370 * 24 * 60


@dataclass(frozen=True)
class CronSchedule:
    raw: str
    minutes: FrozenSet[int]
    hours: FrozenSet[int]
    days_of_month: FrozenSet[int]
    months: FrozenSet[int]
    days_of_week: FrozenSet[int]
    dom_any: bool
    month_any: bool
    dow_any: bool


def _is_disabled(value: str) -> bool:
    return value.strip().lower() in _DISABLED_SYNC_VALUES


def _parse_field_value(raw: str, minimum: int, maximum: int, name: str, allow_sunday_7: bool = False) -> int:
    try:
        value = int(raw)
    except ValueError as error:
        raise RuntimeError(f"Invalid {name} value '{raw}'.") from error
    if allow_sunday_7 and value == 7:
        value = 0
    if value < minimum or value > maximum:
        raise RuntimeError(f"{name} values must be between {minimum} and {maximum}.")
    return value


def _field_is_full_range(values: set[int], minimum: int, maximum: int) -> bool:
    return values == set(range(minimum, maximum + 1))


def _parse_cron_field(raw: str, minimum: int, maximum: int, name: str, allow_sunday_7: bool = False) -> tuple[FrozenSet[int], bool]:
    values: set[int] = set()
    for part in raw.split(','):
        token = part.strip()
        if not token:
            raise RuntimeError(f"Invalid {name} field in cron expression.")
        if '/' in token:
            base, step_text = token.split('/', 1)
            try:
                step = int(step_text)
            except ValueError as error:
                raise RuntimeError(f"Invalid step '{step_text}' in {name} field.") from error
            if step <= 0:
                raise RuntimeError(f"{name} field step must be above 0.")
        else:
            base = token
            step = 1

        if base == '*':
            start = minimum
            end = maximum
        elif '-' in base:
            start_text, end_text = base.split('-', 1)
            start = _parse_field_value(start_text, minimum, maximum, name, allow_sunday_7=allow_sunday_7)
            end = _parse_field_value(end_text, minimum, maximum, name, allow_sunday_7=allow_sunday_7)
            if start > end:
                raise RuntimeError(f"Invalid range '{base}' in {name} field.")
        else:
            value = _parse_field_value(base, minimum, maximum, name, allow_sunday_7=allow_sunday_7)
            values.add(value)
            continue

        for value in range(start, end + 1, step):
            if allow_sunday_7 and value == 7:
                value = 0
            values.add(value)

    return frozenset(sorted(values)), _field_is_full_range(values, minimum, maximum)


def parse_sync_cron(value: str) -> Optional[CronSchedule]:
    raw = ' '.join(str(value or '').strip().split())
    if _is_disabled(raw):
        return None
    parts = raw.split(' ')
    if len(parts) != 5:
        raise RuntimeError("Sync cron must use five fields like '0 1 * * *', or 'off' to disable.")

    minutes, minute_any = _parse_cron_field(parts[0], 0, 59, 'minute')
    hours, hour_any = _parse_cron_field(parts[1], 0, 23, 'hour')
    days_of_month, dom_any = _parse_cron_field(parts[2], 1, 31, 'day-of-month')
    months, month_any = _parse_cron_field(parts[3], 1, 12, 'month')
    days_of_week, dow_any = _parse_cron_field(parts[4], 0, 6, 'day-of-week', allow_sunday_7=True)

    return CronSchedule(
        raw=raw,
        minutes=minutes,
        hours=hours,
        days_of_month=days_of_month,
        months=months,
        days_of_week=days_of_week,
        dom_any=dom_any,
        month_any=month_any,
        dow_any=dow_any,
    )


def normalize_sync_cron(value: str) -> str:
    schedule = parse_sync_cron(value)
    return 'off' if schedule is None else schedule.raw


def _cron_weekday(local_dt: dt.datetime) -> int:
    return (local_dt.weekday() + 1) % 7


def cron_matches(local_dt: dt.datetime, schedule: CronSchedule) -> bool:
    if local_dt.minute not in schedule.minutes or local_dt.hour not in schedule.hours:
        return False
    if local_dt.month not in schedule.months:
        return False

    dom_match = local_dt.day in schedule.days_of_month
    dow_match = _cron_weekday(local_dt) in schedule.days_of_week
    if schedule.dom_any and schedule.dow_any:
        return True
    if schedule.dom_any:
        return dow_match
    if schedule.dow_any:
        return dom_match
    return dom_match or dow_match


def _local_now(now: Optional[dt.datetime]) -> dt.datetime:
    if now is None:
        return dt.datetime.now().astimezone()
    if now.tzinfo is None:
        return now.replace(tzinfo=dt.timezone.utc).astimezone()
    return now.astimezone()


def next_scheduled_sync_utc(sync_cron: str, now: Optional[dt.datetime] = None) -> Optional[dt.datetime]:
    schedule = parse_sync_cron(sync_cron)
    if schedule is None:
        return None
    candidate = _local_now(now).replace(second=0, microsecond=0) + dt.timedelta(minutes=1)
    for _ in range(_MAX_SCHEDULE_SCAN_MINUTES):
        if cron_matches(candidate, schedule):
            return candidate.astimezone(dt.timezone.utc)
        candidate += dt.timedelta(minutes=1)
    raise RuntimeError(f"Unable to find the next run for sync cron '{schedule.raw}' within 370 days.")


def latest_scheduled_sync_utc(sync_cron: str, now: Optional[dt.datetime] = None) -> Optional[dt.datetime]:
    schedule = parse_sync_cron(sync_cron)
    if schedule is None:
        return None
    candidate = _local_now(now).replace(second=0, microsecond=0)
    for _ in range(_MAX_SCHEDULE_SCAN_MINUTES):
        if cron_matches(candidate, schedule):
            return candidate.astimezone(dt.timezone.utc)
        candidate -= dt.timedelta(minutes=1)
    raise RuntimeError(f"Unable to find the last run for sync cron '{schedule.raw}' within 370 days.")


def describe_sync_schedule(sync_cron: str) -> str:
    schedule = parse_sync_cron(sync_cron)
    if schedule is None:
        return 'Disabled'

    if len(schedule.minutes) == 1 and len(schedule.hours) == 1 and schedule.month_any:
        hour = next(iter(schedule.hours))
        minute = next(iter(schedule.minutes))
        time_label = dt.time(hour=hour, minute=minute).strftime('%I:%M %p').lstrip('0')
        if schedule.dom_any and schedule.dow_any:
            return f'Daily at {time_label}'
        if schedule.dom_any and schedule.days_of_week == frozenset({1, 2, 3, 4, 5}):
            return f'Weekdays at {time_label}'
        if schedule.dow_any and len(schedule.days_of_month) == 1:
            day = next(iter(schedule.days_of_month))
            suffix = 'th' if 10 <= day % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
            return f'Monthly on the {day}{suffix} at {time_label}'
    return f'Cron {schedule.raw}'


__all__ = [
    'DEFAULT_SYNC_CRON',
    'CronSchedule',
    'describe_sync_schedule',
    'latest_scheduled_sync_utc',
    'next_scheduled_sync_utc',
    'normalize_sync_cron',
    'parse_sync_cron',
]
