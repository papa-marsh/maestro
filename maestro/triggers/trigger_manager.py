from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable
from enum import StrEnum, auto
from inspect import signature
from typing import Any, ClassVar, TypedDict, final

from structlog.stdlib import get_logger

from maestro.integrations.home_assistant.types import StateChangeEvent

log = get_logger()


class TriggerType(StrEnum):
    STATE_CHANGE = auto()
    CRON = auto()


class StateChangeTriggerParams(TypedDict):
    state_change: StateChangeEvent


class CronTriggerParams(TypedDict): ...


WrappedFuncParamsT = StateChangeTriggerParams | CronTriggerParams
RegistryT = dict[TriggerType, defaultdict[str, list[Callable]]]


def initialize_trigger_registry() -> RegistryT:
    """Build the trigger registry dictionary that will map triggers to functions."""
    return {trig_type: defaultdict(list) for trig_type in TriggerType}


class TriggerManager(ABC):
    registry: ClassVar[RegistryT] = initialize_trigger_registry()
    _test_registry: RegistryT  # Initialize to override with a temporary testing registry

    @classmethod
    @final
    def register_function(
        cls,
        trigger_type: TriggerType,
        registry_key: str,
        func: Callable,
    ) -> None:
        """Register a function to be called when the specified trigger fires."""
        target_registry = getattr(cls, "_test_registry", None) or cls.registry
        target_registry[trigger_type][registry_key].append(func)
        log.info(
            "Successfully registered state trigger function",
            function_name=func.__name__,
            trigger_type=trigger_type,
            registry_key=registry_key,
        )

    @classmethod
    @abstractmethod
    def execute_triggers(cls, *args: Any, **kwargs: Any) -> None:
        """Execute all registered functions for the given trigger. Must call `cls.invoke_funcs`"""
        raise NotImplementedError

    @classmethod
    @final
    def invoke_funcs(
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
