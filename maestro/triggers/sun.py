from collections.abc import Callable
from datetime import timedelta
from enum import StrEnum
from functools import wraps
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler  # type:ignore[import-untyped]
from apscheduler.triggers.date import DateTrigger  # type:ignore[import-untyped]
from structlog.stdlib import get_logger

from maestro.config import TIMEZONE
from maestro.registry import sun
from maestro.triggers.trigger_manager import TriggerManager
from maestro.triggers.types import SunParams, TriggerRegistryEntry, TriggerType
from maestro.utils.dates import local_now

log = get_logger()


class SolarEvent(StrEnum):
    DAWN = "next_dawn"
    DUSK = "next_dusk"
    SOLAR_MIDNIGHT = "next_midnight"
    SOLAR_NOON = "next_noon"
    SUNRISE = "next_rising"
    SUNSET = "next_setting"


class SunTriggerManager(TriggerManager):
    trigger_type = TriggerType.SUN
    scheduler: BackgroundScheduler

    @classmethod
    def register_jobs(cls, scheduler: BackgroundScheduler) -> None:
        cls.scheduler = scheduler
        for trigger_obj, trigger_entries in cls.get_registry()[cls.trigger_type].items():
            for trigger_entry in trigger_entries:
                cls.scheduler.add_job(
                    func=trigger_entry["func"],
                    trigger=trigger_obj,
                )

    @classmethod
    def fire_triggers(cls) -> None:
        """Not used for cron triggers"""
        raise NotImplementedError

    @classmethod
    def build_date_trigger(
        cls,
        solar_event: SolarEvent,
        offset: timedelta,
        rescheduling: bool,
    ) -> DateTrigger:
        solar_event_datetime = getattr(sun.sun, solar_event)

        # Avoid infinite trigger loops that can caused by offsets when a trigger fires and is
        # rescheduled. (eg. if <sunset - 1 hour> fires, it will try to reschedule based on the
        # next sunset time, which is still 1 hour from now).
        if rescheduling and solar_event_datetime < local_now() + timedelta(hours=20):
            solar_event_datetime += timedelta(hours=24)

        next_run = solar_event_datetime + offset
        if next_run <= local_now():
            log.info(
                "Sun trigger offset yields next run in the past, adding 24h to next run time",
                now=local_now(),
                next_run=next_run,
            )
            next_run += timedelta(days=1)

        return DateTrigger(run_date=next_run, timezone=TIMEZONE)


def sun_trigger(solar_event: SolarEvent, offset: timedelta = timedelta()) -> Callable:
    """
    Decorator to register a function as a sun-based trigger for the specified cron pattern.
    Note sun triggers require that the `sun.sun` entity has been populated in maestro/registry.
    Eg. Open the blinds 1h before sunrise:
        `@sun_trigger(event=SunEvent.SUNRISE, offset=timedelta(hours=-1))

    Available function params:
        `None`
    """
    if not (timedelta(hours=-12) < offset < timedelta(hours=12)):
        raise ValueError("Sun trigger offset length must be 12 hours or less")

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            log.info(
                "Thread created for triggered script",
                function_name=func.__name__,
                trigger_type=TriggerType.SUN,
            )

            next_trigger = SunTriggerManager.build_date_trigger(
                solar_event=solar_event,
                offset=offset,
                rescheduling=True,
            )
            SunTriggerManager.scheduler.add_job(func=wrapper, trigger=next_trigger)

            return func(*args, **kwargs)

        trigger = SunTriggerManager.build_date_trigger(
            solar_event=solar_event,
            offset=offset,
            rescheduling=False,
        )

        trigger_args = SunParams.TriggerParams(solar_event=solar_event, offset=offset)
        registry_entry = TriggerRegistryEntry(func=wrapper, trigger_args=trigger_args)

        SunTriggerManager.register_function(
            trigger_type=TriggerType.SUN,
            registry_key=trigger,
            registry_entry=registry_entry,
        )

        return wrapper

    return decorator
