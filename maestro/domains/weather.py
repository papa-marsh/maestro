from enum import StrEnum, auto

from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.types import Domain


class ForecastType(StrEnum):
    HOURLY = auto()
    TWICE_DAILY = auto()
    DAILY = auto()


class Weather(Entity):
    domain = Domain.WEATHER

    def get_forecasts(self, type: ForecastType) -> None:
        self.perform_action("get_forecasts", type=type)
