from maestro.domains import ON, UNAVAILABLE, UNKNOWN
from maestro.integrations import StateChangeEvent
from maestro.triggers import cron_trigger, state_change_trigger
from maestro.utils import Notif

from registry import person

from .common import Nyx, Tess, get_vehicle_config

DEFAULT_CHARGE_LIMIT = 80


@state_change_trigger(Nyx.charger, Tess.charger, to_state=ON)
def high_charge_limit(state_change: StateChangeEvent) -> None:
    vehicle = get_vehicle_config(state_change.entity_id)
    if vehicle.charge_limit.state in [UNKNOWN, UNAVAILABLE]:
        return

    if float(vehicle.charge_limit.state) > DEFAULT_CHARGE_LIMIT:
        name = vehicle.__name__
        Notif(
            title="High Charge Limit",
            message=f"{name} is plugged in with a charge limit of {vehicle.charge_limit.state}%.",
            tag="high_charge_limit",
        ).send(person.marshall)


@cron_trigger(hour=20, minute=30)
def charge_reminder() -> None:
    for vehicle in (Nyx, Tess):
        name = vehicle.__name__

        unplugged = not vehicle.charger.is_on
        low_battery = float(vehicle.battery.state) < float(vehicle.charge_limit.state) - 25

        if vehicle.location.is_home and unplugged and low_battery:
            Notif(
                title=f"{name} Battery",
                message=f"{name} is unplugged with only {vehicle.battery.state}% battery",
                tag=f"{name.lower()}_charge_reminder",
                priority=Notif.Priority.TIME_SENSITIVE,
            ).send(person.marshall, person.emily)
