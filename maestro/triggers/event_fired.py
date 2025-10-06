from collections.abc import Callable
from functools import wraps
from typing import Any, cast

from structlog.stdlib import get_logger

from maestro.integrations.home_assistant.types import FiredEvent
from maestro.triggers.trigger_manager import TriggerManager
from maestro.triggers.types import EventFiredParams, TriggerRegistryEntry, TriggerType

log = get_logger()


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

            if user_id is not None and event.user_id != user_id:
                continue

            funcs_to_execute.append(registry_entry["func"])

        cls.invoke_threaded_funcs(funcs_to_execute, func_params)


def event_fired_trigger(
    event_type: str,
    user_id: str | None = None,
) -> Callable:
    """
    Decorator to register a function as an event fired trigger for the specified entity.

    Available function params:
        `event: FiredEvent`
    """

    def decorator(func: Callable) -> Callable:
        from maestro.app import EventType

        if event_type in EventType:
            raise ValueError(
                "Avoid `event_fired_trigger` when an event-specific trigger exists. "
                "eg. Use state_change_trigger, not event_fired_trigger(event_type='state_changed')"
            )

        trigger_args = EventFiredParams.TriggerParams(
            {
                "user_id": user_id,
                "event_type": event_type,
            }
        )
        registry_entry = TriggerRegistryEntry(
            func=func,
            trigger_args=trigger_args,
        )

        EventFiredTriggerManager.register_function(
            trigger_type=TriggerType.EVENT_FIRED,
            registry_key=event_type,
            registry_entry=registry_entry,
        )

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        return wrapper

    return decorator
