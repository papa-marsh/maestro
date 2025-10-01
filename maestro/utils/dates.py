from datetime import datetime
from enum import IntEnum
from zoneinfo import ZoneInfo

from maestro.config import TIMEZONE

LOCAL_TZ = ZoneInfo(TIMEZONE)

SECONDS_PER_HOUR = 3600


class IntervalSeconds(IntEnum):
    ONE_HOUR = SECONDS_PER_HOUR
    ONE_DAY = 24 * SECONDS_PER_HOUR
    ONE_WEEK = 7 * 24 * SECONDS_PER_HOUR
    THIRTY_DAYS = 30 * 24 * SECONDS_PER_HOUR


def local_now() -> datetime:
    return datetime.now().astimezone(LOCAL_TZ)


def resolve_timestamp(iso_string: str) -> datetime:
    dt = datetime.fromisoformat(iso_string)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=LOCAL_TZ)
    else:
        return dt.astimezone(LOCAL_TZ)
