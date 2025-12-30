from datetime import datetime
from typing import Any

from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.domain import Domain


class Calendar(Entity):
    domain = Domain.CALENDAR
    allow_set_state = False

    def create_event(self, **kwargs: Any) -> None:
        self.perform_action("create_event", **kwargs)

    def get_events(
        self,
        start_date_time: datetime | None = None,
        end_date_time: datetime | None = None,
        duration: dict[str, int] | None = None,
    ) -> dict[str, Any]:  # TODO: specific return type
        """
        Use only one of start/end_date_time or duration.
        Duration example: {"hours": 48} or {"days": 7}.
        """
        if duration and any([start_date_time, end_date_time]):
            raise ValueError("Action get_events accepts start/end dates or duration, but not both")

        kwargs: dict[str, Any]

        if duration:
            kwargs = {"duration": duration}
        elif start_date_time and end_date_time:
            kwargs = {"start_date_time": start_date_time, "end_date_time": end_date_time}
        else:
            raise ValueError("Action get_events must be passed start/end dates or duration")

        response = self.perform_action("get_events", **kwargs, response_expected=True)

        # TODO: actually parse the response into something useful

        return response
