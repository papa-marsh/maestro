from datetime import timedelta

import pytest
from maestro import db
from maestro.integrations import Domain
from maestro.testing import MaestroTest
from maestro.utils import local_now

from registry import person
from scripts.common.event_type import EventType
from scripts.config.secrets import PERSON_TO_USER_ID

from .. import events
from ..models import SleepEvent
from ..queries import save_sleep_event


def test_olivia_wakeup_event(mt: MaestroTest) -> None:
    # Event is saved and notification sent for wakeup event
    mt.trigger_event(EventType.OLIVIA_AWAKE)
    sleep_events = db.session.query(SleepEvent).all()
    assert len(sleep_events) == 1
    assert sleep_events[0].wakeup is True
    mt.assert_action_called(Domain.NOTIFY, person.marshall.notify_action_name)
    mt.assert_action_called(Domain.NOTIFY, person.emily.notify_action_name)

    # Wakeup event notifies only Emily and exits if already awake
    mt.clear_action_calls()
    mt.trigger_event(EventType.OLIVIA_AWAKE)
    sleep_events = db.session.query(SleepEvent).all()
    assert len(sleep_events) == 1
    mt.assert_action_called(Domain.NOTIFY, person.emily.notify_action_name)
    mt.assert_action_not_called(Domain.NOTIFY, person.marshall.notify_action_name)


@pytest.mark.parametrize(
    ("nap_events", "request_hour", "expected_bedtime"),
    [
        ([], 16, "7:45"),
        ([(12, False), (13, True)], 16, "7:15"),
        ([(10, False), (11, True), (13, False), (14, True)], 16, "8:15"),
        ([(12, False)], 13, "7:45"),
        ([(12, False)], 13.5, "7:45"),
        ([(12, False)], 14, "8:15"),
        ([(12, False), (13, True)], 20, "7:15"),
        ([(9, False), (10, True)], 10.5, "8:45"),
        ([(9, False), (10, True)], 11, "7:15"),
        ([(9, False), (10, True), (10.5, False)], 10.75, "8:45"),
        ([(9, False)], 10, "7:45"),
    ],
)
def test_olivia_info_bedtime(
    mt: MaestroTest,
    nap_events: list[tuple[float, bool]],
    request_hour: float,
    expected_bedtime: str,
) -> None:
    """Estimate bedtime from awake time and only today's recorded naps."""
    midnight = local_now().replace(hour=0, minute=0, second=0, microsecond=0)
    for hours, wakeup in [(-12, False), (-11, True), (-4, False)]:
        save_sleep_event(midnight + timedelta(hours=hours), wakeup=wakeup)
    save_sleep_event(midnight + timedelta(hours=7, minutes=15), wakeup=True)
    for hour, wakeup in nap_events:
        save_sleep_event(midnight + timedelta(hours=hour), wakeup=wakeup)

    with mt.mock_datetime_as(midnight + timedelta(hours=request_hour)):
        mt.trigger_event(EventType.OLIVIA_INFO, user_id=PERSON_TO_USER_ID[person.marshall])

    calls = mt.get_action_calls(Domain.NOTIFY, person.marshall.notify_action_name)
    assert len(calls) == 1
    lines = calls[0].kwargs["message"].splitlines()
    assert lines[0] == f"Bedtime: ~{expected_bedtime}pm"
    assert lines[1].startswith("Olivia has been ")
    assert lines[2].startswith("Wake time today: ")
    mt.assert_action_not_called(Domain.NOTIFY, person.emily.notify_action_name)


@pytest.mark.parametrize("after_nap", [False, True])
def test_only_nap_wakeup_notification_ends_with_bedtime(mt: MaestroTest, after_nap: bool) -> None:
    """Include bedtime after a nap, but not after overnight sleep."""
    midnight = local_now().replace(hour=0, minute=0, second=0, microsecond=0)
    save_sleep_event(midnight - timedelta(hours=4), wakeup=False)
    if after_nap:
        save_sleep_event(midnight + timedelta(hours=7, minutes=15), wakeup=True)
        save_sleep_event(midnight + timedelta(hours=12), wakeup=False)
    wakeup_time = midnight + (timedelta(hours=13) if after_nap else timedelta(hours=7, minutes=15))
    with mt.mock_datetime_as(wakeup_time):
        mt.trigger_event(EventType.OLIVIA_AWAKE)

    for target in (person.marshall, person.emily):
        calls = mt.get_action_calls(Domain.NOTIFY, target.notify_action_name)
        assert len(calls) == 1
        lines = calls[0].kwargs["message"].splitlines()
        assert lines[0].startswith("Olivia woke up after ")
        assert lines[1].startswith("Wake time today: ")
        assert lines[2:] == (["Bedtime: ~7:15pm"] if after_nap else [])


@pytest.mark.parametrize("sleep_hour", [12, 16.5, 17, 20])
def test_nap_start_notification_bedtime(mt: MaestroTest, sleep_hour: float) -> None:
    """Assume a full nap at sleep onset, but omit the estimate at nighttime bedtime."""
    midnight = local_now().replace(hour=0, minute=0, second=0, microsecond=0)
    save_sleep_event(midnight + timedelta(hours=7, minutes=15), wakeup=True)

    with mt.mock_datetime_as(midnight + timedelta(hours=sleep_hour)):
        mt.trigger_event(EventType.OLIVIA_ASLEEP)
        for target in (person.marshall, person.emily):
            calls = mt.get_action_calls(Domain.NOTIFY, target.notify_action_name)
            assert len(calls) == 1
            lines = calls[0].kwargs["message"].splitlines()
            assert lines[0].startswith("Olivia went to sleep after ")
            assert lines[2:] == (["Bedtime: ~7:45pm"] if sleep_hour < 17 else [])


def test_early_nap_wakeup_assumes_another_nap(mt: MaestroTest) -> None:
    """Include another nap in the wakeup estimate before 11 AM."""
    midnight = local_now().replace(hour=0, minute=0, second=0, microsecond=0)
    save_sleep_event(midnight + timedelta(hours=7, minutes=15), wakeup=True)
    save_sleep_event(midnight + timedelta(hours=9), wakeup=False)

    with mt.mock_datetime_as(midnight + timedelta(hours=10)):
        mt.trigger_event(EventType.OLIVIA_AWAKE)

    for target in (person.marshall, person.emily):
        calls = mt.get_action_calls(Domain.NOTIFY, target.notify_action_name)
        assert len(calls) == 1
        assert calls[0].kwargs["message"].splitlines()[-1] == "Bedtime: ~8:45pm"


def test_olivia_asleep_event(mt: MaestroTest) -> None:
    one_hour_ago = local_now() - timedelta(hours=1)
    with mt.mock_datetime_as(one_hour_ago):
        mt.trigger_event(EventType.OLIVIA_AWAKE)

    # Event is saved and notification sent for asleep event
    mt.trigger_event(EventType.OLIVIA_ASLEEP)
    sleep_events = db.session.query(SleepEvent).all()
    assert len(sleep_events) == 2
    assert sleep_events[1].wakeup is False
    mt.assert_action_called(Domain.NOTIFY, person.marshall.notify_action_name)
    mt.assert_action_called(Domain.NOTIFY, person.emily.notify_action_name)

    # Sleep event notifies only Emily and exits if already asleep
    mt.clear_action_calls()
    mt.trigger_event(EventType.OLIVIA_ASLEEP)
    sleep_events = db.session.query(SleepEvent).all()
    assert len(sleep_events) == 2
    mt.assert_action_called(Domain.NOTIFY, person.emily.notify_action_name)
    mt.assert_action_not_called(Domain.NOTIFY, person.marshall.notify_action_name)


def test_asleep_false_alarm_threshold(mt: MaestroTest) -> None:
    # Asleep event notifies, deletes previous, and exits if below false alarm threshold
    within_threshold_datetime = local_now() - events.FALSE_ALARM_THRESHOLD + timedelta(minutes=1)
    with mt.mock_datetime_as(within_threshold_datetime):
        mt.trigger_event(EventType.OLIVIA_AWAKE)

    sleep_events = db.session.query(SleepEvent).all()
    assert len(sleep_events) == 1
    mt.clear_action_calls()

    mt.trigger_event(EventType.OLIVIA_ASLEEP)
    sleep_events = db.session.query(SleepEvent).all()
    assert len(sleep_events) == 0
    mt.assert_action_called(Domain.NOTIFY, person.marshall.notify_action_name)
    mt.assert_action_called(Domain.NOTIFY, person.emily.notify_action_name)


def test_wakeup_false_alarm_threshold(mt: MaestroTest) -> None:
    one_hour_ago = local_now() - timedelta(hours=1)
    with mt.mock_datetime_as(one_hour_ago):
        mt.trigger_event(EventType.OLIVIA_AWAKE)

    # Wakeup event notifies, deletes previous, and exits if below false alarm threshold
    within_threshold_datetime = local_now() - events.FALSE_ALARM_THRESHOLD + timedelta(minutes=1)
    with mt.mock_datetime_as(within_threshold_datetime):
        mt.trigger_event(EventType.OLIVIA_ASLEEP)

    sleep_events = db.session.query(SleepEvent).all()
    assert len(sleep_events) == 2
    mt.clear_action_calls()

    mt.trigger_event(EventType.OLIVIA_AWAKE)
    sleep_events = db.session.query(SleepEvent).all()
    assert len(sleep_events) == 1
    mt.assert_action_called(Domain.NOTIFY, person.marshall.notify_action_name)
    mt.assert_action_called(Domain.NOTIFY, person.emily.notify_action_name)


def test_olivia_info(mt: MaestroTest) -> None:
    # Notification is sent to requestor only
    mt.trigger_event(EventType.OLIVIA_AWAKE)
    mt.clear_action_calls()

    mt.trigger_event(EventType.OLIVIA_INFO, user_id=PERSON_TO_USER_ID[person.marshall])
    mt.assert_action_called(Domain.NOTIFY, person.marshall.notify_action_name)
    mt.assert_action_not_called(Domain.NOTIFY, person.emily.notify_action_name)

    mt.clear_action_calls()
    mt.trigger_event(EventType.OLIVIA_INFO, user_id=PERSON_TO_USER_ID[person.emily])
    mt.assert_action_called(Domain.NOTIFY, person.emily.notify_action_name)
    mt.assert_action_not_called(Domain.NOTIFY, person.marshall.notify_action_name)
