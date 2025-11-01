from collections.abc import Callable
from enum import StrEnum, auto
from functools import wraps
from typing import Any

from maestro.triggers.trigger_manager import TriggerManager
from maestro.triggers.types import (
    HassParams,
    TriggerRegistryEntry,
    TriggerType,
)


class HassEvent(StrEnum):
    STARTUP_NOT_WORKING_YET = auto()
    SHUTDOWN = auto()


class HassTriggerManager(TriggerManager):
    trigger_type = TriggerType.HASS

    @classmethod
    def fire_triggers(cls, event: HassEvent) -> None:
        """Execute registered Home Assistant event (eg. startup or shutdown) functions."""
        func_params = HassParams.FuncParams()
        registry = cls.get_registry(registry_union=True)
        funcs_to_execute = []

        for registry_entry in registry[cls.trigger_type].get(event, []):
            funcs_to_execute.append(registry_entry["func"])

        cls.invoke_funcs_threaded(funcs_to_execute, func_params)


def hass_trigger(event: HassEvent) -> Callable:
    """
    Decorator to register a function to fire upon a Home Assistant service event (eg. startup).

    Available function params:
        `None`
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        trigger_args = HassParams.TriggerParams(event=event)
        registry_entry = TriggerRegistryEntry(
            func=wrapper,
            trigger_args=trigger_args,
            qual_name=TriggerManager._get_qual_name(func),
        )

        HassTriggerManager.register_function(
            trigger_type=TriggerType.HASS,
            registry_key=event,
            registry_entry=registry_entry,
        )

        return wrapper

    return decorator
