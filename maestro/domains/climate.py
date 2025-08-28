from enum import StrEnum, auto

from maestro.domains.domain import Domain
from maestro.domains.entity import Entity, EntityAttribute


class TeslaHVACMode(StrEnum):
    OFF = auto()
    HEAT_COOL = auto()


class ThermostatHVACMode(StrEnum):
    OFF = auto()
    COOL = auto()
    HEAT = auto()


class BathroomFloorHVACMode(StrEnum):
    AUTO = auto()
    HEAT = auto()


class TeslaFanMode(StrEnum):
    OFF = auto()
    BIOWEAPON = auto()


class ThermostatFanMode(StrEnum):
    ON = auto()
    AUTO = auto()
    DIFFUSE = auto()


HVACModeT = TeslaHVACMode | ThermostatHVACMode | BathroomFloorHVACMode
FanModeT = TeslaFanMode | ThermostatFanMode


class Climate(Entity):
    domain = Domain.CLIMATE

    current_temperature = EntityAttribute[int]()
    temperature = EntityAttribute[int]()
    hvac_modes = EntityAttribute[HVACModeT]()
    fan_mode = EntityAttribute[FanModeT]

    def turn_on(self) -> None:
        self.perform_action("turn_on")

    def turn_off(self) -> None:
        self.perform_action("turn_off")

    def toggle(self) -> None:
        self.perform_action("toggle")

    def set_fan_mode(self, mode: StrEnum) -> None:
        self.perform_action("set_fan_mode", mode=mode)

    def set_temperature(self, target_temp: int) -> None:
        self.perform_action("set_temperature", target_temp=target_temp)
