from dataclasses import dataclass
from datetime import datetime, timedelta

from maestro.domains import AWAY, HOME
from maestro.integrations import StateChangeEvent
from maestro.triggers import state_change_trigger
from maestro.utils import JobScheduler, Notif, format_duration, local_now

from custom_domains import Emily, Marshall, ZoneExtended
from registry import person
from scripts.common.gates import Gate, gate_check
from scripts.location_tracking.queries import (
    get_last_left_home,
    get_last_zone_arrival,
    set_last_left_home,
    set_last_zone_arrival,
)

NOTIF_IDENTIFIER = "zone_update"
JOB_ID_PREFIX = f"{NOTIF_IDENTIFIER}_job_"

GATE_MAP = {
    person.emily.id: Gate.NOTIF_ON_EMILY_ZONE_CHANGE,
    person.marshall.id: Gate.NOTIF_ON_MARSHALL_ZONE_CHANGE,
}


@dataclass
class ZoneChangeEvent:
    name: str
    person: Marshall | Emily
    spouse: Marshall | Emily
    timestamp: datetime
    old_zone: str
    old_zone_is_region: bool
    old_zone_full: str
    new_zone: str
    new_zone_is_region: bool
    new_zone_full: str
    debounce: timedelta


def build_zone_change_event(state_change: StateChangeEvent) -> ZoneChangeEvent:
    person_ = state_change.entity_id.resolve_entity()
    spouse = person.emily if person_ == person.marshall else person.marshall
    if not isinstance(person_, Marshall | Emily):
        raise TypeError

    old_metadata = ZoneExtended.get_zone_metadata(state_change.old.state)
    new_metadata = ZoneExtended.get_zone_metadata(state_change.new.state)

    return ZoneChangeEvent(
        name=person_.entity_name,
        person=person_,
        spouse=spouse,
        timestamp=state_change.time_fired,
        old_zone=state_change.old.state,
        old_zone_is_region=old_metadata.region,
        old_zone_full=f"{old_metadata.prefix} {state_change.old.state}".lstrip(),
        new_zone=state_change.new.state,
        new_zone_is_region=new_metadata.region,
        new_zone_full=f"{new_metadata.prefix} {state_change.new.state}".lstrip(),
        debounce=new_metadata.debounce,
    )


@state_change_trigger(person.marshall, person.emily)
def location_update_orchestrator(state_change: StateChangeEvent) -> None:
    event = build_zone_change_event(state_change)
    scheduler = JobScheduler()
    job_id = JOB_ID_PREFIX + event.person.id.entity

    if event.old_zone == HOME:
        set_last_left_home(person=event.person, value=event.timestamp)

    if debounced_job := scheduler.get_job(job_id):
        scheduler.cancel_job(job_id)
        debounced_event: ZoneChangeEvent = debounced_job.kwargs.get("event")
        if event.old_zone == debounced_event.new_zone:
            return

    if event.debounce:
        scheduler.schedule_job(
            run_time=local_now() + event.debounce,
            func=send_location_update,
            func_params={"event": event},
            job_id=job_id,
        )
    else:
        send_location_update(event)


def send_location_update(event: ZoneChangeEvent) -> None:
    if not gate_check(gate=GATE_MAP[event.person.id], func_name="send_location_update"):
        return

    if not event.new_zone_is_region:
        message = f"{event.name} arrived at {event.new_zone_full}"

        if event.new_zone == HOME and (left_home := get_last_left_home(event.person)):
            duration = event.timestamp - left_home
            message += f" after {format_duration(duration)}"
            Notif(
                message=f"You were away for {format_duration(duration)}",
                group=NOTIF_IDENTIFIER,
            ).send(event.person)

    elif not event.old_zone_is_region:
        message = f"{event.name} left {event.old_zone_full}"

        if prev_zone_arrival_time := get_last_zone_arrival(event.person):
            duration = event.timestamp - prev_zone_arrival_time
            message += f" after {format_duration(duration)}"

            if event.old_zone != HOME and duration > timedelta(minutes=10):
                Notif(
                    message=f"You spent {format_duration(duration)} at {event.old_zone_full}",
                    group=NOTIF_IDENTIFIER,
                ).send(event.person)

    elif event.new_zone != AWAY:
        message = f"{event.name} is in {event.new_zone_full}"

    else:
        street = event.person.location.thoroughfare
        city = event.person.location.locality
        message = f"{event.name} left {event.old_zone_full} near {street} in {city}"

    set_last_zone_arrival(person=event.person, value=event.timestamp)

    Notif(
        message=message,
        group=NOTIF_IDENTIFIER,
    ).send(event.spouse)
