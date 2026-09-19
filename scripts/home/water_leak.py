from maestro.domains import OFF, ON
from maestro.triggers import state_change_trigger
from maestro.utils import Notif

from registry import binary_sensor, person


@state_change_trigger(binary_sensor.laundry_room_water_leak, from_state=OFF, to_state=ON)
def laundry_room_water_leak() -> None:
    Notif(
        title="Water Leak!",
        message="Water has been detected in the laundry room",
        priority=Notif.Priority.CRITICAL,
    ).send(person.marshall)
