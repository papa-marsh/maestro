from datetime import datetime, timedelta

from maestro.domains import OFF, ON
from maestro.integrations import StateChangeEvent
from maestro.triggers import cron_trigger, state_change_trigger
from maestro.utils import JobScheduler, Notif, format_duration, local_now

from registry import binary_sensor, person, switch

ELLIE_SOUND_MACHINE_JOB_ID = "ellie_sound_machine_off_after_wakeup"


@cron_trigger(hour=19)
def ellie_sound_machine_on() -> None:
    switch.ellies_sound_machine.turn_on()


@cron_trigger(hour=8)
def ellie_sound_machine_off() -> None:
    switch.ellies_sound_machine.turn_off()


@state_change_trigger(switch.ellies_sound_machine)
def toggle_butterfly_light(state_change: StateChangeEvent) -> None:
    if state_change.new.state == "off":
        switch.butterfly_night_light.turn_on()
    else:
        switch.butterfly_night_light.turn_off()


@state_change_trigger(binary_sensor.ellie_bedroom_door, from_state=OFF, to_state=ON)
def notify_ellie_wakeup(state_change: StateChangeEvent) -> None:
    if not 4 <= state_change.time_fired.hour < 8:
        return

    last_closed = state_change.old.attributes.get("last_changed")
    if not isinstance(last_closed, datetime):
        raise TypeError

    duration = format_duration(state_change.time_fired - last_closed)
    wake_time = state_change.time_fired.strftime("%-I:%M")
    Notif(message=f"Ellie woke up at {wake_time} after {duration}").send(
        person.marshall, person.emily
    )


@state_change_trigger(binary_sensor.ellie_bedroom_door, from_state=OFF, to_state=ON)
def ellie_door_opened_at_wakeup(state_change: StateChangeEvent) -> None:
    if not 6 <= state_change.time_fired.hour < 8:
        return

    switch.master_sound_machine.turn_off()

    JobScheduler().schedule_job(
        run_time=local_now() + timedelta(minutes=2),
        func=ellie_sound_machine_off,
        job_id=ELLIE_SOUND_MACHINE_JOB_ID,
    )


@state_change_trigger(binary_sensor.ellie_bedroom_door, from_state=ON, to_state=OFF)
def cancel_ellie_sound_machine_job() -> None:
    JobScheduler().cancel_job(ELLIE_SOUND_MACHINE_JOB_ID)
