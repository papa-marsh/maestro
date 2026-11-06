"""Sleep-time correction prompts, validation, and stale replies."""

from datetime import datetime, timedelta

import pytest
from maestro import db
from maestro.domains import Person
from maestro.integrations import Domain, NotifActionEvent
from maestro.testing import MaestroTest
from maestro.utils import local_now

from registry import person
from scripts.common.event_type import EventType
from scripts.config.secrets import PERSON_TO_USER_ID

from .. import correction
from ..models import SleepEvent
from ..queries import delete_last_event, get_last_event, save_sleep_event


def request_prompt(mt: MaestroTest, target: Person = person.marshall) -> dict[str, str]:
    mt.trigger_event(EventType.OLIVIA_CORRECTION, user_id=PERSON_TO_USER_ID[target])
    calls = mt.get_action_calls(Domain.NOTIFY, target.notify_action_name)
    data: dict[str, str] = calls[-1].kwargs["data"]["action_data"]
    return data


def reply(data: dict[str, str], text: object, target: Person = person.marshall) -> None:
    correction.apply_correction(
        NotifActionEvent(
            time_fired=local_now(),
            type="ios.notification_action_fired",
            data={"textInput": text},
            user_id=PERSON_TO_USER_ID[target],
            name=correction.CORRECTION_ACTION,
            action_data=data,
            device_id="test_device",
            device_name="Test Device",
        )
    )


@pytest.mark.parametrize(
    ("now", "text", "expected"),
    [
        ("2026-11-06T14:00", "1:38", "2026-11-06T13:38"),
        ("2026-11-06T02:00", "01:38", "2026-11-06T01:38"),
        ("2026-11-06T00:15", "11:50", "2026-11-05T23:50"),
        ("2026-11-06T12:15", "11:50", "2026-11-06T11:50"),
        ("2026-11-06T14:00", "12:00", "2026-11-06T12:00"),
        ("2026-11-06T02:00", "12:00", "2026-11-06T00:00"),
        ("2026-11-06T14:00", "2:01", "2026-11-06T02:01"),
        ("2026-11-06T14:00", "2:00", "2026-11-06T14:00"),
    ],
)
def test_most_recent_12_hour_time(mt: MaestroTest, now: str, text: str, expected: str) -> None:
    tz = local_now().tzinfo
    assert correction.parse_correction_time(
        text, datetime.fromisoformat(now).replace(tzinfo=tz)
    ) == (datetime.fromisoformat(expected).replace(tzinfo=tz))


@pytest.mark.parametrize("target", [person.marshall, person.emily])
@pytest.mark.parametrize("wakeup", [True, False])
def test_correction_updates_only_latest_timestamp(
    mt: MaestroTest, target: Person, wakeup: bool
) -> None:
    now = local_now().replace(hour=14, minute=0, second=0, microsecond=0)
    previous = now - timedelta(hours=3)
    save_sleep_event(previous, not wakeup)
    save_sleep_event(now - timedelta(minutes=10), wakeup)
    with mt.mock_datetime_as(now):
        data = request_prompt(mt, target)
        calls = mt.get_action_calls(Domain.NOTIFY, target.notify_action_name)
        action = calls[0].kwargs["data"]["actions"][0]
        assert action["behavior"] == "textInput"
        assert action["action"] == correction.CORRECTION_ACTION
        other = person.emily if target is person.marshall else person.marshall
        mt.assert_action_not_called(Domain.NOTIFY, other.notify_action_name)
        reply(data, "1:38", target)

    records = db.session.query(SleepEvent).order_by(SleepEvent.timestamp).all()
    assert len(records) == 2
    assert records[0].timestamp == previous
    assert records[1].timestamp == now.replace(hour=13, minute=38)
    assert records[1].wakeup is wakeup


@pytest.mark.parametrize(
    "text",
    [
        "",
        "13:38",
        "0:38",
        "1:60",
        "1:3",
        "1:38pm",
        " 1:38",
        "1:38\n",
        "1",
        None,
        138,
        "12:59",
        "1:00",
    ],
)
def test_invalid_input_reprompts_without_modifying_history(mt: MaestroTest, text: object) -> None:
    now = local_now().replace(hour=14, minute=0, second=0, microsecond=0)
    original = now - timedelta(minutes=10)
    save_sleep_event(now - timedelta(hours=1), True)
    save_sleep_event(original, False)
    with mt.mock_datetime_as(now):
        data = request_prompt(mt)
        mt.clear_action_calls()
        reply(data, text)
        assert get_last_event().timestamp == original
        calls = mt.get_action_calls(Domain.NOTIFY, person.marshall.notify_action_name)
        assert len(calls) == 1
        assert "Invalid entry" in calls[0].kwargs["message"]
        assert calls[0].kwargs["data"]["action_data"] == data
        assert calls[0].kwargs["data"]["actions"][0]["behavior"] == "textInput"
        mt.assert_action_not_called(Domain.NOTIFY, person.emily.notify_action_name)
        reply(data, "1:38")
        assert get_last_event().timestamp == now.replace(hour=13, minute=38)


@pytest.mark.parametrize("change", ["new_event", "deleted_event", "corrected_event"])
def test_stale_reply_does_not_modify_history(mt: MaestroTest, change: str) -> None:
    now = local_now().replace(hour=14, minute=0, second=0, microsecond=0)
    save_sleep_event(now - timedelta(hours=3), True)
    save_sleep_event(now - timedelta(hours=1), False)
    with mt.mock_datetime_as(now):
        data = request_prompt(mt)
        if change == "new_event":
            save_sleep_event(now, True)
        elif change == "deleted_event":
            delete_last_event()
        else:
            reply(data, "1:38")
        expected = [(e.timestamp, e.wakeup) for e in db.session.query(SleepEvent).all()]
        mt.clear_action_calls()
        reply(data, "1:40")
        assert [(e.timestamp, e.wakeup) for e in db.session.query(SleepEvent).all()] == expected
        calls = mt.get_action_calls(Domain.NOTIFY, person.marshall.notify_action_name)
        assert len(calls) == 1
        assert calls[0].kwargs["message"] == "Sleep history changed. Retry."
        assert not calls[0].kwargs["data"]["actions"]


def test_other_person_cannot_submit_prompt(mt: MaestroTest) -> None:
    original = local_now() - timedelta(hours=1)
    save_sleep_event(original, False)
    data = request_prompt(mt)
    mt.clear_action_calls()
    reply(data, "1:38", person.emily)
    assert get_last_event().timestamp == original
    assert not mt.get_action_calls(Domain.NOTIFY)


def test_unknown_requestor_is_not_notified(mt: MaestroTest) -> None:
    mt.trigger_event(EventType.OLIVIA_CORRECTION, user_id="unknown")
    assert not mt.get_action_calls(Domain.NOTIFY)
