from abc import ABC, abstractmethod
from calendar import Day, Month
from collections import defaultdict
from collections.abc import Callable
from enum import StrEnum, auto
from inspect import signature
from typing import Any, ClassVar, TypedDict, final

from apscheduler.triggers.cron import CronTrigger  # type:ignore[import-untyped]
from structlog.stdlib import get_logger

from maestro.integrations.home_assistant.types import EntityId, StateChangeEvent

log = get_logger()


class TriggerType(StrEnum):
    STATE_CHANGE = auto()
    CRON = auto()


class StateChangeTriggerArgs(TypedDict):
    entity_id: EntityId
    from_state: str | None
    to_state: str | None


class CronTriggerArgs(TypedDict):
    pattern: str | None
    minute: int | str | None
    hour: int | str | None
    day_of_month: int | list[int] | str | None
    month: int | Month | list[int | Month] | str | None
    day_of_week: int | Day | list[int | Day] | str | None


class TriggerRegistryEntry(TypedDict):
    func: Callable
    trigger_args: StateChangeTriggerArgs | CronTriggerArgs


class StateChangeTriggerFuncParams(TypedDict):
    state_change: StateChangeEvent


RegistryT = dict[TriggerType, defaultdict[str, list[TriggerRegistryEntry]]]
TriggerFuncParamsT = StateChangeTriggerFuncParams


def initialize_trigger_registry() -> RegistryT:
    """Build the trigger registry dictionary that will map triggers to functions."""
    return {trig_type: defaultdict(list) for trig_type in TriggerType}


class TriggerManager(ABC):
    trigger_type: TriggerType
    _registry: ClassVar[RegistryT] = initialize_trigger_registry()
    _test_registry: ClassVar[RegistryT]  # Temporary registry for testing if initialized

    @classmethod
    @final
    def get_registry(cls, registry_union: bool = False) -> RegistryT:
        """
        Return the test registry if one exists, otherwise the production registry.
        Setting `registry_union` will return a dictionary union of the two.
        """
        test_registry = getattr(cls, "_test_registry", {})
        if registry_union:
            return test_registry | cls._registry
        return test_registry or cls._registry

    @classmethod
    @final
    def register_function(
        cls,
        trigger_type: TriggerType,
        registry_key: str | CronTrigger,
        registry_entry: TriggerRegistryEntry,
    ) -> None:
        """Register a function to be called when the specified trigger fires."""
        cls.get_registry()[trigger_type][registry_key].append(registry_entry)
        log.info(
            "Successfully registered trigger function",
            function_name=registry_entry["func"].__name__,
            trigger_type=trigger_type,
            registry_key=registry_key,
        )

    @classmethod
    @abstractmethod
    def resolve_triggers(cls, *args: Any, **kwargs: Any) -> None:
        """Execute registered functions for the given trigger. Should call `cls.invoke_funcs`"""
        raise NotImplementedError

    @classmethod
    @final
    def invoke_funcs(
        cls,
        funcs_to_execute: list[Callable],
        trigger_params: TriggerFuncParamsT,
    ) -> None:
        """
        Wrapper logic to handle a varied number of optional args passed to a decorated function.

        Both of these examples are valid depending on whether or not the state change var is needed:
            @state_change_trigger(): ...
            @state_change_trigger(state_change: StateChangeEvent): ...

        trigger_params is a typeddict to enumerate the available valid arguments.
        """
        params_dict = dict(trigger_params)

        for func in funcs_to_execute:
            execution_args = []
            for signature_param in signature(func).parameters:
                if signature_param not in params_dict:
                    log.error(
                        "Invalid argument for trigger decorated function",
                        trigger_type=cls.trigger_type,
                        function_name=func.__name__,
                        arg=signature_param,
                    )
                    continue
                execution_args.append(params_dict[signature_param])
            try:
                func(*execution_args)
            except Exception:
                log.exception("Error executing triggered function", function_name=func.__name__)
