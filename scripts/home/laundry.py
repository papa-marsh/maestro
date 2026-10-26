from datetime import datetime, timedelta
from math import isfinite

from maestro import get_config
from maestro.integrations import StateChangeEvent
from maestro.triggers import state_change_trigger
from maestro.utils import JobScheduler, Notif, local_now

from registry import person, sensor

POWER_THRESHOLD = 10
COMPLETION_DELAY = timedelta(minutes=5)
COMPLETION_JOB_ID = "washer_cycle_complete"


def parse_power(state: str) -> float | None:
    try:
        power = float(state)
    except ValueError:
        return None
    return power if isfinite(power) else None


@state_change_trigger(sensor.washer_plug_power)
def washer_power_changed(state_change: StateChangeEvent) -> None:
    power = parse_power(state_change.new.state)
    if power is None or power >= POWER_THRESHOLD:
        JobScheduler().cancel_job(COMPLETION_JOB_ID)
        return

    old_power = parse_power(state_change.old.state)
    if old_power is None or old_power < POWER_THRESHOLD:
        return

    completed_at = state_change.time_fired.astimezone(get_config().timezone)
    JobScheduler().schedule_job(
        run_time=local_now() + COMPLETION_DELAY,
        func=notify_laundry_complete,
        func_params={"completed_at": completed_at},
        job_id=COMPLETION_JOB_ID,
    )


def notify_laundry_complete(completed_at: datetime) -> None:
    power = parse_power(sensor.washer_plug_power.state)
    if power is None or power >= POWER_THRESHOLD:
        return

    time = completed_at.strftime("%-I:%M%p").lower()
    Notif(
        title="Laundry's Done",
        message=f"The washing machine completed its cycle at {time}",
    ).send(person.marshall, person.emily)
