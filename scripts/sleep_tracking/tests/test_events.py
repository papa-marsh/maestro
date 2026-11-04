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
        ([(12, False)], 13, "7:15"),
        ([(12, False), (13, True)], 20, "7:15"),
    ],
)
def test_olivia_info_bedtime(
    mt: MaestroTest,
    nap_events: list[tuple[int, bool]],
    request_hour: int,
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
    assert lines[0] == f"Bedtime: ~{expected_bedtime}"
    assert lines[1].startswith("Olivia has been ")
    assert lines[2].startswith("Wake time today: ")
    mt.assert_action_not_called(Domain.NOTIFY, person.emily.notify_action_name)


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
