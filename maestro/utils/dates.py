from datetime import date, datetime, timedelta
from enum import IntEnum
from typing import Any

from maestro.config import TIMEZONE

SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 60 * SECONDS_PER_MINUTE
SECONDS_PER_DAY = 24 * SECONDS_PER_HOUR


class IntervalSeconds(IntEnum):
    FIFTEEN_MINUTES = 15 * SECONDS_PER_MINUTE
    THIRTY_MINUTES = 30 * SECONDS_PER_MINUTE
    ONE_HOUR = SECONDS_PER_HOUR
    NINETY_MINUTES = 90 * SECONDS_PER_MINUTE
    ONE_DAY = SECONDS_PER_DAY
    ONE_WEEK = 7 * SECONDS_PER_DAY
    TWO_WEEKS = 14 * SECONDS_PER_DAY
    THIRTY_DAYS = 30 * SECONDS_PER_DAY


def local_now() -> datetime:
    return datetime.now().astimezone(TIMEZONE)


def resolve_timestamp(iso_string: str) -> datetime:
    dt = datetime.fromisoformat(iso_string)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TIMEZONE)
    else:
        return dt.astimezone(TIMEZONE)


def format_duration(duration: timedelta, verbose: bool = False) -> str:
    """Format duration in a human-readable way."""
    duration_seconds = int(duration.total_seconds())
    if duration_seconds < SECONDS_PER_MINUTE:
        output = f"{duration_seconds}s"
        if verbose:
            return output.replace("s", " second" if duration_seconds == 1 else " seconds")

    output = ""
    total_seconds = duration_seconds

    if total_seconds > SECONDS_PER_DAY:
        days = duration_seconds // SECONDS_PER_DAY
        duration_seconds %= SECONDS_PER_DAY
        output += f"{days}d "
        if verbose:
            output = output.replace("d", " day " if days == 1 else " days ")

    if total_seconds > SECONDS_PER_HOUR:
        hours = duration_seconds // SECONDS_PER_HOUR
        duration_seconds %= SECONDS_PER_HOUR
        output += f"{hours}h "
        if verbose:
            output = output.replace("h", " hour " if hours == 1 else " hours ")

    minutes = duration_seconds // SECONDS_PER_MINUTE
    output += f"{minutes}m"
    if verbose:
        output = output.replace("m", " minute" if minutes == 1 else " minutes")

    return output


def serialize_datetimes(obj: Any) -> Any:
    """Recursively convert datetime objects to ISO format strings for JSON serialization"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: serialize_datetimes(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [serialize_datetimes(item) for item in obj]
    else:
        return obj


def readable_relative_date(target_date: datetime | date) -> str:
    """Returns a human-readable date string (eg. Today, Tomorrow, Thursday, or July 21)"""
    if isinstance(target_date, datetime):
        target_date = target_date.date()

    today = local_now().date()
    days_diff = (target_date - today).days

    if days_diff == 0:
        return "today"
    elif days_diff == 1:
        return "tomorrow"
    elif days_diff < 7:
        return target_date.strftime("%A")
    else:
        return target_date.strftime("%B %d")
