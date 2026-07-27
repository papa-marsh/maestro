from datetime import timedelta

from maestro.domains import OFF, ON, UNAVAILABLE, BinarySensor
from maestro.integrations import EntityId, NotifActionEvent, StateChangeEvent
from maestro.triggers import notif_action_trigger, state_change_trigger
from maestro.utils import JobScheduler, Notif, format_duration, local_now

from registry import binary_sensor, person

PROCESS_ID_PREFIX = "door_left_open"
SILENCE_NOTIF_ACTION_ID = "silence_door_notif"

EXTERIOR_DOORS: list[BinarySensor] = [
    binary_sensor.front_door,
    binary_sensor.garage_door,
    binary_sensor.service_door,
    binary_sensor.slider_door,
]
GARAGE_STALLS: list[BinarySensor] = [binary_sensor.east_stall, binary_sensor.west_stall]

NOTIFICATION_TIMES: list[timedelta] = [
    timedelta(minutes=10),
    timedelta(minutes=30),
    timedelta(minutes=60),
    timedelta(minutes=120),
]


def get_process_id(entity_id: EntityId) -> str:
    return f"{PROCESS_ID_PREFIX}_{entity_id.entity}"


def get_job_id(entity_id: EntityId, time: timedelta) -> str:
    return f"{get_process_id(entity_id)}_{int(time.total_seconds())}"


@state_change_trigger(*EXTERIOR_DOORS, *GARAGE_STALLS, to_state=ON)
def schedule_notifications(state_change: StateChangeEvent) -> None:
    if state_change.old.state == UNAVAILABLE:
        return

    scheduler = JobScheduler()
    now = local_now()
    door = state_change.entity_id.resolve_entity()

    for time in NOTIFICATION_TIMES:
        job_id = get_job_id(entity_id=state_change.entity_id, time=time)
        scheduler.schedule_job(
            run_time=now + time,
            func=send_notifications,
            func_params={"door": door, "duration": time},
            job_id=job_id,
        )


def send_notifications(door: BinarySensor, duration: timedelta) -> None:
    duration_str = format_duration(duration, verbose=True).replace(" 0 minutes", "")
    silence_action = Notif.build_action(
        name=SILENCE_NOTIF_ACTION_ID,
        title="Silence",
    )

    Notif(
        title="Door Left Open",
        message=f"{door.friendly_name} has been open for {duration_str}",
        group=PROCESS_ID_PREFIX,
        tag=get_process_id(door.id),
        actions=[silence_action],
        action_data={"entity_id": door.id},
    ).send(person.marshall, person.emily)


@state_change_trigger(*EXTERIOR_DOORS, *GARAGE_STALLS, to_state=OFF)
def door_closed_cancel_notifs(state_change: StateChangeEvent) -> None:
    cancel_notifications(state_change.entity_id)


@notif_action_trigger(SILENCE_NOTIF_ACTION_ID)
def silence_notif_action_called(notif_action: NotifActionEvent) -> None:
    if not isinstance(notif_action.action_data, dict):
        raise TypeError

    entity_id = notif_action.action_data["entity_id"]
    if not isinstance(entity_id, str):
        raise TypeError

    cancel_notifications(EntityId(entity_id))


def cancel_notifications(entity_id: EntityId) -> None:
    scheduler = JobScheduler()
    for time in NOTIFICATION_TIMES:
        job_id = get_job_id(entity_id, time)
        scheduler.cancel_job(job_id)
