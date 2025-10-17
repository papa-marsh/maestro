from collections.abc import Callable
from enum import StrEnum, auto
from functools import wraps
from typing import Any

from structlog.stdlib import get_logger

from maestro.triggers.trigger_manager import TriggerManager
from maestro.triggers.types import (
    MaestroParams,
    TriggerRegistryEntry,
    TriggerType,
)

log = get_logger()


class MaestroEvent(StrEnum):
    STARTUP = auto()
    SHUTDOWN = auto()


class MaestroTriggerManager(TriggerManager):
    trigger_type = TriggerType.MAESTRO

    @classmethod
    def fire_triggers(cls, event: MaestroEvent) -> None:
        """Execute registered meastro event (eg. startup or shutdown) functions."""
        func_params = MaestroParams.FuncParams()
        registry = cls.get_registry(registry_union=True)
        funcs_to_execute = []

        for registry_entry in registry[cls.trigger_type].get(event, []):
            funcs_to_execute.append(registry_entry["func"])

        cls.invoke_threaded_funcs(funcs_to_execute, func_params)


def maestro_trigger(event: MaestroEvent) -> Callable:
    """
    Decorator to register a function to fire upon a Maestro service event (eg. startup).

    Available function params:
        `None`
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        trigger_args = MaestroParams.TriggerParams(event=event)
        registry_entry = TriggerRegistryEntry(
            func=wrapper,
            trigger_args=trigger_args,
            qual_name=TriggerManager._get_qual_name(func),
        )

        MaestroTriggerManager.register_function(
            trigger_type=TriggerType.MAESTRO,
            registry_key=event,
            registry_entry=registry_entry,
        )

        return wrapper

    return decorator
