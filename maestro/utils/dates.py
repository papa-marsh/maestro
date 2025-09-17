from datetime import datetime
from zoneinfo import ZoneInfo

from maestro.config import TIMEZONE

LOCAL_TZ = ZoneInfo(TIMEZONE)


def local_now() -> datetime:
    return datetime.now().astimezone(LOCAL_TZ)


def resolve_timestamp(iso_string: str) -> datetime:
    dt = datetime.fromisoformat(iso_string)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=LOCAL_TZ)
    else:
        return dt.astimezone(LOCAL_TZ)
