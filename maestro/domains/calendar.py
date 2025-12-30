from datetime import datetime
from typing import Any

from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.domain import Domain
from maestro.integrations.home_assistant.types import EntityId


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
        calendars: list[EntityId] | None = None,
    ) -> dict[str, Any]:
        """
        Use only one of start/end_date_time or duration.
        Duration example: {"hours": 48} or {"days": 7}.
        Pass multiple calendar entity IDs to return events from multiple calendars.
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

        _entities, response = self.state_manager.hass_client.perform_action(
            domain=self.domain,
            action="get_events",
            entity_id=[str(c) for c in calendars] if calendars else str(self.id),
            **kwargs,
            response_expected=True,
        )

        return response or {}
