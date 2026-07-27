from datetime import timedelta

from maestro.domains import AWAY, HOME, ON
from maestro.integrations import Domain
from maestro.testing import MaestroTest
from maestro.utils import local_now

from registry import binary_sensor, person
from scripts.common.gates import Gate, GateManager
from scripts.home.doors import EXTERIOR_DOORS

from .. import critical_door_notif


def test_send_for_every_door_when_away(mt: MaestroTest) -> None:
    # Every exterior door triggers notifs when nobody's home
    assert len(EXTERIOR_DOORS) == 4
    mt.set_state(person.marshall, AWAY)
    mt.set_state(person.emily, AWAY)
    for door in EXTERIOR_DOORS:
        mt.trigger_state_change(door, new=ON)
        mt.assert_action_called(Domain.NOTIFY, person.marshall.notify_action_name)
        mt.assert_action_called(Domain.NOTIFY, person.emily.notify_action_name)
        mt.clear_action_calls()

    # Don't send notifs when somebody is home
    for marshall_state, emily_state in [(HOME, HOME), (HOME, AWAY), (AWAY, HOME)]:
        mt.set_state(person.marshall, marshall_state)
        mt.set_state(person.emily, emily_state)
        mt.trigger_state_change(binary_sensor.front_door, new=ON)
        mt.assert_action_not_called(Domain.NOTIFY, person.marshall.notify_action_name)
        mt.assert_action_not_called(Domain.NOTIFY, person.emily.notify_action_name)


def test_send_at_night(mt: MaestroTest) -> None:
    now = local_now()
    one_week_ago = now - timedelta(days=7)

    # Send notif to only marshall at night
    mt.set_state(person.marshall, HOME, attributes={"last_changed": one_week_ago})
    mt.set_state(person.emily, HOME, attributes={"last_changed": one_week_ago})
    test_times = [(0, 0, True), (4, 59, True), (5, 0, False), (23, 59, False)]

    for hour, minute, should_send in test_times:
        test_time = local_now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        with mt.mock_datetime_as(test_time):
            mt.trigger_state_change(binary_sensor.front_door, new=ON)
            if should_send:
                mt.assert_action_called(Domain.NOTIFY, person.marshall.notify_action_name)
            else:
                mt.assert_action_not_called(Domain.NOTIFY, person.marshall.notify_action_name)
            mt.assert_action_not_called(Domain.NOTIFY, person.emily.notify_action_name)
            mt.clear_action_calls()


def test_just_got_home(mt: MaestroTest) -> None:
    now = local_now()
    one_minute_ago = now - timedelta(minutes=1)
    one_week_ago = now - timedelta(days=7)

    # Don't send if someone just got home
    mt.set_state(person.marshall, HOME, attributes={"last_changed": one_minute_ago})
    mt.set_state(person.emily, HOME, attributes={"last_changed": one_week_ago})
    mt.trigger_state_change(binary_sensor.front_door, new=ON)

    mt.set_state(person.marshall, HOME, attributes={"last_changed": one_week_ago})
    mt.set_state(person.emily, HOME, attributes={"last_changed": one_minute_ago})
    mt.trigger_state_change(binary_sensor.front_door, new=ON)

    mt.assert_action_not_called(Domain.NOTIFY, person.marshall.notify_action_name)
    mt.assert_action_not_called(Domain.NOTIFY, person.emily.notify_action_name)


def test_silence_action_closes_gate_for_an_hour(mt: MaestroTest) -> None:
    """Pressing the Silence action closes the gate, suppressing notifs for an hour"""
    mt.set_state(person.marshall, AWAY)
    mt.set_state(person.emily, AWAY)

    # Notif sends with the silence action attached
    mt.trigger_state_change(binary_sensor.front_door, new=ON)
    mt.assert_action_called(Domain.NOTIFY, person.marshall.notify_action_name)
    mt.clear_action_calls()

    # Pressing the action closes the gate for an hour
    mt.trigger_notif_action(critical_door_notif.SILENCE_NOTIF_ACTION_ID)
    expiry = GateManager.is_closed(Gate.CRITICAL_DOOR_NOTIFS)
    assert expiry is not None
    assert abs((expiry - local_now()) - critical_door_notif.SILENCE_DURATION) < timedelta(seconds=5)

    # Subsequent door opens are suppressed
    mt.trigger_state_change(binary_sensor.front_door, new=ON)
    mt.assert_action_not_called(Domain.NOTIFY, person.marshall.notify_action_name)
    mt.assert_action_not_called(Domain.NOTIFY, person.emily.notify_action_name)
