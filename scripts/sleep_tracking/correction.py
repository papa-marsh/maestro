import re
from datetime import datetime, timedelta

from maestro import db
from maestro.domains import Person
from maestro.integrations import FiredEvent, NotifActionEvent, StateManager
from maestro.triggers import event_fired_trigger, notif_action_trigger
from maestro.utils import Notif, local_now

from scripts.common.event_type import EventType
from scripts.config.secrets import USER_ID_TO_PERSON

from .models import SleepEvent
from .queries import SLEEP_HISTORY_LOCK

CORRECTION_ACTION = "olivia_correction_submit"
CORRECTION_TITLE = "Correct Olivia's sleep time"
INVALID_MESSAGE = (
    "Invalid entry. Enter a time in h:mm format that is after the previous sleep event."
)


def parse_correction_time(text: str, now: datetime) -> datetime | None:
    if not re.fullmatch(r"(0?[1-9]|1[0-2]):[0-5][0-9]", text):
        return None
    hour, minute = map(int, text.split(":"))
    candidate = now.replace(
        hour=hour % 12 + (12 if now.hour >= 12 else 0),
        minute=minute,
        second=0,
        microsecond=0,
    )
    if candidate > now:
        candidate -= timedelta(hours=12)
    return candidate


def send_correction_prompt(target: Person, timestamp: str, *, invalid: bool = False) -> None:
    Notif(
        title=CORRECTION_TITLE,
        message=INVALID_MESSAGE if invalid else "Enter the updated time (h:mm).",
        tag=EventType.OLIVIA_CORRECTION,
        actions=[Notif.build_action(CORRECTION_ACTION, CORRECTION_TITLE, input=True)],
        action_data={"timestamp": timestamp, "person": str(target.id)},
    ).send(target)


@event_fired_trigger(EventType.OLIVIA_CORRECTION)
def request_correction(event: FiredEvent) -> None:
    if target := USER_ID_TO_PERSON.get(event.user_id or ""):
        latest = db.session.query(SleepEvent).order_by(SleepEvent.timestamp.desc()).first()
        send_correction_prompt(target, latest.timestamp.isoformat())


@notif_action_trigger(CORRECTION_ACTION)
def apply_correction(notif_action: NotifActionEvent) -> None:
    with StateManager().redis_client.lock(SLEEP_HISTORY_LOCK):
        _apply_correction(notif_action)


def _apply_correction(notif_action: NotifActionEvent) -> None:
    target = USER_ID_TO_PERSON.get(notif_action.user_id or "")
    data = notif_action.action_data
    if target is None or not isinstance(data, dict) or data.get("person") != str(target.id):
        return

    recent = db.session.query(SleepEvent).order_by(SleepEvent.timestamp.desc()).limit(2).all()
    if not recent or data.get("timestamp") != recent[0].timestamp.isoformat():
        Notif(
            title=CORRECTION_TITLE,
            message="Sleep history changed. Retry.",
            tag=EventType.OLIVIA_CORRECTION,
        ).send(target)
        return

    latest = recent[0]
    text = notif_action.data.get("textInput")
    timestamp = parse_correction_time(text, local_now()) if isinstance(text, str) else None
    if timestamp is None or (len(recent) > 1 and timestamp <= recent[1].timestamp):
        send_correction_prompt(target, latest.timestamp.isoformat(), invalid=True)
        return

    latest.timestamp = timestamp
    db.session.commit()
