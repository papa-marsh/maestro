from maestro.domains import OFF, ON, UNAVAILABLE, UNKNOWN, BinarySensor, Sensor
from maestro.triggers import cron_trigger
from maestro.utils import Notif

from registry import maestro, person
from scripts.frontend.common.entity_card import RowColor
from scripts.vehicles.common import Nyx, Tess

from .doors import EXTERIOR_DOORS, GARAGE_STALLS

LOW_BATTERY_THRESHOLD = 50


def get_vehicle_task(name: str, battery: Sensor, charger: BinarySensor) -> str | None:
    if charger.state != OFF or battery.state in [UNKNOWN, UNAVAILABLE]:
        return None

    try:
        battery_level = float(battery.state)
    except ValueError:
        return None

    if battery_level >= LOW_BATTERY_THRESHOLD:
        return None

    return f"{name} is unplugged at {battery_level:g}%"


def get_bedtime_tasks() -> list[str]:
    tasks = [
        f"{door.friendly_name} is open"
        for door in [*EXTERIOR_DOORS, *GARAGE_STALLS]
        if door.state == ON
    ]

    home_card = maestro.entity_card_3
    if home_card.state not in [UNKNOWN, UNAVAILABLE]:
        if home_card.blink:
            tasks.append("The garbage bins need to go out")
        if home_card.row_3_color == RowColor.RED:
            tasks.append("Chelsea hasn't been fed")

    for task in [
        get_vehicle_task("Nyx", Nyx.battery, Nyx.charger),
        get_vehicle_task("Tess", Tess.battery, Tess.charger),
    ]:
        if task:
            tasks.append(task)

    return tasks


@cron_trigger(hour=21, minute=45)
def bedtime_check() -> None:
    tasks = get_bedtime_tasks()
    if not tasks:
        return

    Notif(
        title="Before Bed",
        message="\n".join(f"• {task}" for task in tasks),
        priority=Notif.Priority.TIME_SENSITIVE,
        tag="bedtime_check",
    ).send(person.marshall, person.emily)
