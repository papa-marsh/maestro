from maestro.domains import HOME
from maestro.integrations import Domain
from maestro.testing import MaestroTest

from registry import climate, person

from .. import thermostat

lakeshore_zone_name = "Grand Haven"


def test_thermostat_hold_reminder(mt: MaestroTest) -> None:
    # Notif not sent when Marshall is not at lakeshore
    mt.set_state(person.marshall, HOME)
    mt.set_state(person.emily, "Grand Haven")
    mt.set_state(
        entity=climate.thermostat,
        state=climate.thermostat.HVACMode.HEAT,
        attributes={"preset_mode": climate.thermostat.PresetMode.NONE},
    )
    thermostat.thermostat_hold_reminder()
    mt.assert_action_not_called(Domain.NOTIFY, person.marshall.notify_action_name)

    # Notif not sent when Emily is not at lakeshore
    mt.set_state(person.marshall, "Grand Haven")
    mt.set_state(person.emily, HOME)
    thermostat.thermostat_hold_reminder()
    mt.assert_action_not_called(Domain.NOTIFY, person.marshall.notify_action_name)

    # Notif not sent when thermostat is on hold
    mt.set_state(person.marshall, "Grand Haven")
    mt.set_state(person.emily, "Grand Haven")
    mt.set_state(
        entity=climate.thermostat,
        state=climate.thermostat.HVACMode.HEAT,
        attributes={"preset_mode": climate.thermostat.PresetMode.HOLD},
    )
    thermostat.thermostat_hold_reminder()
    mt.assert_action_not_called(Domain.NOTIFY, person.marshall.notify_action_name)

    # Notif sent when both at lakeshore and thermostat not on hold
    mt.set_state(person.marshall, "Grand Haven")
    mt.set_state(person.emily, "Grand Haven")
    mt.set_state(
        entity=climate.thermostat,
        state=climate.thermostat.HVACMode.HEAT,
        attributes={"preset_mode": climate.thermostat.PresetMode.NONE, "temperature": 68},
    )
    thermostat.thermostat_hold_reminder()
    mt.assert_action_called(Domain.NOTIFY, person.marshall.notify_action_name)
    mt.assert_action_not_called(Domain.NOTIFY, person.emily.notify_action_name)


def test_check_thermostat_hold(mt: MaestroTest) -> None:
    mt.set_state(
        entity=climate.thermostat,
        state=climate.thermostat.HVACMode.HEAT,
        attributes={"preset_mode": climate.thermostat.PresetMode.NONE},
    )
    # Notif not sent when thermostat is not on hold
    thermostat.check_thermostat_hold()
    mt.assert_action_not_called(Domain.NOTIFY, person.marshall.notify_action_name)
    mt.assert_action_not_called(Domain.NOTIFY, person.emily.notify_action_name)

    # Notif sent when thermostat is on hold
    mt.set_state(
        entity=climate.thermostat,
        state=climate.thermostat.HVACMode.HEAT,
        attributes={"preset_mode": climate.thermostat.PresetMode.HOLD, "temperature": 70},
    )
    thermostat.check_thermostat_hold()
    mt.assert_action_called(Domain.NOTIFY, person.marshall.notify_action_name)
    mt.assert_action_not_called(Domain.NOTIFY, person.emily.notify_action_name)
