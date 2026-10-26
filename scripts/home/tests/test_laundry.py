"""Tests for debounced washing machine completion notifications."""

from datetime import timedelta

import pytest
from maestro.integrations import Domain
from maestro.testing import MaestroTest
from maestro.utils import local_now

from registry import person, sensor

from .. import laundry


def test_completion_notifies_both_people_after_five_minutes(mt: MaestroTest) -> None:
    """Keep the falling-edge time in the delayed notification."""
    completed_at = local_now().replace(hour=13, minute=23, second=0, microsecond=0)
    received_at = completed_at + timedelta(seconds=65)
    with mt.mock_datetime_as(received_at):
        mt.trigger_state_change(
            sensor.washer_plug_power, old="50", new="9.9", time_fired=completed_at
        )
    mt.assert_job_scheduled(
        laundry.COMPLETION_JOB_ID,
        laundry.notify_laundry_complete,
        run_time=received_at + timedelta(minutes=5),
    )
    assert not mt.get_action_calls(Domain.NOTIFY)

    with mt.mock_datetime_as(completed_at + timedelta(minutes=2)):
        mt.trigger_state_change(sensor.washer_plug_power, new="2")
    mt.assert_job_scheduled(
        laundry.COMPLETION_JOB_ID,
        laundry.notify_laundry_complete,
        run_time=received_at + timedelta(minutes=5),
    )
    job = mt.get_scheduled_job(laundry.COMPLETION_JOB_ID)
    with mt.mock_datetime_as(received_at + timedelta(minutes=5)):
        job.func(**job.kwargs)

    for recipient in (person.marshall, person.emily):
        mt.assert_action_called(
            Domain.NOTIFY,
            recipient.notify_action_name,
            call_count=1,
            title="Laundry's Done",
            message="The washing machine completed its cycle at 1:23pm",
        )
    assert len(mt.get_action_calls(Domain.NOTIFY)) == 2


@pytest.mark.parametrize("new", ["10", "100", "unknown", "unavailable", "nan"])
def test_interrupted_idle_period_cancels_notification(mt: MaestroTest, new: str) -> None:
    """Resumed activity or missing readings invalidate the pending completion."""
    mt.trigger_state_change(sensor.washer_plug_power, old="100", new="0")
    mt.trigger_state_change(sensor.washer_plug_power, new=new)
    mt.assert_job_not_scheduled(laundry.COMPLETION_JOB_ID)
    assert not mt.get_action_calls(Domain.NOTIFY)


def test_next_falling_edge_starts_a_fresh_delay(mt: MaestroTest) -> None:
    """A brief pause does not determine the final completion time."""
    start = local_now()
    with mt.mock_datetime_as(start):
        mt.trigger_state_change(sensor.washer_plug_power, old="100", new="0")
    mt.trigger_state_change(sensor.washer_plug_power, new="10")
    with mt.mock_datetime_as(start + timedelta(minutes=3)):
        mt.trigger_state_change(sensor.washer_plug_power, new="0")
    mt.assert_job_scheduled(
        laundry.COMPLETION_JOB_ID,
        laundry.notify_laundry_complete,
        run_time=start + timedelta(minutes=8),
    )
    assert len(mt.get_scheduled_jobs()) == 1


@pytest.mark.parametrize(
    ("old", "new"),
    [("0", "1"), ("20", "10"), ("unknown", "0"), ("unavailable", "0"), ("nan", "0")],
)
def test_only_a_numeric_falling_edge_schedules(mt: MaestroTest, old: str, new: str) -> None:
    """Idle updates and sensor recovery are not completed cycles."""
    mt.trigger_state_change(sensor.washer_plug_power, old=old, new=new)
    mt.assert_job_not_scheduled(laundry.COMPLETION_JOB_ID)
    assert not mt.get_action_calls(Domain.NOTIFY)


@pytest.mark.parametrize("power", ["10", "100", "unknown", "unavailable", "nan"])
def test_callback_checks_current_power(mt: MaestroTest, power: str) -> None:
    """Do not notify if the washer is no longer known to be idle."""
    mt.set_state(sensor.washer_plug_power, power)
    laundry.notify_laundry_complete(local_now())
    assert not mt.get_action_calls(Domain.NOTIFY)
