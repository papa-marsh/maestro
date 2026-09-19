from maestro.domains import AWAY, HOME, OFF, ON
from maestro.integrations import Domain
from maestro.testing import MaestroTest

from registry import person

from .. import charging
from ..common import Nyx, Tess

default_limit = str(charging.DEFAULT_CHARGE_LIMIT)
high_limit = str(charging.DEFAULT_CHARGE_LIMIT + 5)
low_battery = str(charging.DEFAULT_CHARGE_LIMIT - 26)
ok_battery = str(charging.DEFAULT_CHARGE_LIMIT - 5)


def test_high_charge_limit(mt: MaestroTest) -> None:
    # Notif not sent when charge limit is at default
    mt.set_state(Nyx.charge_limit, default_limit)
    mt.trigger_state_change(Nyx.charger, new=ON)
    mt.assert_action_not_called(Domain.NOTIFY, person.marshall.notify_action_name)

    # Notif sent when charge limit is above default
    mt.set_state(Tess.charge_limit, high_limit)
    mt.trigger_state_change(Tess.charger, new=ON)
    mt.assert_action_called(Domain.NOTIFY, person.marshall.notify_action_name)

    # Notif sent for both vehicles when charge limit is high
    mt.clear_action_calls()
    mt.set_state(Nyx.charge_limit, high_limit)
    mt.trigger_state_change(Nyx.charger, new=ON)
    mt.assert_action_called(Domain.NOTIFY, person.marshall.notify_action_name)


def test_charge_reminder(mt: MaestroTest) -> None:
    # Notif sent when vehicle is home, unplugged, and low battery
    initialize_charge_reminder_mocks(mt)
    mt.set_state(Tess.charger, ON)
    charging.charge_reminder()
    mt.assert_action_called(Domain.NOTIFY, person.marshall.notify_action_name)
    mt.assert_action_called(Domain.NOTIFY, person.emily.notify_action_name)
    assert len(mt.get_action_calls(Domain.NOTIFY)) == 2

    # Notif sent for multiple vehicles meeting criteria
    mt.set_state(Nyx.charger, ON)
    mt.set_state(Tess.charger, OFF)
    charging.charge_reminder()
    assert len(mt.get_action_calls(Domain.NOTIFY)) == 4

    # Notif not sent when vehicle is away
    initialize_charge_reminder_mocks(mt)
    mt.set_state(Nyx.location, AWAY)
    mt.set_state(Tess.location, AWAY)
    charging.charge_reminder()
    mt.assert_action_not_called(Domain.NOTIFY, person.marshall.notify_action_name)
    mt.assert_action_not_called(Domain.NOTIFY, person.emily.notify_action_name)

    # Notif not sent when vehicle is plugged in
    initialize_charge_reminder_mocks(mt)
    mt.set_state(Nyx.charger, ON)
    mt.set_state(Tess.charger, ON)
    charging.charge_reminder()
    mt.assert_action_not_called(Domain.NOTIFY, person.marshall.notify_action_name)
    mt.assert_action_not_called(Domain.NOTIFY, person.emily.notify_action_name)

    # Notif not sent when battery is not low
    mt.set_state(Nyx.battery, ok_battery)
    mt.set_state(Tess.battery, ok_battery)
    charging.charge_reminder()
    mt.assert_action_not_called(Domain.NOTIFY, person.marshall.notify_action_name)
    mt.assert_action_not_called(Domain.NOTIFY, person.emily.notify_action_name)


def initialize_charge_reminder_mocks(mt: MaestroTest) -> None:
    mt.clear_action_calls()

    mt.set_state(Nyx.location, HOME)
    mt.set_state(Nyx.charger, OFF)
    mt.set_state(Nyx.charge_limit, default_limit)
    mt.set_state(Nyx.battery, low_battery)

    mt.set_state(Tess.location, HOME)
    mt.set_state(Tess.charger, OFF)
    mt.set_state(Tess.charge_limit, default_limit)
    mt.set_state(Tess.battery, low_battery)
