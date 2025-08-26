from datetime import datetime
from enum import StrEnum
from typing import Any

from maestro.domains.entity import Domain, Entity, EntityAttribute


class CalendarAction(StrEnum):
    CREATE_EVENT = "create_event"  # There's also a google.create_event (?)
    GET_EVENTS = "get_events"


class Calendar(Entity):
    domain = Domain.CALENDAR

    message = EntityAttribute[str]()
    all_day = EntityAttribute[bool]()
    start_time = EntityAttribute[datetime]()  # TODO datetime or str?
    end_time = EntityAttribute[datetime]()  # TODO datetime or str?
    location = EntityAttribute[str]()
    description = EntityAttribute[str]()

    def create_event(self, **kwargs: Any) -> None:
        self.perform_action(CalendarAction.CREATE_EVENT, **kwargs)

    def get_events(
        self,
        start_date_time: datetime | None,
        end_date_time: datetime | None,
        duration: dict[str, int] | None,
    ) -> None:
        """
        Use only one of end_date_time or duration.
        Duration example: {"hours": 48} or {"days": 7}.
        """
        self.perform_action(
            CalendarAction.GET_EVENTS,
            start_date_time=start_date_time,
            end_date_time=end_date_time,
            duration=duration,
        )
