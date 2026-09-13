from maestro.triggers import cron_trigger
from maestro.utils import Notif

from custom_domains.zone_extended import ZoneExtended
from registry import climate, person

thermostat = climate.thermostat


@cron_trigger(hour=12)
@cron_trigger(hour=20)
def thermostat_hold_reminder() -> None:
    marshall_zone = ZoneExtended.get_zone_metadata(person.marshall.state)
    emily_zone = ZoneExtended.get_zone_metadata(person.emily.state)

    if not marshall_zone.lakeshore or not emily_zone.lakeshore:
        return
    if thermostat.preset_mode == thermostat.PresetMode.HOLD:
        return

    Notif(
        title="Thermostat on Auto",
        message=(
            f"The thermostat is set to auto mode at {thermostat.temperature}°. "
            "Consider setting a hold at a more conservative setpoint to save energy."
        ),
    ).send(person.marshall)


@cron_trigger(hour=8)
@cron_trigger(hour=20)
def check_thermostat_hold() -> None:
    if thermostat.preset_mode == thermostat.PresetMode.HOLD:
        Notif(
            title="Thermostat Set To Hold",
            message=f"The thermostat is still set to hold at {thermostat.temperature}",
        ).send(person.marshall)
