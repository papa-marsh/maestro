from collections import defaultdict
from collections.abc import Callable
from enum import StrEnum, auto
from functools import wraps
from inspect import signature
from typing import Any, ClassVar, TypedDict

from structlog.stdlib import get_logger

from maestro.integrations.home_assistant.types import EntityId, StateChangeEvent

log = get_logger()


class TriggerType(StrEnum):
    STATE_CHANGE = auto()
    CRON = auto()


class StateChangeTriggerParams(TypedDict):
    state_change: StateChangeEvent


class CronTriggerParams(TypedDict): ...


WrappedFuncParamsT = StateChangeTriggerParams | CronTriggerParams


class TriggerManager:
    registry: ClassVar[defaultdict[EntityId, list[Callable]]] = defaultdict(list)

    @classmethod
    def register_function(cls, entity_id: EntityId, func: Callable) -> None:
        """Register a function to be called when the specified entity's state changes."""
        cls.registry[entity_id].append(func)
        log.info(
            "Successfully registered state trigger function",
            function_name=func.__name__,
            trigger_entity=entity_id,
        )

    @classmethod
    def execute_state_change_triggers(cls, state_change: StateChangeEvent) -> None:
        """Execute all registered state change functions for the given entity."""
        if state_change.entity_id in cls.registry:
            trigger_params = StateChangeTriggerParams(state_change=state_change)
            funcs_to_execute = cls.registry[state_change.entity_id]
            cls.execute_funcs(
                funcs_to_execute=funcs_to_execute,
                trigger_params=trigger_params,
            )

    @classmethod
    def execute_cron_triggers(cls) -> None: ...

    @classmethod
    def execute_funcs(
        cls,
        funcs_to_execute: list[Callable],
        trigger_params: WrappedFuncParamsT,
    ) -> None:
        params_dict = dict(trigger_params)

        for func in funcs_to_execute:
            execution_args = []
            for signature_param in signature(func).parameters:
                if signature_param not in params_dict:
                    log.error(
                        "Invalid function argument for state change trigger",
                        function_name=func.__name__,
                        arg=signature_param,
                    )
                    continue
                execution_args.append(params_dict[signature_param])
            try:
                func(*execution_args)
            except Exception:
                log.exception("Error executing triggered function", function_name=func.__name__)


def state_change_trigger(entity_id: str | EntityId) -> Callable:
    """Decorator to register a function as a state change trigger for the specified entity."""

    def decorator(func: Callable) -> Callable:
        entity_id_obj = EntityId(entity_id) if isinstance(entity_id, str) else entity_id

        TriggerManager.register_function(entity_id_obj, func)

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
