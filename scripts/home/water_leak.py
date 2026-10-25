from maestro.domains import OFF, ON
from maestro.triggers import state_change_trigger
from maestro.utils import Notif, local_now

from registry import binary_sensor, person


@state_change_trigger(binary_sensor.laundry_room_water_leak, from_state=OFF, to_state=ON)
def laundry_room_water_leak() -> None:
    time = local_now().strftime("%-I:%M %p")
    Notif(
        title="⚠️ Water Leak Detected ⚠️",
        message=f"Laundry Room water detected at {time}",
        priority=Notif.Priority.CRITICAL,
    ).send(person.marshall)
