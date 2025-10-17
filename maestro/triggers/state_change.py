from collections.abc import Callable
from functools import wraps
from typing import Any, cast

from structlog.stdlib import get_logger

from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.types import EntityId, StateChangeEvent
from maestro.triggers.trigger_manager import TriggerManager
from maestro.triggers.types import StateChangeParams, TriggerRegistryEntry, TriggerType

log = get_logger()


class StateChangeTriggerManager(TriggerManager):
    trigger_type = TriggerType.STATE_CHANGE

    @classmethod
    def fire_triggers(cls, state_change: StateChangeEvent) -> None:
        """Execute all registered state change functions for the given entity."""
        trigger_params = StateChangeParams.FuncParams(state_change=state_change)
        registry = cls.get_registry(registry_union=True)
        funcs_to_execute = []

        for registry_entry in registry[cls.trigger_type].get(state_change.entity_id, []):
            trigger_args = cast(StateChangeParams.TriggerParams, registry_entry["trigger_args"])
            from_state = trigger_args["from_state"]
            to_state = trigger_args["to_state"]

            if from_state is not None and state_change.old.state != from_state:
                continue
            if to_state is not None and state_change.new.state != to_state:
                continue

            funcs_to_execute.append(registry_entry["func"])

        cls.invoke_funcs_threaded(funcs_to_execute, trigger_params)


def state_change_trigger(
    *entities: Entity | str,
    from_state: str | None = None,
    to_state: str | None = None,
) -> Callable:
    """
    Decorator to register a function as a state change trigger for the specified entity or entities.

    Available function params:
        `state_change: StateChangeEvent`
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        for entity in entities:
            entity_id = entity.id if isinstance(entity, Entity) else EntityId(entity)
            trigger_args = StateChangeParams.TriggerParams(
                entity_id=entity_id,
                from_state=from_state,
                to_state=to_state,
            )
            registry_entry = TriggerRegistryEntry(
                func=wrapper,
                trigger_args=trigger_args,
                qual_name=TriggerManager._get_qual_name(func),
            )

            StateChangeTriggerManager.register_function(
                trigger_type=TriggerType.STATE_CHANGE,
                registry_key=entity_id,
                registry_entry=registry_entry,
            )

        return wrapper

    return decorator
