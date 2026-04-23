from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any


DateLike = str | date | datetime | None


def parse_date_bound(value: DateLike) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone().date() if value.tzinfo else value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return value_to_local_date(int(text))
    if len(text) == 10:
        try:
            return date.fromisoformat(text)
        except ValueError:
            return None
    parsed = _parse_datetime_text(text)
    return parsed.astimezone().date() if parsed else None


def value_to_local_date(value: Any) -> date | None:
    dt = value_to_datetime(value)
    return dt.astimezone().date() if dt else None


def value_to_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=timezone.utc)
    if isinstance(value, int | float):
        seconds = value / 1000 if value > 10_000_000_000 else value
        return datetime.fromtimestamp(seconds, tz=timezone.utc)
    if isinstance(value, dict):
        for key in ("epochSecond", "time"):
            nested = value.get(key)
            if nested is not None:
                return value_to_datetime(nested)
        display = value.get("display")
        if isinstance(display, str):
            return _parse_datetime_text(display)
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            return value_to_datetime(int(text))
        return _parse_datetime_text(text)
    return None


def is_date_in_range(value: Any, *, from_date: DateLike = None, to_date: DateLike = None) -> bool:
    start = parse_date_bound(from_date)
    end = parse_date_bound(to_date)
    if start is None and end is None:
        return True
    current = value_to_local_date(value)
    if current is None:
        return False
    if start is not None and current < start:
        return False
    if end is not None and current > end:
        return False
    return True


def _parse_datetime_text(text: str) -> datetime | None:
    for candidate in (text, text.replace("Z", "+00:00")):
        try:
            parsed = datetime.fromisoformat(candidate)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    for fmt in ("%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M", "%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None
