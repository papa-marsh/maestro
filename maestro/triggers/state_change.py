from collections.abc import Callable
from functools import wraps
from typing import Any

from structlog.stdlib import get_logger

from maestro.integrations.home_assistant.types import EntityId, StateChangeEvent
from maestro.triggers.trigger_manager import StateChangeTriggerParams, TriggerManager, TriggerType

log = get_logger()


class StateChangeTriggerManager(TriggerManager):
    @classmethod
    def execute_triggers(cls, state_change: StateChangeEvent) -> None:
        """Execute all registered state change functions for the given entity."""
        if state_change.entity_id in cls.registry[TriggerType.STATE_CHANGE]:
            trigger_params = StateChangeTriggerParams(state_change=state_change)
            funcs_to_execute = cls.registry[TriggerType.STATE_CHANGE][state_change.entity_id]
            cls.invoke_funcs(
                funcs_to_execute=funcs_to_execute,
                trigger_params=trigger_params,
            )


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


@state_change_trigger("sensor.processor_use")
def test(state_change: StateChangeEvent) -> None:
    log.info(f"HERE {state_change.entity_id}")


@state_change_trigger("sensor.processor_use")
def test2() -> None:
    log.info("HEREEE")


@state_change_trigger("sensor.memory_free")
def test3(state_change: StateChangeEvent) -> None:
    log.info(f"HERE {state_change.entity_id}")


@state_change_trigger("sensor.memory_free")
def test4() -> None:
    log.info("HEREEE")
