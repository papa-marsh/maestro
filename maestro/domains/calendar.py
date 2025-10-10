from datetime import datetime
from typing import Any

from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.domain import Domain


class Calendar(Entity):
    domain = Domain.CALENDAR

    def create_event(self, **kwargs: Any) -> None:
        self.perform_action("create_event", **kwargs)

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
            "get_events",
            start_date_time=start_date_time,
            end_date_time=end_date_time,
            duration=duration,
        )
