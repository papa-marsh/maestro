"""Tests for laundry room water leak alerts."""

from maestro.domains import OFF, ON, UNAVAILABLE, UNKNOWN
from maestro.integrations import Domain
from maestro.testing import MaestroTest
from maestro.utils import local_now

from registry import binary_sensor, person

from .. import water_leak


def test_water_leak_sends_critical_alert_only_to_marshall(mt: MaestroTest) -> None:
    """A newly detected leak sends Marshall one timestamped critical alert."""
    with mt.mock_datetime_as(local_now().replace(hour=15, minute=42)):
        mt.trigger_state_change(binary_sensor.laundry_room_water_leak, old=OFF, new=ON)

    mt.assert_action_called(
        Domain.NOTIFY,
        person.marshall.notify_action_name,
        call_count=1,
        title="⚠️ Water Leak Detected ⚠️",
        message="Laundry Room water detected at 3:42 PM",
    )
    calls = mt.get_action_calls(Domain.NOTIFY)
    assert len(calls) == 1
    assert calls[0].kwargs["data"]["push"]["interruption-level"] == "critical"


def test_water_leak_only_alerts_on_dry_to_wet_transition(mt: MaestroTest) -> None:
    """Only a fresh dry-to-wet transition sends a leak alert."""
    for old, new in [
        (ON, OFF),
        (ON, ON),
        (OFF, OFF),
        (OFF, UNKNOWN),
        (OFF, UNAVAILABLE),
        (UNKNOWN, ON),
        (UNAVAILABLE, ON),
    ]:
        mt.trigger_state_change(binary_sensor.laundry_room_water_leak, old=old, new=new)

    assert not mt.get_action_calls(Domain.NOTIFY)

    mt.trigger_state_change(binary_sensor.laundry_room_water_leak, old=OFF, new=ON)
    mt.assert_action_called(Domain.NOTIFY, person.marshall.notify_action_name, call_count=1)
