from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from flask import Response

from maestro.handlers.event_fired import handle_event_fired
from maestro.handlers.hass_shutdown import handle_hass_shutdown
from maestro.handlers.hass_startup import handle_hass_startup
from maestro.handlers.notif_action import handle_notif_action
from maestro.handlers.state_changed import handle_state_changed


class EventTypeName(StrEnum):
    STATE_CHANGED = "state_changed"
    IOS_NOTIF_ACTION = "ios.notification_action_fired"
    HASS_STARTUP = "maestro_hass_started"
    HASS_SHUTDOWN = "homeassistant_final_write"
    DEFAULT = "event_fired"


@dataclass
class EventType:
    name: EventTypeName
    handler_func: Callable[[dict], tuple[Response, int]]
    process_id_prefix: str


EVENT_TYPE_REGISTRY: dict[EventTypeName, EventType] = {
    EventTypeName.STATE_CHANGED: EventType(
        name=EventTypeName.STATE_CHANGED,
        handler_func=handle_state_changed,
        process_id_prefix="state_change",
    ),
    EventTypeName.IOS_NOTIF_ACTION: EventType(
        name=EventTypeName.IOS_NOTIF_ACTION,
        handler_func=handle_notif_action,
        process_id_prefix="ios_notif_action",
    ),
    EventTypeName.HASS_STARTUP: EventType(
        name=EventTypeName.HASS_STARTUP,
        handler_func=handle_hass_startup,
        process_id_prefix="hass_startup",
    ),
    EventTypeName.HASS_SHUTDOWN: EventType(
        name=EventTypeName.HASS_SHUTDOWN,
        handler_func=handle_hass_shutdown,
        process_id_prefix="hass_shutdown",
    ),
}

DEFAULT_EVENT_TYPE = EventType(
    name=EventTypeName.DEFAULT,
    handler_func=handle_event_fired,
    process_id_prefix="event_fired",
)


def get_event_type(event_type_name: str) -> EventType:
    try:
        event_type_name = EventTypeName(event_type_name)
        return EVENT_TYPE_REGISTRY[event_type_name]
    except ValueError:
        return DEFAULT_EVENT_TYPE
