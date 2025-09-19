from calendar import Day, Month
from collections.abc import Callable
from functools import wraps
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler  # type:ignore[import-untyped]
from apscheduler.triggers.cron import CronTrigger  # type:ignore[import-untyped]
from structlog.stdlib import get_logger

from maestro.config import TIMEZONE
from maestro.triggers.trigger_manager import (
    CronTriggerArgs,
    TriggerManager,
    TriggerRegistryEntry,
    TriggerType,
)

log = get_logger()


class CronTriggerManager(TriggerManager):
    trigger_type = TriggerType.CRON

    @classmethod
    def register_jobs(cls, scheduler: BackgroundScheduler) -> None:
        for trigger_obj, trigger_entries in cls.get_registry()[cls.trigger_type].items():
            for trigger_entry in trigger_entries:
                scheduler.add_job(
                    func=trigger_entry["func"],
                    trigger=trigger_obj,
                )

    @classmethod
    def fire_triggers(cls) -> None:
        """Not used for cron triggers"""
        raise NotImplementedError


def cron_trigger(
    pattern: str | None = None,
    minute: int | str | None = None,
    hour: int | str | None = None,
    day_of_month: int | list[int] | str | None = None,
    month: int | Month | list[int | Month] | str | None = None,
    day_of_week: int | Day | list[int | Day] | str | None = None,
) -> Callable:
    """
    Decorator to register a function as a time-based trigger for the specified cron pattern.
    For parameter format, see:
        https://apscheduler.readthedocs.io/en/3.x/modules/triggers/cron.html#module-apscheduler.triggers.cron
    """

    def decorator(func: Callable) -> Callable:
        if pattern is not None and any(
            arg is not None for arg in [minute, hour, day_of_month, month, day_of_week]
        ):
            raise ValueError("Cron triggers accept a pattern or individual args, but not both")

        _day_of_month = (
            ",".join(str(d) for d in day_of_month)
            if isinstance(day_of_month, list)
            else day_of_month
        )
        _month = month if not isinstance(month, list) else ",".join(str(m) for m in month)
        _day_of_week = (
            day_of_week
            if not isinstance(day_of_week, list)
            else ",".join(str(d) for d in day_of_week)
        )

        trigger = (
            CronTrigger.from_crontab(expr=pattern, timezone=TIMEZONE)
            if pattern is not None
            else CronTrigger(
                minute=minute,
                hour=hour,
                day=_day_of_month,
                month=_month,
                day_of_week=_day_of_week,
                timezone=TIMEZONE,
            )
        )
        trigger_args = CronTriggerArgs(
            pattern=pattern,
            minute=minute,
            hour=hour,
            day_of_month=_day_of_month,
            month=_month,
            day_of_week=_day_of_week,
        )
        registry_entry = TriggerRegistryEntry(
            func=func,
            trigger_args=trigger_args,
        )

        CronTriggerManager.register_function(
            trigger_type=TriggerType.CRON,
            registry_key=trigger,
            registry_entry=registry_entry,
        )

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        return wrapper

    return decorator
