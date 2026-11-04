from datetime import timedelta

from maestro.domains import Person
from maestro.integrations import FiredEvent
from maestro.triggers import event_fired_trigger
from maestro.utils import Notif, format_duration, local_now

from registry import person
from scripts.common.event_type import EventType
from scripts.config.secrets import USER_ID_TO_PERSON

from .queries import (
    delete_last_event,
    get_awake_time,
    get_last_event,
    get_wake_windows,
    save_sleep_event,
)

FALSE_ALARM_THRESHOLD = timedelta(minutes=20)

NOTIF_TITLE = "Sleep Tracker"
NOTIF_ID = "sleep_tracker"


def sleep_tracker_notify(
    message: str,
    target: Person | list[Person] = [person.marshall, person.emily],
) -> None:
    targets = [target] if not isinstance(target, list) else target
    Notif(
        message=message,
        title=NOTIF_TITLE,
        tag=NOTIF_ID,
    ).send(*targets)


def notif_message(duration: str, total_duration: str, wakeup: bool) -> str:
    event_text = "woke up" if wakeup else "went to sleep"
    return f"Olivia {event_text} after {duration}\nWake time today: {total_duration}"


@event_fired_trigger(EventType.OLIVIA_ASLEEP)
@event_fired_trigger(EventType.OLIVIA_AWAKE)
def olivia_sleep_event(event: FiredEvent) -> None:
    wakeup = event.type == "olivia_awake"
    olivia_state = event.type.split("_")[1]
    now = local_now()
    last_event = get_last_event()

    if last_event.wakeup == wakeup:
        sleep_tracker_notify(f"Olivia is already {olivia_state}", target=person.emily)
        return

    if now - last_event.timestamp < FALSE_ALARM_THRESHOLD:
        delete_last_event()
        last_event = get_last_event()
        duration = format_duration(now - last_event.timestamp)
        sleep_tracker_notify(f"False alarm. Olivia has been {olivia_state} for {duration}")
        return

    duration = format_duration(now - last_event.timestamp)
    save_sleep_event(timestamp=now, wakeup=wakeup)
    total_duration = format_duration(get_awake_time())

    message = notif_message(duration, total_duration, wakeup=wakeup)
    sleep_tracker_notify(message)


@event_fired_trigger(EventType.OLIVIA_INFO)
def olivia_info(event: FiredEvent) -> None:
    now = local_now()
    last_event = get_last_event()

    duration = format_duration(now - last_event.timestamp)
    awake_time = get_awake_time(end=now)
    total_duration = format_duration(awake_time)
    wake_windows = get_wake_windows(end=now)
    bedtime = now + timedelta(hours=11) - awake_time
    if not any(start and end for start, end in wake_windows):
        bedtime += timedelta(minutes=90)

    state = "awake" if last_event.wakeup else "asleep"
    message = (
        f"Bedtime: ~{bedtime.strftime('%-I:%M')}\n"
        f"Olivia has been {state} for {duration}\nWake time today: {total_duration}\n"
    )

    for wake_window in wake_windows:
        start, end = wake_window
        start_str = start.strftime("%-I:%M%P") if start else ""
        end_str = end.strftime("%-I:%M%P") if end else ""

        if start is None and end:
            message += f"\nAwake until {end_str}"
        if start and end:
            duration = format_duration(end - start)
            message += f"\n{start_str}-{end_str} ({duration})"
        if start and end is None:
            duration = format_duration(local_now() - start)
            message += f"\nAwake since {start_str} ({duration})"

    if target := USER_ID_TO_PERSON.get(event.user_id or ""):
        sleep_tracker_notify(message, target)
