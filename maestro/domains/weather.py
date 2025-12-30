from enum import StrEnum, auto

from maestro.domains.entity import Entity
from maestro.integrations.home_assistant.domain import Domain


class ForecastType(StrEnum):
    HOURLY = auto()
    TWICE_DAILY = auto()
    DAILY = auto()


class Weather(Entity):
    domain = Domain.WEATHER
    allow_set_state = False

    def get_forecasts(self, type: ForecastType) -> dict:  # TODO: specific return type
        response = self.perform_action(
            "get_forecasts",
            type=type,
            response_expected=True,
        )

        # TODO: actually parse the response into something useful

        return response
