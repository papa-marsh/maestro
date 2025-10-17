from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable
from inspect import signature
from threading import Thread
from typing import TYPE_CHECKING, Any, ClassVar, final

from apscheduler.triggers.cron import CronTrigger  # type:ignore[import-untyped]
from structlog.stdlib import get_logger

from maestro.triggers.types import (
    TriggerFuncParamsT,
    TriggerRegistryEntry,
    TriggerType,
)

if TYPE_CHECKING:
    from maestro.app import MaestroFlask

log = get_logger()


RegistryT = dict[TriggerType, defaultdict[str, list[TriggerRegistryEntry]]]


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
        registry_entries = cls.get_registry()[trigger_type][registry_key]
        for existing_entry in registry_entries:
            if registry_entry["qual_name"] == existing_entry["qual_name"]:
                log.info(
                    "Skipping duplicate trigger registration",
                    function_name=registry_entry["func"].__name__,
                    trigger_type=trigger_type,
                    registry_key=registry_key,
                )
                return

        registry_entries.append(registry_entry)
        log.info(
            "Registered trigger function",
            function_name=registry_entry["func"].__name__,
            trigger_type=trigger_type,
            registry_key=registry_key,
        )

    @staticmethod
    @final
    def _get_qual_name(func: Callable) -> str:
        """Build the normalized, fully qualified name for a function"""
        module = func.__module__
        normalized_module = module.removeprefix("scripts.")
        return f"{normalized_module}.{func.__qualname__}"

    @classmethod
    @abstractmethod
    def fire_triggers(cls, *args: Any, **kwargs: Any) -> None:
        """Execute registered functions for the given trigger. Should call `cls.invoke_funcs`"""
        raise NotImplementedError

    @classmethod
    @final
    def invoke_funcs_threaded(
        cls,
        funcs_to_execute: list[Callable],
        trigger_params: TriggerFuncParamsT,
    ) -> None:
        """Execute a list of trigger functions in background threads."""
        from flask import current_app

        params_dict = dict(trigger_params)
        app: MaestroFlask = current_app._get_current_object()  # type:ignore[attr-defined]

        for func in funcs_to_execute:
            thread = Thread(
                target=cls._invoke_func_with_param_handling,
                args=(func, params_dict, app),
                daemon=True,
            )
            thread.start()
            log.info(
                "Thread created for triggered script",
                function_name=func.__name__,
                trigger_type=cls.trigger_type,
                thread_name=thread.name,
            )

    @classmethod
    @final
    def invoke_funcs_sync(
        cls,
        funcs_to_execute: list[Callable],
        trigger_params: TriggerFuncParamsT,
        app: "MaestroFlask",
    ) -> None:
        """Execute a list of trigger functions synchronously (blocking)."""
        params_dict = dict(trigger_params)

        for func in funcs_to_execute:
            cls._invoke_func_with_param_handling(func, params_dict, app)
            log.info(
                "Executed triggered script synchronously",
                function_name=func.__name__,
                trigger_type=cls.trigger_type,
            )

    @classmethod
    @final
    def _invoke_func_with_param_handling(
        cls,
        func: Callable,
        params_dict: dict[str, Any],
        app: "MaestroFlask",
    ) -> None:
        """
        Wrapper logic to handle a varied number of optional args passed to a decorated function.
        Each function is executed in its own thread for concurrent execution.

        Both of these examples are valid depending on whether or not the state change arg is needed:
            @state_change_trigger(): ...
            @state_change_trigger(state_change: StateChangeEvent): ...

        trigger_params is a typeddict to enumerate the available valid arguments.
        """
        try:
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

            with app.app_context():
                func(*execution_args)
        except Exception:
            log.exception("Error executing triggered function", function_name=func.__name__)
