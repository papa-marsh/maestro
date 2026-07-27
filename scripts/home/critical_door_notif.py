from datetime import timedelta

from maestro.domains import ON, Person
from maestro.integrations import StateChangeEvent
from maestro.triggers import notif_action_trigger, state_change_trigger
from maestro.utils import Notif, local_now

from registry import person
from scripts.common.gates import Gate, GateManager, require_gate_check
from scripts.home.doors import EXTERIOR_DOORS

SILENCE_NOTIF_ACTION_ID = "silence_critical_door_notifs"
SILENCE_DURATION = timedelta(hours=1)


@state_change_trigger(*EXTERIOR_DOORS, to_state=ON)
@require_gate_check(Gate.CRITICAL_DOOR_NOTIFS)
def send_critical_door_open_notif(state_change: StateChangeEvent) -> None:
    now = local_now()
    nobody_home = not person.marshall.is_home and not person.emily.is_home
    is_nighttime = now.hour < 5

    just_got_home = (
        person.marshall.is_home and now - person.marshall.last_changed < timedelta(minutes=5)
    ) or (person.emily.is_home and now - person.emily.last_changed < timedelta(minutes=5))

    if nobody_home or (is_nighttime and not just_got_home):
        door = state_change.entity_id.resolve_entity()
        friendly_name = door.friendly_name.replace(" Sensor", "")
        time = now.strftime("%-I:%M %p")

        target: list[Person] = [person.marshall, person.emily] if nobody_home else [person.marshall]

        silence_action = Notif.build_action(
            name=SILENCE_NOTIF_ACTION_ID,
            title="Silence",
            destructive=True,
        )

        Notif(
            title="⚠️ Door Opened ⚠️",
            message=f"{friendly_name} opened at {time}",
            priority=Notif.Priority.CRITICAL,
            actions=[silence_action],
        ).send(*target)


@notif_action_trigger(SILENCE_NOTIF_ACTION_ID)
def silence_critical_door_notifs() -> None:
    GateManager.close(
        Gate.CRITICAL_DOOR_NOTIFS,
        ttl_seconds=int(SILENCE_DURATION.total_seconds()),
    )
