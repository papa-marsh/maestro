from calendar import Day, Month
from collections.abc import Callable
from functools import wraps
from typing import Any
from uuid import uuid4

from apscheduler.schedulers.background import BackgroundScheduler  # type:ignore[import-untyped]
from apscheduler.triggers.cron import CronTrigger  # type:ignore[import-untyped]

from maestro.config import TIMEZONE
from maestro.triggers.trigger_manager import TriggerManager
from maestro.triggers.types import CronParams, TriggerRegistryEntry, TriggerType
from maestro.utils.logging import log

SCHEDULER_JOB_PREFIX = "cron_trigger_job_"


class CronTriggerManager(TriggerManager):
    trigger_type = TriggerType.CRON

    @classmethod
    def register_jobs(cls, scheduler: BackgroundScheduler) -> None:
        for existing_job in scheduler.get_jobs():
            if SCHEDULER_JOB_PREFIX in existing_job.id:
                scheduler.remove_job(existing_job.id)

        for trigger_obj, trigger_entries in cls.get_registry()[cls.trigger_type].items():
            for trigger_entry in trigger_entries:
                scheduler.add_job(
                    func=trigger_entry["func"],
                    trigger=trigger_obj,
                    id=SCHEDULER_JOB_PREFIX + str(uuid4())[:8],
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

    Available function params:
        `None`
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            log.info(
                "Thread created for triggered script",
                function_name=func.__name__,
                trigger_type=TriggerType.CRON,
            )
            return func(*args, **kwargs)

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
        trigger_args = CronParams.TriggerParams(
            pattern=pattern,
            minute=minute,
            hour=hour,
            day_of_month=_day_of_month,
            month=_month,
            day_of_week=_day_of_week,
        )
        registry_entry = TriggerRegistryEntry(
            func=wrapper,
            trigger_args=trigger_args,
            qual_name=TriggerManager._get_qual_name(func),
        )

        CronTriggerManager.register_function(
            trigger_type=TriggerType.CRON,
            registry_key=trigger,
            registry_entry=registry_entry,
        )

        return wrapper

    return decorator
