"""Tests for laundry room water leak alerts."""

from maestro.domains import OFF, ON
from maestro.integrations import Domain
from maestro.testing import MaestroTest

from registry import binary_sensor, person

from .. import water_leak


def test_water_leak_sends_critical_notification(mt: MaestroTest) -> None:
    """A newly detected leak sends Marshall one critical alert identifying the room."""
    mt.set_state(binary_sensor.laundry_room_water_leak, OFF)

    mt.trigger_state_change(binary_sensor.laundry_room_water_leak, new=ON)

    calls = mt.get_action_calls(Domain.NOTIFY, person.marshall.notify_action_name)
    assert len(calls) == 1
    payload = calls[0].kwargs
    assert payload["title"] == "Water Leak!"
    assert "laundry room" in payload["message"]
    assert payload["data"]["push"]["interruption-level"] == "critical"
    mt.assert_action_not_called(Domain.NOTIFY, person.emily.notify_action_name)


def test_water_leak_does_not_notify_on_unchanged_or_dry_state(mt: MaestroTest) -> None:
    """Repeated wet readings and clearing a leak do not send leak alerts."""
    for old, new in [(ON, ON), (ON, OFF), (OFF, OFF)]:
        mt.trigger_state_change(binary_sensor.laundry_room_water_leak, old=old, new=new)

        assert mt.get_action_calls(Domain.NOTIFY) == []
