from calendar import Day, Month
from collections.abc import Callable
from datetime import timedelta
from enum import StrEnum, auto
from typing import TYPE_CHECKING, Any, TypedDict

from maestro.integrations.home_assistant.types import (
    EntityId,
    FiredEvent,
    NotifActionEvent,
    StateChangeEvent,
)

if TYPE_CHECKING:
    from maestro.triggers.hass import HassEvent
    from maestro.triggers.maestro import MaestroEvent
    from maestro.triggers.sun import SolarEvent


class TriggerType(StrEnum):
    STATE_CHANGE = auto()
    CRON = auto()
    EVENT_FIRED = auto()
    NOTIF_ACTION = auto()
    SUN = auto()
    MAESTRO = auto()
    HASS = auto()


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
        event_data: dict[str, Any]

    class FuncParams(TypedDict):
        event: FiredEvent


class NotifActionParams:
    class TriggerParams(TypedDict):
        action: str
        device_id: str | None

    class FuncParams(TypedDict):
        notif_action: NotifActionEvent


class SunParams:
    class TriggerParams(TypedDict):
        solar_event: "SolarEvent"
        offset: timedelta

    class FuncParams(TypedDict):
        pass


class MaestroParams:
    class TriggerParams(TypedDict):
        event: "MaestroEvent"

    class FuncParams(TypedDict):
        pass


class HassParams:
    class TriggerParams(TypedDict):
        event: "HassEvent"

    class FuncParams(TypedDict):
        pass


class TriggerRegistryEntry(TypedDict):
    func: Callable
    trigger_args: (
        StateChangeParams.TriggerParams
        | CronParams.TriggerParams
        | EventFiredParams.TriggerParams
        | NotifActionParams.TriggerParams
        | SunParams.TriggerParams
        | MaestroParams.TriggerParams
        | HassParams.TriggerParams
    )
    qual_name: str


TriggerFuncParamsT = (
    StateChangeParams.FuncParams
    | CronParams.FuncParams
    | EventFiredParams.FuncParams
    | NotifActionParams.FuncParams
    | SunParams.FuncParams
    | MaestroParams.FuncParams
    | HassParams.FuncParams
)
