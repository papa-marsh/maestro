from collections.abc import Callable
from functools import wraps
from typing import Any, cast

from structlog.stdlib import get_logger

from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.types import EntityId, StateChangeEvent
from maestro.triggers.trigger_manager import (
    StateChangeTriggerArgs,
    StateChangeTriggerFuncParams,
    TriggerManager,
    TriggerRegistryEntry,
    TriggerType,
)

log = get_logger()


class StateChangeTriggerManager(TriggerManager):
    trigger_type = TriggerType.STATE_CHANGE

    @classmethod
    def fire_triggers(cls, state_change: StateChangeEvent) -> None:
        """Execute all registered state change functions for the given entity."""
        trigger_params = StateChangeTriggerFuncParams(state_change=state_change)
        registry = cls.get_registry(registry_union=True)
        funcs_to_execute = []

        for registry_entry in registry[cls.trigger_type].get(state_change.entity_id, []):
            trigger_args = cast(StateChangeTriggerArgs, registry_entry["trigger_args"])
            from_state = trigger_args["from_state"]
            to_state = trigger_args["to_state"]

            if from_state is not None and state_change.old.state != from_state:
                continue
            if to_state is not None and state_change.new.state != to_state:
                continue
            funcs_to_execute.append(registry_entry["func"])

        cls.invoke_threaded_funcs(funcs_to_execute, trigger_params)


def state_change_trigger(
    entity: Entity | EntityId | str,
    from_state: str | None = None,
    to_state: str | None = None,
) -> Callable:
    """Decorator to register a function as a state change trigger for the specified entity."""

    def decorator(func: Callable) -> Callable:
        entity_id = entity.id if isinstance(entity, Entity) else EntityId(entity)
        trigger_args = StateChangeTriggerArgs(
            {
                "entity_id": entity_id,
                "from_state": from_state,
                "to_state": to_state,
            }
        )
        registry_entry = TriggerRegistryEntry(
            func=func,
            trigger_args=trigger_args,
        )

        StateChangeTriggerManager.register_function(
            trigger_type=TriggerType.STATE_CHANGE,
            registry_key=entity_id,
            registry_entry=registry_entry,
        )

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        return wrapper

    return decorator
