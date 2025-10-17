from collections.abc import Callable
from functools import wraps
from typing import Any, cast

from structlog.stdlib import get_logger

from maestro.integrations.home_assistant.types import NotifActionEvent
from maestro.triggers.trigger_manager import TriggerManager
from maestro.triggers.types import NotifActionParams, TriggerRegistryEntry, TriggerType

log = get_logger()


class NotifActionTriggerManager(TriggerManager):
    trigger_type = TriggerType.NOTIF_ACTION

    @classmethod
    def fire_triggers(cls, notif_action: NotifActionEvent) -> None:
        """Execute all registered notif action functions for the given notif action."""
        func_params = NotifActionParams.FuncParams(notif_action=notif_action)
        registry = cls.get_registry(registry_union=True)
        funcs_to_execute = []

        for registry_entry in registry[cls.trigger_type].get(notif_action.name, []):
            trigger_params = cast(NotifActionParams.TriggerParams, registry_entry["trigger_args"])
            device_id = trigger_params["device_id"]

            if device_id is not None and notif_action.device_id != device_id:
                continue

            funcs_to_execute.append(registry_entry["func"])

        cls.invoke_funcs_threaded(funcs_to_execute, func_params)


def notif_action_trigger(
    action: str,
    device_id: str | None = None,
) -> Callable:
    """
    Decorator to register a function as a notification action trigger for the specified entity.

    Available function params:
        `notif_action: NotifActionEvent`
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        trigger_args = NotifActionParams.TriggerParams(action=action, device_id=device_id)
        registry_entry = TriggerRegistryEntry(
            func=wrapper,
            trigger_args=trigger_args,
            qual_name=TriggerManager._get_qual_name(func),
        )

        NotifActionTriggerManager.register_function(
            trigger_type=TriggerType.NOTIF_ACTION,
            registry_key=action,
            registry_entry=registry_entry,
        )

        return wrapper

    return decorator
