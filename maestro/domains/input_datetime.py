from datetime import date, datetime, time

from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.domain import Domain


class InputDatetime(Entity):
    domain = Domain.INPUT_DATETIME

    def set_datetime(self, value: datetime) -> None:
        """Set the datetime value"""
        self.perform_action("set_datetime", datetime=value)

    def set_date(self, value: date) -> None:
        """Set the date value"""
        self.perform_action("set_datetime", date=value)

    def set_time(self, value: time) -> None:
        """Set the time value"""
        self.perform_action("set_datetime", time=value)

    def set_timestamp(self, value: int) -> None:
        """Set the value from a Unix timestamp"""
        self.perform_action("set_datetime", timestamp=value)
