from collections.abc import Callable
from contextlib import suppress
from functools import wraps
from typing import Any, cast

from maestro.handlers.types import EventTypeName
from maestro.integrations.home_assistant.types import FiredEvent
from maestro.triggers.trigger_manager import TriggerManager
from maestro.triggers.types import EventFiredParams, TriggerRegistryEntry, TriggerType
from maestro.utils.exceptions import EventTriggerOverrideError


class EventFiredTriggerManager(TriggerManager):
    trigger_type = TriggerType.EVENT_FIRED

    @classmethod
    def fire_triggers(cls, event: FiredEvent) -> None:
        """Execute all registered event fired functions for the given event type."""
        func_params = EventFiredParams.FuncParams(event=event)
        registry = cls.get_registry(registry_union=True)
        funcs_to_execute = []

        for registry_entry in registry[cls.trigger_type].get(event.type, []):
            trigger_params = cast(EventFiredParams.TriggerParams, registry_entry["trigger_args"])
            user_id = trigger_params["user_id"]
            event_data = trigger_params["event_data"]

            if user_id is not None and event.user_id != user_id:
                continue
            if not all(event.data.get(key) == value for key, value in event_data.items()):
                continue

            funcs_to_execute.append(registry_entry["func"])

        cls.invoke_funcs_threaded(funcs_to_execute, func_params)


def event_fired_trigger(
    event_type: str,
    user_id: str | None = None,
    **event_data: Any,
) -> Callable:
    """
    Decorator to register a function as an event fired trigger for the specified entity.

    Optionally pass kwargs to filter by matching event data. The following example will
    trigger only if `"trigger": "weather_card_tap"` is present in the event_data dict
        Example: `@event_fired_trigger("maestro_ui_event", trigger="weather_card_tap")

    Available function params:
        `event: FiredEvent`
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        with suppress(ValueError):
            EventTypeName(event_type)
            raise EventTriggerOverrideError(
                "Avoid `event_fired_trigger` when an event-specific trigger exists. "
                "eg. Use state_change_trigger, not event_fired_trigger(event_type='state_changed')"
            )

        trigger_args = EventFiredParams.TriggerParams(
            user_id=user_id,
            event_type=event_type,
            event_data=event_data,
        )
        registry_entry = TriggerRegistryEntry(
            func=wrapper,
            trigger_args=trigger_args,
            qual_name=TriggerManager._get_qual_name(func),
        )

        EventFiredTriggerManager.register_function(
            trigger_type=TriggerType.EVENT_FIRED,
            registry_key=event_type,
            registry_entry=registry_entry,
        )

        return wrapper

    return decorator
