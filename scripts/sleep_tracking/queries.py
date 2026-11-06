from datetime import datetime, timedelta

from maestro import db
from maestro.integrations import StateManager
from maestro.utils import local_now

from .models import SleepEvent

SLEEP_HISTORY_LOCK = "sleep_history"


def save_sleep_event(timestamp: datetime, wakeup: bool) -> None:
    with StateManager().redis_client.lock(SLEEP_HISTORY_LOCK):
        sleep_event = SleepEvent(timestamp=timestamp, wakeup=wakeup)
        db.session.add(sleep_event)
        db.session.commit()


def get_last_event() -> SleepEvent:
    """Get the most recent sleep event."""
    latest_event = db.session.query(SleepEvent).order_by(SleepEvent.timestamp.desc()).first()

    if latest_event is None:
        midnight_today = local_now().replace(hour=0, minute=0, second=0, microsecond=0)
        latest_event = SleepEvent(timestamp=midnight_today, wakeup=False)

    if not isinstance(latest_event, SleepEvent) or not isinstance(latest_event.timestamp, datetime):
        raise TypeError

    return latest_event


def get_last_events(count: int = 1) -> list[SleepEvent]:
    """Get the most recent sleep events."""
    events: list[SleepEvent] = (
        db.session.query(SleepEvent).order_by(SleepEvent.timestamp.desc()).limit(count).all()
    )

    if not events:
        midnight_today = local_now().replace(hour=0, minute=0, second=0, microsecond=0)
        events = [SleepEvent(timestamp=midnight_today, wakeup=False)]

    return events


def delete_last_event() -> None:
    """Delete the most recent sleep event."""
    with StateManager().redis_client.lock(SLEEP_HISTORY_LOCK):
        latest_event = db.session.query(SleepEvent).order_by(SleepEvent.timestamp.desc()).first()
        if latest_event:
            db.session.delete(latest_event)
            db.session.commit()


def get_wake_windows(
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[tuple[datetime | None, datetime | None]]:
    """Return a list of 'wake window' tuples: (start, end) for the given time interval"""
    if start is None:
        start = local_now().replace(hour=0, minute=0, second=0, microsecond=0)
    if end is None:
        end = local_now()

    events: list[SleepEvent] = (
        db.session.query(SleepEvent)
        .filter(SleepEvent.timestamp >= start)
        .filter(SleepEvent.timestamp < end)
        .order_by(SleepEvent.timestamp.asc())
        .all()
    )

    if not events:
        return []

    wake_windows: list[tuple[datetime | None, datetime | None]] = []
    current_window_start: datetime | None = None

    for event in events:
        if not isinstance(event.wakeup, bool) or not isinstance(event.timestamp, datetime):
            raise TypeError

        if event.wakeup:
            current_window_start = event.timestamp
        else:
            if not current_window_start:
                wake_windows.append((None, event.timestamp))
            else:
                wake_windows.append((current_window_start, event.timestamp))
            current_window_start = None

    if current_window_start:
        wake_windows.append((current_window_start, None))

    return wake_windows


def get_awake_time(
    start: datetime | None = None,
    end: datetime | None = None,
) -> timedelta:
    """Calculate total awake time time for a given day."""
    if start is None:
        start = local_now().replace(hour=0, minute=0, second=0, microsecond=0)
    if end is None:
        end = local_now()

    wake_windows = get_wake_windows(start, end)
    total_wake_time = timedelta()

    for window in wake_windows:
        window_start = window[0] or start
        window_end = window[1] or end

        total_wake_time += window_end - window_start

    return total_wake_time
