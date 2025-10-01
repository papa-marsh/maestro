from calendar import Day, Month
from collections.abc import Callable
from enum import StrEnum, auto
from typing import TypedDict

from maestro.integrations.home_assistant.types import EntityId, FiredEvent, StateChangeEvent


class TriggerType(StrEnum):
    STATE_CHANGE = auto()
    CRON = auto()
    EVENT_FIRED = auto()


class StateChangeParams:
    class TriggerParams(TypedDict):
        entity_id: EntityId
        from_state: str | None
        to_state: str | None

    class FuncParams(TypedDict):
        state_change: StateChangeEvent


class CronParams:
    class TriggerParams(TypedDict):
        pattern: str | None
        minute: int | str | None
        hour: int | str | None
        day_of_month: int | list[int] | str | None
        month: int | Month | list[int | Month] | str | None
        day_of_week: int | Day | list[int | Day] | str | None

    class FuncParams(TypedDict):
        pass


class EventFiredParams:
    class TriggerParams(TypedDict):
        event_type: str
        user_id: str | None

    class FuncParams(TypedDict):
        event: FiredEvent


class TriggerRegistryEntry(TypedDict):
    func: Callable
    trigger_args: (
        StateChangeParams.TriggerParams | CronParams.TriggerParams | EventFiredParams.TriggerParams
    )


TriggerFuncParamsT = (
    StateChangeParams.FuncParams | CronParams.FuncParams | EventFiredParams.FuncParams
)
