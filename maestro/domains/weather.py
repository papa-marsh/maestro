from enum import StrEnum, auto

from maestro.domains.entity import Entity, EntityAttribute
from maestro.integrations.home_assistant.types import Domain


class ForecastType(StrEnum):
    HOURLY = auto()
    TWICE_DAILY = auto()
    DAILY = auto()


class Weather(Entity):
    domain = Domain.WEATHER

    temperature = EntityAttribute(int)
    apparent_temperature = EntityAttribute(int)
    dew_point = EntityAttribute(int)
    temperature_unit = EntityAttribute(str)
    humidity = EntityAttribute(int)
    ozone = EntityAttribute(float)
    cloud_coverage = EntityAttribute(int)
    pressure = EntityAttribute(float)
    pressure_unit = EntityAttribute(str)
    wind_bearing = EntityAttribute(int)
    wind_gust_speed = EntityAttribute(float)
    wind_speed = EntityAttribute(float)
    wind_speed_unit = EntityAttribute(str)
    visibility = EntityAttribute(int)
    visibility_unit = EntityAttribute(str)
    precipitation_unit = EntityAttribute(str)

    def get_forecasts(self, type: ForecastType) -> None:
        self.perform_action("get_forecasts", type=type)
