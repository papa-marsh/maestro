from collections.abc import Callable
from functools import wraps
from typing import Any

from structlog.stdlib import get_logger

from maestro.integrations.home_assistant.types import EntityId, StateChangeEvent
from maestro.triggers.trigger_manager import StateChangeTriggerParams, TriggerManager, TriggerType

log = get_logger()


class StateChangeTriggerManager(TriggerManager):
    trigger_type = TriggerType.STATE_CHANGE

    @classmethod
    def execute_triggers(cls, state_change: StateChangeEvent) -> None:
        """Execute all registered state change functions for the given entity."""
        trigger_params = StateChangeTriggerParams(state_change=state_change)
        registry_key = state_change.entity_id

        cls.invoke_funcs(registry_key, trigger_params)


def state_change_trigger(entity_id: str | EntityId) -> Callable:
    """Decorator to register a function as a state change trigger for the specified entity."""

    def decorator(func: Callable) -> Callable:
        entity_id_obj = EntityId(entity_id) if isinstance(entity_id, str) else entity_id

        StateChangeTriggerManager.register_function(
            trigger_type=TriggerType.STATE_CHANGE,
            registry_key=entity_id_obj,
            func=func,
        )

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        return wrapper

    return decorator
