from dataclasses import asdict
from datetime import timedelta
from time import sleep

from maestro.integrations import StateManager
from maestro.triggers import (
    HassEvent,
    MaestroEvent,
    cron_trigger,
    event_fired_trigger,
    hass_trigger,
    maestro_trigger,
)
from maestro.utils import format_duration, local_now

from registry import maestro
from scripts.common.event_type import EventType
from scripts.frontend.common.entity_card import EntityCardAttributes
from scripts.frontend.common.icons import Icon
from scripts.sleep_tracking.queries import get_awake_time, get_last_events

card = maestro.entity_card_5


def _format_card_duration(duration: timedelta) -> str:
    if duration < timedelta(minutes=1):
        return "0m"
    return format_duration(duration)


@hass_trigger(HassEvent.STARTUP)
@maestro_trigger(MaestroEvent.STARTUP)
def initialize_card() -> None:
    attributes = EntityCardAttributes(
        title="Livi",
        icon=Icon.BABY,
    )
    StateManager().initialize_hass_entity(
        entity_id=card.id,
        state="Loading...",
        attributes=asdict(attributes),
        restore_cached=True,
    )
    card.update(
        title=attributes.title,
        row_1_icon=Icon.TIMER_OUTLINE,
        row_2_icon=Icon.HISTORY,
        row_3_icon=Icon.CALENDAR_TODAY,
    )


@cron_trigger("* * * * *")
def update_card() -> None:
    most_recent_event, previous_event = get_last_events(count=2)
    awake: bool = most_recent_event.wakeup
    duration: timedelta = local_now() - most_recent_event.timestamp
    prev_duration: timedelta = most_recent_event.timestamp - previous_event.timestamp
    awake_time = get_awake_time()

    card.update(
        state="Awake" if awake else "Asleep",
        icon=Icon.BABY_BUGGY if awake else Icon.SLEEP,
        active=not awake,
        row_1_value=_format_card_duration(duration),
        row_2_value=_format_card_duration(prev_duration),
        row_3_value=_format_card_duration(awake_time),
    )


@event_fired_trigger(EventType.OLIVIA_ASLEEP)
@event_fired_trigger(EventType.OLIVIA_AWAKE)
def trigger_update() -> None:
    sleep(2)  # Let DB operations complete
    update_card()
