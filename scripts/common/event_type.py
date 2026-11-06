from collections.abc import Callable
from enum import StrEnum, auto

from maestro.triggers import event_fired_trigger


class EventType(StrEnum):
    ADMIN_EVENT = auto()

    BATHROOM_FLOOR = auto()

    MEETING_ACTIVE = auto()

    OLIVIA_ASLEEP = auto()
    OLIVIA_AWAKE = auto()
    OLIVIA_INFO = auto()
    OLIVIA_CORRECTION = auto()

    MAESTRO_UI_EVENT = "maestro_ui_event"


class UIEvent(StrEnum):
    """Avoid auto() since these are hardcoded in lovelace yaml"""

    SPRINKLERS_RUN_PROGRAM = "sprinklers_run_program"
    SPRINKLERS_SKIP_NEXT = "sprinklers_skip_next"
    SPRINKLERS_STOP_ALL = "sprinklers_stop_all"

    ENTITY_CARD_1_TAP = "entity_card_1_tap"
    ENTITY_CARD_1_DOUBLE_TAP = "entity_card_1_double_tap"
    ENTITY_CARD_1_HOLD = "entity_card_1_hold"
    ENTITY_CARD_2_TAP = "entity_card_2_tap"
    ENTITY_CARD_2_DOUBLE_TAP = "entity_card_2_double_tap"
    ENTITY_CARD_2_HOLD = "entity_card_2_hold"
    ENTITY_CARD_3_TAP = "entity_card_3_tap"
    ENTITY_CARD_3_DOUBLE_TAP = "entity_card_3_double_tap"
    ENTITY_CARD_3_HOLD = "entity_card_3_hold"
    ENTITY_CARD_4_TAP = "entity_card_4_tap"
    ENTITY_CARD_4_DOUBLE_TAP = "entity_card_4_double_tap"
    ENTITY_CARD_4_HOLD = "entity_card_4_hold"
    ENTITY_CARD_5_TAP = "entity_card_5_tap"
    ENTITY_CARD_5_DOUBLE_TAP = "entity_card_5_double_tap"
    ENTITY_CARD_5_HOLD = "entity_card_5_hold"
    ENTITY_CARD_6_TAP = "entity_card_6_tap"
    ENTITY_CARD_6_DOUBLE_TAP = "entity_card_6_double_tap"
    ENTITY_CARD_6_HOLD = "entity_card_6_hold"


def ui_event_trigger(trigger: UIEvent) -> Callable:
    """Shorthand for @event_fired_trigger with EventType.MAESTRO_UI_EVENT."""
    return event_fired_trigger(EventType.MAESTRO_UI_EVENT, trigger=trigger)
